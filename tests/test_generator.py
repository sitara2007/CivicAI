import zlib
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

EMBEDDING_DIM = 384


def _fake_encode(sentences, *args, **kwargs):
    single = isinstance(sentences, str)
    items = [sentences] if single else list(sentences)

    vectors = np.stack([
        np.random.default_rng(zlib.crc32(s.encode("utf-8"))).random(
            EMBEDDING_DIM, dtype=np.float32
        )
        for s in items
    ])
    return vectors[0] if single else vectors


@pytest.fixture
def mock_sentence_transformer():
    with patch("app.services.rag.generator.SentenceTransformer") as mock_cls:
        mock_model = MagicMock(name="SentenceTransformerInstance")
        mock_model.encode.side_effect = _fake_encode
        mock_model.get_sentence_embedding_dimension.return_value = EMBEDDING_DIM
        mock_cls.return_value = mock_model
        yield mock_cls


def test_generator_uses_embeddings(mock_sentence_transformer):
    from app.services.rag.generator import Generator

    gen = Generator()

    mock_sentence_transformer.assert_called_once()

    emb = gen.model.encode(["pothole on Main St", "broken streetlight"])
    assert emb.shape == (2, EMBEDDING_DIM)
    assert emb.dtype == np.float32
