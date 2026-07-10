import re

from notion_client import Client

from study_mcp.core.config import settings

_MAX_BLOCKS_PER_REQUEST = 100

_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_HEADING_RE = re.compile(r'^(#{1,3})\s+(.*)$')
_BULLET_RE = re.compile(r'^[-*]\s+(.*)$')
_NUMBERED_RE = re.compile(r'^\d+\.\s+(.*)$')
_HEADING_TYPES = {1: 'heading_1', 2: 'heading_2', 3: 'heading_3'}


def _rich_text(text: str) -> list[dict[str, object]]:
    chunks = [text[i : i + 2000] for i in range(0, len(text), 2000)]
    return [{'type': 'text', 'text': {'content': c}} for c in chunks]


def _text_span(content: str, bold: bool = False) -> dict[str, object]:
    span: dict[str, object] = {'type': 'text', 'text': {'content': content}}
    if bold:
        span['annotations'] = {'bold': True}
    return span


def _inline_rich_text(text: str) -> list[dict[str, object]]:
    # NOTE: only handles **bold** inline - no italics/links/code. Also
    # doesn't chunk past 2000 chars like _rich_text does, since a
    # single markdown line that long is not a realistic summary case.
    spans: list[dict[str, object]] = []
    last = 0
    for match in _BOLD_RE.finditer(text):
        if match.start() > last:
            spans.append(_text_span(text[last : match.start()]))
        spans.append(_text_span(match.group(1), bold=True))
        last = match.end()
    if last < len(text):
        spans.append(_text_span(text[last:]))
    return spans or [_text_span('')]


def _markdown_blocks(text: str) -> list[dict[str, object]]:
    """Render #/##/### headings, -/* bullets, 1. numbered lists and
    **bold** as real Notion blocks instead of flat paragraphs showing
    the raw markdown syntax. Assumes one logical line per paragraph
    (typical of LLM-generated markdown), not hand-wrapped prose.
    """
    blocks: list[dict[str, object]] = []
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        heading = _HEADING_RE.match(line)
        bullet = _BULLET_RE.match(line)
        numbered = _NUMBERED_RE.match(line)

        if heading:
            block_type = _HEADING_TYPES[len(heading.group(1))]
            blocks.append({
                'type': block_type,
                block_type: {'rich_text': _inline_rich_text(heading.group(2))},
            })
        elif bullet:
            blocks.append({
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': _inline_rich_text(bullet.group(1))
                },
            })
        elif numbered:
            blocks.append({
                'type': 'numbered_list_item',
                'numbered_list_item': {
                    'rich_text': _inline_rich_text(numbered.group(1))
                },
            })
        else:
            blocks.append({
                'type': 'paragraph',
                'paragraph': {'rich_text': _inline_rich_text(line)},
            })
    return blocks


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
            'Name': {'title': _rich_text(material_name)},
            'Type': {'select': {'name': 'Summary'}},
            'Material': {'rich_text': _rich_text(material_id)},
        }

        if tags:
            properties['Tags'] = {
                'multi_select': [{'name': t} for t in tags],
            }

        header: dict[str, object] = {
            'type': 'callout',
            'callout': {
                'rich_text': _rich_text(f'Resumo de {material_name}'),
                'icon': {'type': 'emoji', 'emoji': '📚'},
                'color': 'blue_background',
            },
        }
        body_blocks = [header, *_markdown_blocks(summary)]
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
            'Name': {'title': _rich_text(material_name)},
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
            'Name': {'title': _rich_text(material_name)},
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
