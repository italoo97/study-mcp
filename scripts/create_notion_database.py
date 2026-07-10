"""One-off script: create a study-mcp-compatible Notion database.

Usage:
    poetry run python scripts/create_notion_database.py \
        <parent_page_id> [title]

NOTION_TOKEN must be set (in .env or the environment) before running.
Prints the resulting database ID - copy it into NOTION_DATABASE_ID.

Since the database is created BY your integration, it's already
shared with it - no extra "Connections" step needed afterwards.
"""

import sys

from notion_client import Client
from study_mcp.core.config import settings

_SCHEMA: dict[str, object] = {
    'Name': {'title': {}},
    'Type': {
        'select': {
            'options': [
                {'name': 'Summary', 'color': 'blue'},
                {'name': 'Flashcards', 'color': 'green'},
                {'name': 'Quiz', 'color': 'purple'},
            ]
        }
    },
    'Material': {'rich_text': {}},
    'Tags': {'multi_select': {}},
}


def create_database(parent_page_id: str, title: str) -> str:
    if not settings.NOTION_TOKEN:
        raise SystemExit(
            'NOTION_TOKEN is not set. Export it before running this '
            'script, e.g.:\n'
            '  NOTION_TOKEN=secret_xxx poetry run python '
            'scripts/create_notion_database.py <page_id>'
        )

    client = Client(auth=settings.NOTION_TOKEN, notion_version='2022-06-28')
    database = client.databases.create(
        parent={'type': 'page_id', 'page_id': parent_page_id},
        title=[{'type': 'text', 'text': {'content': title}}],
        properties=_SCHEMA,
    )
    return str(database['id'])  # type: ignore[index]


def main() -> None:
    if len(sys.argv) < 2:
        print(
            'Usage: poetry run python scripts/create_notion_database.py '
            '<parent_page_id> [title]'
        )
        raise SystemExit(1)

    parent_page_id = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else 'study-mcp'

    database_id = create_database(parent_page_id, title)
    print(f'Database created: {database_id}')
    print('Copy this into NOTION_DATABASE_ID in your Claude Desktop config.')


if __name__ == '__main__':
    main()
