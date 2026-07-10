import pytest
from study_mcp.tools import materials

from tests.conftest import FakeRepository


@pytest.fixture(autouse=True)
def _patch_repository(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(materials, 'repository', fake_repository)


def test_delete_material_tool(fake_repository: FakeRepository) -> None:
    fake_repository.save_chunks('mat-1', 'Material One', ['a', 'b', 'c'])
    result = materials.delete_material_tool('mat-1')
    assert result == {'material_id': 'mat-1', 'chunks_deleted': 3}
    assert 'mat-1' not in fake_repository.chunks


def test_get_material_overview_tool_missing_material() -> None:
    result = materials.get_material_overview_tool('does-not-exist')
    assert 'error' in result


def test_get_material_overview_tool_returns_leading_chunks(
    fake_repository: FakeRepository,
) -> None:
    fake_repository.save_chunks(
        'mat-1', 'Material One', ['chunk 0', 'chunk 1', 'chunk 2']
    )
    result = materials.get_material_overview_tool('mat-1', num_chunks=2)

    assert result['material_id'] == 'mat-1'
    assert result['source'] == 'Material One'
    assert result['total_chunks'] == 3
    assert result['chunks'] == ['chunk 0', 'chunk 1']


def test_generate_quiz_context_tool_missing_material() -> None:
    result = materials.generate_quiz_context_tool('does-not-exist')
    assert 'error' in result


def test_generate_quiz_context_tool_returns_all_when_fewer_than_requested(
    fake_repository: FakeRepository,
) -> None:
    fake_repository.save_chunks('mat-1', 'Material One', ['a', 'b'])
    result = materials.generate_quiz_context_tool('mat-1', num_topics=5)
    assert result['chunks'] == ['a', 'b']


def test_generate_quiz_context_tool_samples_spread(
    fake_repository: FakeRepository,
) -> None:
    chunks = [f'chunk {i}' for i in range(10)]
    fake_repository.save_chunks('mat-1', 'Material One', chunks)
    result = materials.generate_quiz_context_tool('mat-1', num_topics=3)
    sampled = result['chunks']
    assert isinstance(sampled, list)
    assert len(sampled) == 3
    assert len(set(sampled)) == 3


def test_study_stats_tool_empty(fake_repository: FakeRepository) -> None:
    result = materials.study_stats_tool()
    assert result == {
        'total_materials': 0,
        'total_chunks': 0,
        'chunks_per_material': [],
    }


def test_study_stats_tool_aggregates_materials(
    fake_repository: FakeRepository,
) -> None:
    fake_repository.save_chunks('mat-1', 'Material One', ['a', 'b'])
    fake_repository.save_chunks('mat-2', 'Material Two', ['c'])

    result = materials.study_stats_tool()

    assert result['total_materials'] == 2
    assert result['total_chunks'] == 3
    per_material = result['chunks_per_material']
    assert isinstance(per_material, list)
    assert {
        'material_id': 'mat-1',
        'source': 'Material One',
        'chunks': 2,
    } in per_material
