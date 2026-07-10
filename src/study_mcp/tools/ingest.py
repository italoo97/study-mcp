import hashlib
import logging
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

from study_mcp.core.chunker import chunk_text
from study_mcp.core.transcript import extract_start_time, parse_transcript
from study_mcp.db import repository

logger = logging.getLogger(__name__)

_DIRECT_TEXT_SUFFIXES = {'.txt', '.md'}
_TRANSCRIPT_SUFFIXES = {'.srt', '.vtt'}


class IngestService:
    def __init__(self) -> None:
        self._converter: DocumentConverter | None = None

    def _get_converter(self) -> DocumentConverter:
        if self._converter is None:
            self._converter = DocumentConverter(
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.DOCX,
                    InputFormat.PPTX,
                    InputFormat.HTML,
                    InputFormat.IMAGE,
                ]
            )
        return self._converter

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in _DIRECT_TEXT_SUFFIXES:
            return path.read_text(encoding='utf-8')
        if suffix in _TRANSCRIPT_SUFFIXES:
            return parse_transcript(path.read_text(encoding='utf-8'))
        converter = self._get_converter()
        result = converter.convert(str(path))
        return result.document.export_to_markdown()

    @staticmethod
    def _save_text(
        text: str, source_name: str, source_type: str = 'material'
    ) -> dict[str, str | int]:
        material_id = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

        existing_ids = {m['material_id'] for m in repository.list_materials()}
        if material_id in existing_ids:
            logger.info('Material already indexed: %s', source_name)
            return {
                'status': 'already_indexed',
                'material_id': material_id,
            }

        started = time.perf_counter()
        chunks, discarded = chunk_text(text)
        start_times = [extract_start_time(c) for c in chunks]
        saved = repository.save_chunks(
            material_id,
            source_name,
            chunks,
            source_type=source_type,
            start_times=start_times,
        )
        duration = time.perf_counter() - started
        logger.info(
            'Ingested %s: %d chunks saved, %d discarded (%.2fs)',
            source_name,
            saved,
            discarded,
            duration,
        )
        return {
            'material_id': material_id,
            'source': source_name,
            'chunks_saved': saved,
            'chunks_discarded': discarded,
            'status': 'ok',
        }

    def ingest_file(
        self,
        file_path: str,
        material_name: str | None = None,
    ) -> dict[str, str | int]:
        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return {'error': f'File not found: {file_path}'}

        source_name = material_name or path.name
        source_type = (
            'transcript'
            if path.suffix.lower() in _TRANSCRIPT_SUFFIXES
            else 'material'
        )

        try:
            text = self._extract_text(path)
        except Exception as exc:
            logger.error('Failed to read %s: %s', path.name, exc)
            return {'error': f'Failed to read {path.name}: {exc}'}

        return self._save_text(text, source_name, source_type)

    def ingest_text(
        self,
        text: str,
        material_name: str,
        source_type: str = 'transcript',
    ) -> dict[str, str | int]:
        result = self._save_text(text, material_name, source_type)
        result['source_type'] = source_type
        return result


ingest_service = IngestService()


def ingest_file_tool(
    file_path: str,
    material_name: str | None = None,
) -> dict[str, str | int]:
    """
    Ingest a local file into the vector store.
    Supported formats: PDF, DOCX, PPTX, HTML, images, plain text and
    video transcripts (.txt, .md, .srt, .vtt).

    Args:
        file_path: Absolute or relative path to the file.
        material_name: Optional human-friendly name.

    Returns:
        dict with material_id, source, chunks_saved and status,
        or a dict with 'error' if the file could not be read.
    """
    return ingest_service.ingest_file(file_path, material_name)


def ingest_text_tool(
    text: str,
    material_name: str,
    source_type: str = 'transcript',
) -> dict[str, str | int]:
    """
    Ingest raw text (e.g. a pasted video transcript) into the vector
    store, following the same chunk -> embed -> save pipeline as
    ingest_file_tool.

    Args:
        text: Raw text content to ingest.
        material_name: Human-friendly name for this material.
        source_type: One of 'transcript', 'notes', 'article'.

    Returns:
        dict with material_id, source, chunks_saved and status.
    """
    return ingest_service.ingest_text(text, material_name, source_type)
