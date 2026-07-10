import re

from study_mcp.core.config import settings

_MIN_CHUNK_LENGTH = 30
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def _split_by_headings(text: str) -> list[str]:
    parts = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_into_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _split_into_sentences(text: str) -> list[str]:
    # ponytail: naive punctuation split, doesn't handle abbreviations
    # (e.g. "Dr. Smith" splits in two). Ceiling: occasional over-split.
    # Upgrade path: a real sentence tokenizer (nltk/spacy) if search
    # quality suffers because of it.
    sentences = _SENTENCE_RE.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _tail_overlap(
    sentences: list[str], overlap_chars: int
) -> tuple[list[str], int]:
    """Keep whole trailing sentences until ~overlap_chars is covered."""
    tail: list[str] = []
    tail_len = 0
    for sentence in reversed(sentences):
        if tail and tail_len >= overlap_chars:
            break
        tail.insert(0, sentence)
        tail_len += len(sentence) + 1
    return tail, tail_len


def _group_sentences(
    sentences: list[str], size: int, overlap_chars: int
) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current and current_len + len(sentence) + 1 > size:
            chunks.append(' '.join(current))
            current, current_len = _tail_overlap(current, overlap_chars)

        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        chunks.append(' '.join(current))

    return chunks


def _split_long_section(text: str, size: int, overlap_chars: int) -> list[str]:
    chunks: list[str] = []
    for paragraph in _split_into_paragraphs(text):
        if len(paragraph) <= size:
            chunks.append(paragraph)
            continue
        sentences = _split_into_sentences(paragraph)
        chunks.extend(_group_sentences(sentences, size, overlap_chars))
    return chunks


def chunk_text(text: str) -> tuple[list[str], int]:
    """Chunk text by heading, then paragraph, then sentence.

    Returns (chunks, discarded_count) - discarded chunks are ones that
    fell below the minimum length filter.
    """
    sections = _split_by_headings(text)
    raw_chunks: list[str] = []

    for section in sections:
        if len(section) <= settings.CHUNK_SIZE:
            raw_chunks.append(section)
        else:
            raw_chunks.extend(
                _split_long_section(
                    section, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP
                )
            )

    chunks = [c for c in raw_chunks if len(c) > _MIN_CHUNK_LENGTH]
    discarded = len(raw_chunks) - len(chunks)
    return chunks, discarded
