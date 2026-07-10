from typing import TYPE_CHECKING, Any, Protocol

from study_mcp.core.config import settings

if TYPE_CHECKING:
    from study_mcp.db.chroma import ChromaRepository
    from study_mcp.db.pgvector import PgVectorRepository


class VectorRepository(Protocol):
    def save_chunks(
        self,
        material_id: str,
        source_name: str,
        chunks: list[str],
    ) -> int: ...

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, str | float]]: ...

    def list_materials(self) -> list[dict[str, str]]: ...


repository: Any

if settings.VECTOR_BACKEND == 'pgvector':
    from study_mcp.db.pgvector import pgvector_repository as repository
else:
    from study_mcp.db.chroma import chroma_repository as repository

__all__ = [
    'repository',
    'VectorRepository',
    'ChromaRepository',
    'PgVectorRepository',
]
