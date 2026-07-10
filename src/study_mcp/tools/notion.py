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


def _question_blocks(
    index: int, q: dict[str, object]
) -> list[dict[str, object]]:
    question = str(q['question'])
    answer = str(q['answer'])
    raw_options = q.get('options')
    options = (
        [str(o) for o in raw_options]
        if isinstance(raw_options, list)
        else None
    )
    explanation = q.get('explanation')

    blocks: list[dict[str, object]] = [
        {
            'type': 'callout',
            'callout': {
                'rich_text': _rich_text(f'Pergunta {index}: {question}'),
                'icon': {'type': 'emoji', 'emoji': '🎯'},
                'color': (
                    'purple_background' if options else 'blue_background'
                ),
            },
        }
    ]

    if options:
        for option in options:
            blocks.append({
                'type': 'to_do',
                'to_do': {
                    'rich_text': _rich_text(option),
                    'checked': False,
                },
            })
    else:
        blocks.append({
            'type': 'callout',
            'callout': {
                'rich_text': _rich_text('Escreva sua resposta abaixo:'),
                'icon': {'type': 'emoji', 'emoji': '✍️'},
                'color': 'gray_background',
            },
        })
        blocks.append({
            'type': 'paragraph',
            'paragraph': {'rich_text': []},
        })

    reveal_children: list[dict[str, object]] = [
        {
            'type': 'paragraph',
            'paragraph': {
                'rich_text': _rich_text(f'✅ Resposta certa: {answer}')
            },
        }
    ]
    if explanation:
        reveal_children.append({
            'type': 'paragraph',
            'paragraph': {'rich_text': _rich_text(str(explanation))},
        })

    blocks.append({
        'type': 'toggle',
        'toggle': {
            'rich_text': _rich_text('🔎 Ver resposta certa'),
            'children': reveal_children,
        },
    })
    blocks.append({'type': 'divider', 'divider': {}})

    return blocks


def _quiz_blocks(
    questions: list[dict[str, object]],
) -> list[dict[str, object]]:
    intro: dict[str, object] = {
        'type': 'callout',
        'callout': {
            'rich_text': _rich_text(
                'Responda cada pergunta antes de abrir o toggle com a '
                'resposta certa. Quando terminar, volte para o chat e '
                'cole suas respostas para eu conferir!'
            ),
            'icon': {'type': 'emoji', 'emoji': '🎮'},
            'color': 'blue_background',
        },
    }
    outro: dict[str, object] = {
        'type': 'callout',
        'callout': {
            'rich_text': _rich_text(
                'Fim do quiz! Volte para o chat e cole suas respostas '
                'para eu conferir.'
            ),
            'icon': {'type': 'emoji', 'emoji': '🏁'},
            'color': 'green_background',
        },
    }

    blocks: list[dict[str, object]] = [intro]
    for i, q in enumerate(questions, start=1):
        blocks.extend(_question_blocks(i, q))
    blocks.append(outro)
    return blocks


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
            # NOTE: pinned to the pre-2025-09-03 API, where pages are
            # parented directly by database_id. From 2025-09-03 onward
            # Notion requires a data_source_id instead (databases can
            # hold multiple data sources) - out of scope for this
            # single-database integration.
            self._client = Client(
                auth=settings.NOTION_TOKEN, notion_version='2022-06-28'
            )
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
            'suggestion': (
                'Ask the user if they would also like flashcards '
                '(save_flashcards_tool) and/or an interactive quiz '
                '(create_quiz_tool) generated for this same material.'
            ),
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
        properties: dict[str, object] = {
            'Name': {
                'title': _rich_text(f'Flashcards — {material_name}'),
            },
            'Type': {'select': {'name': 'Flashcards'}},
            'Material': {'rich_text': _rich_text(material_id)},
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

    def create_quiz(
        self,
        material_id: str,
        material_name: str,
        questions: list[dict[str, object]],
    ) -> dict[str, str | int]:
        if not settings.NOTION_DATABASE_ID:
            return {'error': 'NOTION_DATABASE_ID is not configured.'}

        client = self._get_client()
        properties: dict[str, object] = {
            'Name': {
                'title': _rich_text(f'Quiz — {material_name}'),
            },
            'Type': {'select': {'name': 'Quiz'}},
            'Material': {'rich_text': _rich_text(material_id)},
        }

        body_blocks = _quiz_blocks(questions)
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
            'questions_saved': len(questions),
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

    After a successful save, offer to also generate flashcards
    (save_flashcards_tool) and/or an interactive quiz
    (create_quiz_tool) for the same material - ask the user first,
    don't create them unprompted.

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


def create_quiz_tool(
    material_id: str,
    material_name: str,
    questions: list[dict[str, object]],
) -> dict[str, str | int]:
    """
    Create an interactive quiz page in Notion for active recall. The
    user answers directly in Notion (writes free-text answers or
    checks multiple-choice boxes) before revealing the correct answer
    in a toggle, then comes back to this chat and pastes their
    answers for the assistant to check.

    Each item in questions is a dict with:
        - 'question' (str, required): the question text.
        - 'answer' (str, required): the correct answer. For
          multiple-choice questions this must match one of 'options'
          exactly.
        - 'options' (list[str], optional): if given, the question
          renders as multiple-choice with a checkbox per option. If
          omitted, it renders as an open question with blank space
          to write the answer.
        - 'explanation' (str, optional): shown next to the answer
          once revealed.

    Args:
        material_id: ID of the ingested material.
        material_name: Human-readable name for the material.
        questions: List of question dicts as described above.
    """
    return _notion_service.create_quiz(material_id, material_name, questions)
