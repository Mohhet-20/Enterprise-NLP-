import uuid

import pytest

from backend.core.constants import ModelArchitecture, NLPTask
from backend.core.exceptions import ValidationError
from backend.nlp.inference.base_model import BaseNLPModel
from backend.nlp.inference.model_factory import ModelFactory
from backend.nlp.inference.models.bert_model import BertModel
from backend.nlp.inference.models.zero_shot_model import ZeroShotModel
from backend.repositories.user_repository import UserRepository


def _login(client, db_session=None, role=None):
    username = f"infer_{uuid.uuid4().hex[:10]}"
    password = "StrongPass123!"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    if role:
        user = UserRepository(db_session).find_by_username(username)
        user.role = role
        db_session.commit()
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


# --- API: predict / batch / embed -----------------------------------------


def test_predict_forwards_task_specific_arguments(client, _stub_models):
    headers = _login(client)
    response = client.post(
        "/api/v1/predict",
        headers=headers,
        json={
            "task": "zero_shot_classification",
            "text": "The striker scored twice.",
            "candidate_labels": ["sports", "politics"],
        },
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["label"] == "sports"
    assert _stub_models.calls[-1]["candidate_labels"] == ["sports", "politics"]


def test_batch_predict_returns_one_item_per_text_in_order(client):
    headers = _login(client)
    texts = ["I love it", "terrible", "great stuff"]
    response = client.post(
        "/api/v1/predict/batch", headers=headers, json={"task": "sentiment_analysis", "texts": texts}
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["text"] for item in body["items"]] == texts
    assert [item["results"][0]["label"] for item in body["items"]] == ["POSITIVE", "NEGATIVE", "POSITIVE"]
    assert body["throughput_texts_per_second"] > 0


def test_batch_predict_enforces_size_limit(client):
    headers = _login(client)
    response = client.post(
        "/api/v1/predict/batch",
        headers=headers,
        json={"task": "sentiment_analysis", "texts": ["x"] * 65},
    )
    assert response.status_code == 422


def test_batch_rejects_blank_text(client):
    headers = _login(client)
    response = client.post(
        "/api/v1/predict/batch", headers=headers, json={"task": "sentiment_analysis", "texts": ["ok", "   "]}
    )
    assert response.status_code == 422


def test_embed_endpoint_returns_vectors(client):
    headers = _login(client)
    response = client.post("/api/v1/embed", headers=headers, json={"texts": ["a", "abc"]})
    assert response.status_code == 200
    body = response.json()
    assert body["dimension"] == 3
    assert len(body["embeddings"]) == 2


def test_explain_rejects_task_without_explainer(client):
    headers = _login(client)
    response = client.post(
        "/api/v1/explain", headers=headers, json={"task": "semantic_similarity", "text": "hello there"}
    )
    assert response.status_code == 422


def test_tasks_endpoint_lists_every_task_with_metadata(client):
    body = client.get("/api/v1/tasks").json()
    tasks = {t["task"]: t for t in body["tasks"]}
    assert set(tasks) == {t.value for t in NLPTask}
    assert tasks["sentiment_analysis"]["explainable"] is True
    assert all(t["description"] for t in tasks.values())
    # Local checkpoints are absolute paths server-side; they must never leak.
    assert all(":\\" not in t["default_model"] and not t["default_model"].startswith("/") for t in tasks.values())


# --- Model strategies (no weights needed) ---------------------------------


def _bert_with_labels(labels, multi_label):
    model = BertModel("dummy")
    model._id2label = dict(enumerate(labels))
    model._multi_label = multi_label
    return model


def test_single_label_head_returns_argmax_only():
    model = _bert_with_labels(["NEGATIVE", "POSITIVE"], multi_label=False)
    preds = model._to_predictions([0.2, 0.8])
    assert [p.label for p in preds] == ["POSITIVE"]
    assert preds[0].raw_scores == {"NEGATIVE": 0.2, "POSITIVE": 0.8}


def test_multi_label_head_returns_every_label_over_threshold_sorted():
    model = _bert_with_labels(["toxic", "insult", "threat"], multi_label=True)
    preds = model._to_predictions([0.91, 0.62, 0.03])
    assert [p.label for p in preds] == ["toxic", "insult"]


def test_multi_label_head_never_returns_empty():
    model = _bert_with_labels(["toxic", "insult"], multi_label=True)
    preds = model._to_predictions([0.1, 0.3])
    assert [p.label for p in preds] == ["insult"]


@pytest.mark.parametrize("labels", [None, ["only-one"], [" ", "x"], [f"l{i}" for i in range(21)]])
def test_zero_shot_validates_candidate_labels_before_loading(labels):
    model = ZeroShotModel("never-loaded")
    with pytest.raises(ValidationError):
        model.predict("text", NLPTask.ZERO_SHOT_CLASSIFICATION, candidate_labels=labels)
    assert not model.is_loaded


class _CountingModel(BaseNLPModel):
    supported_tasks = []

    def load(self):
        self._model = object()
        self._is_loaded = True

    def predict(self, text, task, **kwargs):
        self.load()
        return []


def test_factory_evicts_least_recently_used_loaded_model(monkeypatch):
    import backend.nlp.inference.model_factory as mf

    monkeypatch.setitem(mf._ARCHITECTURE_REGISTRY, ModelArchitecture.BERT, _CountingModel)
    factory = ModelFactory(max_loaded_models=2)

    a = factory.get_model(ModelArchitecture.BERT, "a")
    a.predict("x", NLPTask.SENTIMENT_ANALYSIS)
    b = factory.get_model(ModelArchitecture.BERT, "b")
    b.predict("x", NLPTask.SENTIMENT_ANALYSIS)
    factory.get_model(ModelArchitecture.BERT, "a")  # touch a -> b is now LRU
    c = factory.get_model(ModelArchitecture.BERT, "c")
    c.predict("x", NLPTask.SENTIMENT_ANALYSIS)

    assert a.is_loaded and c.is_loaded
    assert not b.is_loaded
    assert not hasattr(b, "_model")


def test_zero_shot_task_routes_to_zero_shot_strategy():
    model = ModelFactory().get_model(ModelArchitecture.DEBERTA, "m", task=NLPTask.ZERO_SHOT_CLASSIFICATION)
    assert isinstance(model, ZeroShotModel)


# --- Integrated Gradients on a tiny, randomly initialised BERT ------------


@pytest.fixture
def tiny_bert(tmp_path):
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")

    words = ["the", "movie", "was", "great", "awful", "not", "plot", "acting"]
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *words, "##ly"]
    vocab_file = tmp_path / "vocab.txt"
    vocab_file.write_text("\n".join(vocab))

    torch.manual_seed(0)
    config = transformers.BertConfig(
        vocab_size=len(vocab), hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
        intermediate_size=64, num_labels=2, id2label={0: "NEGATIVE", 1: "POSITIVE"},
        label2id={"NEGATIVE": 0, "POSITIVE": 1},
    )
    model = BertModel("tiny-bert")
    model._model = transformers.BertForSequenceClassification(config).eval()
    model._tokenizer = transformers.BertTokenizerFast(vocab_file=str(vocab_file))
    model._id2label = config.id2label
    model._multi_label = False
    model._max_length = 64
    model._is_loaded = True
    return model


def test_integrated_gradients_satisfies_completeness(tiny_bert):
    from backend.explainability.integrated_gradients import IntegratedGradientsExplainer

    explanation = IntegratedGradientsExplainer(tiny_bert, n_steps=64).explain_full(
        "the acting was not great", "POSITIVE"
    )
    score_gap = explanation.target_score - explanation.baseline_score
    attribution_sum = sum(a.importance for a in explanation.attributions)

    # Completeness axiom: attributions sum to F(x) - F(baseline).
    assert abs(attribution_sum - score_gap) == pytest.approx(abs(explanation.convergence_delta), abs=1e-5)
    assert abs(explanation.convergence_delta) < 0.01


def test_integrated_gradients_merges_subwords_into_words(tiny_bert):
    from backend.explainability.integrated_gradients import IntegratedGradientsExplainer

    attributions = IntegratedGradientsExplainer(tiny_bert, n_steps=8).explain("the movie was great", "NEGATIVE")
    assert [a.token for a in attributions] == ["the", "movie", "was", "great"]


def test_integrated_gradients_rejects_unknown_label(tiny_bert):
    from backend.core.exceptions import ModelInferenceError
    from backend.explainability.integrated_gradients import IntegratedGradientsExplainer

    with pytest.raises(ModelInferenceError):
        IntegratedGradientsExplainer(tiny_bert).explain("the movie", "NEUTRAL")


def test_batched_predictions_match_single_predictions(tiny_bert):
    texts = ["the movie was great", "awful", "the plot was not great acting"]
    batched = tiny_bert.predict_batch(texts, NLPTask.SENTIMENT_ANALYSIS)
    for text, batch_preds in zip(texts, batched):
        single = tiny_bert.predict(text, NLPTask.SENTIMENT_ANALYSIS)
        assert single[0].label == batch_preds[0].label
        assert single[0].score == pytest.approx(batch_preds[0].score, abs=1e-5)


# --- Evaluation against served models and uploaded datasets ---------------


def test_served_and_baseline_evaluations_are_recorded_separately(client, db_session):
    headers = _login(client, db_session, role="ml_engineer")
    served = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "sentiment_analysis"}).json()
    baseline = client.post(
        "/api/v1/evaluation/run",
        headers=headers,
        json={"task": "sentiment_analysis", "model": "lexicon_baseline"},
    ).json()

    assert served["model_kind"] == "served"
    assert baseline["model_name"] == "lexicon-baseline-v1"
    assert served["num_samples"] == baseline["num_samples"] == 48

    listing = client.get("/api/v1/evaluation/runs", headers=headers).json()
    assert listing[0]["run_id"] == baseline["run_id"]  # newest first


def test_evaluate_served_model_on_uploaded_dataset(client, db_session):
    headers = _login(client, db_session, role="ml_engineer")
    dataset = client.post(
        "/api/v1/datasets",
        headers=headers,
        json={"name": f"eval_{uuid.uuid4().hex[:6]}", "task": "sentiment_analysis", "label_set": ["POSITIVE", "NEGATIVE"]},
    ).json()
    csv_body = "text,label\nI love this,POSITIVE\nreally great,POSITIVE\nawful thing,NEGATIVE\ngreat... not,NEGATIVE\n"
    client.post(
        f"/api/v1/datasets/{dataset['id']}/upload",
        headers=headers,
        files={"file": ("d.csv", csv_body, "text/csv")},
    )

    result = client.post(
        "/api/v1/evaluation/run",
        headers=headers,
        json={"task": "sentiment_analysis", "dataset_id": dataset["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["eval_set"].startswith("dataset:")
    assert body["num_samples"] == 4
    assert body["accuracy"] == 0.75  # the fake model misses the sarcastic row


def test_multi_label_task_cannot_be_accuracy_evaluated(client, db_session):
    headers = _login(client, db_session, role="ml_engineer")
    response = client.post("/api/v1/evaluation/run", headers=headers, json={"task": "topic_classification"})
    assert response.status_code == 400


@pytest.mark.parametrize("run_id", ["..%5C..%5Csecrets", "not-a-uuid", "..\\..\\x"])
def test_evaluation_run_ids_cannot_escape_store(client, db_session, run_id):
    headers = _login(client, db_session, role="ml_engineer")
    response = client.get(f"/api/v1/evaluation/runs/{run_id}", headers=headers)
    assert response.status_code == 404
