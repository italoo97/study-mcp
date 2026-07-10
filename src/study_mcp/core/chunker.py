import re

from study_mcp.core.config import settings


def _split_by_headings(text: str) -> list[str]:
    parts = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_by_size(text: str, size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def chunk_text(text: str) -> list[str]:
    sections = _split_by_headings(text)
    chunks: list[str] = []

    for section in sections:
        if len(section) <= settings.CHUNK_SIZE:
            chunks.append(section)
        else:
            chunks.extend(
                _split_by_size(
                    section,
                    settings.CHUNK_SIZE,
                    settings.CHUNK_OVERLAP,
                )
            )

    return [c for c in chunks if len(c) > 30]
