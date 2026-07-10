import logging

import numpy as np
import pytest
from study_mcp.core import embeddings


class _FakeModel:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str], **_kwargs: object) -> np.ndarray:
        self.calls.append(list(texts))
        return np.zeros((len(texts), self.dim), dtype=float)


def test_prefix_applied_for_e5_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embeddings.settings,
        'EMBEDDING_MODEL',
        'intfloat/multilingual-e5-small',
    )
    engine = embeddings.EmbeddingEngine()
    assert engine._prefix(['hello'], 'passage') == ['passage: hello']


def test_prefix_not_applied_for_non_e5_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embeddings.settings, 'EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5'
    )
    engine = embeddings.EmbeddingEngine()
    assert engine._prefix(['hello'], 'passage') == ['hello']


def test_embed_texts_uses_passage_prefix_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embeddings.settings,
        'EMBEDDING_MODEL',
        'intfloat/multilingual-e5-small',
    )
    monkeypatch.setattr(embeddings.settings, 'EMBEDDING_DIM', 4)
    fake_model = _FakeModel(dim=4)
    monkeypatch.setattr(
        embeddings, 'SentenceTransformer', lambda _name: fake_model
    )

    engine = embeddings.EmbeddingEngine()
    result = engine.embed_texts(['hello world'])

    assert fake_model.calls[-1] == ['passage: hello world']
    assert len(result[0]) == 4


def test_embed_query_uses_query_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embeddings.settings,
        'EMBEDDING_MODEL',
        'intfloat/multilingual-e5-small',
    )
    monkeypatch.setattr(embeddings.settings, 'EMBEDDING_DIM', 4)
    fake_model = _FakeModel(dim=4)
    monkeypatch.setattr(
        embeddings, 'SentenceTransformer', lambda _name: fake_model
    )

    engine = embeddings.EmbeddingEngine()
    engine.embed_query('what is python')

    # calls[0] is _load_model's own internal dim-validation probe
    assert fake_model.calls[-1] == ['query: what is python']


def test_load_model_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings.settings, 'EMBEDDING_DIM', 4)
    fake_model = _FakeModel(dim=4)
    construction_count = 0

    def _construct(_name: str) -> _FakeModel:
        nonlocal construction_count
        construction_count += 1
        return fake_model

    monkeypatch.setattr(embeddings, 'SentenceTransformer', _construct)

    engine = embeddings.EmbeddingEngine()
    engine.embed_texts(['first'])
    engine.embed_texts(['second'])

    assert construction_count == 1


def test_validate_dim_logs_error_on_mismatch(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(embeddings.settings, 'EMBEDDING_DIM', 999)
    fake_model = _FakeModel(dim=4)
    monkeypatch.setattr(
        embeddings, 'SentenceTransformer', lambda _name: fake_model
    )

    engine = embeddings.EmbeddingEngine()
    with caplog.at_level(logging.ERROR, logger='study_mcp.core.embeddings'):
        engine._load_model()

    assert 'EMBEDDING_DIM mismatch' in caplog.text


def test_validate_dim_silent_when_matching(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(embeddings.settings, 'EMBEDDING_DIM', 4)
    fake_model = _FakeModel(dim=4)
    monkeypatch.setattr(
        embeddings, 'SentenceTransformer', lambda _name: fake_model
    )

    engine = embeddings.EmbeddingEngine()
    with caplog.at_level(logging.ERROR, logger='study_mcp.core.embeddings'):
        engine._load_model()

    assert 'EMBEDDING_DIM mismatch' not in caplog.text
