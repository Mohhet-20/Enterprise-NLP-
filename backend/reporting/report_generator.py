"""Reporting subsystem: turns experiment/monitoring data into
human-readable summaries. Kept separate from experiments/monitoring so
report formats (markdown, PDF, HTML dashboard) can multiply without
touching the data-producing subsystems."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseReportGenerator(ABC):
    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> str:
        """Return a rendered report (format depends on the concrete class,
        e.g. Markdown, HTML)."""
        raise NotImplementedError


class MarkdownExperimentReport(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> str:
        lines = [f"# Experiment Report: {data.get('name', 'Unnamed')}", ""]
        lines.append(f"- **Task**: {data.get('task', 'n/a')}")
        lines.append(f"- **Model**: {data.get('model_name', 'n/a')}")
        lines.append(f"- **Status**: {data.get('status', 'n/a')}")
        lines.append("")
        lines.append("## Metrics")
        for metric_snapshot in data.get("metric_history", []):
            lines.append(f"- {metric_snapshot}")
        return "\n".join(lines)


class MarkdownEvaluationReport(BaseReportGenerator):
    """Renders a full evaluation-run dict (see
    backend/services/evaluation_service.py) as a downloadable Markdown
    report — confusion matrix, per-class metrics, calibration, and the
    top misclassified samples."""

    def generate(self, data: Dict[str, Any]) -> str:
        lines = [
            f"# Evaluation Report — {data['task']}",
            "",
            f"- **Run ID**: `{data['run_id']}`",
            f"- **Model**: {data['model_name']}",
            f"- **Generated**: {data['created_at']}",
            f"- **Samples evaluated**: {data['num_samples']}",
            "",
            "## Overall Metrics",
            "",
            "| Accuracy | Macro F1 | Weighted F1 | ROC-AUC |",
            "|---|---|---|---|",
            f"| {data['accuracy']:.2%} | {data['macro_f1']:.4f} | {data['weighted_f1']:.4f} "
            f"| {data['roc_auc'] if data['roc_auc'] is not None else 'n/a'} |",
            "",
            "## Per-Class Metrics",
            "",
            "| Label | Precision | Recall | F1 | Support |",
            "|---|---|---|---|---|",
        ]
        for pc in data["per_class"]:
            lines.append(
                f"| {pc['label']} | {pc['precision']:.4f} | {pc['recall']:.4f} "
                f"| {pc['f1']:.4f} | {pc['support']} |"
            )

        lines += ["", "## Confusion Matrix", ""]
        labels = data["labels"]
        header = "| actual \\ predicted | " + " | ".join(labels) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(labels) + 1))
        for label, row in zip(labels, data["confusion_matrix"]):
            lines.append(f"| **{label}** | " + " | ".join(str(v) for v in row) + " |")

        summary = data["error_summary"]
        lines += [
            "",
            "## Error Summary",
            "",
            f"- **Total errors**: {summary['total_errors']} / {data['num_samples']}",
            f"- **Confidence errors** (wrong despite high confidence): {summary['confidence_error_count']}",
            f"- **Hard examples** (low confidence, regardless of outcome): {summary['hard_example_count']}",
            f"- **Errors by true class**: {summary['errors_by_class']}",
        ]

        if summary["length_slices"]:
            lines += ["", "### Accuracy by Text Length", "", "| Slice | Count | Accuracy | Errors |", "|---|---|---|---|"]
            for ls in summary["length_slices"]:
                lines.append(f"| {ls['name']} | {ls['count']} | {ls['accuracy']:.2%} | {ls['error_count']} |")

        if data["misclassified_samples"]:
            lines += ["", "## Misclassified Samples", ""]
            for s in data["misclassified_samples"]:
                lines.append(
                    f"- **true={s['true_label']}, predicted={s['predicted_label']}, "
                    f"confidence={s['confidence']:.2f}**: {s['text']}"
                )

        return "\n".join(lines)
