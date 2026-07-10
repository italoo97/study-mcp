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
            self._ensure_table()
        return self._conn

    def _ensure_table(self) -> None:
        conn = self._conn
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS study_chunks (
                    id            TEXT PRIMARY KEY,
                    material_id   TEXT        NOT NULL,
                    source        TEXT        NOT NULL,
                    chunk_index   INTEGER     NOT NULL,
                    content       TEXT        NOT NULL,
                    embedding     vector({settings.EMBEDDING_DIM}),
                    source_type   TEXT,
                    start_time    REAL        NULL,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                'ALTER TABLE study_chunks '
                'ADD COLUMN IF NOT EXISTS source_type TEXT;'
            )
            cur.execute(
                'ALTER TABLE study_chunks '
                'ADD COLUMN IF NOT EXISTS start_time REAL NULL;'
            )

            cur.execute(
                'SELECT indexdef FROM pg_indexes '
                "WHERE indexname = 'study_chunks_embedding_idx'"
            )
            existing_index = cur.fetchone()
            if existing_index and 'ivfflat' in existing_index[0]:
                cur.execute('DROP INDEX study_chunks_embedding_idx;')

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS study_chunks_embedding_idx
                    ON study_chunks
                    USING hnsw (embedding vector_cosine_ops);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS study_chunks_material_idx
                    ON study_chunks (material_id);
                """
            )

    def save_chunks(
        self,
        material_id: str,
        source_name: str,
        chunks: list[str],
        source_type: str = 'material',
        start_times: list[float | None] | None = None,
    ) -> int:
        conn = self._get_conn()
        embeddings = embedding_engine.embed_texts(chunks)
        times = start_times or [None] * len(chunks)

        rows = [
            (
                f'{material_id}_{i}',
                material_id,
                source_name,
                i,
                chunk,
                embedding,
                source_type,
                times[i],
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
                        chunk_index, content, embedding,
                        source_type, start_time
                    )
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE
                        SET content     = EXCLUDED.content,
                            embedding   = EXCLUDED.embedding,
                            source_type = EXCLUDED.source_type,
                            start_time  = EXCLUDED.start_time
                    """,
                    rows,
                    template='(%s, %s, %s, %s, %s, %s::vector, %s, %s)',
                )
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[dict[str, str | float | None]]:
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
            SELECT content, source, material_id, source_type,
                   start_time,
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
                'source_type': str(r['source_type']),
                'start_time': (
                    float(r['start_time'])
                    if r['start_time'] is not None
                    else None
                ),
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

    def delete_material(self, material_id: str) -> int:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM study_chunks WHERE material_id = %s',
                (material_id,),
            )
            return int(cur.rowcount)

    def get_chunks_by_material(
        self, material_id: str
    ) -> list[dict[str, str | int | float | None]]:
        conn = self._get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT content, source, chunk_index, '
                '       source_type, start_time '
                'FROM study_chunks '
                'WHERE material_id = %s '
                'ORDER BY chunk_index',
                (material_id,),
            )
            rows = cur.fetchall()

        return [
            {
                'text': str(r['content']),
                'source': str(r['source']),
                'chunk_index': int(r['chunk_index']),
                'source_type': str(r['source_type']),
                'start_time': (
                    float(r['start_time'])
                    if r['start_time'] is not None
                    else None
                ),
            }
            for r in rows
        ]

    def material_exists(self, material_id: str) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM study_chunks WHERE id = %s LIMIT 1',
                (f'{material_id}_0',),
            )
            return cur.fetchone() is not None

    def count_chunks_by_material(self) -> dict[str, int]:
        conn = self._get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT material_id, COUNT(*) AS chunks '
                'FROM study_chunks '
                'GROUP BY material_id'
            )
            rows = cur.fetchall()
        return {str(r['material_id']): int(r['chunks']) for r in rows}


pgvector_repository = PgVectorRepository()
