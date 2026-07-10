import pytest
from study_mcp.tools import search

from tests.conftest import FakeRepository


def test_empty_query_returns_error(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(search, 'repository', fake_repository)
    result = search.search_tool('   ')
    assert result == {'error': 'Query cannot be empty.'}


def test_no_results_returns_message(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(search, 'repository', fake_repository)
    result = search.search_tool('nothing indexed yet')
    assert result == {
        'results': [],
        'message': 'No relevant content found.',
    }


def test_search_returns_formatted_results(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(search, 'repository', fake_repository)
    fake_repository.save_chunks(
        'mat-1', 'Python Basics', ['Python is a programming language.']
    )

    result = search.search_tool('python', top_k=3)

    assert result['query'] == 'python'
    assert result['total'] == 1
    results = result['results']
    assert isinstance(results, list)
    assert results[0]['text'] == 'Python is a programming language.'
    assert results[0]['source'] == 'Python Basics'
    assert results[0]['material_id'] == 'mat-1'


def test_search_respects_top_k(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(search, 'repository', fake_repository)
    fake_repository.save_chunks(
        'mat-1',
        'Repetitive Material',
        ['python here'] * 5,
    )

    result = search.search_tool('python', top_k=2)
    assert result['total'] == 2


def test_search_can_restrict_to_material_id(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(search, 'repository', fake_repository)
    fake_repository.save_chunks('mat-1', 'Material One', ['python content'])
    fake_repository.save_chunks('mat-2', 'Material Two', ['python content'])

    result = search.search_tool('python', material_id='mat-2')
    results = result['results']
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]['material_id'] == 'mat-2'
