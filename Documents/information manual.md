# AI Knowledge Platform — Information & Architecture Manual

This document provides a deep-dive analysis into the core components that power the AI Knowledge Platform. It is intended for software engineers, IT administrators, or curious stakeholders who want to understand _how_ the system achieves its results.

The platform is built on four core pillars.

---

## 1. Document Ingestion & Processing Pipeline

The ingestion pipeline transforms unstructured text (like a messy PDF or a PowerPoint deck) into mathematically searchable data.

- **S3 Blob Storage:** When a user uploads a document, the original raw file (up to 500 MB) is immediately piped into an **AWS S3 Bucket**. This keeps the application server's disk space free and ensures files are resiliently stored. A local `data/uploads/` fallback is used automatically when S3 credentials are not configured.
- **Multi-Parser Text Extraction:** The system uses `PyPDF2`, `python-docx`, and `pandas` to scrape raw text from various proprietary file formats. A UTF-8/Latin-1 fallback decoder handles encoding edge cases.
- **Adaptive Chunking:** The system splits documents into overlapping chunks (default: 1,000 characters, 200-character overlap). The overlap ensures that sentences broken between chunks do not lose their context.
- **Vectorization (Embeddings):** Each text chunk is passed through the `BAAI/bge-large-en-v1.5` sentence-transformer model running locally (1024-dimensional vectors). Configurable via the `EMBEDDING_MODEL` environment variable; defaults to `bge-base-en-v1.5` (768-dim) if not overridden.
- **ChromaDB Vector Store:** Vectors are stored in ChromaDB, a high-performance vector database that enables fast nearest-neighbor (semantic) search across all uploaded content.

---

## 2. Multi-Provider LLM Router

Retrieval-Augmented Generation (RAG) forces the AI to answer based _only_ on evidence retrieved from uploaded documents, preventing hallucination.

### Provider Architecture

Every API request carries a `provider` field (`"openai"` or `"bedrock"`). The `LLMRouter` dispatches accordingly:

```
Request { provider, model, messages }
         │
         LLMRouter.generate()
         │
   ┌─────┴──────┐
   ▼            ▼
OpenAI API   Bedrock Converse API
(GPT-4o/4.1) (any model ID)
```

### OpenAI Provider

- Routes through the OpenAI Chat Completions API.
- Three registered models: `gpt-4o` (fast), `gpt-4.1` (reasoning), `gpt-4.1-mini` (lightweight).
- **Auto-routing:** `model="auto"` selects `gpt-4o` for simple queries and `gpt-4.1` for complex ones (based on length + keyword heuristics).
- **Legacy aliases:** old model names (`llama3`, `gemma`, etc.) are silently remapped to the nearest GPT equivalent.

### AWS Bedrock Provider

- Routes through the **AWS Bedrock Converse API** — one unified call for all model families.
- **No allowlist:** any valid Bedrock model ID is accepted and passed straight through. Adding a new model requires zero code changes.
- **Async-safe:** boto3 (synchronous) runs in `asyncio.to_thread()` to avoid blocking the FastAPI event loop.
- **Cross-region inference profiles:** model IDs prefixed with `us.` use AWS's multi-region routing for higher availability.

### When to use which model

| Use Case | Recommended Model | Provider |
|---|---|---|
| Fast document Q&A | `gpt-4o` or `amazon.nova-micro-v1:0` | openai / bedrock |
| Complex multi-document analysis | `gpt-4.1` or `us.anthropic.claude-opus-4-7-20260416-v1:0` | openai / bedrock |
| Financial extraction | `gpt-4.1` or `amazon.nova-pro-v1:0` | openai / bedrock |
| Cost-sensitive bulk processing | `gpt-4.1-mini` or `amazon.nova-micro-v1:0` | openai / bedrock |
| RAG-optimised retrieval | `gpt-4o` or `cohere.command-r-plus-v1:0` | openai / bedrock |

### Global Context Awareness

Before answering, the system injects a dynamically generated index of every file currently in the knowledge base into the system prompt — regardless of which provider is used.

---

## 3. Business Features

### 3.1 Translation
Queries can be translated to English post-generation. The `translate_to_english` flag in the query payload triggers a second GPT call that translates the answer while preserving citations (`[1]`, `[2]`) and numeric values. This is ideal for Brazilian Portuguese documents where the AI response is generated in Portuguese but the user needs English output. The toggle is persistent across the browser session via `localStorage`.

### 3.2 Currency Conversion — 45+ Currencies (ANY→ANY)

The `CurrencyService` (`services/currency_service.py`) detects and converts currency amounts in AI-generated text to any of 45+ supported target currencies. Conversion is performed using live exchange rates with a multi-tier fallback:

| Tier | Provider | Notes |
|---|---|---|
| Primary | fawazahmed0 currency-api (JSDelivr CDN) | Free, open-source, 150+ currencies, no API key |
| Fallback | open.er-api.com | Free, no key required |
| Static | USD cross-rate table (in-process) | Used only when both live APIs are unreachable |

Rates are cached in-process for **1 hour** (`_CACHE_TTL = 3600`).

**Three-pass text scanning:**
1. **BRL pass** — `R$` with Brazilian multipliers (`mil` = ×1000, `M`/`MM` = ×1,000,000)
2. **Symbol-prefix pass** — `$` (USD), `€` (EUR), `£` (GBP), `₹` (INR), `¥` (JPY/CNY), `R$` (BRL), `A$` (AUD), `C$` (CAD), and 15 more symbols
3. **ISO-code suffix pass** — `"100 USD"`, `"200.50 EUR"`, etc.

Position-based overlap detection prevents any text span from being converted twice.

**Auto-Detection (`GET /api/detect_currency`):** A heuristic endpoint scans up to 300 indexed document chunks using the same regex patterns. It counts currency occurrences per code and returns the most frequent with a confidence level (`high` ≥ 60%, `medium` ≥ 35%, `low` below). No LLM is involved — zero hallucination risk. The frontend calls this on load and auto-selects the detected currency as the "Default" option.

**Supported currencies (45):** BRL, USD, CAD, MXN, ARS, CLP, COP, PEN, EUR, GBP, CHF, NOK, SEK, DKK, PLN, CZK, HUF, RON, TRY, RUB, UAH, JPY, CNY, INR, KRW, SGD, HKD, TWD, THB, IDR, MYR, PHP, VND, AUD, NZD, AED, SAR, QAR, ILS, EGP, ZAR, NGN, KES, PKR, BDT

### 3.3 Financial Dashboard
`POST /api/analytics/financial_dashboard` uses GPT to extract structured financial data from indexed documents. It returns a JSON payload with:
- `revenue`: f_and_b, sponsorship, tickets, retail, player_sales
- `expenses`: player_salary, coach_salary, travel, stadium, retail, f_and_b, back_office, misc
- `totals`: revenue_total, expense_total, net_total
- `notes` and `source_documents`

A normalized default (all zeros) is returned gracefully if extraction fails. The model can be selected per-request (gpt-4o, gpt-4.1, gpt-4.1-mini).

### 3.4 Document Index Status
`GET /api/documents/status` compares the PostgreSQL document registry against the ChromaDB vector store and returns two lists: `indexed` (chunks present in vector store) and `not_indexed` (uploaded but not yet searchable). This allows operators to audit data completeness without manual inspection.

### 3.5 Copy Response
Every assistant chat message has a **Copy** button in the top-right corner. Clicking it writes the full plain-text markdown content to the system clipboard. A green "Copied" confirmation is shown for 2 seconds using a `useRef` timer to avoid stale closures.

### 3.6 Delete Conversation
`DELETE /api/conversations/{session_id}` permanently removes a conversation and all its messages from PostgreSQL. The frontend exposes this as a trash icon button that appears on hover next to each conversation in the sidebar. If the deleted conversation is currently active, the chat area is cleared automatically.

---

## 4. Analytics & the Content Engine

Unlike basic file managers that only show pie charts of "File Types", this platform features an advanced `analytics_engine.py` that generates Business Intelligence directly from the unstructured text.

- **Bigram Extraction:** The backend analyzes thousands of text chunks and counts the highest-frequency 2-word pairs (bigrams), filtering English and Portuguese stop words to isolate real themes (e.g., `"Operação interna"`, `"Ticket médio"`).
- **Financial Context Identification:** Regex patterns scan raw text for currency symbols and percentages and pull them into the analytics dashboard for immediate auditing.
- **Entity Detection:** The engine identifies monetary values, percentages, organizations, dates, emails, and URLs across the entire document corpus.
- **Jaccard Similarity:** Document similarity is computed by comparing key-phrase sets using Jaccard scoring (0.0–1.0).

---

## 5. Frontend Architecture

The platform uses a **Next.js frontend** (`frontend-nextjs/`) as the primary UI, served on port **3001**.

- **Next.js Frontend (Active):** A production-grade React app with server-side rendering. All API calls are proxied through a Next.js API route (`/api/backend/[...path]`) to the FastAPI backend, preserving CORS security.
- **Markdown Rendering:** Assistant chat responses are rendered with `react-markdown` + `remark-gfm`, supporting bold, italic, headers, lists, tables, code blocks, and blockquotes with Tailwind-styled components.
- **App Preferences Context:** User preferences (model, currency, category, translate toggle, API key) are persisted in `localStorage` under the key `akp_preferences` and injected into every query automatically.
- **Legacy Streamlit UI (`frontend/streamlit_app.py`):** Retained for reference only. Not used in production. The Next.js app supersedes it entirely.
- **FastAPI Backend:** Handles all compute asynchronously. Runs on port **8010**.
- **PostgreSQL Persistence:** All relational state — user accounts, document metadata, conversation histories, and prompt libraries — is stored in PostgreSQL via SQLAlchemy ORM.
- **Redis Caching:** Repeated identical queries are served from a Redis cache (1-hour TTL), providing up to 100× speedup on cache hits.

---

## 6. Local Run Quick Reference

```bash
cd /home/ubuntu/AI-Documents-Analyser
source .venv/bin/activate

# Terminal 1 — Backend (port 8010)
uvicorn backend.main:app --host 0.0.0.0 --port 8010

# Terminal 2 — Frontend (port 3001)
cd frontend-nextjs
npm run start -- --hostname 0.0.0.0 --port 3001
```

Required environment variables:

```ini
OPENAI_API_KEY=sk-your-key                                        # Required — all GPT features
REDIS_URL=redis://localhost:6379/0                                 # Optional — defaults to localhost
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_knowledge_platform
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5                            # Optional — overrides default bge-base
```

Health checks:

```bash
curl http://localhost:8010/api/health
curl http://localhost:8010/api/detect_currency
curl -o /dev/null -w "%{http_code}" http://localhost:3001
```
