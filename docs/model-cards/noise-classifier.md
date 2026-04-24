# Model Card: Noise Classifier

## Purpose

Classify captured text as useful content or noise.

Labels:

- `0`: keep
- `1`: noise

## Inputs

Capture metadata and text:

- app name
- window title
- source type
- content text

## Training Data

Manual labels from `ml/train/label_captures.py`.

Recommended minimum:

- 500-1000 labeled captures for a useful first version.
- Include both keep and noise examples.

## Model

Current implementation:

- TF-IDF vectorizer
- Logistic regression classifier

Artifact:

```text
ml/models/noise_classifier.joblib
```

## Metrics

Primary metric:

- Precision on the keep class.

Reason:

False negatives are costly because they discard useful personal memory.

## Limitations

- Quality depends on representative manual labels.
- App-specific UI noise may require periodic relabeling.
- The baseline is intentionally simple and inspectable.
