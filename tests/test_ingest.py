from pathlib import Path

import pytest
from study_mcp.tools import ingest

from tests.conftest import FakeRepository

SRT_SAMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello there, welcome to the video.

2
00:00:04,500 --> 00:00:08,000
Today we're going to talk about Python and testing.
"""


class _RaisingConverter:
    @staticmethod
    def convert(path: str) -> None:
        raise ValueError('unsupported or corrupted file')


@pytest.fixture(autouse=True)
def _patch_repository(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(ingest, 'repository', fake_repository)


def test_ingest_text_saves_via_repository(
    fake_repository: FakeRepository,
) -> None:
    result = ingest.ingest_text_tool(
        'Python is a great language. ' * 10, 'My Notes'
    )
    assert result['status'] == 'ok'
    assert result['source'] == 'My Notes'
    assert isinstance(result['chunks_saved'], int)
    assert result['chunks_saved'] > 0
    assert result['material_id'] in fake_repository.chunks


def test_ingest_text_dedup_returns_already_indexed() -> None:
    text = 'Repeated content for dedup test. ' * 10
    first = ingest.ingest_text_tool(text, 'First Name')
    second = ingest.ingest_text_tool(text, 'Second Name')

    assert first['status'] == 'ok'
    assert second['status'] == 'already_indexed'
    assert second['material_id'] == first['material_id']


def test_ingest_file_missing_returns_error() -> None:
    result = ingest.ingest_file_tool('/no/such/file/anywhere.txt')
    assert 'error' in result


def test_ingest_file_txt_reads_directly(
    tmp_path: Path, fake_repository: FakeRepository
) -> None:
    file_path = tmp_path / 'notes.txt'
    file_path.write_text('Plain text content. ' * 10, encoding='utf-8')

    result = ingest.ingest_file_tool(str(file_path))

    assert result['status'] == 'ok'
    material_id = result['material_id']
    assert isinstance(material_id, str)
    chunks = fake_repository.chunks[material_id]
    assert chunks[0]['source_type'] == 'material'


def test_ingest_file_srt_routes_through_transcript_parser(
    tmp_path: Path, fake_repository: FakeRepository
) -> None:
    file_path = tmp_path / 'lecture.srt'
    file_path.write_text(SRT_SAMPLE, encoding='utf-8')

    result = ingest.ingest_file_tool(str(file_path))

    assert result['status'] == 'ok'
    material_id = result['material_id']
    assert isinstance(material_id, str)
    chunks = fake_repository.chunks[material_id]
    assert chunks[0]['source_type'] == 'transcript'
    assert chunks[0]['start_time'] == 1.0


def test_ingest_file_extraction_error_returns_error_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / 'broken.pdf'
    file_path.write_bytes(b'not a real pdf')

    monkeypatch.setattr(
        ingest.IngestService,
        '_get_converter',
        lambda self: _RaisingConverter(),
    )

    result = ingest.ingest_file_tool(str(file_path))
    assert 'error' in result
    assert 'broken.pdf' in result['error']
