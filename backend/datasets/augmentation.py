"""
Text augmentation: seedable implementations of the four EDA operations
(Wei & Zou, 2019) — synonym replacement, random deletion, random swap and
random insertion. Synonym replacement uses a small hand-built table so
augmentation stays deterministic and dependency-free.

Back-translation and neural paraphrasing are not implemented; both need a
generation model, which is out of scope for a classification platform.
"""

import random
import re
from dataclasses import dataclass
from typing import List, Optional

_SYNONYMS = {
    "good": ["great", "solid", "decent"],
    "bad": ["poor", "terrible", "subpar"],
    "big": ["large", "huge", "sizable"],
    "small": ["tiny", "compact", "little"],
    "fast": ["quick", "speedy", "rapid"],
    "slow": ["sluggish", "unhurried"],
    "happy": ["pleased", "glad", "content"],
    "sad": ["unhappy", "down", "disappointed"],
    "easy": ["simple", "straightforward"],
    "hard": ["difficult", "tough", "challenging"],
    "cheap": ["affordable", "inexpensive"],
    "expensive": ["costly", "pricey"],
    "love": ["adore", "enjoy"],
    "hate": ["dislike", "despise"],
    "buy": ["purchase", "get"],
    "broken": ["damaged", "defective"],
}

_WORD_PATTERN = re.compile(r"\b[\w']+\b")


@dataclass
class AugmentationResult:
    method: str
    original_text: str
    augmented_text: str


class DataAugmenter:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._random = random.Random(seed)

    def synonym_replacement(self, text: str, n: int = 1) -> AugmentationResult:
        words = text.split()
        candidates = [i for i, w in enumerate(words) if w.lower().strip(".,!?") in _SYNONYMS]
        self._random.shuffle(candidates)
        replaced = list(words)
        for idx in candidates[:n]:
            key = words[idx].lower().strip(".,!?")
            synonym = self._random.choice(_SYNONYMS[key])
            replaced[idx] = synonym
        return AugmentationResult("synonym_replacement", text, " ".join(replaced))

    def random_deletion(self, text: str, deletion_prob: float = 0.15) -> AugmentationResult:
        words = text.split()
        if len(words) <= 1:
            return AugmentationResult("random_deletion", text, text)
        kept = [w for w in words if self._random.random() > deletion_prob]
        if not kept:
            kept = [self._random.choice(words)]
        return AugmentationResult("random_deletion", text, " ".join(kept))

    def random_swap(self, text: str, n: int = 1) -> AugmentationResult:
        words = text.split()
        result = list(words)
        for _ in range(n):
            if len(result) < 2:
                break
            i, j = self._random.sample(range(len(result)), 2)
            result[i], result[j] = result[j], result[i]
        return AugmentationResult("random_swap", text, " ".join(result))

    def random_insertion(self, text: str, n: int = 1) -> AugmentationResult:
        words = text.split()
        result = list(words)
        synonym_words = [w for w in words if w.lower().strip(".,!?") in _SYNONYMS]
        for _ in range(n):
            if not synonym_words:
                break
            source_word = self._random.choice(synonym_words).lower().strip(".,!?")
            synonym = self._random.choice(_SYNONYMS[source_word])
            insert_pos = self._random.randint(0, len(result))
            result.insert(insert_pos, synonym)
        return AugmentationResult("random_insertion", text, " ".join(result))

    def augment_all_methods(self, text: str) -> List[AugmentationResult]:
        return [
            self.synonym_replacement(text),
            self.random_deletion(text),
            self.random_swap(text),
            self.random_insertion(text),
        ]


data_augmenter = DataAugmenter()
