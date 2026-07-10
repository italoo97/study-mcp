import uuid
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

from study_mcp.core.chunker import chunk_text
from study_mcp.db import repository


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

    def ingest_file(
        self,
        file_path: str,
        material_name: str | None = None,
    ) -> dict[str, str | int]:
        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return {'error': f'File not found: {file_path}'}

        source_name = material_name or path.name
        material_id = str(uuid.uuid4())

        converter = self._get_converter()
        result = converter.convert(str(path))
        markdown = result.document.export_to_markdown()

        chunks = chunk_text(markdown)
        saved = repository.save_chunks(material_id, source_name, chunks)

        return {
            'material_id': material_id,
            'source': source_name,
            'chunks_saved': saved,
            'status': 'ok',
        }


ingest_service = IngestService()


def ingest_file_tool(
    file_path: str,
    material_name: str | None = None,
) -> dict[str, str | int]:
    """
    Ingest a local file into the vector store.
    Supported formats: PDF, DOCX, PPTX, HTML, images.

    Args:
        file_path: Absolute or relative path to the file.
        material_name: Optional human-friendly name.

    Returns:
        dict with material_id, source, chunks_saved and status.
    """
    return ingest_service.ingest_file(file_path, material_name)
