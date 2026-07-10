import pytest
from study_mcp.tools import list_materials

from tests.conftest import FakeRepository


def test_list_materials_empty(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(list_materials, 'repository', fake_repository)
    result = list_materials.list_materials_tool()
    assert result == {'materials': [], 'total': 0}


def test_list_materials_returns_saved_materials(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(list_materials, 'repository', fake_repository)
    fake_repository.save_chunks('mat-1', 'Material One', ['chunk'])
    fake_repository.save_chunks('mat-2', 'Material Two', ['chunk'])

    result = list_materials.list_materials_tool()

    assert result['total'] == 2
    materials = result['materials']
    assert isinstance(materials, list)
    assert {'material_id': 'mat-1', 'source': 'Material One'} in materials
    assert {'material_id': 'mat-2', 'source': 'Material Two'} in materials
