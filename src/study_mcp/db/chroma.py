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
    ) -> list[dict[str, str | float]]:
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

        hits: list[dict[str, str | float]] = []
        for doc, meta, dist in zip(
            results['documents'][0],  # type: ignore[index]
            results['metadatas'][0],  # type: ignore[index]
            results['distances'][0],  # type: ignore[index]
        ):
            hits.append({
                'text': doc,
                'source': str(meta.get('source', '')),
                'material_id': str(meta.get('material_id', '')),
                'score': round(1 - float(dist), 4),
            })
        return hits

    def list_materials(self) -> list[dict[str, str]]:
        collection = self._get_collection()
        results = collection.get(include=['metadatas'])

        seen: dict[str, dict[str, str]] = {}
        for meta in results['metadatas']:  # type: ignore[union-attr]
            mid = str(meta.get('material_id', ''))
            if mid and mid not in seen:
                seen[mid] = {
                    'material_id': mid,
                    'source': str(meta.get('source', '')),
                }
        return list(seen.values())


chroma_repository = ChromaRepository()
