import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from study_mcp.core.config import settings
from study_mcp.core.embeddings import embedding_engine


class PgVectorRepository:
    def __init__(self) -> None:
        self._conn: PgConnection | None = None

    def _get_conn(self) -> PgConnection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(settings.DATABASE_URL)
            self._conn.autocommit = True
        return self._conn

    def save_chunks(
        self,
        material_id: str,
        source_name: str,
        chunks: list[str],
    ) -> int:
        conn = self._get_conn()
        embeddings = embedding_engine.embed_texts(chunks)

        rows = [
            (
                f'{material_id}_{i}',
                material_id,
                source_name,
                i,
                chunk,
                embedding,
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        with conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO study_chunks (
                        id, material_id, source,
                        chunk_index, content, embedding
                    )
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE
                        SET content   = EXCLUDED.content,
                            embedding = EXCLUDED.embedding
                    """,
                    rows,
                    template='(%s, %s, %s, %s, %s, %s::vector)',
                )
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, str | float]]:
        conn = self._get_conn()
        query_embedding = embedding_engine.embed_query(query)

        where_clause = 'WHERE material_id = %s' if material_id else ''
        params: tuple[object, ...] = (
            (
                str(query_embedding),
                material_id,
                str(query_embedding),
                top_k,
            )
            if material_id
            else (str(query_embedding), str(query_embedding), top_k)
        )

        sql = f"""
            SELECT content, source, material_id,
                   1 - (embedding <=> %s::vector) AS score
            FROM   study_chunks
            {where_clause}
            ORDER  BY embedding <=> %s::vector
            LIMIT  %s
        """

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [
            {
                'text': str(r['content']),
                'source': str(r['source']),
                'material_id': str(r['material_id']),
                'score': round(float(r['score']), 4),
            }
            for r in rows
        ]

    def list_materials(self) -> list[dict[str, str]]:
        conn = self._get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT DISTINCT material_id, source '
                'FROM study_chunks '
                'ORDER BY material_id'
            )
            rows = cur.fetchall()

        return [
            {
                'material_id': str(r['material_id']),
                'source': str(r['source']),
            }
            for r in rows
        ]


pgvector_repository = PgVectorRepository()
