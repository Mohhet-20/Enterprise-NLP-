import csv
import io
import uuid

from backend.nlp.embeddings.tfidf_embedder import TfidfEmbedder
from backend.repositories.user_repository import UserRepository
from backend.services.embedding_service import EmbeddingIndexService


# --- Unit tests ---


def test_tfidf_embedder_produces_a_vector_per_text():
    embedder = TfidfEmbedder()
    vectors = embedder.embed(["good product", "bad product", "another good product"])
    assert len(vectors) == 3
    assert all(len(v) == len(vectors[0]) for v in vectors)


def test_tfidf_embedder_similarity_ranks_related_text_higher():
    embedder = TfidfEmbedder()
    # Fit over a small shared corpus first so both similarity calls are
    # comparable in the same vector space.
    embedder.embed(["excellent quality product", "terrible broken item", "excellent build quality"])
    sim_related = embedder.similarity("excellent quality product", "excellent build quality")
    sim_unrelated = embedder.similarity("excellent quality product", "terrible broken item")
    assert sim_related > sim_unrelated


def test_embedding_index_service_search_finds_the_closest_match():
    service = EmbeddingIndexService()
    service.build_index(
        dataset_id="ds1",
        record_ids=["r1", "r2", "r3"],
        texts=["the battery life is excellent", "shipping was slow and late", "battery lasts all day long"],
        labels=["POSITIVE", "NEGATIVE", "POSITIVE"],
    )
    results = service.search("ds1", "great battery performance", top_k=2)
    assert len(results) == 2
    # Both battery-related records should outrank the unrelated shipping complaint.
    result_ids = {r.record_id for r in results}
    assert result_ids == {"r1", "r3"}


def test_embedding_index_service_similarity_between_records():
    service = EmbeddingIndexService()
    service.build_index(
        dataset_id="ds1",
        record_ids=["r1", "r2"],
        texts=["great battery life", "terrible customer support"],
        labels=[None, None],
    )
    sim = service.similarity_between_records("ds1", "r1", "r2")
    assert -1.0 <= sim <= 1.0


def test_embedding_index_service_raises_for_unbuilt_dataset():
    import pytest

    from backend.core.exceptions import RecordNotFoundError

    service = EmbeddingIndexService()
    with pytest.raises(RecordNotFoundError):
        service.search("nonexistent", "query")


# --- API integration tests ---


def _unique_name(prefix: str = "emb") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _ml_engineer_headers(client, db_session):
    username = _unique_name("embuser")
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


def test_build_search_and_compare_embeddings_end_to_end(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    csv_bytes = _build_csv(
        [
            {"text": "The battery life on this laptop is fantastic", "label": "POSITIVE"},
            {"text": "Shipping took over three weeks and arrived damaged", "label": "NEGATIVE"},
            {"text": "Battery performance is excellent, lasts all day", "label": "POSITIVE"},
        ]
    )
    client.post(
        f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files={"file": ("r.csv", csv_bytes, "text/csv")}
    )

    build = client.post(f"/api/v1/datasets/{dataset_id}/embeddings/build", headers=headers)
    assert build.status_code == 200
    assert build.json()["num_vectors"] == 3

    search = client.get(
        f"/api/v1/datasets/{dataset_id}/embeddings/search",
        headers=headers,
        params={"query": "great battery life", "top_k": 2},
    )
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 2
    assert all("battery" in r["text"].lower() for r in results)

    record_ids = [r["record_id"] for r in results]
    similarity = client.get(
        f"/api/v1/datasets/{dataset_id}/embeddings/similarity",
        headers=headers,
        params={"record_id_a": record_ids[0], "record_id_b": record_ids[1]},
    )
    assert similarity.status_code == 200
    assert -1.0 <= similarity.json()["similarity"] <= 1.0


def test_search_before_build_returns_404(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_name(), "task": "sentiment_analysis"}
    ).json()["id"]

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/embeddings/search", headers=headers, params={"query": "anything"}
    )
    assert response.status_code == 404
