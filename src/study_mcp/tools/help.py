TOOLS_REGISTRY: list[dict[str, object]] = [
    {
        'name': 'ingest_file_tool',
        'description': (
            'Converts and indexes a local file '
            '(PDF, DOCX, PPTX, HTML, image) into the vector store '
            'using Docling for extraction.'
        ),
        'parameters': {
            'file_path': (
                '(str, required) Absolute or relative path to the file.'
            ),
            'material_name': (
                '(str, optional) Human-friendly name. Defaults to filename.'
            ),
        },
        'example': {
            'file_path': '/Users/you/Downloads/lecture.pdf',
            'material_name': 'Machine Learning Lecture 1',
        },
    },
    {
        'name': 'search_tool',
        'description': (
            'Searches all ingested study materials using semantic similarity. '
            'Returns the most relevant chunks for the given query.'
        ),
        'parameters': {
            'query': ('(str, required) The question or topic to search for.'),
            'top_k': (
                '(int, optional) Number of results to return. Default: 5.'
            ),
            'material_id': (
                '(str, optional) Restrict search to a single material.'
            ),
        },
        'example': {
            'query': 'What is gradient descent?',
            'top_k': 3,
            'material_id': None,
        },
    },
    {
        'name': 'list_materials_tool',
        'description': (
            'Lists all study materials currently stored '
            'in the vector database, showing their '
            'material_id and source name.'
        ),
        'parameters': {},
        'example': {},
    },
    {
        'name': 'save_summary_tool',
        'description': (
            'Generates and saves a study summary to Notion. '
            'Requires NOTION_TOKEN and NOTION_DATABASE_ID in .env.'
        ),
        'parameters': {
            'material_id': (
                '(str, required) ID returned by ingest_file_tool.'
            ),
            'material_name': '(str, required) Human-readable name.',
            'summary': '(str, required) The summary text to save.',
            'tags': (
                '(list[str], optional) Topic tags e.g. ["algorithms", "CS"].'
            ),
        },
        'example': {
            'material_id': 'abc-123',
            'material_name': 'Machine Learning Lecture 1',
            'summary': 'This lecture covers gradient descent...',
            'tags': ['ML', 'algorithms'],
        },
    },
    {
        'name': 'save_flashcards_tool',
        'description': (
            'Saves a list of flashcards to Notion. '
            'Each flashcard must have a question and an answer. '
            'Requires NOTION_TOKEN and NOTION_DATABASE_ID in .env.'
        ),
        'parameters': {
            'material_id': (
                '(str, required) ID returned by ingest_file_tool.'
            ),
            'material_name': '(str, required) Human-readable name.',
            'flashcards': (
                '(list[dict], required) List of dicts '
                'with "question" and "answer" keys.'
            ),
        },
        'example': {
            'material_id': 'abc-123',
            'material_name': 'Machine Learning Lecture 1',
            'flashcards': [
                {
                    'question': 'What is gradient descent?',
                    'answer': 'An optimization algorithm that minimizes loss.',
                },
                {
                    'question': 'What is backpropagation?',
                    'answer': (
                        'Algorithm to compute gradients ' 'in neural networks.'
                    ),
                },
            ],
        },
    },
    {
        'name': 'help_tool',
        'description': (
            'Lists all available tools with their descriptions, '
            'parameters and usage examples.'
        ),
        'parameters': {},
        'example': {},
    },
]


def help_tool() -> dict[str, object]:
    """
    List all available tools in study-mcp with descriptions,
    parameters and usage examples.

    Use this tool to discover what you can do and how to call each tool.
    """
    return {
        'total_tools': len(TOOLS_REGISTRY),
        'tools': TOOLS_REGISTRY,
    }
