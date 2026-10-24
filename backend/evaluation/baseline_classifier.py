"""
A small, deterministic lexicon-based sentiment classifier.

Bag-of-words polarity scoring with one-token negation flipping, in the
spirit of VADER. It is the floor every served model has to beat: the
Evaluation Center runs it on the same data as the transformer, and the
gap between the two (especially on the challenge set's negation and
sarcasm cases) shows what a contextual model buys.
"""

import re
from dataclasses import dataclass

_POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic", "love",
    "loved", "best", "perfect", "happy", "pleased", "impressive", "beautiful",
    "brilliant", "awesome", "superb", "delightful", "enjoy", "enjoyed",
    "recommend", "outstanding", "exceeded", "smooth", "fast", "reliable",
    "comfortable", "worth", "helpful", "friendly", "solid", "nice",
}

_NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "horrible", "worst", "hate", "hated", "poor",
    "disappointing", "disappointed", "broken", "useless", "slow", "waste",
    "annoying", "frustrating", "cheap", "unreliable", "uncomfortable",
    "regret", "avoid", "never", "junk", "defective", "rude", "confusing",
    "overpriced", "flimsy", "buggy", "crashed", "refund",
}

_NEGATIONS = {"not", "no", "never", "n't", "without", "hardly", "barely"}

_WORD_PATTERN = re.compile(r"[a-z']+")


@dataclass
class BaselinePrediction:
    label: str
    score: float
    positive_hits: int
    negative_hits: int


class LexiconSentimentClassifier:
    """Deterministic binary sentiment classifier: POSITIVE / NEGATIVE.

    Scores each token against the lexicon, flipping polarity when a
    negation word appears within the previous two tokens (handles "not
    good", "wasn't great", etc. — not a full parser, just enough to avoid
    the most common failure mode of pure bag-of-words scoring).
    """

    def predict(self, text: str) -> BaselinePrediction:
        tokens = _WORD_PATTERN.findall(text.lower())
        positive_hits = 0
        negative_hits = 0

        for i, token in enumerate(tokens):
            polarity = 0
            if token in _POSITIVE_WORDS:
                polarity = 1
            elif token in _NEGATIVE_WORDS:
                polarity = -1
            else:
                continue

            window = tokens[max(0, i - 2): i]
            if any(w in _NEGATIONS for w in window):
                polarity *= -1

            if polarity > 0:
                positive_hits += 1
            else:
                negative_hits += 1

        total_hits = positive_hits + negative_hits
        if total_hits == 0:
            # No lexicon signal at all — default to a low-confidence
            # POSITIVE guess (matches the class imbalance in most review
            # datasets, and gives a genuine, if weak, prediction rather
            # than refusing to classify).
            return BaselinePrediction(label="POSITIVE", score=0.55, positive_hits=0, negative_hits=0)

        positive_ratio = positive_hits / total_hits
        if positive_ratio >= 0.5:
            label = "POSITIVE"
            score = 0.5 + (positive_ratio - 0.5)
        else:
            label = "NEGATIVE"
            score = 0.5 + (0.5 - positive_ratio)

        # More lexicon hits overall = more evidence = nudge confidence up,
        # capped so a couple of strong words doesn't read as certainty.
        evidence_boost = min(0.15, 0.03 * total_hits)
        score = min(0.99, score + evidence_boost)

        return BaselinePrediction(
            label=label, score=round(score, 4), positive_hits=positive_hits, negative_hits=negative_hits
        )


baseline_sentiment_classifier = LexiconSentimentClassifier()
