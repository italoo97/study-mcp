import hashlib
from pathlib import Path

import pytest
from study_mcp.core.config import settings
from study_mcp.core.embeddings import embedding_engine
from study_mcp.db.chroma import ChromaRepository


def _fake_vector(text: str, dim: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(dim)]


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        embedding_engine,
        'embed_texts',
        lambda texts: [_fake_vector(t) for t in texts],
    )
    monkeypatch.setattr(embedding_engine, 'embed_query', _fake_vector)


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ChromaRepository:
    monkeypatch.setattr(settings, 'CHROMA_PATH', str(tmp_path))
    monkeypatch.setattr(settings, 'CHROMA_COLLECTION', 'test_collection')
    return ChromaRepository()


def test_save_and_list_materials(repo: ChromaRepository) -> None:
    repo.save_chunks('mat-1', 'Material One', ['chunk a', 'chunk b'])
    materials = repo.list_materials()
    assert materials == [{'material_id': 'mat-1', 'source': 'Material One'}]


def test_save_returns_chunk_count(repo: ChromaRepository) -> None:
    saved = repo.save_chunks('mat-1', 'Material One', ['a', 'b', 'c'])
    assert saved == 3


def test_search_finds_saved_chunks(repo: ChromaRepository) -> None:
    repo.save_chunks('mat-1', 'Material One', ['python programming'])
    repo.save_chunks('mat-2', 'Material Two', ['completely unrelated topic'])

    results = repo.search_chunks('python programming', top_k=1)
    assert len(results) == 1
    assert results[0]['text'] == 'python programming'
    assert results[0]['material_id'] == 'mat-1'


def test_search_can_restrict_to_material_id(repo: ChromaRepository) -> None:
    repo.save_chunks('mat-1', 'Material One', ['shared text'])
    repo.save_chunks('mat-2', 'Material Two', ['shared text'])

    results = repo.search_chunks('shared text', material_id='mat-2')
    assert all(r['material_id'] == 'mat-2' for r in results)


def test_search_no_matches_returns_empty(repo: ChromaRepository) -> None:
    assert repo.search_chunks('anything') == []


def test_save_with_source_type_and_start_time(
    repo: ChromaRepository,
) -> None:
    repo.save_chunks(
        'mat-1',
        'Lecture',
        ['[00:01] intro chunk', 'no marker chunk'],
        source_type='transcript',
        start_times=[1.0, None],
    )
    chunks = repo.get_chunks_by_material('mat-1')
    assert chunks[0]['source_type'] == 'transcript'
    assert chunks[0]['start_time'] == 1.0
    assert chunks[1]['start_time'] is None


def test_get_chunks_by_material_ordered_by_index(
    repo: ChromaRepository,
) -> None:
    repo.save_chunks('mat-1', 'Material One', ['first', 'second', 'third'])
    chunks = repo.get_chunks_by_material('mat-1')
    assert [c['text'] for c in chunks] == ['first', 'second', 'third']
    assert [c['chunk_index'] for c in chunks] == [0, 1, 2]
    assert chunks[0]['source_type'] == 'material'


def test_get_chunks_by_material_missing_returns_empty(
    repo: ChromaRepository,
) -> None:
    assert repo.get_chunks_by_material('does-not-exist') == []


def test_delete_material_removes_all_chunks(repo: ChromaRepository) -> None:
    repo.save_chunks('mat-1', 'Material One', ['a', 'b', 'c'])
    deleted = repo.delete_material('mat-1')
    assert deleted == 3
    assert repo.get_chunks_by_material('mat-1') == []
    assert repo.list_materials() == []


def test_delete_material_missing_returns_zero(
    repo: ChromaRepository,
) -> None:
    assert repo.delete_material('does-not-exist') == 0
