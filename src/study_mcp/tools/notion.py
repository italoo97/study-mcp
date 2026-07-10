from notion_client import Client

from study_mcp.core.config import settings

_MAX_BLOCKS_PER_REQUEST = 100


def _rich_text(text: str) -> list[dict[str, object]]:
    chunks = [text[i : i + 2000] for i in range(0, len(text), 2000)]
    return [{'type': 'text', 'text': {'content': c}} for c in chunks]


def _paragraph_blocks(text: str) -> list[dict[str, object]]:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return [
        {
            'type': 'paragraph',
            'paragraph': {'rich_text': _rich_text(p)},
        }
        for p in paragraphs
    ]


def _flashcard_blocks(
    flashcards: list[dict[str, str]],
) -> list[dict[str, object]]:
    return [
        {
            'type': 'toggle',
            'toggle': {
                'rich_text': _rich_text(fc['question']),
                'children': [
                    {
                        'type': 'paragraph',
                        'paragraph': {'rich_text': _rich_text(fc['answer'])},
                    }
                ],
            },
        }
        for fc in flashcards
    ]


def _append_blocks_batched(
    client: Client, page_id: str, blocks: list[dict[str, object]]
) -> None:
    for i in range(0, len(blocks), _MAX_BLOCKS_PER_REQUEST):
        batch = blocks[i : i + _MAX_BLOCKS_PER_REQUEST]
        client.blocks.children.append(block_id=page_id, children=batch)


class NotionService:
    def __init__(self) -> None:
        self._client: Client | None = None

    def _get_client(self) -> Client:
        if self._client is None:
            if not settings.NOTION_TOKEN:
                raise RuntimeError('NOTION_TOKEN is not configured.')
            self._client = Client(auth=settings.NOTION_TOKEN)
        return self._client

    def save_summary(
        self,
        material_id: str,
        material_name: str,
        summary: str,
        tags: list[str] | None = None,
    ) -> dict[str, str]:
        if not settings.NOTION_DATABASE_ID:
            return {'error': 'NOTION_DATABASE_ID is not configured.'}

        client = self._get_client()
        properties: dict[str, object] = {
            'Name': {
                'title': _rich_text(f'Summary — {material_name}'),
            },
            'Type': {'select': {'name': 'Summary'}},
            'Material': {'rich_text': _rich_text(material_id)},
            'Content': {'rich_text': _rich_text(summary)},
        }

        if tags:
            properties['Tags'] = {
                'multi_select': [{'name': t} for t in tags],
            }

        body_blocks = _paragraph_blocks(summary)
        page = client.pages.create(
            parent={'database_id': settings.NOTION_DATABASE_ID},
            properties=properties,
            children=body_blocks[:_MAX_BLOCKS_PER_REQUEST],
        )
        if len(body_blocks) > _MAX_BLOCKS_PER_REQUEST:
            _append_blocks_batched(
                client,
                page['id'],  # type: ignore[index]
                body_blocks[_MAX_BLOCKS_PER_REQUEST:],
            )

        return {
            'status': 'ok',
            'notion_url': str(page['url']),  # type: ignore[index]
        }

    def save_flashcards(
        self,
        material_id: str,
        material_name: str,
        flashcards: list[dict[str, str]],
    ) -> dict[str, str | int]:
        if not settings.NOTION_DATABASE_ID:
            return {'error': 'NOTION_DATABASE_ID is not configured.'}

        client = self._get_client()
        content = '\n\n'.join(
            f"Q: {fc['question']}\nA: {fc['answer']}" for fc in flashcards
        )

        properties: dict[str, object] = {
            'Name': {
                'title': _rich_text(f'Flashcards — {material_name}'),
            },
            'Type': {'select': {'name': 'Flashcards'}},
            'Material': {'rich_text': _rich_text(material_id)},
            'Content': {'rich_text': _rich_text(content)},
        }

        body_blocks = _flashcard_blocks(flashcards)
        page = client.pages.create(
            parent={'database_id': settings.NOTION_DATABASE_ID},
            properties=properties,
            children=body_blocks[:_MAX_BLOCKS_PER_REQUEST],
        )
        if len(body_blocks) > _MAX_BLOCKS_PER_REQUEST:
            _append_blocks_batched(
                client,
                page['id'],  # type: ignore[index]
                body_blocks[_MAX_BLOCKS_PER_REQUEST:],
            )

        return {
            'status': 'ok',
            'flashcards_saved': len(flashcards),
            'notion_url': str(page['url']),  # type: ignore[index]
        }


_notion_service = NotionService()


def save_summary_tool(
    material_id: str,
    material_name: str,
    summary: str,
    tags: list[str] | None = None,
) -> dict[str, str]:
    """
    Save a study summary to Notion.

    Args:
        material_id: ID of the ingested material.
        material_name: Human-readable name for the material.
        summary: The summary text to save.
        tags: Optional list of topic tags.
    """
    return _notion_service.save_summary(
        material_id, material_name, summary, tags
    )


def save_flashcards_tool(
    material_id: str,
    material_name: str,
    flashcards: list[dict[str, str]],
) -> dict[str, str | int]:
    """
    Save flashcards to Notion.

    Args:
        material_id: ID of the ingested material.
        material_name: Human-readable name for the material.
        flashcards: List of dicts with 'question' and 'answer' keys.
    """
    return _notion_service.save_flashcards(
        material_id, material_name, flashcards
    )
