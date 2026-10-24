# Sentiment results

| System | SST-2 val accuracy | SST-2 val macro-F1 | Challenge set accuracy | Challenge set macro-F1 |
|---|---|---|---|---|
| lexicon-baseline-v1 | 55.73% | 0.444 | 81.25% | 0.812 |
| distilbert/distilbert-base-uncased-finetuned-sst-2-english | 91.06% | 0.910 | 87.50% | 0.874 |
| distilbert-sst2 (ours) | 90.37% | 0.903 | 81.25% | 0.812 |

Reproduce: `python scripts/evaluate_sentiment.py`
