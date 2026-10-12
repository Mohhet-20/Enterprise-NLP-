"""
Dataset validation. Every check here inspects the actual records passed
in — nothing is a fixed "looks fine" placeholder.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SHORT_TEXT_WORD_THRESHOLD = 3
LONG_TEXT_WORD_THRESHOLD = 500
# A class is flagged as imbalanced if it's under this fraction of the
# best-represented class's count.
CLASS_IMBALANCE_RATIO_THRESHOLD = 0.2


@dataclass
class DatasetRecordInput:
    text: str
    label: Optional[str] = None


@dataclass
class ValidationIssue:
    kind: str
    message: str
    record_indices: List[int] = field(default_factory=list)


@dataclass
class ValidationReport:
    total_records: int
    is_valid: bool
    issues: List[ValidationIssue]
    label_distribution: Dict[str, int]
    duplicate_count: int
    empty_count: int
    short_text_count: int
    long_text_count: int
    missing_label_count: int
    invalid_label_count: int


class DatasetValidator:
    def validate(
        self, records: List[DatasetRecordInput], label_set: Optional[List[str]] = None
    ) -> ValidationReport:
        if not records:
            return ValidationReport(
                total_records=0,
                is_valid=False,
                issues=[ValidationIssue("empty_dataset", "The dataset has no records.")],
                label_distribution={},
                duplicate_count=0,
                empty_count=0,
                short_text_count=0,
                long_text_count=0,
                missing_label_count=0,
                invalid_label_count=0,
            )

        issues: List[ValidationIssue] = []
        allowed_labels = set(label_set) if label_set else None

        # --- Encoding: look for the tell-tale replacement character that
        # shows up when bytes were decoded with the wrong codec. ---
        encoding_bad_indices = [i for i, r in enumerate(records) if "\ufffd" in r.text]
        if encoding_bad_indices:
            issues.append(
                ValidationIssue(
                    "encoding_errors",
                    f"{len(encoding_bad_indices)} record(s) contain the Unicode replacement "
                    f"character, indicating a decoding error upstream.",
                    encoding_bad_indices,
                )
            )

        # --- Duplicates (exact text match) ---
        text_counts = Counter(r.text.strip() for r in records)
        duplicate_texts = {t for t, count in text_counts.items() if count > 1}
        duplicate_indices = [i for i, r in enumerate(records) if r.text.strip() in duplicate_texts]
        if duplicate_indices:
            issues.append(
                ValidationIssue(
                    "duplicates",
                    f"{len(duplicate_indices)} record(s) are exact-text duplicates of another record.",
                    duplicate_indices,
                )
            )

        # --- Empty documents ---
        empty_indices = [i for i, r in enumerate(records) if not r.text.strip()]
        if empty_indices:
            issues.append(ValidationIssue("empty_documents", f"{len(empty_indices)} record(s) are empty.", empty_indices))

        # --- Very short / very long text ---
        short_indices = [
            i for i, r in enumerate(records)
            if r.text.strip() and len(r.text.split()) < SHORT_TEXT_WORD_THRESHOLD
        ]
        if short_indices:
            issues.append(
                ValidationIssue(
                    "very_short_text",
                    f"{len(short_indices)} record(s) have fewer than {SHORT_TEXT_WORD_THRESHOLD} words.",
                    short_indices,
                )
            )

        long_indices = [i for i, r in enumerate(records) if len(r.text.split()) > LONG_TEXT_WORD_THRESHOLD]
        if long_indices:
            issues.append(
                ValidationIssue(
                    "very_long_text",
                    f"{len(long_indices)} record(s) have more than {LONG_TEXT_WORD_THRESHOLD} words.",
                    long_indices,
                )
            )

        # --- Missing labels ---
        missing_label_indices = [i for i, r in enumerate(records) if not r.label]
        if missing_label_indices:
            issues.append(
                ValidationIssue(
                    "missing_labels",
                    f"{len(missing_label_indices)} record(s) have no label.",
                    missing_label_indices,
                )
            )

        # --- Invalid labels (not in the declared label set) ---
        invalid_label_indices: List[int] = []
        if allowed_labels is not None:
            invalid_label_indices = [
                i for i, r in enumerate(records) if r.label and r.label not in allowed_labels
            ]
            if invalid_label_indices:
                issues.append(
                    ValidationIssue(
                        "invalid_labels",
                        f"{len(invalid_label_indices)} record(s) use a label outside the "
                        f"declared label set {sorted(allowed_labels)}.",
                        invalid_label_indices,
                    )
                )

        # --- Class balance ---
        label_distribution = dict(Counter(r.label for r in records if r.label))
        if len(label_distribution) > 1:
            max_count = max(label_distribution.values())
            imbalanced = [
                label for label, count in label_distribution.items()
                if count / max_count < CLASS_IMBALANCE_RATIO_THRESHOLD
            ]
            if imbalanced:
                issues.append(
                    ValidationIssue(
                        "class_imbalance",
                        f"Class(es) {imbalanced} are under {CLASS_IMBALANCE_RATIO_THRESHOLD:.0%} of the "
                        f"largest class's count ({max_count}).",
                    )
                )

        # A dataset is "invalid" (blocking) only for issues that would
        # corrupt training — encoding errors and empty documents. Class
        # imbalance, duplicates, and short/long text are warnings a team
        # can consciously accept.
        blocking_kinds = {"encoding_errors", "empty_documents"}
        is_valid = not any(issue.kind in blocking_kinds for issue in issues)

        return ValidationReport(
            total_records=len(records),
            is_valid=is_valid,
            issues=issues,
            label_distribution=label_distribution,
            duplicate_count=len(duplicate_indices),
            empty_count=len(empty_indices),
            short_text_count=len(short_indices),
            long_text_count=len(long_indices),
            missing_label_count=len(missing_label_indices),
            invalid_label_count=len(invalid_label_indices),
        )


dataset_validator = DatasetValidator()
