import csv
import io
import uuid

from backend.evaluation.baseline_classifier import baseline_sentiment_classifier
from backend.evaluation.error_analysis import EvalSampleResult, error_analyzer
from backend.evaluation.metrics import compute_classification_metrics
from backend.repositories.user_repository import UserRepository

# --- Unit tests: metrics ---


def test_compute_classification_metrics_matches_hand_worked_example():
    # 4 samples, 1 wrong (predicted NEGATIVE, actually POSITIVE) — easy to
    # hand-verify: accuracy 3/4, POSITIVE recall 1/2, NEGATIVE recall 2/2.
    y_true = ["POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE"]
    y_pred = ["POSITIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE"]
    confidences = [0.9, 0.6, 0.8, 0.95]

    metrics = compute_classification_metrics(y_true, y_pred, confidences, labels=["NEGATIVE", "POSITIVE"])

    assert metrics.accuracy == 0.75
    positive_metric = next(pc for pc in metrics.per_class if pc.label == "POSITIVE")
    negative_metric = next(pc for pc in metrics.per_class if pc.label == "NEGATIVE")
    assert positive_metric.recall == 0.5
    assert negative_metric.recall == 1.0
    assert metrics.confusion_matrix == [[2, 0], [1, 1]]  # rows/cols ordered NEGATIVE, POSITIVE
    assert metrics.roc_auc is not None


def test_compute_classification_metrics_rejects_mismatched_lengths():
    import pytest

    with pytest.raises(ValueError):
        compute_classification_metrics(["POSITIVE"], ["POSITIVE", "NEGATIVE"], [0.9, 0.5])


def test_compute_classification_metrics_rejects_empty_input():
    import pytest

    with pytest.raises(ValueError):
        compute_classification_metrics([], [], [])


# --- Unit tests: error analysis ---


def test_error_analyzer_flags_confidence_errors_and_hard_examples():
    samples = [
        EvalSampleResult("clearly wrong but confident", "POSITIVE", "NEGATIVE", 0.95),  # confidence error
        EvalSampleResult("correct and confident", "POSITIVE", "POSITIVE", 0.9),
        EvalSampleResult("wrong and unsure", "NEGATIVE", "POSITIVE", 0.55),  # hard example, also an error
        EvalSampleResult("correct but unsure", "NEGATIVE", "NEGATIVE", 0.52),  # hard example, correct
    ]
    result = error_analyzer.analyze(samples)

    assert len(result.misclassified) == 2
    assert len(result.confidence_errors) == 1
    assert result.confidence_errors[0].text == "clearly wrong but confident"
    assert len(result.hard_examples) == 2  # both low-confidence samples, regardless of correctness
    assert result.false_negatives_by_class.get("POSITIVE") == 1
    assert result.false_positives_by_class.get("NEGATIVE") == 1


def test_error_analyzer_length_slices_bucket_correctly():
    samples = [
        EvalSampleResult("short one", "POSITIVE", "POSITIVE", 0.9),  # 2 words -> short
        EvalSampleResult(" ".join(["word"] * 40), "NEGATIVE", "POSITIVE", 0.6),  # 40 words -> long, wrong
    ]
    result = error_analyzer.analyze(samples)
    slice_names = {s.name for s in result.length_slices}
    assert "short" in slice_names
    assert "long" in slice_names
    long_slice = next(s for s in result.length_slices if s.name == "long")
    assert long_slice.error_count == 1


def test_error_analyzer_rejects_empty_input():
    import pytest

    with pytest.raises(ValueError):
        error_analyzer.analyze([])


# --- Unit test: baseline classifier ---


def test_baseline_classifier_is_deterministic():
    text = "This is a great product, I really love it."
    first = baseline_sentiment_classifier.predict(text)
    second = baseline_sentiment_classifier.predict(text)
    assert first.label == second.label
    assert first.score == second.score
    assert first.label == "POSITIVE"


def test_baseline_classifier_handles_negation():
    result = baseline_sentiment_classifier.predict("This was not a good experience.")
    assert result.label == "NEGATIVE"


# --- API integration tests ---


def _unique_username(prefix: str = "evaluser") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _register_and_login(client, password: str = "StrongPass123!"):
    username = _unique_username()
    email = f"{username}@example.com"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return username, login.json()["access_token"]


def _promote_role(db_session, username: str, role: str) -> None:
    user = UserRepository(db_session).find_by_username(username)
    user.role = role
    db_session.commit()


def test_run_evaluation_requires_experiment_write_permission(client):
    _, access_token = _register_and_login(client)  # default role: read_only_user
    response = client.post(
        "/api/v1/evaluation/run",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"task": "sentiment_analysis"},
    )
    assert response.status_code == 403


def test_run_evaluation_produces_real_metrics(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")

    response = client.post(
        "/api/v1/evaluation/run",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"task": "sentiment_analysis", "model": "lexicon_baseline"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["model_name"] == "lexicon-baseline-v1"
    assert 0.0 < body["accuracy"] < 1.0  # genuine mixed performance, not 0% or 100%
    assert body["num_samples"] > 0
    assert len(body["confusion_matrix"]) == len(body["labels"])
    assert body["error_summary"]["total_errors"] > 0  # the eval set includes real hard cases
    assert any(pc["label"] == "POSITIVE" for pc in body["per_class"])
    assert any(pc["label"] == "NEGATIVE" for pc in body["per_class"])


def test_run_evaluation_rejects_unsupported_task(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")

    response = client.post(
        "/api/v1/evaluation/run",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"task": "toxicity_detection"},
    )
    assert response.status_code == 400


def test_get_run_returns_persisted_result(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")
    headers = {"Authorization": f"Bearer {access_token}"}

    run = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "sentiment_analysis"}).json()
    fetched = client.get(f"/api/v1/evaluation/runs/{run['run_id']}", headers=headers)

    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run["run_id"]
    assert fetched.json()["accuracy"] == run["accuracy"]


def test_get_nonexistent_run_returns_404(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")

    response = client.get(
        "/api/v1/evaluation/runs/does-not-exist",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 404


def test_list_runs_includes_newly_created_run(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")
    headers = {"Authorization": f"Bearer {access_token}"}

    run = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "sentiment_analysis"}).json()
    listing = client.get("/api/v1/evaluation/runs", headers=headers)

    assert listing.status_code == 200
    run_ids = [r["run_id"] for r in listing.json()]
    assert run["run_id"] in run_ids


def test_report_endpoint_returns_markdown_with_expected_sections(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")
    headers = {"Authorization": f"Bearer {access_token}"}

    run = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "sentiment_analysis"}).json()
    report = client.get(f"/api/v1/evaluation/runs/{run['run_id']}/report", headers=headers)

    assert report.status_code == 200
    text = report.text
    assert "# Evaluation Report" in text
    assert "## Confusion Matrix" in text
    assert "## Error Summary" in text
    assert "## Misclassified Samples" in text


def test_csv_export_contains_real_misclassified_rows(client, db_session):
    username, access_token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")
    headers = {"Authorization": f"Bearer {access_token}"}

    run = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "sentiment_analysis"}).json()
    csv_response = client.get(
        f"/api/v1/evaluation/runs/{run['run_id']}/misclassified.csv", headers=headers
    )

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")

    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert len(rows) == run["error_summary"]["total_errors"]
    for row in rows:
        assert row["true_label"] != row["predicted_label"]


def test_read_only_user_can_view_but_not_run_evaluations(client, db_session):
    """READ_ONLY_USER has experiment:read (can view results) but not
    experiment:write (cannot trigger a new run) — an ML engineer runs it
    first, then a plain viewer should still be able to read it."""
    ml_username, ml_token = _register_and_login(client)
    _promote_role(db_session, ml_username, "ml_engineer")
    run = client.post(
        "/api/v1/evaluation/run",
        headers={"Authorization": f"Bearer {ml_token}"},
        json={"task": "sentiment_analysis"},
    ).json()

    _, viewer_token = _register_and_login(client)  # stays read_only_user
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    read_response = client.get(f"/api/v1/evaluation/runs/{run['run_id']}", headers=viewer_headers)
    assert read_response.status_code == 200

    write_response = client.post(
        "/api/v1/evaluation/run", headers=viewer_headers, json={"task": "sentiment_analysis"}
    )
    assert write_response.status_code == 403
