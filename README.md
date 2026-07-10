# 📚 study-mcp

> A Model Context Protocol (MCP) server that turns any study material into a searchable, AI-powered knowledge base — directly inside Claude Desktop.

[![CI](https://github.com/italoo97/study-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/italoo97/study-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ What it does

Upload a PDF, slide deck, DOCX, image, or HTML file and instantly:

- 🔍 **Search semantically** — ask questions in natural language across all your materials
- 🧠 **Generate summaries** — get structured summaries saved directly to Notion
- 🃏 **Create flashcards** — auto-generate Q&A cards saved to Notion
- 📂 **Manage materials** — list and organize everything you've indexed

---

## 🏗️ Architecture

```
study-mcp/
├── src/study_mcp/
│   ├── core/
│   │   ├── config.py       # All settings via environment variables
│   │   ├── embeddings.py   # HuggingFace Transformers (local, no API cost)
│   │   └── chunker.py      # Markdown-aware smart text chunker
│   ├── db/
│   │   ├── chroma.py       # Local vector store (ChromaDB)
│   │   └── pgvector.py     # Cloud vector store (Supabase / Postgres)
│   ├── tools/
│   │   ├── ingest.py       # File ingestion via Docling
│   │   ├── search.py       # Semantic search
│   │   ├── notion.py       # Notion integration
│   │   ├── list_materials.py
│   │   └── help.py         # Tools registry
│   └── server.py           # FastMCP server entry point
├── tests/
└── docs/
    └── claude_desktop_config.json
```

---

## 🛠️ Available Tools

| Tool | Description |
|---|---|
| `ingest_file_tool` | Convert and index any file (PDF, PPTX, DOCX, HTML, images) |
| `search_tool` | Semantic search across all indexed materials |
| `list_materials_tool` | List all indexed materials |
| `save_summary_tool` | Save a summary to Notion |
| `save_flashcards_tool` | Save flashcards to Notion |
| `help_tool` | List all tools with descriptions and usage examples |

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/italoo97/study-mcp.git
cd study-mcp
poetry install
```

### 2. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "study-mcp": {
      "command": "poetry",
      "args": [
        "--directory", "/absolute/path/to/study-mcp",
        "run", "python", "-m", "study_mcp.server"
      ],
      "env": {
        "EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
        "EMBEDDING_DIM": "384",
        "CHROMA_PATH": "./chroma_db",
        "CHROMA_COLLECTION": "study_chunks",
        "CHUNK_SIZE": "512",
        "CHUNK_OVERLAP": "64",
        "NOTION_TOKEN": "secret_...",
        "NOTION_DATABASE_ID": "your-database-id",
        "DATABASE_URL": ""
      }
    }
  }
}
```

> **Vector backend is auto-detected:**
> - `DATABASE_URL` empty → uses ChromaDB locally (zero setup)
> - `DATABASE_URL` set → uses pgvector on Supabase (free tier works)

### 3. Restart Claude Desktop

The tools will appear automatically in Claude Desktop.

---

## 🧠 Embedding Models

Set `EMBEDDING_MODEL` to any HuggingFace feature-extraction model:

| Model | Languages | Dims |
|---|---|---|
| `intfloat/multilingual-e5-small` | PT + EN + more | 384 |
| `BAAI/bge-small-en-v1.5` | EN only | 384 |
| `neuralmind/bert-base-portuguese-cased` | PT only | 768 |

> Update `EMBEDDING_DIM` if you change models.

---

## 📋 Notion Setup

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create an integration
2. Create a database with these properties:
   - `Name` → Title
   - `Type` → Select (`Summary`, `Flashcards`)
   - `Material` → Rich text
   - `Content` → Rich text
   - `Tags` → Multi-select
3. Share the database with your integration
4. Set `NOTION_TOKEN` and `NOTION_DATABASE_ID` in the config

---

## 💡 Example Usage in Claude

```
"Ingest this file: /Users/me/Downloads/algorithms_lecture.pdf"

"Search my materials for: what is dynamic programming?"

"Generate 10 flashcards from material abc-123 and save to Notion"

"Summarize material abc-123 and save to Notion with tags: algorithms, CS"

"List all materials I've ingested"
```

---

## 🔧 Development

```bash
# Install dependencies
poetry install

# Run lint
poetry run task lint

# Run type check
poetry run task type_check

# Run tests
poetry run task test

# Format code
poetry run task format
```

---

## 📄 License

MIT