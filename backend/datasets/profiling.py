"""
Dataset profiling: descriptive statistics computed directly from the
records — token counts, vocabulary size, sequence-length distribution,
label distribution, and top word frequencies.
"""

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from backend.datasets.validation import DatasetRecordInput

_WORD_PATTERN = re.compile(r"[a-z']+")

# Extremely common English function words excluded from "top words" so the
# frequency list is actually informative rather than dominated by "the",
# "a", "is". Deliberately small and English-specific — worth revisiting if
# this dataset platform needs to profile multilingual corpora.
_STOPWORDS = {
    "the", "a", "an", "is", "it", "to", "of", "and", "in", "was", "for",
    "on", "with", "this", "that", "i", "you", "but", "or", "as", "at",
    "be", "are", "not", "have", "has", "had", "so", "if", "my", "me",
}


@dataclass
class SequenceLengthStats:
    min_words: int
    max_words: int
    mean_words: float
    median_words: float


@dataclass
class DatasetProfile:
    total_records: int
    vocabulary_size: int
    sequence_length: SequenceLengthStats
    label_distribution: Dict[str, int]
    top_words: List[Tuple[str, int]] = field(default_factory=list)


class DatasetProfiler:
    def profile(self, records: List[DatasetRecordInput], top_n_words: int = 20) -> DatasetProfile:
        word_counts_per_record = [len(r.text.split()) for r in records]
        vocabulary: Counter = Counter()
        for r in records:
            tokens = _WORD_PATTERN.findall(r.text.lower())
            vocabulary.update(t for t in tokens if t not in _STOPWORDS)

        top_words = vocabulary.most_common(top_n_words)
        label_distribution = dict(Counter(r.label for r in records if r.label))

        if word_counts_per_record:
            seq_stats = SequenceLengthStats(
                min_words=min(word_counts_per_record),
                max_words=max(word_counts_per_record),
                mean_words=round(statistics.mean(word_counts_per_record), 2),
                median_words=round(statistics.median(word_counts_per_record), 2),
            )
        else:
            seq_stats = SequenceLengthStats(0, 0, 0.0, 0.0)

        # Vocabulary size counts distinct raw tokens (post-lowercasing),
        # including stopwords, since "how many unique word forms" is a
        # different question from "what are the informative top words".
        all_tokens = set()
        for r in records:
            all_tokens.update(_WORD_PATTERN.findall(r.text.lower()))

        return DatasetProfile(
            total_records=len(records),
            vocabulary_size=len(all_tokens),
            sequence_length=seq_stats,
            label_distribution=label_distribution,
            top_words=top_words,
        )


dataset_profiler = DatasetProfiler()
