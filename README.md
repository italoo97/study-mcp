# 📚 study-mcp

> A Model Context Protocol (MCP) server that turns video transcripts and study materials into a searchable, AI-powered knowledge base — directly inside Claude Desktop.

[![CI](https://github.com/italoo97/study-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/italoo97/study-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](#-development)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ What it does

Paste a video transcript or point to a PDF, slide deck, DOCX, or image and instantly:

- 🎬 **Ingest video transcripts** — paste raw text or load `.srt`/`.vtt` caption files; timestamps are preserved so you can jump back to the exact moment in the video
- 🔍 **Search semantically** — ask questions in natural language across all your materials, powered by local embeddings (no API cost)
- 🎯 **Generate quizzes** — sample representative context from any material so Claude can quiz you on it
- 🧠 **Summarize & create flashcards** — saved directly to Notion
- 📊 **Track your library** — list materials, inspect overviews, view stats, delete what you no longer need

Everything runs locally by default (ChromaDB + HuggingFace embeddings). Set a single environment variable to switch to pgvector on Supabase/Postgres.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| MCP server | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP) |
| Embeddings | [sentence-transformers](https://sbert.net) + HuggingFace models (local inference, PyTorch) |
| Vector stores | [ChromaDB](https://www.trychroma.com) (local) · [pgvector](https://github.com/pgvector/pgvector) on Supabase/Postgres (cloud) |
| Document parsing | [Docling](https://github.com/docling-project/docling) (PDF, DOCX, PPTX, HTML, images) + native SRT/VTT parser |
| Integrations | [Notion API](https://developers.notion.com) (`notion-client`) |
| Configuration | pydantic-settings (typed, env-based) |
| Tooling | Poetry · pytest (+coverage) · ruff · mypy `--strict` · pre-commit · commitizen |
| CI | GitHub Actions (lint, type check, tests on every push/PR) |

---

## 🏗️ Architecture

```
study-mcp/
├── src/study_mcp/
│   ├── core/
│   │   ├── config.py       # Settings via environment variables (pydantic-settings)
│   │   ├── embeddings.py   # sentence-transformers, local inference, E5 prefixing
│   │   ├── chunker.py      # Heading → paragraph → sentence-aware chunking
│   │   └── transcript.py   # SRT/VTT parser with timestamp preservation
│   ├── db/
│   │   ├── __init__.py     # VectorRepository protocol + backend auto-detection
│   │   ├── chroma.py       # Local vector store (ChromaDB, zero setup)
│   │   └── pgvector.py     # Cloud vector store (Supabase/Postgres, HNSW index)
│   ├── tools/
│   │   ├── ingest.py       # File & raw-text ingestion (Docling + native parsers)
│   │   ├── search.py       # Semantic search
│   │   ├── materials.py    # Overview, quiz context, stats, deletion
│   │   ├── list_materials.py
│   │   └── notion.py       # Notion integration (summaries & flashcards)
│   └── server.py           # FastMCP server: tools, resource, prompt, lifespan
├── tests/                  # 60 tests, ~96% coverage, no model download needed
└── docs/
    └── claude_desktop_config.json
```

**Design highlights:**

- **Repository pattern** — both vector backends implement the same `VectorRepository` protocol; the backend is chosen at startup from `DATABASE_URL` with no code changes.
- **E5 query/passage prefixing** — `intfloat/multilingual-e5-*` models are trained with `query:` / `passage:` prefixes; applying them measurably improves retrieval quality. Applied automatically when an E5 model is configured.
- **Sentence-aware chunking** — text is split by heading, then paragraph, then grouped by whole sentences with sentence-level overlap. Chunks never cut a word or sentence in half.
- **Idempotent ingestion** — `material_id` is a SHA-256 content hash, so re-ingesting the same material is a no-op (`already_indexed`) instead of a duplicate.
- **Timestamp-aware transcripts** — SRT/VTT cues are grouped into paragraphs by speech pauses; search results on transcripts carry a `start_time` so you can jump back into the video.

---

## 🛠️ Available Tools

| Tool | Description |
|---|---|
| `ingest_text_tool` | Ingest raw text — e.g. a pasted video transcript — into the vector store |
| `ingest_file_tool` | Convert and index a file: PDF, DOCX, PPTX, HTML, images, `.txt`, `.md`, `.srt`, `.vtt` |
| `search_tool` | Semantic search across all indexed materials (optionally scoped to one) |
| `list_materials_tool` | List all indexed materials |
| `get_material_overview_tool` | Preview the first chunks of a material before summarizing or quizzing |
| `generate_quiz_context_tool` | Sample chunks spread across a material so Claude can write quiz questions |
| `study_stats_tool` | Totals: materials, chunks, chunks per material |
| `delete_material_tool` | Remove a material and all of its chunks |
| `save_summary_tool` | Save a summary to Notion |
| `save_flashcards_tool` | Save Q&A flashcards to Notion |

The server also exposes an MCP **resource** (`study://materials`, the current library as JSON) and a **prompt** (`study_prompt`, a ready-made study-plan workflow for any material).

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/italoo97/study-mcp.git
cd study-mcp
poetry install
```

### 2. Configure environment

```bash
cp .env.example .env
```

All variables have sensible defaults — the server works out of the box with ChromaDB and no external services. See [`.env.example`](.env.example) for every option.

### 3. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (see [`docs/claude_desktop_config.json`](docs/claude_desktop_config.json) for a full example):

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
        "CHROMA_PATH": "/absolute/path/to/study-mcp/chroma_db"
      }
    }
  }
}
```

> ⚠️ Claude Desktop launches the server from its own working directory, so relative paths (like the `.env` file or the default `./chroma_db`) won't resolve to the project folder. Set `CHROMA_PATH` to an absolute path as above, and pass any other variables (`NOTION_TOKEN`, `DATABASE_URL`, ...) in the `env` block — see [`docs/claude_desktop_config.json`](docs/claude_desktop_config.json) for a complete example.

> **Vector backend is auto-detected:**
> - `DATABASE_URL` empty → ChromaDB locally (zero setup)
> - `DATABASE_URL` set → pgvector on Supabase/Postgres (free tier works; table and HNSW index are created automatically)

### 4. Restart Claude Desktop

The tools appear automatically.

---

## 🎬 Ingesting video transcripts

The main workflow this server was built for:

1. Open a video (YouTube, a recorded lecture, a course platform) and copy its transcript — or download the captions as `.srt`/`.vtt`.
2. Paste it into Claude: *"Ingest this transcript as 'Linear Algebra — Lecture 3': ..."* → Claude calls `ingest_text_tool`.
3. Ask anything: *"According to my lecture, what is an eigenvector?"* → `search_tool` returns the most relevant passages, each with a `start_time` when available, so you can jump back to that moment in the video.
4. Study actively: *"Quiz me on this lecture"* → `generate_quiz_context_tool` samples passages spread across the whole material and Claude writes the questions.

`.srt`/`.vtt` files are parsed natively: cue numbers and markup are stripped, consecutive cues are merged into paragraphs at natural speech pauses, and paragraph start times are preserved as metadata.

---

## 🧠 Embedding Models

Set `EMBEDDING_MODEL` to any [sentence-transformers](https://sbert.net) compatible model:

| Model | Languages | Dims |
|---|---|---|
| `intfloat/multilingual-e5-small` *(default)* | PT + EN + 90 more | 384 |
| `intfloat/multilingual-e5-base` | PT + EN + 90 more | 768 |
| `BAAI/bge-small-en-v1.5` | EN only | 384 |

> Update `EMBEDDING_DIM` to match — the server validates the dimension at startup and fails fast on a mismatch.

---

## 📋 Notion Setup (optional)

Only needed for `save_summary_tool` and `save_flashcards_tool`.

1. Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a database with these properties:
   - `Name` → Title
   - `Type` → Select (`Summary`, `Flashcards`)
   - `Material` → Rich text
   - `Content` → Rich text
   - `Tags` → Multi-select
3. Share the database with your integration
4. Set `NOTION_TOKEN` and `NOTION_DATABASE_ID` in `.env`

---

## 💡 Example usage in Claude

```
"Ingest this transcript as 'ML Course — Gradient Descent': [pasted transcript]"

"Ingest this file: /Users/me/Downloads/algorithms_lecture.pdf"

"Search my materials: what is dynamic programming?"

"Give me an overview of material a1b2c3d4"

"Quiz me with 10 questions about my gradient descent lecture"

"Summarize it and save to Notion with tags: ML, optimization"

"Show my study stats"
```

---

## 🔧 Development

```bash
poetry install

poetry run task lint        # ruff check
poetry run task format      # ruff format
poetry run task type_check  # mypy --strict
poetry run task test        # pytest (60 tests, coverage gate at 80%)
```

The test suite runs without downloading any embedding model — embeddings are faked with deterministic vectors and the repository layer is tested against an in-memory double plus a real ChromaDB instance in a temp directory.

CI (GitHub Actions) runs lint, strict type checking, and the full test suite on every push and PR.

---

## 📄 License

[MIT](LICENSE)
