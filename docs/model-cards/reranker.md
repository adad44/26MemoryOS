# Model Card: Temporal Re-ranker

## Purpose

Re-rank initial search results using similarity, recency, and behavioral signals.

## Inputs

Features:

- vector similarity
- hours since capture
- app match
- title token match
- content length

## Training Data

Click logs from the web UI:

```text
search_clicks
```

Generated through:

```text
POST /click
```

## Model

Current implementation:

- GradientBoostingClassifier

Artifact:

```text
ml/models/temporal_reranker.joblib
```

## Limitations

- Cannot train until search click logs exist.
- Click behavior can encode habits that are not always relevance.
- Should be treated as v2 ranking polish, not a blocker for first search.
