# 🧠 AI Knowledge Platform

A production-ready AI-powered document analysis and knowledge management platform.  
Upload documents, query them using multiple LLMs, manage prompts and conversations, generate reports, and visualize data — all from a unified interface.

This system supports **two AI providers**: OpenAI GPT (default) and AWS Bedrock (any model via the universal Converse API). Switch providers per-request with a single `"provider"` field. Any valid Bedrock model ID is accepted — not limited to a fixed list.

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Next.js    │─────▶│   FastAPI    │─────▶│  PostgreSQL  │
│   Frontend   │      │   Backend    │      │   Database   │
│   :3000      │      │   :8010      │      │   :5432      │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                    ┌────────┼────────┐
                    ▼        ▼        ▼
              ┌─────────┐ ┌─────────┐ ┌──────────┐
              │ ChromaDB│ │ OpenAI  │ │  AWS S3   │
              │  :8001  │ │  GPT API│ │  Storage  │
              └─────────┘ └─────────┘ └──────────┘
```

## Features

| Feature | Description |
|---|---|
| 📄 Document Ingestion | Upload PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON |
| 🔍 RAG Query | Retrieval-augmented generation with source citations |
| 🤖 GPT API | All generation now runs through OpenAI GPT API models |
| 📝 Prompt Templates | Create, edit, and reuse prompt templates |
| 💬 Conversations | Persistent chat history, categorized sessions |
| 📊 Dashboards | Plotly charts, data visualizations |
| 📄 Reports | Generate markdown, table, or JSON reports |
| 📤 BI Export | CSV/JSON exports for Tableau and PowerBI |
| 🔐 Auth | JWT-based authentication |
| 🐳 Docker | One-command deployment |

---

## Quick Start & Documentation

For detailed guides, please refer to the comprehensive manuals located in the `Documents/` folder:
- 🚀 **[Deployment Manual](Documents/deployment%20manual.md):** Step-by-step instructions for installing and running the platform locally or on a cloud server like AWS EC2.
- 📖 **[User Manual](Documents/user%20manual.md):** A complete guide on how to navigate the platform, upload documents, chat with the AI, and use the professional dashboards.
- 🧠 **[Information Manual](Documents/information%20manual.md):** A deep dive into the platform's core architecture, including RAG logic, the LLM router, and the content analytics engine.
- ☁️ **[AWS EC2 Launch Guide](Documents/AWS%20EC2%20Launch%20Guide.md):** Detailed, step-by-step AWS Console instructions for launching the optimized `t4g.large` instance and setting up security groups.

### Prerequisites

- **Docker** & **Docker Compose**
- **OpenAI API key**
- **AWS S3 bucket** (for document storage)

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
#   - AWS S3 keys
#   - OpenAI API key (required for chat, translation, reports, and financial extraction)
#   - PostgreSQL password
```

Required environment variable:

```ini
OPENAI_API_KEY=your_key
```

### 2. Launch

```bash
docker compose up --build -d
```

### 3. Access

| Service | URL |
|---|---|
| 🖥️ Next.js UI | [http://localhost:3000](http://localhost:3000) |
| ⚡ FastAPI Docs | [http://localhost:8010/docs](http://localhost:8010/docs) |
| 🗄️ PostgreSQL | `localhost:5432` |
| 🔷 ChromaDB | `localhost:8001` |

---

## Local Development (without Docker)

### First-time setup

```bash
cd /home/ubuntu/AI-Documents-Analyser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Start services (2 terminals)

Terminal 1 (Backend):
```bash
cd /home/ubuntu/AI-Documents-Analyser
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8010
```

Terminal 2 (Frontend):
```bash
cd /home/ubuntu/AI-Documents-Analyser/frontend-nextjs
npm install
NEXT_PUBLIC_BACKEND_API_URL=http://127.0.0.1:8010/api npm run dev -- --hostname 0.0.0.0 --port 3000
```

### Quick health checks

```bash
curl -sS http://127.0.0.1:8010/api/health
curl -I http://127.0.0.1:3000
```

### Clean restart (if ports are stuck)

```bash
pkill -f "uvicorn backend.main:app" || true
pkill -f "next dev --hostname 0.0.0.0 --port 3000" || true
```

---

## Project Structure

```
AI Documents Analyser/
├── backend/
│   ├── main.py                  # FastAPI app & endpoints
│   ├── rag_pipeline.py          # RAG orchestration
│   ├── vector_store.py          # ChromaDB / Qdrant abstraction
│   ├── embeddings.py            # Sentence-transformers wrapper
│   ├── llm_router.py            # Multi-model routing
│   ├── prompt_manager.py        # Prompt template CRUD
│   ├── conversation_manager.py  # Chat session management
│   └── report_generator.py      # Report generation
├── frontend/
│   └── streamlit_app.py         # Legacy Streamlit UI
├── frontend-nextjs/             # Active local/prod frontend
├── services/
│   ├── s3_storage.py            # AWS S3 client
│   └── document_parser.py       # Multi-format text extraction
├── db/
│   ├── database.py              # SQLAlchemy engine & session
│   └── models.py                # ORM models
├── config/
│   └── settings.py              # Pydantic settings
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login and get JWT token |
| `POST` | `/api/upload_document` | Upload & ingest a single document |
| `POST` | `/api/upload_batch` | Upload multiple documents (background processing) |
| `GET` | `/api/batch_status/{batch_id}` | Poll batch upload progress |
| `GET` | `/api/documents` | List documents |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `GET` | `/api/documents/status` | Index status: indexed vs not_indexed |
| `POST` | `/api/query` | RAG query — supports `translate_to_english` and `target_currency` |
| `GET` | `/api/prompts` | List prompt templates |
| `POST` | `/api/prompts` | Create prompt template |
| `PUT` | `/api/prompts/{id}` | Update prompt template |
| `DELETE` | `/api/prompts/{id}` | Delete prompt template |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation detail |
| `POST` | `/api/conversations` | Create conversation |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `POST` | `/api/generate_report` | Generate structured report |
| `GET` | `/api/analytics/overview` | Document & storage overview stats |
| `GET` | `/api/analytics/content` | Word count, reading time, frequencies |
| `GET` | `/api/analytics/content_insights` | Topics, entities, financial context |
| `GET` | `/api/analytics/storage` | Storage usage stats |
| `POST` | `/api/analytics/financial_dashboard` | GPT-based revenue/expense extraction |
| `GET` | `/api/models` | List available GPT models |
| `GET` | `/api/health` | Health check |

Full interactive docs at [http://localhost:8010/docs](http://localhost:8010/docs)

---

## Configuration

All configuration is managed via environment variables (`.env`). See `.env.example` for all available options.

### Key Settings

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `S3_BUCKET_NAME` | — | AWS S3 bucket for documents |
| `OPENAI_API_KEY` | — | **Required.** API key for all GPT features (chat, translation, reports, financial extraction) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for query caching. Set to your Redis instance URL. |
| `EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | Embedding model |
| `VECTOR_STORE_TYPE` | `chroma` | `chroma` or `qdrant` |
| `CHUNK_SIZE` | `1000` | Document chunk size (chars) |
| `TOP_K` | `5` | Number of chunks to retrieve |

## Multi-Model Architecture

### How provider routing works

```
API request  { "provider": "openai"|"bedrock", "model": "<model_id>", ... }
                         │
               LLMRouter.generate()
                         │
         ┌───────────────┴────────────────┐
         ▼                                ▼
   OpenAI GPT API                AWS Bedrock Converse API
   (gpt-4o, gpt-4.1, …)         (ANY model ID accepted)
```

### OpenAI models

| ID | Notes |
|---|---|
| `gpt-4o` | Fast; auto-selected for simple queries |
| `gpt-4.1` | Higher reasoning; auto-selected for complex queries |
| `gpt-4.1-mini` | Lightweight / low-latency |

### AWS Bedrock models (default list — not an allowlist)

Any valid Bedrock model ID works. Examples:

| Example model_id | Provider | Notes |
|---|---|---|
| `amazon.nova-micro-v1:0` | Amazon | Fastest / cheapest |
| `amazon.nova-lite-v1:0` | Amazon | Fast + multimodal |
| `amazon.nova-pro-v1:0` | Amazon | Highest quality Nova |
| `us.anthropic.claude-sonnet-4-5-20251203-v1:0` | Anthropic | Balanced |
| `us.anthropic.claude-haiku-3-5-20241022-v1:0` | Anthropic | Fast |
| `us.anthropic.claude-opus-4-5-20251101-v1:0` | Anthropic | Flagship |
| `us.anthropic.claude-opus-4-7-20260416-v1:0` | Anthropic | Latest |
| `us.meta.llama3-70b-instruct-v1:0` | Meta | Open weights |
| `mistral.mistral-large-2402-v1:0` | Mistral | Strong reasoning |
| `cohere.command-r-plus-v1:0` | Cohere | RAG-optimised |

To use a model not in the list, simply pass its Bedrock model ID directly — no code change required.

### Switching providers

```bash
# OpenAI (default)
curl -X POST http://54.175.54.77:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize","model":"gpt-4o","provider":"openai"}'

# Bedrock — Amazon Nova Pro
curl -X POST http://54.175.54.77:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize","model":"amazon.nova-pro-v1:0","provider":"bedrock"}'

# Bedrock — Claude Opus 4.7
curl -X POST http://54.175.54.77:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Analyze financials","model":"us.anthropic.claude-opus-4-7-20260416-v1:0","provider":"bedrock"}'

# Bedrock — any custom model ID
curl -X POST http://54.175.54.77:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{"skill":"financial_analysis","provider":"bedrock","model":"<your-model-id>","input":{}}'
```

### Required environment variables

```ini
OPENAI_API_KEY=sk-...                  # For OpenAI provider
AWS_ACCESS_KEY_ID=...                  # For Bedrock (same key as S3)
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=amazon.nova-lite-v1:0   # Default when no model specified
```

## Notes

- Bedrock requires IAM `bedrock:Converse` permission — see the Deployment Manual.
- Any Bedrock model ID is accepted; the BEDROCK_DEFAULT_MODELS list is informational only.
- Internet/API access required for all generation (both providers).
- Frontend: use the **Provider** + **Model** dropdowns, or type any model ID in the custom field.

---

## Skills System

The Skills System adds a **structured workflow layer** on top of the base RAG
and analytics stack.  Skills accept JSON input, call GPT, and return
deterministic JSON output — enabling repeatable, auditable AI workflows.

### Available Skills

| Skill | Endpoint | Description |
|---|---|---|
| `financial_analysis` | `POST /api/skills/run` | Extracts revenue breakdown, expense breakdown, key insights and risk flags from documents |
| `report_generation` | `POST /api/skills/run` | Generates a full business report: executive summary, metrics, findings, recommendations |
| `consulting_insights` | `POST /api/skills/run` | Applies a SWOT + strategic priorities framework to surface opportunities and risks |

### How to Call a Skill

```bash
curl -X POST http://localhost:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{
    "skill": "financial_analysis",
    "input": {
      "document_text": "Revenue this quarter was R$4.2M, up 12% year-on-year..."
    }
  }'
```

If you omit `document_text` / `context`, the skill automatically retrieves
relevant context from the vector store (indexed documents).

### File Structure

```
backend/
  skills/
    __init__.py
    financial_analysis.py   ← Revenue / expense extraction skill
    report_generation.py    ← Business report generation skill
    consulting_insights.py  ← SWOT + strategic priorities skill
    skill_router.py         ← Dispatches requests to the correct skill

  mcp/
    __init__.py
    skills_mcp.py           ← MCP server stub (stdio, JSON-RPC 2.0)
    README.md               ← MCP integration guide
```

### MCP Integration

Skills are architected as **MCP-ready callable units**.  The
`backend/mcp/skills_mcp.py` module implements a Model Context Protocol
server that exposes all three skills as discoverable tools.

To run the MCP server (connects to a live FastAPI instance):

```bash
python -m backend.mcp.skills_mcp
```

This enables integration with:
- **Claude Desktop** (via `mcp` config)
- **Cursor Background Agents** (tool calling)
- **n8n** (MCP node or HTTP Request node)
- Any agent platform that supports MCP tool discovery

### Frontend

The **Analytics Dashboard** (`frontend/pages/1_📊_Analytics_Dashboard.py`)
includes a **Skills Workbench** section with three one-click buttons:

- **Run Financial Analysis**
- **Generate Report**
- **Get Consulting Insights**

Each button calls `/api/skills/run`, renders the structured result inline,
and provides a JSON viewer for the full response.

---

## License

MIT
