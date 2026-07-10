import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from study_mcp.core.embeddings import embedding_engine
from study_mcp.db import repository
from study_mcp.tools.ingest import ingest_file_tool, ingest_text_tool
from study_mcp.tools.list_materials import list_materials_tool
from study_mcp.tools.materials import (
    delete_material_tool,
    generate_quiz_context_tool,
    get_material_overview_tool,
    study_stats_tool,
)
from study_mcp.tools.notion import (
    create_quiz_tool,
    save_flashcards_tool,
    save_summary_tool,
)
from study_mcp.tools.search import search_tool

logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logging.getLogger('study_mcp').setLevel(logging.INFO)


@asynccontextmanager
async def app_lifespan(server: FastMCP[None]) -> AsyncIterator[None]:
    embedding_engine.load()
    yield


mcp = FastMCP(
    name='study-mcp',
    instructions=(
        'You are a study assistant powered by study-mcp. '
        'You can ingest study materials and video transcripts, '
        'search them semantically, generate quiz context, summaries, '
        'flashcards and interactive Notion quizzes the user can '
        'answer directly in Notion. '
        'Always call list_materials_tool first to check what is already '
        'indexed before ingesting new files. '
        'After saving a summary with save_summary_tool, always ask '
        'the user whether they would also like flashcards '
        '(save_flashcards_tool) and/or an interactive quiz '
        '(create_quiz_tool) generated for the same material - offer, '
        "don't create them unprompted. "
        'When it fits the conversation, remind the user what else '
        'this server can do: search_tool for semantic search across '
        'everything ingested, get_material_overview_tool to preview '
        'a material before summarizing, study_stats_tool for a study '
        'dashboard, and delete_material_tool to remove outdated '
        'materials.'
    ),
    lifespan=app_lifespan,
)

mcp.tool()(ingest_file_tool)
mcp.tool()(ingest_text_tool)
mcp.tool()(search_tool)
mcp.tool()(list_materials_tool)
mcp.tool()(save_summary_tool)
mcp.tool()(save_flashcards_tool)
mcp.tool()(create_quiz_tool)
mcp.tool()(delete_material_tool)
mcp.tool()(get_material_overview_tool)
mcp.tool()(generate_quiz_context_tool)
mcp.tool()(study_stats_tool)


@mcp.resource('study://materials')
def materials_resource() -> str:
    """Lists all indexed study materials available for search."""
    materials = repository.list_materials()
    return json.dumps(materials, ensure_ascii=False, indent=2)


@mcp.prompt()
def study_prompt(material_name: str) -> str:
    """
    Generate a study plan prompt for a given material.

    Args:
        material_name: Name of the material to study.
    """
    return (
        f"I want to study '{material_name}'. Please help me by:\n"
        '1. Searching for the main topics using search_tool\n'
        '2. Generating a structured summary\n'
        '3. Creating 10 flashcards covering the key concepts\n'
        '4. Saving both the summary and flashcards to Notion\n'
        '5. Asking if I would also like an interactive quiz '
        '(create_quiz_tool) to test myself on this material'
    )


if __name__ == '__main__':
    mcp.run()
