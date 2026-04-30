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

## Enterprise Features

### Skills System

Each skill enforces **strict JSON output schemas** — no free-text responses.
The LLM is instructed to return a pure JSON object; the skill layer validates
and merges the response against a known schema before returning it.

| Skill | Endpoint | Strict Output Schema |
|---|---|---|
| `financial_analysis` | `POST /api/skills/run` | `{revenue:{}, expenses:{}, insights:[], risks:[], opportunities:[]}` |
| `report_generation` | `POST /api/skills/run` | `{title, executive_summary, key_metrics:{}, analysis:[], recommendations:[]}` |
| `consulting_insights` | `POST /api/skills/run` | `{strengths:[], weaknesses:[], opportunities:[], threats:[], strategic_actions:[]}` |

```bash
curl -X POST http://localhost:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{"skill":"financial_analysis","input":{"document_text":"..."},"provider":"openai"}'
```

---

### Workflow Engine

Multi-step pipelines that chain document retrieval → skill execution → output:

| Workflow | Endpoint | Steps |
|---|---|---|
| `financial` | `POST /api/workflows/run` | retrieve_documents → extract_financials → calculate_totals → generate_insights |
| `consulting` | `POST /api/workflows/run` | retrieve_documents → swot_analysis → strategic_planning → compile_output |
| `report` | `POST /api/workflows/run` | retrieve_documents → collect_metrics → generate_summary → compile_report |

```bash
# List available workflows
curl http://localhost:8000/api/workflows/list

# Run a workflow
curl -X POST http://localhost:8000/api/workflows/run \
  -H "Content-Type: application/json" \
  -d '{"workflow":"financial","provider":"openai","model":"gpt-4o","input":{}}'
```

---

### MCP Server (JSON-RPC 2.0)

A real MCP server is exposed at `POST /api/mcp/execute`. Supports:
- `initialize` — capability negotiation
- `tools/list` — enumerate all 4 tools
- `tools/call` — execute any tool with arguments

```bash
# List tools via MCP
curl -X POST http://localhost:8000/api/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Execute a tool
curl -X POST http://localhost:8000/api/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"financial_analysis","arguments":{"document_text":"Revenue: $1M","provider":"openai"}}}'
```

Available MCP tools: `financial_analysis`, `generate_report`, `consulting_insights`, `run_workflow`

---

### n8n Webhook Endpoints

No-auth external triggers for automation pipelines:

| Webhook | URL |
|---|---|
| Financial | `POST /api/webhooks/financial` |
| Consulting | `POST /api/webhooks/consulting` |
| Report | `POST /api/webhooks/report` |

Body: `{"provider":"openai","model":"auto","document_text":"...","context":"..."}`

---

### Export

```bash
# Export workflow result as JSON (default)
curl -X POST http://localhost:8000/api/export/report \
  -d '{"workflow":"report","provider":"openai","model":"gpt-4o","input":{}}'

# Export as CSV (Tableau-compatible)
curl -X POST http://localhost:8000/api/export/report \
  -d '{"workflow":"financial","input":{"format":"csv"}}'
```

---

### File Structure

```
backend/
  skills/
    financial_analysis.py    ← Strict JSON schema: revenue/expenses/insights
    report_generation.py     ← Strict JSON schema: title/summary/metrics/recs
    consulting_insights.py   ← Strict JSON schema: SWOT + strategic_actions
    skill_router.py

  workflows/
    workflow_engine.py       ← run_workflow(), list_workflows(), WORKFLOW_REGISTRY
    financial_workflow.py    ← 4-step financial pipeline
    consulting_workflow.py   ← 4-step SWOT pipeline
    report_workflow.py       ← 4-step report pipeline

  mcp/
    server.py                ← Real JSON-RPC 2.0 MCP server
    skills_mcp.py            ← stdio MCP server (for Claude Desktop / Cursor)
    README.md

frontend-nextjs/src/app/(app)/
  workflows/page.tsx         ← Workflows page with selector, viz, export
  analytics/page.tsx         ← Skills Workbench section
```

### Frontend — Workflows Page

Navigate to `/workflows` in the Next.js app for:
- Visual workflow selector with step previews
- Provider + model configuration (OpenAI / Bedrock)
- Real-time execution with step progress display
- Structured result visualisation (tables, cards, sections)
- One-click JSON and CSV export

---

## License

MIT

---

## Production Features

### Authentication (JWT)

All sensitive endpoints require a valid Bearer token:

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -d '{"username":"analyst1","password":"Secure1234!"}'

# Login → get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d '{"username":"analyst1","password":"Secure1234!"}' | jq -r .access_token)

# Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me
```

### RBAC (Role-Based Access Control)

| Role    | Permissions |
|---------|------------|
| admin   | Everything including user management |
| analyst | Workflows, skills, MCP, export, save reports |
| user    | Same as analyst (legacy default) |
| viewer  | Read-only: view reports, usage stats, chat |

```bash
# Admin: change another user's role
curl -X PATCH "http://localhost:8000/api/admin/users/alice/role?role=analyst" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Rate Limiting

| Endpoint category | Limit |
|---|---|
| Chat / query | 60/minute |
| Workflow runs | 10/minute |
| MCP tool calls | 20/minute |
| Skills | 30/minute |

Exceeding limits returns HTTP 429.

### Cost Tracking

Every LLM call is logged to the `llm_usage` table with:
- provider, model, tokens (prompt + completion), estimated USD cost
- Accessible via `GET /api/usage/summary`

### Audit Logging

Every sensitive action (login, workflow run, MCP call, skill execution, export)
is written to `audit_logs` with user, IP, action, status, and context.
- Accessible via `GET /api/audit/logs`

### Report Persistence

```bash
# Save a workflow result
curl -X POST http://localhost:8000/api/reports/save \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"report_type":"financial","title":"Q1 2026","data":{...}}'

# List saved reports
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/reports

# Get a specific report
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/reports/<id>
```

### MCP Security

- `initialize` and `tools/list` are public
- `tools/call` requires auth + RBAC role check per tool
- All MCP inputs are validated against prompt-injection patterns
- Denied calls are recorded in audit_logs

### Input Validation (Prompt Injection Protection)

All text inputs to workflows, skills, and MCP tools are screened for:
- Role-switching ("ignore previous instructions")
- Jailbreak patterns ("DAN mode", "developer mode")
- Instruction overrides (`<|im_start|>`, `###SYSTEM###`)
- XSS patterns

Inputs exceeding size limits are truncated.

### Retry + Timeout

LLM calls wrap with:
- Max 2 retries with exponential back-off (2s, 4s)
- 90-second timeout per call
- Graceful fallback response on permanent failure

### Security Environment Variables

```env
JWT_SECRET=<strong-secret-min-32-chars>
WEBHOOK_SECRET=<shared-secret-for-n8n>   # optional
```
