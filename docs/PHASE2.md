# Phase 2 ML Pipeline

Phase 2 adds the local ML tooling for filtering, embedding, indexing, and searching captured MemoryOS data.

## Prerequisites

Install the ML dependencies:

```sh
python3 -m pip install -r ml/requirements.txt
```

The current local environment already has `numpy`, `pandas`, `sklearn`, `joblib`, and `torch`. It still needs `sentence-transformers` and `faiss-cpu` for the full semantic path. Until then, the index builder can use a TF-IDF fallback.

## 2.1 Noise Classifier

Label captures:

```sh
python3 ml/train/label_captures.py --limit 500
```

Train the classifier:

```sh
python3 ml/train/train_noise.py
```

Apply it to unlabeled captures:

```sh
python3 ml/serve/classify_noise.py --limit 1000
```

Output:

```text
ml/models/noise_classifier.joblib
```

## 2.2 Embedding Model Fine-Tuning

Generate positive and negative pairs:

```sh
python3 ml/train/generate_pairs.py --max-pairs 2000
```

Fine-tune the embedder:

```sh
python3 ml/train/finetune_embedder.py \
  --base-model sentence-transformers/all-MiniLM-L6-v2 \
  --output ml/models/memoryos-embedder
```

Output:

```text
ml/data/processed/embedding_pairs.jsonl
ml/models/memoryos-embedder/
```

## 2.3 FAISS Vector Index

Build the search index:

```sh
python3 ml/train/build_index.py --backend sentence --model ml/models/memoryos-embedder
```

For local smoke tests without `sentence-transformers` or FAISS:

```sh
python3 ml/train/build_index.py --backend tfidf
```

Outputs:

```text
ml/models/search_index.joblib
ml/models/memoryos.faiss
ml/models/memoryos_faiss_ids.json
```

`memoryos.faiss` is created when `faiss-cpu` is installed. Otherwise the artifact uses a scikit-learn nearest-neighbor fallback.

Search from the CLI:

```sh
python3 ml/serve/search.py "that article about attention mechanisms I read last week"
```

## 2.4 Temporal Re-Ranker

The re-ranker trains from `search_clicks`, which will be populated by the web UI in Phase 4. Once click data exists:

```sh
python3 ml/train/train_reranker.py
```

Output:

```text
ml/models/temporal_reranker.joblib
```

## Current Completion Notes

The Phase 2 code is complete, but model artifacts require real captured data:

- Noise classifier needs at least 20 labeled rows, with both `0=keep` and `1=noise`.
- Embedding fine-tuning needs enough non-noise captures to generate useful pairs.
- FAISS index creation needs `sentence-transformers` and `faiss-cpu` installed.
- Re-ranker training needs search click logs from the future UI.
