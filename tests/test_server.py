import asyncio
import json

import pytest
from study_mcp import server
from study_mcp.core.embeddings import embedding_engine

from tests.conftest import FakeRepository


def test_materials_resource_returns_json(
    monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository
) -> None:
    monkeypatch.setattr(server, 'repository', fake_repository)
    fake_repository.save_chunks('mat-1', 'Material One', ['chunk'])

    result = server.materials_resource()
    data = json.loads(result)
    assert data == [{'material_id': 'mat-1', 'source': 'Material One'}]


def test_study_prompt_mentions_material_name() -> None:
    result = server.study_prompt('Linear Algebra')
    assert 'Linear Algebra' in result
    assert 'search_tool' in result


def test_app_lifespan_loads_embedding_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        embedding_engine,
        'load',
        lambda: calls.append(True),
    )

    async def _run() -> None:
        async with server.app_lifespan(server.mcp) as ctx:
            assert ctx is None

    asyncio.run(_run())
    assert calls == [True]
