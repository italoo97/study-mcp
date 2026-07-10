import logging

from study_mcp.core.config import settings
from study_mcp.db import repository

logger = logging.getLogger(__name__)


class SearchService:
    @staticmethod
    def search(
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> dict[str, object]:
        if not query.strip():
            return {'error': 'Query cannot be empty.'}

        logger.info(
            'Search: query=%r top_k=%d backend=%s',
            query,
            top_k,
            settings.VECTOR_BACKEND,
        )
        results = repository.search_chunks(
            query=query,
            top_k=top_k,
            material_id=material_id,
        )

        if not results:
            return {'results': [], 'message': 'No relevant content found.'}

        return {
            'query': query,
            'results': results,
            'total': len(results),
        }


_search_service = SearchService()


def search_tool(
    query: str,
    top_k: int = 5,
    material_id: str | None = None,
) -> dict[str, object]:
    """
    Search ingested study materials using semantic similarity.

    Args:
        query: The question or topic to search for.
        top_k: Number of results to return (default 5).
        material_id: If provided, restrict search to a single material.
    """
    return _search_service.search(query, top_k, material_id)
