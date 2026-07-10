import logging

from sentence_transformers import SentenceTransformer

from study_mcp.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info('Loading embedding model %s', settings.EMBEDDING_MODEL)
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self._validate_dim()
        return self._model

    def _validate_dim(self) -> None:
        actual = len(self.embed_query('test'))
        if actual != settings.EMBEDDING_DIM:
            logger.error(
                'EMBEDDING_DIM mismatch: configured %d, model '
                'produces %d. Update EMBEDDING_DIM in your .env.',
                settings.EMBEDDING_DIM,
                actual,
            )

    @staticmethod
    def _prefix(texts: list[str], kind: str) -> list[str]:
        if 'e5' not in settings.EMBEDDING_MODEL.lower():
            return texts
        return [f'{kind}: {text}' for text in texts]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(
            self._prefix(texts, 'passage'),
            batch_size=32,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        model = self._load_model()
        embeddings = model.encode(
            self._prefix([query], 'query'),
            normalize_embeddings=True,
        )
        return embeddings[0].tolist()


embedding_engine = EmbeddingEngine()
