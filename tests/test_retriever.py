from __future__ import annotations

from unittest.mock import Mock, patch

from app.services.rag.retriever import retrieve


class DummyPoint:
    def __init__(self, payload: dict[str, str], score: float) -> None:
        self.payload = payload
        self.score = score


class DummyResults:
    def __init__(self, points: list[DummyPoint]) -> None:
        self.points = points


def test_retrieve_returns_chunks_from_qdrant() -> None:
    mock_query_result = DummyResults(
        points=[
            DummyPoint(payload={"text": "Document one."}, score=0.91),
            DummyPoint(payload={"text": "Document two."}, score=0.72),
        ]
    )

    with (
        patch(
            "app.services.rag.retriever.model.encode",
            return_value=Mock(tolist=lambda: [0.1, 0.2, 0.3]),
        ) as mock_encode,
        patch(
            "app.services.rag.retriever.client.query_points",
            return_value=mock_query_result,
        ) as mock_query,
    ):
        chunks = retrieve("What is this scheme?", top_k=2)

    assert chunks == [
        {"text": "Document one.", "score": 0.91},
        {"text": "Document two.", "score": 0.72},
    ]
    mock_encode.assert_called_once_with("What is this scheme?")
    mock_query.assert_called_once_with(
        collection_name="gov_docs",
        query=[0.1, 0.2, 0.3],
        limit=2,
    )


def test_retrieve_returns_empty_list_when_no_points() -> None:
    with (
        patch(
            "app.services.rag.retriever.model.encode",
            return_value=Mock(tolist=lambda: [0.4, 0.5, 0.6]),
        ),
        patch(
            "app.services.rag.retriever.client.query_points",
            return_value=DummyResults(points=[]),
        ),
    ):
        chunks = retrieve("Empty result query", top_k=3)

    assert chunks == []


def test_retrieve_falls_back_to_pgvector_when_qdrant_times_out() -> None:
    fallback_chunks = [{"text": "Fallback document.", "score": 0.55}]

    with (
        patch(
            "app.services.rag.retriever.model.encode",
            return_value=Mock(tolist=lambda: [0.7, 0.8, 0.9]),
        ),
        patch(
            "app.services.rag.retriever.client.query_points",
            side_effect=TimeoutError("qdrant timed out"),
        ),
        patch(
            "app.services.rag.retriever._pgvector_bm25_fallback",
            return_value=fallback_chunks,
        ) as mock_fallback,
    ):
        chunks = retrieve("Fallback query", top_k=2)

    assert chunks == fallback_chunks
    mock_fallback.assert_called_once_with("Fallback query", 2)
