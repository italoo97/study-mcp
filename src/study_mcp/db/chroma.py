import chromadb
import numpy as np
from chromadb.api import ClientAPI
from chromadb.api.types import Metadata, Where

from study_mcp.core.config import settings
from study_mcp.core.embeddings import embedding_engine


class ChromaRepository:
    def __init__(self) -> None:
        self._client: ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    def _get_collection(self) -> chromadb.Collection:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PATH,
            )
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            embedding_function=None,
            configuration={
                'hnsw': {'space': 'cosine'},
            },
        )
        return self._collection

    def save_chunks(
        self,
        material_id: str,
        source_name: str,
        chunks: list[str],
        source_type: str = 'material',
        start_times: list[float | None] | None = None,
    ) -> int:
        collection = self._get_collection()
        embeddings = np.array(
            embedding_engine.embed_texts(chunks), dtype=np.float32
        )

        ids = [f'{material_id}_{i}' for i in range(len(chunks))]
        metadatas: list[Metadata] = [
            {
                'material_id': material_id,
                'source': source_name,
                'chunk_index': i,
                'source_type': source_type,
                'start_time': start_times[i] if start_times else None,
            }
            for i in range(len(chunks))
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, str | float | None]]:
        collection = self._get_collection()
        query_embedding = np.array(
            [embedding_engine.embed_query(query)], dtype=np.float32
        )

        where: Where | None = (
            {'material_id': material_id} if material_id else None
        )
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where,
            include=['documents', 'metadatas', 'distances'],
        )

        documents = results['documents']
        metadatas = results['metadatas']
        distances = results['distances']

        if documents is None or metadatas is None or distances is None:
            return []

        hits: list[dict[str, str | float | None]] = []
        for doc, meta, dist in zip(
            documents[0],
            metadatas[0],
            distances[0],
        ):
            start_time = meta.get('start_time')
            hits.append({
                'text': doc,
                'source': str(meta.get('source', '')),
                'material_id': str(meta.get('material_id', '')),
                'source_type': str(meta.get('source_type', '')),
                'start_time': (
                    start_time if isinstance(start_time, float) else None
                ),
                'score': round(1 - float(dist), 4),
            })
        return hits

    def list_materials(self) -> list[dict[str, str]]:
        collection = self._get_collection()
        results = collection.get(include=['metadatas'])

        raw_metadatas = results['metadatas']
        if raw_metadatas is None:
            return []

        seen: dict[str, dict[str, str]] = {}
        for meta in raw_metadatas:
            mid = str(meta.get('material_id', ''))
            if mid and mid not in seen:
                seen[mid] = {
                    'material_id': mid,
                    'source': str(meta.get('source', '')),
                }
        return list(seen.values())

    def delete_material(self, material_id: str) -> int:
        collection = self._get_collection()
        where: Where = {'material_id': material_id}
        existing = collection.get(where=where, include=[])
        ids = existing['ids']
        if ids:
            collection.delete(ids=ids)
        return len(ids)

    def get_chunks_by_material(
        self, material_id: str
    ) -> list[dict[str, str | int | float | None]]:
        collection = self._get_collection()
        where: Where = {'material_id': material_id}
        results = collection.get(
            where=where,
            include=['documents', 'metadatas'],
        )

        documents = results['documents']
        metadatas = results['metadatas']
        if documents is None or metadatas is None:
            return []

        indexed: list[tuple[int, dict[str, str | int | float | None]]] = []
        for doc, meta in zip(documents, metadatas):
            idx = int(meta.get('chunk_index', 0))  # type: ignore[arg-type]
            start_time = meta.get('start_time')
            indexed.append((
                idx,
                {
                    'text': doc,
                    'source': str(meta.get('source', '')),
                    'chunk_index': idx,
                    'source_type': str(meta.get('source_type', '')),
                    'start_time': (
                        start_time if isinstance(start_time, float) else None
                    ),
                },
            ))
        indexed.sort(key=lambda pair: pair[0])
        return [c for _, c in indexed]

    def material_exists(self, material_id: str) -> bool:
        collection = self._get_collection()
        existing = collection.get(ids=[f'{material_id}_0'], include=[])
        return bool(existing['ids'])

    def count_chunks_by_material(self) -> dict[str, int]:
        collection = self._get_collection()
        results = collection.get(include=['metadatas'])
        raw_metadatas = results['metadatas']
        if raw_metadatas is None:
            return {}

        counts: dict[str, int] = {}
        for meta in raw_metadatas:
            mid = str(meta.get('material_id', ''))
            if mid:
                counts[mid] = counts.get(mid, 0) + 1
        return counts


chroma_repository = ChromaRepository()
