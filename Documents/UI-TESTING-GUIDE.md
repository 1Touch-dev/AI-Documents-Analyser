# UI Testing Guide — AI Knowledge Platform

## Table of Contents
- [1. Project Overview](#1-project-overview)
- [2. Test Environment Setup](#2-test-environment-setup)
- [3. UI Testing Workflows](#3-ui-testing-workflows)
  - [3.1 Authentication Testing](#31-authentication-testing)
  - [3.2 Document Management Testing](#32-document-management-testing)
  - [3.3 RAG Query Testing](#33-rag-query-testing)
  - [3.4 Translation & Currency Testing](#34-translation--currency-testing)
  - [3.5 Financial Dashboard Testing](#35-financial-dashboard-testing)
  - [3.6 Document Status Testing](#36-document-status-testing)
  - [3.7 Prompt Template Testing](#37-prompt-template-testing)
  - [3.8 Conversation Management Testing](#38-conversation-management-testing)
  - [3.9 Analytics Testing](#39-analytics-testing)
  - [3.10 Copy Response Testing](#310-copy-response-testing)
- [4. API Endpoint Testing](#4-api-endpoint-testing)
- [5. Performance Testing](#5-performance-testing)
- [6. Troubleshooting](#6-troubleshooting)
- [7. Test Checklist](#7-test-checklist)

---

## 1. Project Overview

**AI Knowledge Platform** is an enterprise document management and AI-powered analysis platform.

### Key Capabilities
- Upload documents (PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON)
- RAG (Retrieval-Augmented Generation) queries via OpenAI GPT
- Markdown-rendered assistant responses (bold, italic, lists, tables, code blocks)
- Copy response button on every assistant message
- Translation to English (post-generation, GPT-powered, toggle on/off)
- Multi-currency conversion (ANY→ANY, 45+ currencies, live exchange rates via fawazahmed0 open-source API)
- Auto-detection of dominant document currency (heuristic, no LLM)
- Financial dashboard extraction (GPT-based, structured JSON)
- Document index status tracking (indexed vs. not indexed)
- Conversation persistence with source citations
- Delete individual conversations from the sidebar (trash icon on hover)
- Custom prompt templates
- Analytics: topics, entities, financial context, document explorer

### Technology Stack
| Layer | Technology |
|---|---|
| Frontend | Next.js (React, `react-markdown` + `remark-gfm`) |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL + ChromaDB (vector store) |
| AI / LLM | OpenAI GPT API (gpt-4o, gpt-4.1, gpt-4.1-mini) |
| Embeddings | BAAI/bge-large-en-v1.5 (local, 1024-dim, no GPU needed) |
| Caching | Redis (1-hour TTL, 100× speedup on cache hits) |
| Storage | AWS S3 (with local fallback) |
| Currency Rates | fawazahmed0 currency-api (primary) → open.er-api.com (fallback) → static table |

### Architecture
```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Next.js (React) │─────▶│   FastAPI        │─────▶│   PostgreSQL     │
│  :3001           │      │   :8010          │      │   :5432          │
└──────────────────┘      └──────┬───────────┘      └──────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ ChromaDB │  │ OpenAI   │  │  Redis   │
              │ :8001    │  │ GPT API  │  │  :6379   │
              └──────────┘  └──────────┘  └──────────┘
```

> **No Ollama / local LLM.** All generation runs through the OpenAI GPT API. `OPENAI_API_KEY` must be set.

---

## 2. Test Environment Setup

### Prerequisites

1. **Start all services:**
   ```bash
   docker compose up -d
   ```
   or for native dev:
   ```bash
   # Backend
   source .venv/bin/activate
   uvicorn backend.main:app --host 0.0.0.0 --port 8010

   # Frontend (separate terminal)
   cd frontend-nextjs && npm run start -- --hostname 0.0.0.0 --port 3001
   ```

2. **Verify services are running:**
   - Next.js UI: http://localhost:3001
   - FastAPI Backend: http://localhost:8010
   - API Docs (Swagger): http://localhost:8010/docs
   - Health Check: http://localhost:8010/api/health → `{"status":"healthy"}`
   - Currency Detection: http://localhost:8010/api/detect_currency → `{"currency":"BRL","confidence":"high",...}`

3. **Required configuration:**
   ```ini
   OPENAI_API_KEY=sk-your-key        # Required — all AI features
   REDIS_URL=redis://localhost:6379/0 # Optional — caching
   DATABASE_URL=postgresql://...      # Required — persistence
   ```

4. **Prepare test data:**
   - Sample PDFs (small: 1–5 MB, medium: 10–25 MB, large: 50 MB+)
   - Sample DOCX, XLSX, CSV files with text content

---

## 3. UI Testing Workflows

### 3.1 Authentication Testing

**Login (http://localhost:3001/login)**
1. Enter valid credentials (e.g., `Admin` / `Admin@123`)
2. ✅ Expect: redirect to `/dashboard`
3. Check that JWT token is stored in app state

**Register (http://localhost:3001/register)**
1. Enter a new username and password
2. ✅ Expect: account created, redirected to dashboard

**Invalid credentials**
1. Enter wrong password
2. ✅ Expect: `"Invalid credentials."` error message, no redirect

---

### 3.2 Document Management Testing

**Upload single document**
1. Navigate to Documents page
2. Select a PDF file
3. Optionally set a category
4. Click Upload
5. ✅ Expect: status changes `processing` → `ready`

**Batch upload**
1. Select 3+ files of different types
2. Click Upload
3. ✅ Expect: all files reach `ready` (or `failed` with reason for invalid types)
4. ✅ Duplicate detection: uploading same file twice shows `"duplicate"` status

**Delete document**
1. Click delete on a document
2. ✅ Expect: document removed from list and vector store

---

### 3.3 RAG Query Testing

**Basic query**
1. Navigate to Chat page
2. Type: `"What are the key topics in the uploaded documents?"`
3. Press **Enter** to send
4. ✅ Expect: formatted answer with source citations (bold headings, bullet lists rendered)
5. ✅ Expect: **Copy** button visible in the top-right of the assistant message

**Model selection**
1. Open Chat Settings → Query Controls
2. Select `gpt-4.1`
3. Ask a complex analytical question
4. ✅ Expect: deeper, more structured response

**Category filter**
1. Set Category to a specific value (e.g., `Financials`)
2. Ask a question
3. ✅ Expect: response only references documents in that category

**Session persistence**
1. Ask 3 questions in sequence
2. ✅ Expect: conversation persists in the left sidebar with a session ID
3. Refresh the page
4. ✅ Expect: conversation still visible in sidebar

---

### 3.4 Translation & Currency Testing

**Translate to English**
1. Open Chat Settings → Query Controls
2. Enable **Translate to English** toggle
3. Ask any question about a Portuguese document
4. ✅ Expect: response in English regardless of document language
5. ✅ Source citations (`[1]`, `[2]`) and numbers preserved

**Auto-detected default currency**
1. Navigate to Chat page
2. Open Chat Settings → Query Controls
3. ✅ Expect: first dropdown option shows `Default (Brazilian Real — BRL, auto-detected)` (or detected currency if documents use something else)
4. ✅ Expect: status bar badge shows `Currency: Default (BRL)`

**Currency: Default → USD**
1. In Chat Settings, set Currency to `US Dollar (USD)`
2. Ask: `"What is the total revenue in the documents?"`
3. ✅ Expect: R$ amounts in answer replaced with live $USD values using current exchange rates

**Currency: ANY → ANY**
1. Set Currency to `Euro (EUR)`
2. Ask a financial question
3. ✅ Expect: all currency amounts (BRL, USD, etc.) converted to € EUR using live rates
4. Try `Indian Rupee (INR)`, `Japanese Yen (JPY)`, `UAE Dirham (AED)`
5. ✅ Expect: all 45 currencies in the dropdown

**Currency status display**
- Status bar at top of chat shows current currency setting
- ✅ Expect: badge updates immediately when currency changes in settings

---

### 3.5 Financial Dashboard Testing

1. Navigate to Analytics page
2. Ensure at least one financial document is indexed
3. Click **Extract Financial Data**
4. ✅ Expect within 10–20 seconds:
   - Revenue table: F&B, Sponsorship, Tickets, Retail, Player Sales
   - Expenses table: Player Salary, Coach Salary, Travel, Stadium, Retail, F&B, Back Office, Misc
   - Revenue Total, Expense Total, Net Total KPI cards
   - Bar chart rendered
5. ✅ Expect graceful fallback (all zeros) if no financial data found — no crash
6. ✅ Expect `model_used` field populated in response

---

### 3.6 Document Status Testing

1. Navigate to Documents page
2. Click **Check Document Status**
3. ✅ Expect: section showing:
   - `indexed` — list of documents with vector embeddings
   - `not_indexed` — documents uploaded but not yet searchable
   - Counts for each group

---

### 3.7 Prompt Template Testing

**Create prompt**
1. Navigate to Prompts section
2. Create a new prompt with name and template text
3. ✅ Expect: prompt appears in the list

**Use prompt in chat**
1. Open Chat Settings → Query Controls
2. Select the prompt from the **Prompt Template** dropdown
3. Ask a question
4. ✅ Expect: response formatted according to the template

**Edit and delete**
1. Edit the template text and save
2. ✅ Expect: updated template available in chat
3. Delete the prompt
4. ✅ Expect: removed from dropdown

---

### 3.8 Conversation Management Testing

**Conversation persistence**
1. Start a new chat and exchange 3+ messages
2. ✅ Expect: conversation appears in sidebar
3. Refresh the page
4. ✅ Expect: conversation history persists
5. Click a past conversation
6. ✅ Expect: full message history restored with sources and markdown rendering
7. Click **+ New Chat**
8. ✅ Expect: blank chat, new session ID on next message

**Delete conversation**
1. Hover over any conversation in the sidebar
2. ✅ Expect: trash icon button becomes visible
3. Click the trash icon
4. ✅ Expect: conversation removed from sidebar immediately
5. If the deleted conversation was active: ✅ Expect chat area cleared

---

### 3.9 Analytics Testing

1. Navigate to Analytics page
2. ✅ Expect: KPI cards load (Documents, Chunks, Estimated Words)
3. Apply category/type filters
4. ✅ Expect: charts and Data Explorer update reactively
5. Topic Tags panel
6. ✅ Expect: bigram tags visible when documents are indexed
7. Monetary Values panel
8. ✅ Expect: currency figures extracted from text appear

---

### 3.10 Copy Response Testing

1. Submit any question in Chat
2. Wait for the assistant response
3. ✅ Expect: **Copy** button (clipboard icon + "Copy" text) in top-right of assistant bubble
4. Click the **Copy** button
5. ✅ Expect: button briefly changes to green check + "Copied" for 2 seconds
6. Paste into a text editor
7. ✅ Expect: full plain-text markdown content pasted correctly
8. ✅ Verify: **Copy** button only appears on assistant messages, not user messages

---

## 4. API Endpoint Testing

All endpoints can be tested via Swagger at `http://localhost:8010/docs` or via curl.

### Authentication
```bash
# Register
curl -X POST http://localhost:8010/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@123"}'

# Login
curl -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@123"}'
# → {"access_token":"...", "token_type":"bearer"}
```

### Query (RAG)
```bash
# Basic query
curl -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"summarize the documents","model":"auto","target_currency":"BRL"}'

# With translation + currency conversion
curl -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"receita total","model":"auto","translate_to_english":true,"target_currency":"USD"}'
```

### Financial Dashboard
```bash
curl -X POST http://localhost:8010/api/analytics/financial_dashboard \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","top_k":20}'
# → {"revenue":{...},"expenses":{...},"totals":{...},"notes":[...],"model_used":"gpt-4.1"}
```

### Document Status
```bash
curl http://localhost:8010/api/documents/status
# → {"indexed":[...],"not_indexed":[...],"indexed_count":N,"not_indexed_count":N}
```

### Currency Detection
```bash
curl http://localhost:8010/api/detect_currency
# → {"currency":"BRL","confidence":"high","counts":{"BRL":1224}}
```

### Delete Conversation
```bash
curl -X DELETE http://localhost:8010/api/conversations/<session-id>
# → {"deleted":true}
```

### Health & Models
```bash
curl http://localhost:8010/api/health
# → {"status":"healthy","app":"AI Knowledge Platform"}

curl http://localhost:8010/api/models
# → {"models":["gpt-4.1","gpt-4.1-mini","gpt-4o"]}
```

### Error Handling
```bash
# Bad API key → clean error message (no stack trace)
curl -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"test","openai_api_key":"sk-bad"}'

# Invalid currency → 400
curl -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"test","target_currency":"FAKE"}'
# → {"detail":"Unsupported currency: FAKE"}
```

---

## 5. Performance Testing

### Cache Hit (Redis)
```bash
# First request — cache miss (2–5 seconds)
time curl -s -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"what is in the documents","model":"auto"}' > /dev/null

# Second identical request — cache hit (~50 ms)
time curl -s -X POST http://localhost:8010/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"what is in the documents","model":"auto"}' > /dev/null
```

✅ Second request should be ~50–100× faster.

### Concurrent Load
```bash
# 5 simultaneous queries
for i in $(seq 1 5); do
  curl -s -X POST http://localhost:8010/api/query \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"test query $i\",\"model\":\"auto\"}" &
done
wait
echo "All done"
```

✅ All 5 should complete without 500 errors.

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `502 Bad Gateway` on query | `OPENAI_API_KEY` missing or invalid | Set key in `.env` or paste in Chat Settings |
| `400 Unsupported currency` | Invalid `target_currency` value | Use any of the 45 supported ISO codes (BRL, USD, EUR, GBP, JPY, INR, …) |
| Documents stuck `processing` | Parser error on file content | Check backend logs; try re-uploading |
| Financial dashboard all zeros | No financial documents indexed | Upload a document with R$ / $ amounts |
| Translate toggle no effect | `translate_to_english` not sent | Ensure Chat Settings are saved before submitting |
| Frontend 404 | Next.js server not running | Run `npm run start -- --port 3001` in `frontend-nextjs/` |
| Slow first query | Embedding model loading | Normal on first request; subsequent requests are fast |
| Currency not converting | Docs use detected currency as default | If `targetCurrency === detectedCurrency`, no conversion applied (same→same = 1.0 rate) |
| Copy button not working | Browser clipboard API blocked | Requires HTTPS or localhost; doesn't work on plain HTTP remote origins |

### Log Access
```bash
# Backend logs (tail live)
tail -f /home/ubuntu/AI-Documents-Analyser/backend.log

# Or from Docker
docker compose logs -f ai-backend
```

---

## 7. Test Checklist

### Core Features (OpenAI)
- [ ] Login with valid credentials → dashboard redirect
- [ ] Register new user → success
- [ ] Upload PDF → status reaches `ready`
- [ ] Batch upload (3+ files) → all processed
- [ ] Ask a question (provider=openai) → GPT answer with formatted markdown (bold, lists)
- [ ] `model_used` is `gpt-4o` or `gpt-4.1` (never local model)
- [ ] Copy button on assistant message → clipboard receives text, button shows "Copied"
- [ ] Translate to English → answer in English, citations preserved
- [ ] Currency auto-detected on Chat page load → "Default (X — CODE, auto-detected)" in dropdown
- [ ] Currency USD selected → R$ values converted in answer using live rates
- [ ] Financial Dashboard → revenue + expenses tables rendered
- [ ] Check Document Status → indexed / not_indexed lists returned
- [ ] Delete conversation via trash icon → removed from sidebar
- [ ] Create, use, and delete a prompt template
- [ ] Conversation history persists after page refresh

### Multi-Provider / Model Switching Tests
- [ ] Sidebar shows **Provider** dropdown with "OpenAI (GPT)" and "AWS Bedrock (Claude / Nova / Llama)"
- [ ] Switching provider to "bedrock" changes model dropdown to Bedrock model list
- [ ] Switching back to "openai" restores GPT model options
- [ ] Chat query with `provider=openai` + `model=gpt-4o` → response from OpenAI
- [ ] Chat query with `provider=bedrock` + `model=nova-lite` → response from Bedrock
- [ ] Analytics Skills Workbench shows Provider + Model selectors above skill buttons
- [ ] Running "Financial Analysis" with `provider=bedrock` + `model=nova-pro` → structured JSON result

### AWS Bedrock Validation Steps
```bash
# 1. Test Bedrock connectivity directly via API
curl -X POST http://localhost:8000/api/skills/run \
  -H "Content-Type: application/json" \
  -d '{"skill":"report_generation","input":{},"provider":"bedrock"}'
# Expected: {"skill":"report_generation","result":{...}}

# 2. Test Nova Micro (fastest)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize the documents","model":"nova-micro","provider":"bedrock"}'

# 3. Test Claude Sonnet via Bedrock
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the key financial figures?","model":"claude-sonnet-4.6","provider":"bedrock"}'

# 4. Verify all models are returned
curl http://localhost:8000/api/models
# Expected: {"models":[...openai...],"all_models":{"openai":[...],"bedrock":[...12 models...]}}
```

- [ ] `POST /api/skills/run` with `provider=bedrock` → Bedrock response
- [ ] `POST /api/query` with `provider=bedrock, model=nova-lite` → answer from Bedrock
- [ ] `GET /api/models` → returns `all_models` with both `openai` and `bedrock` sections
- [ ] `POST /api/analytics/financial_dashboard` with `provider=bedrock` → structured dashboard JSON
- [ ] Invalid Bedrock model name → graceful fallback to nova-lite (logged as warning)
- [ ] Missing AWS credentials → clean error: "AWS credentials not configured"

### API
- [ ] `GET /api/health` → `{"status":"healthy"}`
- [ ] `GET /api/models` → contains `all_models.bedrock` with 12+ entries
- [ ] `GET /api/detect_currency` → `{"currency":"...","confidence":"high/medium/low",...}`
- [ ] `POST /api/query` → 200 with answer (openai or bedrock)
- [ ] `POST /api/analytics/financial_dashboard` → structured JSON
- [ ] `GET /api/documents/status` → indexed + not_indexed
- [ ] `DELETE /api/conversations/{id}` → `{"deleted":true}`
- [ ] Bad API key → clean error message, no stack trace
- [ ] Invalid currency → 400 with clean message
- [ ] `GET /api/skills` → lists 3 skills with descriptions

### Skills System Tests
- [ ] `POST /api/skills/run {"skill":"financial_analysis","input":{},"provider":"openai"}` → structured result
- [ ] `POST /api/skills/run {"skill":"report_generation","input":{},"provider":"bedrock"}` → structured result
- [ ] `POST /api/skills/run {"skill":"consulting_insights","input":{},"provider":"bedrock"}` → SWOT result
- [ ] Unknown skill name → 400 with descriptive error listing supported skills

### Regression
- [ ] No reference to `localhost:11434` in active code
- [ ] No reference to Ollama in API responses
- [ ] Existing `/api/query` endpoint unchanged (backwards-compatible, provider defaults to "openai")
- [ ] Currency rate source is fawazahmed0 (not static table)
- [ ] Skills system still works after Bedrock integration (no breaking changes)
