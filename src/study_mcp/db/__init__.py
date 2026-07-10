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
        source_type: str = 'material',
        start_times: list[float | None] | None = None,
    ) -> int: ...

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, str | float | None]]: ...

    def list_materials(self) -> list[dict[str, str]]: ...

    def delete_material(self, material_id: str) -> int: ...

    def get_chunks_by_material(
        self, material_id: str
    ) -> list[dict[str, str | int | float | None]]: ...


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
