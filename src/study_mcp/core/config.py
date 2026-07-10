from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Embedding
    EMBEDDING_MODEL: str = 'intfloat/multilingual-e5-small'
    EMBEDDING_DIM: int = 384

    # ChromaDB
    CHROMA_PATH: str = './chroma_db'
    CHROMA_COLLECTION: str = 'study_chunks'

    # pgvector / Supabase — if set, pgvector is used automatically
    DATABASE_URL: str = ''

    # Notion
    NOTION_TOKEN: str = ''
    NOTION_DATABASE_ID: str = ''

    # Chunking
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    @property
    def VECTOR_BACKEND(self) -> str:
        return 'pgvector' if self.DATABASE_URL else 'chroma'

    model_config = SettingsConfigDict(
        env_file=Path('.env'),
        env_file_encoding='utf-8',
        case_sensitive=True,
    )


settings = Settings()
