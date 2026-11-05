"""
Integrated Gradients (Sundararajan et al., 2017) for HF sequence classifiers.

For input embeddings x and a baseline x' (here: every non-special token
replaced by [PAD], special tokens kept), the attribution of dimension i is

    IG_i(x) = (x_i - x'_i) * ∫_0^1 ∂F(x' + α(x - x')) / ∂x_i dα

approximated with a Riemann (trapezoid) sum over `n_steps` points, run as
batched forward/backward passes of at most `internal_batch_size` points
(default: all at once). Smaller batches give the same attributions with a
bounded activation peak, for small hosts. Per-token scores are the sum over the
embedding dimension; sub-word pieces are then merged back into the
original words using the fast tokenizer's word alignment.

IG satisfies *completeness*: Σ attributions ≈ F(x) − F(x'). We report the
gap as `convergence_delta` so a caller can see how faithful the
approximation was (small |delta| relative to the score gap = trustworthy).
"""

from dataclasses import dataclass
from typing import List

from backend.core.exceptions import ModelInferenceError
from backend.explainability.base_explainer import BaseExplainer, TokenAttribution


@dataclass
class Explanation:
    label: str
    target_score: float
    baseline_score: float
    convergence_delta: float
    attributions: List[TokenAttribution]


class IntegratedGradientsExplainer(BaseExplainer):
    def __init__(self, model, n_steps: int = 32, max_length: int = 128, internal_batch_size: int | None = None) -> None:
        # `model` is a BertModel-family strategy exposing hf_model / hf_tokenizer.
        self._model = model
        self._n_steps = n_steps
        self._max_length = max_length
        if internal_batch_size is None:
            from backend.config.settings import get_settings

            internal_batch_size = get_settings().explain_batch_size
        self._batch = internal_batch_size if internal_batch_size and internal_batch_size > 0 else n_steps + 1

    def explain(self, text: str, predicted_label: str) -> List[TokenAttribution]:
        return self.explain_full(text, predicted_label).attributions

    def explain_full(self, text: str, target_label: str) -> Explanation:
        import torch

        hf_model = self._model.hf_model
        tokenizer = self._model.hf_tokenizer
        if not getattr(tokenizer, "is_fast", False):
            raise ModelInferenceError("Explanations need a fast tokenizer for word alignment.")

        target_idx = self._model.label_index(target_label)
        multi_label = hf_model.config.problem_type == "multi_label_classification"

        encoding = tokenizer(text, return_tensors="pt", truncation=True, max_length=self._max_length)
        input_ids = encoding["input_ids"]
        attention_mask = encoding["attention_mask"]

        embedding_layer = hf_model.get_input_embeddings()
        pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
        special_mask = torch.tensor(
            tokenizer.get_special_tokens_mask(input_ids[0].tolist(), already_has_special_tokens=True),
            dtype=torch.bool,
        )
        baseline_ids = torch.where(special_mask, input_ids[0], torch.full_like(input_ids[0], pad_id)).unsqueeze(0)

        with torch.no_grad():
            x = embedding_layer(input_ids)
            x_base = embedding_layer(baseline_ids)

        alphas = torch.linspace(0.0, 1.0, self._n_steps + 1).view(-1, 1, 1)

        def score(logits):
            probs = torch.sigmoid(logits) if multi_label else torch.softmax(logits, dim=-1)
            return probs[:, target_idx]

        was_training = hf_model.training
        hf_model.eval()
        grad_chunks, score_chunks = [], []
        with torch.enable_grad():
            for chunk in torch.split(alphas, self._batch):
                path = (x_base + chunk * (x - x_base)).detach().requires_grad_(True)
                chunk_scores = score(hf_model(inputs_embeds=path, attention_mask=attention_mask.expand(path.shape[0], -1)).logits)
                (chunk_grads,) = torch.autograd.grad(chunk_scores.sum(), path)
                grad_chunks.append(chunk_grads.detach())
                score_chunks.append(chunk_scores.detach())
        hf_model.train(was_training)
        grads, scores = torch.cat(grad_chunks), torch.cat(score_chunks)

        # Trapezoid rule over the path.
        avg_grads = ((grads[:-1] + grads[1:]) / 2).mean(dim=0)
        token_attr = ((x[0] - x_base[0]) * avg_grads).sum(dim=-1).detach()

        target_score = float(scores[-1])
        baseline_score = float(scores[0])
        delta = float(token_attr.sum()) - (target_score - baseline_score)

        words = _merge_to_words(text, encoding, token_attr.tolist())
        return Explanation(
            label=target_label,
            target_score=round(target_score, 6),
            baseline_score=round(baseline_score, 6),
            convergence_delta=round(delta, 6),
            attributions=words,
        )


def _merge_to_words(text: str, encoding, token_scores: List[float]) -> List[TokenAttribution]:
    """Sum sub-word attributions into whole words, in original-text order."""
    word_ids = encoding.word_ids(0)
    merged: dict[int, float] = {}
    spans: dict[int, tuple[int, int]] = {}
    for tok_idx, word_id in enumerate(word_ids):
        if word_id is None:
            continue
        merged[word_id] = merged.get(word_id, 0.0) + token_scores[tok_idx]
        start, end = encoding.token_to_chars(0, tok_idx)
        prev = spans.get(word_id)
        spans[word_id] = (start, end) if prev is None else (min(prev[0], start), max(prev[1], end))

    return [
        TokenAttribution(token=text[spans[w][0]:spans[w][1]], importance=round(merged[w], 6))
        for w in sorted(merged)
    ]
