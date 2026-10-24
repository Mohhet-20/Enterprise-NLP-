import csv
import io
import uuid

from backend.datasets.augmentation import DataAugmenter
from backend.datasets.cleaning import CleaningConfig, text_cleaner
from backend.datasets.profiling import dataset_profiler
from backend.datasets.validation import DatasetRecordInput, dataset_validator
from backend.repositories.user_repository import UserRepository

# --- Unit tests: cleaning ---


def test_cleaner_strips_html_and_normalizes_whitespace():
    result = text_cleaner.clean("<b>Hello</b>   world  ")
    assert result == "Hello world"


def test_cleaner_replaces_urls_and_mentions():
    result = text_cleaner.clean("check @someuser https://example.com now")
    assert "[MENTION]" in result
    assert "[URL]" in result
    assert "someuser" not in result


def test_cleaner_unwraps_hashtags_by_default():
    result = text_cleaner.clean("I love #NLP and #MachineLearning")
    assert "#" not in result
    assert "NLP" in result


def test_cleaner_normalizes_fullwidth_unicode():
    result = text_cleaner.clean("Ｈｅｌｌｏ")
    assert result == "Hello"


def test_cleaner_respects_keep_config():
    config = CleaningConfig(handle_urls="keep", handle_mentions="keep", remove_html=False)
    result = text_cleaner.clean("<b>hi</b> @user https://x.com", config)
    assert "@user" in result
    assert "https://x.com" in result


# --- Unit tests: validation ---


def test_validator_flags_duplicates():
    records = [DatasetRecordInput("same text", "A"), DatasetRecordInput("same text", "A"), DatasetRecordInput("different", "B")]
    report = dataset_validator.validate(records)
    assert report.duplicate_count == 2


def test_validator_flags_empty_documents_and_marks_invalid():
    records = [DatasetRecordInput("real text here", "A"), DatasetRecordInput("   ", "A")]
    report = dataset_validator.validate(records)
    assert report.empty_count == 1
    assert report.is_valid is False  # empty documents are blocking


def test_validator_flags_missing_and_invalid_labels():
    records = [
        DatasetRecordInput("has a label", "POSITIVE"),
        DatasetRecordInput("no label here", None),
        DatasetRecordInput("bad label here", "NOT_A_REAL_LABEL"),
    ]
    report = dataset_validator.validate(records, label_set=["POSITIVE", "NEGATIVE"])
    assert report.missing_label_count == 1
    assert report.invalid_label_count == 1


def test_validator_flags_short_and_long_text():
    long_text = " ".join(["word"] * 600)
    records = [DatasetRecordInput("ok", "A"), DatasetRecordInput(long_text, "A")]
    report = dataset_validator.validate(records)
    assert report.short_text_count == 1
    assert report.long_text_count == 1


def test_validator_detects_encoding_errors():
    records = [DatasetRecordInput("clean text", "A"), DatasetRecordInput("broken \ufffd text", "A")]
    report = dataset_validator.validate(records)
    assert any(issue.kind == "encoding_errors" for issue in report.issues)
    assert report.is_valid is False  # encoding errors are blocking


def test_validator_handles_empty_dataset():
    report = dataset_validator.validate([])
    assert report.total_records == 0
    assert report.is_valid is False


# --- Unit tests: profiling ---


def test_profiler_computes_real_sequence_stats():
    records = [DatasetRecordInput("one two three", "A"), DatasetRecordInput("one two three four five", "B")]
    profile = dataset_profiler.profile(records)
    assert profile.sequence_length.min_words == 3
    assert profile.sequence_length.max_words == 5
    assert profile.label_distribution == {"A": 1, "B": 1}


def test_profiler_top_words_excludes_stopwords():
    records = [DatasetRecordInput("the product is the best product I have", "A")]
    profile = dataset_profiler.profile(records)
    top_word_strings = [w for w, _ in profile.top_words]
    assert "the" not in top_word_strings
    assert "product" in top_word_strings


# --- Unit tests: augmentation ---


def test_augmenter_is_deterministic_with_a_seed():
    augmenter_a = DataAugmenter(seed=42)
    augmenter_b = DataAugmenter(seed=42)
    text = "This is a good and fast product"
    assert augmenter_a.synonym_replacement(text).augmented_text == augmenter_b.synonym_replacement(text).augmented_text


def test_augmenter_synonym_replacement_actually_changes_text():
    augmenter = DataAugmenter(seed=1)
    result = augmenter.synonym_replacement("This is a good product")
    assert result.original_text != result.augmented_text


def test_augmenter_random_deletion_shortens_or_preserves_text():
    augmenter = DataAugmenter(seed=1)
    result = augmenter.random_deletion("one two three four five six seven eight", deletion_prob=0.5)
    assert len(result.augmented_text.split()) <= 8


# --- API integration tests ---


def _unique_name(prefix: str = "ds") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _ml_engineer_headers(client, db_session):
    username = _unique_name("dsuser")
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]
    user = UserRepository(db_session).find_by_username(username)
    user.role = "ml_engineer"
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


def _build_csv(rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["text", "label"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def test_create_dataset_requires_dataset_write_permission(client):
    response = client.post(
        "/api/v1/datasets", json={"name": "x", "task": "sentiment_analysis", "label_set": ["POSITIVE", "NEGATIVE"]}
    )
    assert response.status_code == 401  # no auth at all


def test_create_and_upload_dataset_with_real_issues(client, db_session):
    headers = _ml_engineer_headers(client, db_session)

    create = client.post(
        "/api/v1/datasets",
        headers=headers,
        json={"name": _unique_name(), "task": "sentiment_analysis", "label_set": ["POSITIVE", "NEGATIVE"]},
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    csv_bytes = _build_csv(
        [
            {"text": "This product is great and works well", "label": "POSITIVE"},
            {"text": "This product is great and works well", "label": "POSITIVE"},  # duplicate
            {"text": "ok", "label": "POSITIVE"},  # short
            {"text": "", "label": "POSITIVE"},  # empty
            {"text": "Decent purchase, would recommend to others", "label": ""},  # missing label
            {"text": "Something strange happened", "label": "UNKNOWN_LABEL"},  # invalid label
        ]
    )
    files = {"file": ("reviews.csv", csv_bytes, "text/csv")}
    upload = client.post(f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files=files)

    assert upload.status_code == 200
    body = upload.json()
    assert body["dataset"]["row_count"] == 6
    report = body["validation_report"]
    assert report["duplicate_count"] == 2
    assert report["empty_count"] == 1
    assert report["short_text_count"] == 1
    assert report["missing_label_count"] == 1
    assert report["invalid_label_count"] == 1
    assert report["is_valid"] is False  # empty documents are blocking


def test_preview_returns_uploaded_records(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    csv_bytes = _build_csv([{"text": "Good product", "label": "POSITIVE"}, {"text": "Bad product", "label": "NEGATIVE"}])
    client.post(
        f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files={"file": ("r.csv", csv_bytes, "text/csv")}
    )

    preview = client.get(f"/api/v1/datasets/{dataset_id}/preview", headers=headers)
    assert preview.status_code == 200
    assert len(preview.json()) == 2


def test_profile_reflects_real_uploaded_content(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    csv_bytes = _build_csv(
        [{"text": "excellent quality product", "label": "POSITIVE"}, {"text": "excellent build and design", "label": "POSITIVE"}]
    )
    client.post(
        f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files={"file": ("r.csv", csv_bytes, "text/csv")}
    )

    profile = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["total_records"] == 2
    assert body["label_distribution"] == {"POSITIVE": 2}
    top_words = [w for w, _ in body["top_words"]]
    assert "excellent" in top_words


def test_versioning_creates_a_linked_copy_with_records(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]
    csv_bytes = _build_csv([{"text": "some content here", "label": "POSITIVE"}])
    client.post(
        f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files={"file": ("r.csv", csv_bytes, "text/csv")}
    )

    version_response = client.post(f"/api/v1/datasets/{dataset_id}/version", headers=headers)
    assert version_response.status_code == 201
    new_version = version_response.json()
    assert new_version["version"] == 2
    assert new_version["parent_version_id"] == dataset_id
    assert new_version["row_count"] == 1

    history = client.get(f"/api/v1/datasets/{new_version['id']}/versions", headers=headers)
    assert [v["version"] for v in history.json()] == [1, 2]


def test_archive_and_restore_dataset(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    archived = client.post(f"/api/v1/datasets/{dataset_id}/archive", headers=headers)
    assert archived.json()["is_archived"] is True
    assert archived.json()["status"] == "archived"

    listing = client.get("/api/v1/datasets", headers=headers)
    assert dataset_id not in [d["id"] for d in listing.json()]

    restored = client.post(f"/api/v1/datasets/{dataset_id}/restore", headers=headers)
    assert restored.json()["is_archived"] is False


def test_update_tags(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    response = client.put(f"/api/v1/datasets/{dataset_id}/tags", headers=headers, json={"tags": ["reviews", "v1"]})
    assert response.status_code == 200
    assert response.json()["tags"] == ["reviews", "v1"]

    filtered = client.get("/api/v1/datasets?tag=reviews", headers=headers)
    assert dataset_id in [d["id"] for d in filtered.json()]


def test_compare_datasets(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    id_a = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]
    id_b = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    client.post(
        f"/api/v1/datasets/{id_a}/upload",
        headers=headers,
        files={"file": ("r.csv", _build_csv([{"text": "one row here", "label": "POSITIVE"}]), "text/csv")},
    )
    client.post(
        f"/api/v1/datasets/{id_b}/upload",
        headers=headers,
        files={
            "file": (
                "r.csv",
                _build_csv([{"text": "row one", "label": "POSITIVE"}, {"text": "row two", "label": "NEGATIVE"}]),
                "text/csv",
            )
        },
    )

    comparison = client.get(f"/api/v1/datasets/compare/{id_a}/{id_b}", headers=headers)
    assert comparison.status_code == 200
    assert comparison.json()["row_count_delta"] == 1


def test_augment_endpoint_runs_all_methods_by_default(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    response = client.post(
        "/api/v1/datasets/augment", headers=headers, json={"text": "This is a good and fast product"}
    )
    assert response.status_code == 200
    methods = {r["method"] for r in response.json()}
    assert methods == {"synonym_replacement", "random_deletion", "random_swap", "random_insertion"}


def test_read_only_user_cannot_create_datasets(client):
    username = _unique_name("viewer")
    email = f"{username}@example.com"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": "StrongPass123!"})
    token = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "StrongPass123!"}
    ).json()["access_token"]

    response = client.post(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "x", "task": "sentiment_analysis"},
    )
    assert response.status_code == 403
