# distilbert-sst2

Fine-tuned `distilbert/distilbert-base-uncased` on `stanfordnlp/sst2` for binary sentiment classification.

| | |
|---|---|
| Train examples | 67,349 |
| Eval examples (validation) | 872 |
| Epochs | 1 |
| Learning rate | 3e-05 |
| Batch size | 32 |
| Max sequence length | 64 |
| Seed | 42 |

## Results on `validation`

| Metric | Value |
|---|---|
| Accuracy | 0.9037 |
| Macro F1 | 0.9035 |
| ROC AUC | 0.9698 |
| Train time (s) | 5538.0 |

Produced by `scripts/train_sentiment.py`.
