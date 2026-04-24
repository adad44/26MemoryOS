from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

from .config import MODEL_DIR, ensure_dirs
from .features import capture_documents, result_snippet


INDEX_ARTIFACT_PATH = MODEL_DIR / "search_index.joblib"
FAISS_INDEX_PATH = MODEL_DIR / "memoryos.faiss"
FAISS_MAPPING_PATH = MODEL_DIR / "memoryos_faiss_ids.json"
DEFAULT_EMBEDDER = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class SearchHit:
    capture_id: int
    score: float
    rank: int
    row: sqlite3.Row


def _load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. Run: python3 -m pip install -r ml/requirements.txt"
        ) from exc
    return SentenceTransformer(model_name)


def _try_import_faiss():
    try:
        import faiss  # type: ignore

        return faiss
    except ImportError:
        return None


def build_index(
    rows: List[sqlite3.Row],
    model_name: str = DEFAULT_EMBEDDER,
    backend: str = "auto",
) -> Path:
    if not rows:
        raise ValueError("No captures available for indexing.")

    ensure_dirs()
    capture_ids = [int(row["id"]) for row in rows]
    docs = capture_documents(rows)

    use_sentence = backend == "sentence" or backend == "auto"
    if use_sentence:
        try:
            model = _load_sentence_transformer(model_name)
            embeddings = model.encode(
                docs,
                batch_size=32,
                show_progress_bar=True,
                normalize_embeddings=True,
            ).astype("float32")
            artifact = {
                "backend": "sentence-transformers",
                "model_name": model_name,
                "capture_ids": capture_ids,
                "documents": docs,
                "shape": embeddings.shape,
            }
            faiss = _try_import_faiss()
            if faiss is not None:
                index = faiss.IndexFlatIP(embeddings.shape[1])
                index.add(embeddings)
                faiss.write_index(index, str(FAISS_INDEX_PATH))
                FAISS_MAPPING_PATH.write_text(json.dumps(capture_ids, indent=2))
                artifact["faiss_index_path"] = str(FAISS_INDEX_PATH)
                artifact["faiss_mapping_path"] = str(FAISS_MAPPING_PATH)
            else:
                nn = NearestNeighbors(metric="cosine")
                nn.fit(embeddings)
                artifact["nearest_neighbors"] = nn
                artifact["embeddings"] = embeddings
            joblib.dump(artifact, INDEX_ARTIFACT_PATH)
            return INDEX_ARTIFACT_PATH
        except RuntimeError:
            if backend == "sentence":
                raise

    vectorizer = TfidfVectorizer(
        max_features=30_000,
        ngram_range=(1, 2),
        min_df=1,
        strip_accents="unicode",
    )
    matrix = vectorizer.fit_transform(docs)
    nn = NearestNeighbors(metric="cosine")
    nn.fit(matrix)
    artifact = {
        "backend": "tfidf",
        "capture_ids": capture_ids,
        "documents": docs,
        "vectorizer": vectorizer,
        "nearest_neighbors": nn,
        "matrix": matrix,
    }
    joblib.dump(artifact, INDEX_ARTIFACT_PATH)
    return INDEX_ARTIFACT_PATH


def search_index(
    query: str,
    rows_by_id: dict[int, sqlite3.Row],
    top_k: int = 10,
    artifact_path: Path = INDEX_ARTIFACT_PATH,
) -> List[SearchHit]:
    artifact = joblib.load(artifact_path)
    capture_ids = [int(value) for value in artifact["capture_ids"]]
    top_k = min(top_k, len(capture_ids))

    if artifact["backend"] == "sentence-transformers":
        model = _load_sentence_transformer(artifact["model_name"])
        query_vec = model.encode([query], normalize_embeddings=True).astype("float32")
        if "faiss_index_path" in artifact:
            faiss = _try_import_faiss()
            if faiss is None:
                raise RuntimeError("This index was built with FAISS, but faiss is not installed.")
            index = faiss.read_index(artifact["faiss_index_path"])
            scores, positions = index.search(query_vec, top_k)
            pairs = [(int(pos), float(score)) for pos, score in zip(positions[0], scores[0]) if pos >= 0]
        else:
            distances, positions = artifact["nearest_neighbors"].kneighbors(query_vec, n_neighbors=top_k)
            pairs = [(int(pos), 1.0 - float(distance)) for pos, distance in zip(positions[0], distances[0])]
    else:
        query_vec = artifact["vectorizer"].transform([query])
        distances, positions = artifact["nearest_neighbors"].kneighbors(query_vec, n_neighbors=top_k)
        # NearestNeighbors cosine distances can be flat for tiny datasets; compute exact cosine for clarity.
        exact_scores = cosine_similarity(query_vec, artifact["matrix"][positions[0]])[0]
        pairs = [(int(pos), float(score)) for pos, score in zip(positions[0], exact_scores)]

    hits: List[SearchHit] = []
    for rank, (position, score) in enumerate(pairs, start=1):
        capture_id = capture_ids[position]
        row = rows_by_id.get(capture_id)
        if row is None:
            continue
        hits.append(SearchHit(capture_id=capture_id, score=score, rank=rank, row=row))
    return hits


def format_hit(hit: SearchHit) -> str:
    row = hit.row
    title = row["window_title"] or row["url"] or row["file_path"] or "(untitled)"
    return (
        f"{hit.rank}. [{hit.score:.3f}] {title}\n"
        f"   id={hit.capture_id} app={row['app_name']} source={row['source_type']} time={row['timestamp']}\n"
        f"   {result_snippet(row['content'])}"
    )
