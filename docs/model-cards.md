# Model Cards

Every task is served by a public Hugging Face checkpoint, except sentiment, which
prefers a checkpoint fine-tuned in this repo. Weights download on first use and are
cached in `MODEL_CACHE_DIR`.

| Task | Checkpoint | Architecture | Size | Output | License |
|---|---|---|---|---|---|
| Sentiment | `artifacts/models/distilbert-sst2` (ours) → fallback `distilbert/distilbert-base-uncased-finetuned-sst-2-english` | DistilBERT | 268MB | NEGATIVE / POSITIVE | Apache-2.0 |
| Emotion | `j-hartmann/emotion-english-distilroberta-base` | DistilRoBERTa | 329MB | anger, disgust, fear, joy, neutral, sadness, surprise | not declared on the card — check before commercial use |
| Toxicity | `unitary/toxic-bert` | BERT | 438MB | multi-label: toxic, severe_toxic, obscene, threat, insult, identity_hate | Apache-2.0 |
| Topic | `cardiffnlp/tweet-topic-21-multi` | RoBERTa | 499MB | multi-label over 19 topics | MIT |
| Language ID | `papluca/xlm-roberta-base-language-detection` | XLM-RoBERTa | 1.1GB | 20 ISO-639-1 codes | MIT |
| Zero-shot | `MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33` | DeBERTa-v3 xsmall (NLI) | 142MB | any labels supplied at request time | MIT |
| Similarity / embeddings | `sentence-transformers/all-MiniLM-L6-v2` | MiniLM-L6 bi-encoder | 91MB | 384-d normalised vector / cosine score | Apache-2.0 |

## Sentiment — `distilbert-sst2` (trained here)

- **Base model:** `distilbert/distilbert-base-uncased`
- **Data:** SST-2 (`stanfordnlp/sst2`): the full 67,349-sentence train split, evaluated
  on the 872-sentence validation split. The GLUE test split has no public labels.
- **Recipe:** 1 epoch, AdamW, lr 3e-5, batch 32, linear schedule with 6% warm-up, weight
  decay 0.01, max length 64, seed 42. See `reports/distilbert-sst2/training_config.json`.
- **Results (SST-2 validation):** accuracy **90.37%**, macro-F1 0.904, ROC-AUC 0.970.
  The public checkpoint scores 91.06%. Comparison: `reports/sentiment_results.md`;
  failure analysis: `reports/sentiment_error_analysis.md`.
- **Limitations:** SST-2 is single sentences from movie reviews. Expect lower accuracy on
  long, multi-topic or domain-specific text (product reviews, support tickets), and on
  sarcasm, which the challenge set probes directly. Labels are binary, so neutral or
  mixed text is forced into one class.
- **Reproduce:** `python scripts/train_sentiment.py`. This run took 92 minutes on an
  Intel Core Ultra 9 185H laptop CPU (2,105 steps). A single GPU takes a few minutes.

## Known limitations of the public checkpoints

- **Emotion:** English only, trained on a mix of social-media, dialogue and review
  datasets. Single-label: a sentence that is both angry and sad gets one label.
- **Toxicity:** trained on Jigsaw Wikipedia comments, and it carries the identity-term
  bias that the Jigsaw Unintended Bias work documents. Measured here: "I am a gay man."
  scores 0.22 `toxic` and "I am a black person." 0.23, against 0.001 for "I am a tall
  man.". Both are under the 0.5 flag threshold, but about 200× the neutral baseline.
  Don't use it as the only signal for moderation decisions.
- **Topic:** trained on tweets, so long formal text (news articles, reports) is out of
  domain.
- **Language ID:** 20 languages only. Very short inputs are unreliable: "ok", "no" and
  "hello" all come back as Swahili (`sw`, 0.32–0.70 confidence). A full sentence is
  identified at >0.99. Gate on input length, or treat < 3 words as "unknown".
- **Zero-shot:** cost grows with the number of labels, because each label is a separate
  NLI hypothesis. All hypotheses go through one batched forward pass: ~83ms for 8 labels
  on the benchmark laptop CPU, vs ~325ms with the pipeline's default one-pass-per-label.
  The xsmall model trades accuracy for that speed; swap in
  `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` for better accuracy at higher latency.
  Phrase labels as natural-language categories ("billing problem") rather
  than codes.
- **Embeddings:** inputs longer than 256 word pieces are truncated. English-centric.
