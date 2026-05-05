# AI Knowledge Platform — User Manual

Welcome to the AI Knowledge Platform. This system empowers you to upload hundreds of large documents (PDFs, PPTXs, CSVs, etc.), extract meaning from them automatically, and query them using state-of-the-art AI powered by **OpenAI GPT**.

---

## 1. Accessing the Platform

| Environment | URL |
|---|---|
| Production (EC2) | `http://54.175.54.77:3001` |
| Local development | `http://localhost:3001` |
| Backend API Docs | `http://54.175.54.77:8000/docs` |

### Default Credentials
Log in with the credentials provided by your administrator. To register a new account, use the **Register** page at `/register`.

---

## 2. Starting and Stopping (Self-Hosted)

### Docker
```bash
cd /home/ubuntu/AI-Documents-Analyser
docker compose up -d      # start
docker compose down       # stop
```

### Native Python (Development)
```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend-nextjs
npm run start -- --hostname 0.0.0.0 --port 3001
```

Stop native processes:
```bash
pkill -f "uvicorn backend.main:app" || true
pkill -f "next.*3001" || true
```

---

## 3. Chat Settings — Model, Currency & Translation

All chat settings are accessed via the **Chat Settings** button (gear icon) in the Chat page. Settings persist across the browser session via `localStorage`.

### Model Selection
The platform routes all requests through a **Universal Multi-Model Router**. Supported providers:

| Provider | Supported Models | Best For |
|---|---|---|
| **OpenAI** | `gpt-4o`, `gpt-4.1`, `gpt-4.1-mini` | High accuracy, fast responses, everyday queries. |
| **AWS Bedrock** | Any Bedrock Model ID (e.g., `amazon.nova-pro-v1:0`, `anthropic.claude-3-5-sonnet-v2:0`) | Enterprise compliance, massive document contexts, varied model choices. |

- **Auto Mode**: If `auto` is selected, the system automatically picks the best model (typically `gpt-4.1` or `gpt-4o`) based on query complexity.
- **Custom Model IDs**: For Bedrock, you can enter any valid Model ID directly in the settings sidebar.

> **No local model is required.** All AI runs through the OpenAI cloud API. Ensure `OPENAI_API_KEY` is set in the server environment, or paste your key in the **OpenAI API** tab of Chat Settings.

### Translate to English
Toggle **Translate to English** in Chat Settings → Query Controls. When enabled, the AI translates its answer into English after generation. Useful when documents are in Portuguese but you need English output. Citations (`[1]`, `[2]`) and numeric values are preserved throughout translation.

### Currency Conversion — 45+ Currencies
Select a target currency in Chat Settings → Query Controls. The system automatically detects all currency amounts in the AI response and converts them using **live exchange rates** sourced from the fawazahmed0 open-source API (updated hourly, no API key required).

**Auto-Detection:** On page load the platform scans your indexed documents and auto-detects the dominant currency (e.g., BRL for Brazilian documents). The first dropdown option shows `Default (Brazilian Real — BRL, auto-detected)` and is pre-selected automatically.

**Supported output currencies (45+):**

| Region | Currencies |
|---|---|
| Americas | BRL, USD, CAD, MXN, ARS, CLP, COP, PEN |
| Europe | EUR, GBP, CHF, NOK, SEK, DKK, PLN, CZK, HUF, RON, TRY, RUB, UAH |
| Asia-Pacific | JPY, CNY, INR, KRW, SGD, HKD, TWD, THB, IDR, MYR, PHP, VND, AUD, NZD |
| Middle East / Africa | AED, SAR, QAR, ILS, EGP, ZAR, NGN, KES |
| South Asia | PKR, BDT |

**Detected input patterns in AI responses:**
- `R$ 1.500,00` — Brazilian Real with multipliers (mil, M, MM)
- `$100`, `€200`, `£50`, `₹1000`, `¥500`, `A$200`, `C$150` — symbol prefix
- `"100 USD"`, `"200 EUR"`, `"50 GBP"` — ISO code suffix

If the live rate API is unreachable, the system falls back to open.er-api.com then to a static USD cross-rate table — the answer is always returned, never blocked.

### OpenAI API Key
If the server does not have a global `OPENAI_API_KEY` configured, paste your personal key in Chat Settings → OpenAI API. The key is used only for your session and is never stored in the database.

---

## 4. Uploading Documents

Supported formats: `PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON` — up to **500 MB per file**.

**From the Documents page:**
1. Click **Choose files** and select one or more files.
2. Optionally set a **Category** (e.g., `Financials Q3`, `Legal Docs`).
3. Click **Upload**. Progress is shown in real time.

**From the Chat page:**
1. Open Chat Settings → Upload Documents tab.
2. Select files and click **Upload to Knowledge Base**.

**Processing stages:**
- `processing` — file is being parsed, chunked, and embedded into the vector store
- `ready` — document is fully indexed and searchable
- `failed` — processing failed (check file format and size)

Large documents (300+ pages) may take 30–60 seconds to reach `ready` status.

---

## 5. Chatting With Your Documents (RAG)

1. Go to the **Chat** page.
2. Type a question and press **Enter** to send (Shift+Enter inserts a new line).
3. The system retrieves the most relevant passages from your documents and generates a cited answer with full markdown formatting.

**Example queries:**
- *"What were the Q3 operational risks mentioned across our board presentations?"*
- *"Summarize the key CAPEX figures from the 2025 budget documents."*
- *"Compare revenue across the last three fiscal years."*

Each answer includes **Sources** — the document name and excerpt the AI used. Source citations `[1]`, `[2]` in the answer body correspond to source cards below.

### Copy Response
Every assistant message has a **Copy** button (clipboard icon) in the top-right corner of the message bubble. Click it to copy the full plain-text response to your clipboard. The button briefly shows a green "Copied" confirmation.

### Conversation History
Every chat session is automatically saved. The left sidebar lists all past conversations. Click any entry to resume it. A **trash icon** appears on hover next to each conversation — click it to permanently delete that conversation. Start a fresh session with **+ New Chat**.

---

## 6. Analytics Dashboard

Navigate to the **Analytics** page for intelligence extracted from your document library.

### Overview KPIs
- Total documents, chunks, estimated words, reading time, storage used

### Financial Dashboard
Click **Extract Financial Data** to trigger GPT-based financial extraction across all indexed documents. The result shows:
- **Revenue categories:** F&B, Sponsorship, Tickets, Retail, Player Sales
- **Expense categories:** Player Salary, Coach Salary, Travel, Stadium, Retail, F&B, Back Office, Misc
- **Totals:** Revenue Total, Expense Total, Net Total

A bar chart and summary cards are rendered automatically. You can select different GPT models for the extraction using the model selector.

### Content Intelligence
- **Topic Tags** — the most frequent bigram themes extracted from document text
- **Monetary Values** — all currency figures detected across the corpus
- **Organizations, Dates, Contacts** — named-entity extraction

### Data Explorer
A searchable, filterable table of all documents with category, type, status, uploader, and chunk count.

---

## 7. Documents Page — Index Status

Click **Check Document Status** to compare the document registry against the vector store. The result shows:
- **Indexed** — documents fully searchable in the vector store
- **Not Indexed** — documents uploaded but not yet searchable (may need re-upload)

---

## 8. Prompt Templates

Frequently use the same complex prompt? Go to the **Prompts** section.

1. Create a template, e.g.: *"Act as a CFO and summarize the key CAPEX takeaways."*
2. Give it a name and optional category.
3. In Chat Settings → Query Controls, select it from the **Prompt Template** dropdown.

---

## 9. Report Generation

Use the **Report Generation** page to create structured reports:
1. Enter a topic and a query.
2. Choose report type (`general`, `financial`, etc.) and output format (`markdown`, `json`, `table`).
3. Click Generate. The system retrieves relevant context from documents and GPT synthesizes a full report.

---

## 10. Conversations

All conversations are listed in the **Chat** sidebar and the Conversations page. Each conversation tracks:
- All messages (user + assistant) with full markdown rendering
- Source citations per assistant message
- Category and timestamp

Delete any conversation using the trash icon that appears on hover in the sidebar, or from the Conversations page.
