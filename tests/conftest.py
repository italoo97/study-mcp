from typing import Any

import pytest


class FakeRepository:
    """In-memory VectorRepository double - no embedding model, no DB."""

    def __init__(self) -> None:
        self.chunks: dict[str, list[dict[str, Any]]] = {}
        self.sources: dict[str, str] = {}

    def save_chunks(
        self,
        material_id: str,
        source_name: str,
        chunks: list[str],
        source_type: str = 'material',
        start_times: list[float | None] | None = None,
    ) -> int:
        times = start_times or [None] * len(chunks)
        self.sources[material_id] = source_name
        self.chunks[material_id] = [
            {
                'text': chunk,
                'chunk_index': i,
                'source': source_name,
                'source_type': source_type,
                'start_time': times[i],
            }
            for i, chunk in enumerate(chunks)
        ]
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, Any]]:
        hits = []
        for mid, chunk_list in self.chunks.items():
            if material_id and mid != material_id:
                continue
            for c in chunk_list:
                if query.lower() in c['text'].lower():
                    hits.append({**c, 'material_id': mid, 'score': 1.0})
        return hits[:top_k]

    def list_materials(self) -> list[dict[str, str]]:
        return [
            {'material_id': mid, 'source': src}
            for mid, src in self.sources.items()
        ]

    def delete_material(self, material_id: str) -> int:
        deleted = len(self.chunks.get(material_id, []))
        self.chunks.pop(material_id, None)
        self.sources.pop(material_id, None)
        return deleted

    def get_chunks_by_material(self, material_id: str) -> list[dict[str, Any]]:
        return list(self.chunks.get(material_id, []))


@pytest.fixture()
def fake_repository() -> FakeRepository:
    return FakeRepository()
