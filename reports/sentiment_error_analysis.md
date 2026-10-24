# Sentiment error analysis — challenge set

Every challenge-set sentence that at least one system gets wrong. Systems: our
fine-tuned `distilbert-sst2`, the public `distilbert-base-uncased-finetuned-sst-2-english`,
and the lexicon baseline. ✅ = correct, ❌ = wrong (our model's confidence in brackets).

| Gold | Ours | Public | Lexicon | Sentence |
|---|---|---|---|---|
| NEG | ❌ (0.60) | ✅ | ❌ | I can't say this was a pleasant experience. |
| POS | ❌ (0.50) | ✅ | ✅ | This never crashed once during the entire trip. |
| POS | ✅ | ✅ | ❌ | I wasn't disappointed, it worked better than expected. |
| POS | ❌ (0.98) | ❌ | ❌ | Nothing about this felt cheap or unreliable. |
| NEG | ❌ (0.98) | ❌ | ❌ | Oh great, another update that broke the app completely. |
| NEG | ✅ | ✅ | ❌ | Wonderful, my order arrived a month late and damaged. |
| NEG | ❌ (0.99) | ❌ | ❌ | Love how it stopped working after just two days. Fantastic. |
| NEG | ❌ (0.79) | ❌ | ❌ | Sure, 'excellent' service — three hours on hold and no answer. |
| NEG | ❌ (0.97) | ❌ | ❌ | Great, the one time I need support, no one responds. Perfect. |
| NEG | ✅ | ✅ | ❌ | The design is beautiful but it broke after one use, so overall bad. |
| NEG | ❌ (0.61) | ✅ | ✅ | Good packaging, terrible product — I'd still avoid buying this. |
| NEG | ❌ (0.55) | ❌ | ✅ | Never again. |

## Findings

1. **Sarcasm is the dominant failure, and it fails confidently.** All three systems miss
   all four sarcastic sentences, and the transformers do so at 0.79–0.99 confidence.
   SST-2 movie-review sentences contain little sarcasm, so the models learned "great",
   "love" and "perfect" as strong positive cues. Fixing this needs sarcasm-bearing
   training data (e.g. product reviews or iSarcasm), not a different architecture.
2. **Double negation** ("Nothing about this felt cheap or unreliable") defeats all
   three. The transformers read the negative adjectives; the lexicon's one-token
   negation window can't reach them.
3. **Ours vs the public checkpoint**: the public model, trained longer, recovers three
   negation and contrast cases that ours misses at low confidence (0.50–0.61). Those
   are exactly the borderline cases a second epoch or a larger max length typically
   fixes. On SST-2 validation the gap is 0.7 points (90.37% vs 91.06%).
4. **Why the lexicon looks good here and not on SST-2**: the challenge set was written
   alongside the lexicon, so almost every sentiment word in it is one the lexicon
   knows. On unseen SST-2 text the lexicon drops to 55.7% (near chance), while the
   transformers stay above 90%. The challenge set is a diagnostic for specific
   phenomena, not a benchmark.

Reproduce: `python scripts/evaluate_sentiment.py` (aggregate numbers in
`sentiment_results.md`).
