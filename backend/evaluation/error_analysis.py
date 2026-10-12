"""
Error Analysis Center.

Takes the raw per-sample results of an evaluation run (text, true label,
predicted label, confidence) and surfaces the patterns a human reviewer
actually cares about: which samples were wrong, which were wrong
*confidently* (the more concerning failure mode), and whether errors
cluster by class or by text length.
"""

from dataclasses import dataclass, field
from typing import Dict, List

# A prediction is a "confidence error" if the model was this sure and
# still wrong — the failure mode worth flagging to a reviewer first.
CONFIDENCE_ERROR_THRESHOLD = 0.75

# A prediction is a "hard example" if the model wasn't sure, regardless of
# whether it happened to land on the right answer.
HARD_EXAMPLE_CONFIDENCE_THRESHOLD = 0.6

SHORT_TEXT_WORD_COUNT = 8
LONG_TEXT_WORD_COUNT = 30


@dataclass
class EvalSampleResult:
    text: str
    true_label: str
    predicted_label: str
    confidence: float

    @property
    def is_correct(self) -> bool:
        return self.true_label == self.predicted_label

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass
class LengthSlice:
    name: str
    count: int
    accuracy: float
    error_count: int


@dataclass
class ErrorAnalysisResult:
    misclassified: List[EvalSampleResult]
    confidence_errors: List[EvalSampleResult]
    hard_examples: List[EvalSampleResult]
    false_positives_by_class: Dict[str, int]
    false_negatives_by_class: Dict[str, int]
    errors_by_class: Dict[str, int]
    length_slices: List[LengthSlice] = field(default_factory=list)


class ErrorAnalyzer:
    def analyze(self, samples: List[EvalSampleResult]) -> ErrorAnalysisResult:
        if not samples:
            raise ValueError("Cannot run error analysis over zero samples.")

        misclassified = [s for s in samples if not s.is_correct]

        confidence_errors = sorted(
            (s for s in misclassified if s.confidence >= CONFIDENCE_ERROR_THRESHOLD),
            key=lambda s: s.confidence,
            reverse=True,
        )
        hard_examples = sorted(
            (s for s in samples if s.confidence < HARD_EXAMPLE_CONFIDENCE_THRESHOLD),
            key=lambda s: s.confidence,
        )

        false_positives_by_class: Dict[str, int] = {}
        false_negatives_by_class: Dict[str, int] = {}
        errors_by_class: Dict[str, int] = {}

        for s in misclassified:
            # From the perspective of the class the sample was incorrectly
            # assigned to, this is a false positive; from the perspective
            # of its true class, it's a false negative.
            false_positives_by_class[s.predicted_label] = false_positives_by_class.get(s.predicted_label, 0) + 1
            false_negatives_by_class[s.true_label] = false_negatives_by_class.get(s.true_label, 0) + 1
            errors_by_class[s.true_label] = errors_by_class.get(s.true_label, 0) + 1

        length_slices = self._compute_length_slices(samples)

        return ErrorAnalysisResult(
            misclassified=misclassified,
            confidence_errors=confidence_errors,
            hard_examples=hard_examples,
            false_positives_by_class=false_positives_by_class,
            false_negatives_by_class=false_negatives_by_class,
            errors_by_class=errors_by_class,
            length_slices=length_slices,
        )

    def _compute_length_slices(self, samples: List[EvalSampleResult]) -> List[LengthSlice]:
        buckets: Dict[str, List[EvalSampleResult]] = {"short": [], "medium": [], "long": []}
        for s in samples:
            if s.word_count <= SHORT_TEXT_WORD_COUNT:
                buckets["short"].append(s)
            elif s.word_count >= LONG_TEXT_WORD_COUNT:
                buckets["long"].append(s)
            else:
                buckets["medium"].append(s)

        slices: List[LengthSlice] = []
        for name, bucket in buckets.items():
            if not bucket:
                continue
            errors = sum(1 for s in bucket if not s.is_correct)
            slices.append(
                LengthSlice(
                    name=name,
                    count=len(bucket),
                    accuracy=round((len(bucket) - errors) / len(bucket), 4),
                    error_count=errors,
                )
            )
        return slices


error_analyzer = ErrorAnalyzer()
