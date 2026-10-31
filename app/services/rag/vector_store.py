import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.services.rag.chunker import chunk_text
from app.services.rag.loader import load_pdf

logger = logging.getLogger(__name__)


class LazySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def encode(self, text: list[str]):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model.encode(text)


settings = get_settings()
model = LazySentenceTransformer(settings.rag_embedding_model)
collection_name = settings.rag_collection_name


def _local_reset_hint(path: Path) -> str:
    return (
        f"Local Qdrant storage at '{path}' appears to be corrupted or invalid. "
        "If you do not need remote persistence, remove the folder and restart the application: "
        f"rm -rf {path} && mkdir -p {path}. "
        "Alternatively, set QDRANT_URL to a valid remote endpoint."
    )


def _init_qdrant_client() -> QdrantClient:
    if settings.qdrant_url.strip():
        logger.info("qdrant_client_initializing", extra={"mode": "remote", "url": settings.qdrant_url})
        return QdrantClient(url=settings.qdrant_url)

    local_path = Path(settings.rag_qdrant_path)
    logger.info("qdrant_client_initializing", extra={"mode": "local", "path": str(local_path)})
    try:
        return QdrantClient(path=str(local_path))
    except Exception as exc:
        error_message = _local_reset_hint(local_path)
        logger.exception("qdrant_local_initialization_failed", extra={"path": str(local_path)})
        raise RuntimeError(error_message) from exc


client = _init_qdrant_client()


def _wrap_qdrant_error(exc: Exception) -> RuntimeError:
    if settings.qdrant_url.strip():
        return RuntimeError(
            f"Remote Qdrant initialization failed for URL '{settings.qdrant_url}'. "
            "Verify network connectivity, endpoint reachability, and your QDRANT_URL setting."
        )

    local_path = Path(settings.rag_qdrant_path)
    return RuntimeError(_local_reset_hint(local_path))


def create_collection():
    try:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": 384,
                    "distance": "Cosine",
                },
            )
    except Exception as exc:
        raise _wrap_qdrant_error(exc) from exc


def store_chunks(chunks: list[str]) -> None:
    create_collection()

    embeddings = model.encode(chunks)
    points: list[PointStruct] = []

    for i, vector in enumerate(embeddings):
        points.append(
            PointStruct(
                id=i,
                vector=vector.tolist(),
                payload={"text": chunks[i]},
            )
        )

    try:
        client.upsert(collection_name=collection_name, points=points)
    except Exception as exc:
        raise _wrap_qdrant_error(exc) from exc


if __name__ == "__main__":
    text = load_pdf("data/documents/scheme.pdf")
    chunks = chunk_text(text)
    store_chunks(chunks)
    print("Stored:", len(chunks))
