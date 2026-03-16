# UI Testing Guide - AI Documents Analyser

## Table of Contents
- [1. Project Overview](#1-project-overview)
- [2. Test Environment Setup](#2-test-environment-setup)
- [3. UI Testing Workflows](#3-ui-testing-workflows)
  - [3.1 Authentication Testing](#31-authentication-testing)
  - [3.2 Document Management Testing](#32-document-management-testing)
  - [3.3 RAG Query Testing](#33-rag-query-testing)
  - [3.4 Prompt Template Testing](#34-prompt-template-testing)
  - [3.5 Conversation Management Testing](#35-conversation-management-testing)
  - [3.6 Dashboard & Analytics Testing](#36-dashboard--analytics-testing)
- [4. Advanced Testing Scenarios](#4-advanced-testing-scenarios)
- [5. Performance Testing via UI](#5-performance-testing-via-ui)
- [6. Troubleshooting Common Issues](#6-troubleshooting-common-issues)
- [7. Test Checklist](#7-test-checklist)

---

## 1. Project Overview

**AI Documents Analyser** is an enterprise-level document management and AI-powered analysis platform that enables users to:
- Upload documents (PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON)
- Perform RAG (Retrieval-Augmented Generation) queries across documents
- Use multiple LLM providers (Ollama, OpenAI, Anthropic, Gemini)
- Manage conversations and custom prompts
- Visualize data with professional BI dashboards

### Technology Stack
- **Frontend:** Streamlit 1.41.1
- **Backend:** FastAPI 0.115.6
- **Database:** PostgreSQL + ChromaDB (vector store)
- **AI/ML:** LangChain, Sentence-Transformers (bge-base-en-v1.5)
- **Caching:** Redis (for 100X query speedup)

### Architecture
```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Streamlit      │─────▶│   FastAPI        │─────▶│   PostgreSQL     │
│   Frontend       │      │   Backend        │      │   Database       │
│   :8501          │      │   :8000          │      │   :5432          │
└──────────────────┘      └──────┬───────────┘      └──────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ ChromaDB │  │  Ollama  │  │  Redis   │
              │ :8001    │  │ :11434   │  │ (Cache)  │
              └──────────┘  └──────────┘  └──────────┘
```

---

## 2. Test Environment Setup

### Prerequisites
1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running:**
   - Streamlit UI: http://localhost:8501
   - FastAPI Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - ChromaDB: http://localhost:8001
   - PostgreSQL: localhost:5432

3. **Check service health:**
   - Navigate to http://localhost:8000/health
   - Expected response: `{"status": "healthy"}`

4. **Prepare test data:**
   - Sample PDFs (small: 1-5MB, medium: 10-25MB, large: 50MB+)
   - Sample DOCX files with text content
   - Sample XLSX files with data tables
   - Sample TXT/JSON files

### Environment Configuration
- **Local Setup:** Default (Ollama models)
- **Cloud LLM Testing:** Prepare API keys for OpenAI/Anthropic/Gemini
- **User Credentials:** Create test user accounts for authentication testing

---

## 3. UI Testing Workflows

### 3.1 Authentication Testing

#### Test Case 1.1: User Registration
**Steps:**
1. Access Streamlit UI at http://localhost:8501
2. If prompted, enter registration details:
   - Username: `testuser1`
   - Password: `SecurePass123!`
3. Click "Register" or submit form

**Expected Result:**
✅ Registration successful message appears
✅ User is automatically logged in or redirected to login

**Validation:**
- Check browser session storage for auth token
- Verify user exists in PostgreSQL `users` table

#### Test Case 1.2: User Login
**Steps:**
1. Open UI in new incognito/private window
2. Enter credentials:
   - Username: `testuser1`
   - Password: `SecurePass123!`
3. Click "Login"

**Expected Result:**
✅ Login successful
✅ JWT token stored in session
✅ Main app interface loads with all tabs visible

**Validation:**
- Refresh page - session should persist
- Check Network tab (F12) for Authorization headers in API calls

#### Test Case 1.3: Invalid Credentials
**Steps:**
1. Enter incorrect username or password
2. Submit login form

**Expected Result:**
❌ Error message: "Invalid credentials"
❌ No redirect to main app
❌ No token stored

---

### 3.2 Document Management Testing

#### Test Case 2.1: Single Document Upload (Drag-and-Drop)
**Steps:**
1. Navigate to **Sidebar > Document Upload** section
2. Drag a PDF file (e.g., `sample_report.pdf`) into the upload box
3. Wait for upload confirmation

**Expected Result:**
✅ Upload progress indicator appears
✅ Success message: "Document uploaded successfully"
✅ File appears in **📁 Documents Tab** with status 🟡 Processing

**Validation:**
1. Navigate to **Documents Tab**
2. Verify new document entry with:
   - Title: `sample_report.pdf`
   - Status: 🟡 Processing → 🟢 Ready (wait 10-30s)
   - Chunks: > 0 (depends on document size)
   - Uploader: Your username
3. Check backend logs for processing completion

#### Test Case 2.2: Single Document Upload (Click Upload)
**Steps:**
1. Click "Browse files" button in sidebar
2. Select a DOCX file from file picker
3. Confirm upload

**Expected Result:**
✅ Same as Test Case 2.1

#### Test Case 2.3: Batch Document Upload
**Steps:**
1. In sidebar batch upload section, select multiple files:
   - `document1.pdf` (10MB)
   - `document2.docx` (5MB)
   - `data.xlsx` (2MB)
2. Click "Upload Batch"
3. Monitor batch status

**Expected Result:**
✅ Batch upload initiated message
✅ Batch ID returned (e.g., `batch_abc123`)
✅ Progress tracker shows: "Processing 1/3, 2/3, 3/3"
✅ All files appear in Documents Tab with 🟡 → 🟢 status transition

**Validation:**
- Navigate to Documents Tab and verify all 3 files listed
- Check each document has `chunk_count > 0`
- Verify total storage metric increased

#### Test Case 2.4: Document List Viewing
**Steps:**
1. Navigate to **📁 Documents Tab**
2. Observe document library table

**Expected Result:**
✅ Table displays columns: Title, Category, Type, Size, Chunks, Status, Uploader, Date
✅ Metrics row shows:
   - Total Documents: Count of all documents
   - Ready: Count of 🟢 Ready documents
   - Total Chunks: Sum of all chunks
   - Storage Used: Total size in MB/GB

**Validation:**
- Sort by Date (newest first) - verify chronological order
- Check status icons: 🟢 Ready, 🟡 Processing, 🔴 Failed

#### Test Case 2.5: Document Deletion
**Steps:**
1. In Documents Tab, locate a document to delete
2. Note the document ID (visible in table)
3. Enter document ID in "Delete Document" input box
4. Click "Delete" button
5. Confirm deletion if prompted

**Expected Result:**
✅ Success message: "Document deleted successfully"
✅ Document removed from table
✅ Metrics updated (Total Documents -1, Storage decreased)

**Validation:**
- Refresh page - document should not reappear
- Check PostgreSQL `documents` table - record should be deleted
- Check ChromaDB - associated vectors should be removed

#### Test Case 2.6: Unsupported File Type Upload
**Steps:**
1. Attempt to upload unsupported file (e.g., `.exe`, `.zip`)

**Expected Result:**
❌ Error message: "Unsupported file type"
❌ No entry created in Documents Tab

---

### 3.3 RAG Query Testing

#### Test Case 3.1: Basic RAG Query
**Prerequisites:** At least one document with status 🟢 Ready

**Steps:**
1. Navigate to **💬 Chat Tab**
2. Ensure model is selected (e.g., "Auto" or "OpenAI")
3. Enter question in chat input:
   ```
   What are the main topics discussed in the uploaded documents?
   ```
4. Press Enter or click Send

**Expected Result:**
✅ Chat message appears with user icon/name
✅ Assistant response generates with typewriter effect (optional)
✅ Response includes relevant content from documents
✅ Source citations displayed as badges: [1], [2], [3]
✅ Clicking citation badge shows source document title

**Validation:**
- Check that response is contextually accurate
- Verify sources match uploaded documents
- Response time should be < 5s (first query) or < 100ms (cached repeat query)

#### Test Case 3.2: Query with Custom Prompt Template
**Steps:**
1. Navigate to **📝 Prompts Tab**
2. Create new prompt:
   - Name: `Summarize Concisely`
   - Category: `Summary`
   - Template:
     ```
     Based on the context: ${context}

     Provide a brief 3-sentence summary to answer: ${question}
     ```
3. Save prompt
4. Return to **💬 Chat Tab**
5. In sidebar, select "Prompt Template" → `Summarize Concisely`
6. Ask question:
   ```
   What is this document about?
   ```

**Expected Result:**
✅ Response is exactly 3 sentences (as constrained by prompt)
✅ Response uses provided template format

#### Test Case 3.3: Model Selection Testing
**Steps:**
1. In Chat Tab sidebar, select different models:
   - OpenAI (requires API key in sidebar)
   - Anthropic Claude (requires API key)
   - Gemini (requires API key)
   - Ollama (local, no key needed)
   - Auto (automatic routing)
2. For each model, ask same question:
   ```
   Summarize the key findings from the financial report.
   ```

**Expected Result:**
✅ Each model responds with different phrasing/style
✅ OpenAI/Anthropic/Gemini only work if API key provided in sidebar
✅ Ollama works without API key
✅ Auto mode selects best available model

**Validation:**
- Check Network tab → `/api/query` request → verify `model` parameter matches selection
- Compare response quality across models

#### Test Case 3.4: Temperature Parameter Testing
**Steps:**
1. Set Temperature slider to 0.0 (deterministic)
2. Ask question: `What is machine learning?`
3. Ask same question again
4. Note responses (should be identical)
5. Set Temperature to 1.0 (creative)
6. Ask same question twice
7. Note responses (should vary)

**Expected Result:**
✅ Temperature 0.0 → Identical responses
✅ Temperature 1.0 → Varied responses

#### Test Case 3.5: Category-Filtered Query
**Steps:**
1. Upload documents with different categories:
   - `finance_report.pdf` → Category: "Finance"
   - `hr_policy.docx` → Category: "HR"
2. In Chat Tab sidebar, select Category filter → "Finance"
3. Ask: `What are the revenue figures?`

**Expected Result:**
✅ Response only references finance_report.pdf
✅ Source citations only show [Finance] category documents

#### Test Case 3.6: New Chat Session
**Steps:**
1. Have an active conversation in Chat Tab
2. Click "New Chat" button in sidebar or tab
3. Verify new session started

**Expected Result:**
✅ Chat history cleared
✅ New session ID generated
✅ Previous conversation saved (visible in Conversations Tab)

---

### 3.4 Prompt Template Testing

#### Test Case 4.1: Create Prompt Template
**Steps:**
1. Navigate to **📝 Prompts Tab**
2. In "Create New Prompt" form (right column):
   - Name: `Financial Analyst`
   - Category: `Finance`
   - Description: `Expert financial analysis with focus on metrics`
   - Template:
     ```
     As a financial analyst, review the following context:
     ${context}

     Question: ${question}

     Provide analysis with:
     1. Key metrics identified
     2. Trends observed
     3. Risk factors
     ```
3. Click "Create Prompt"

**Expected Result:**
✅ Success message: "Prompt created successfully"
✅ New prompt appears in left column list
✅ Prompt is expandable to view full template

**Validation:**
- Refresh page - prompt should persist
- Check PostgreSQL `prompt_templates` table for new entry

#### Test Case 4.2: Edit Prompt Template
**Steps:**
1. Locate created prompt in list
2. Click "Edit" button
3. Modify template text
4. Save changes

**Expected Result:**
✅ Prompt updated successfully
✅ Changes reflected immediately in list

#### Test Case 4.3: Delete Prompt Template
**Steps:**
1. Click "Delete" button on a prompt
2. Confirm deletion

**Expected Result:**
✅ Prompt removed from list
✅ No longer available in Chat Tab dropdown

#### Test Case 4.4: Use Prompt Template in Query
**Steps:**
1. Create prompt with placeholders: `${context}`, `${question}`
2. Navigate to Chat Tab
3. Select prompt in sidebar dropdown
4. Ask question

**Expected Result:**
✅ Query uses custom prompt template
✅ Placeholders replaced with actual context and question
✅ Response format matches template structure

---

### 3.5 Conversation Management Testing

#### Test Case 5.1: Conversation Persistence
**Steps:**
1. In Chat Tab, have a conversation (3+ messages)
2. Navigate away to Documents Tab
3. Return to Chat Tab

**Expected Result:**
✅ Chat history preserved
✅ All messages still visible

#### Test Case 5.2: View Conversation History
**Steps:**
1. Navigate to **🗂️ Conversations Tab**
2. Expand a conversation entry

**Expected Result:**
✅ Displays conversation metadata:
   - Title (auto-generated from first question)
   - Category
   - Message Count
   - Last Updated timestamp
✅ Shows full message history with role indicators (👤 User, 🤖 Assistant)
✅ Source citations visible in assistant messages

#### Test Case 5.3: Resume Previous Conversation
**Steps:**
1. In Conversations Tab, click "Resume" button on a conversation
2. Verify redirect to Chat Tab

**Expected Result:**
✅ Chat Tab loads with previous conversation history
✅ Session ID matches resumed conversation
✅ Can continue conversation with new messages

**Validation:**
- Ask follow-up question - response should have context from previous messages

#### Test Case 5.4: Delete Conversation
**Steps:**
1. In Conversations Tab, click "Delete" button on a conversation
2. Confirm deletion

**Expected Result:**
✅ Conversation removed from list
✅ Success message displayed

**Validation:**
- Check PostgreSQL `conversations` table - record deleted

#### Test Case 5.5: Category Filtering
**Steps:**
1. Create conversations with different categories
2. In Chat Tab sidebar, select category filter
3. Observe Conversations Tab

**Expected Result:**
✅ Only conversations matching selected category are visible

---

### 3.6 Dashboard & Analytics Testing

#### Test Case 6.1: KPI Metrics Validation
**Steps:**
1. Navigate to **📊 Dashboards Tab**
2. Observe KPI cards at top

**Expected Result:**
✅ Displays accurate metrics with delta indicators:
   - Total Documents (with ↑/↓ change)
   - Ready Documents
   - Processing Documents
   - Failed Documents
   - Total Queries
   - Total Chunks
   - Total Words
   - Unique Categories

**Validation:**
- Upload new document → refresh dashboard → Total Documents +1
- Run query → refresh → Total Queries +1

#### Test Case 6.2: Time Series Charts
**Steps:**
1. Scroll to "Document Ingestion Timeline" chart
2. Observe data points and trends

**Expected Result:**
✅ Interactive Plotly chart with hover tooltips
✅ X-axis: Date
✅ Y-axis: Document count
✅ Zoom/pan controls functional

#### Test Case 6.3: Category Distribution Chart
**Steps:**
1. View "Category Distribution" pie/donut chart

**Expected Result:**
✅ Shows percentage breakdown by category
✅ Legend displays category names
✅ Clicking slice highlights data

#### Test Case 6.4: Document Insights Panel
**Steps:**
1. Expand "Document Insights" section
2. View per-document insights

**Expected Result:**
✅ Each document shows:
   - Themes detected (e.g., "technology", "finance", "healthcare")
   - Financial data detected (if applicable): R$, $, €, %, mil/milhões
✅ Insights are contextually accurate

**Validation:**
- Upload financial report → should detect currency and numbers
- Upload tech whitepaper → should detect tech themes

#### Test Case 6.5: Custom Chart Builder
**Steps:**
1. Scroll to "Custom Chart Builder"
2. Select chart type: "Bar"
3. X-axis: "category"
4. Y-axis: "chunk_count"
5. Color by: "status"
6. Click "Generate Chart"

**Expected Result:**
✅ Custom bar chart renders
✅ Data aggregated by category
✅ Bars colored by status (green/yellow/red)

**Validation:**
- Try different chart types: scatter, line, histogram, box, violin, sunburst
- Verify each renders correctly with selected axes

#### Test Case 6.6: Data Explorer
**Steps:**
1. Navigate to "Data Explorer" section
2. Select columns to display: Title, Category, Chunks, Size
3. Enter search term in text box: "finance"
4. Observe filtered results

**Expected Result:**
✅ Only rows containing "finance" (case-insensitive) are shown
✅ Table is sortable by clicking column headers
✅ All selected columns visible

#### Test Case 6.7: Report Generation
**Steps:**
1. Navigate to "Report Generation" section
2. Enter report topic: `Q4 2025 Financial Analysis`
3. Enter research query: `What were the key financial metrics in Q4?`
4. Select report type: "financial_summary"
5. Select format: "markdown"
6. Click "Generate Report"
7. Wait for generation
8. Click "Download Report"

**Expected Result:**
✅ Report generates successfully (may take 10-30s)
✅ Preview shows formatted markdown content
✅ Download button provides `.md` file

**Validation:**
- Open downloaded file - should contain:
  - Executive summary
  - Key findings
  - Metrics table
  - Recommendations
  - Source citations

#### Test Case 6.8: BI Export (CSV)
**Steps:**
1. Navigate to "BI Export" section
2. Click "Export to CSV" button
3. Download file

**Expected Result:**
✅ CSV file downloads successfully
✅ File is compatible with Tableau/PowerBI

**Validation:**
- Open CSV in Excel/Google Sheets
- Verify columns: id, title, category, file_type, file_size, chunk_count, status, uploaded_at
- Verify data integrity (no corruption)

#### Test Case 6.9: Analytics Dashboard Page
**Steps:**
1. Navigate to **📊 Analytics Dashboard** page (sidebar navigation)
2. Observe real-time metrics

**Expected Result:**
✅ Professional enterprise-style dashboard loads
✅ All sections render:
   - KPI Cards with deltas
   - Gauge Charts (storage capacity)
   - Time Series Charts (trends)
   - Category Distribution
   - Performance Metrics (embedding time, query time)
✅ Auto-refresh toggle available (5-60s configurable)

**Validation:**
- Enable auto-refresh → dashboard updates every N seconds
- Upload document → observe metrics increment in real-time

---

## 4. Advanced Testing Scenarios

### Scenario A: End-to-End Workflow
**Goal:** Test complete user journey from registration to report generation

**Steps:**
1. Register new user account
2. Login with credentials
3. Upload batch of 5 documents (mixed types: PDF, DOCX, XLSX)
4. Wait for all documents to show 🟢 Ready status
5. Create custom prompt template for "Executive Summary"
6. Navigate to Chat Tab, select prompt
7. Ask: `Provide an executive summary of all uploaded documents`
8. Review response with source citations
9. Create new category: "Q1 2026 Review"
10. Categorize conversation
11. Navigate to Dashboards Tab
12. Generate "market_analysis" report
13. Download report as JSON
14. Export analytics to CSV
15. Delete one document
16. Verify all metrics updated across tabs

**Expected Result:**
✅ All steps complete without errors
✅ Data consistency across all tabs
✅ Reports accurately reflect uploaded content

---

### Scenario B: Multi-Model Comparison
**Goal:** Compare LLM responses for same query

**Steps:**
1. Inject API keys for OpenAI, Anthropic, Gemini in sidebar
2. Upload technical document (e.g., machine learning whitepaper)
3. Ask same question with each model:
   ```
   Explain the main algorithm described in this paper in simple terms.
   ```
4. Compare responses for:
   - Accuracy
   - Clarity
   - Brevity
   - Technical depth

**Expected Result:**
✅ Each model provides coherent response
✅ OpenAI typically more verbose
✅ Claude (Anthropic) more structured
✅ Gemini more concise

---

### Scenario C: Error Handling Testing
**Goal:** Verify graceful error handling

**Test Cases:**
1. **Query without documents:**
   - Delete all documents
   - Ask query
   - Expected: "No documents available" or graceful error message

2. **Invalid API key:**
   - Enter incorrect OpenAI API key
   - Select OpenAI model
   - Ask query
   - Expected: "Invalid API key" error, fallback to local model

3. **Large file upload (>100MB):**
   - Upload extremely large PDF
   - Expected: Upload rejected or timeout message

4. **Concurrent batch uploads:**
   - Upload 2 batches simultaneously
   - Expected: Both process independently without conflict

5. **Database connection loss:**
   - Stop PostgreSQL container: `docker-compose stop postgres`
   - Attempt document upload
   - Expected: "Database connection error" message
   - Restart: `docker-compose start postgres`

---

## 5. Performance Testing via UI

### Test P1: Query Response Time
**Steps:**
1. Upload 10MB PDF document
2. Wait for 🟢 Ready status
3. Ask question (first time)
4. Measure response time (use browser DevTools Network tab)
5. Ask same question again (cached)
6. Measure response time

**Expected Result:**
✅ First query: 2-5 seconds
✅ Cached query: < 100ms (100X speedup from Redis cache)

---

### Test P2: Batch Upload Performance
**Steps:**
1. Prepare 10 documents (total ~100MB)
2. Upload as batch
3. Monitor processing time

**Expected Result:**
✅ All 10 documents processed in < 10 minutes
✅ Parallel processing visible (multiple status updates simultaneously)

**Validation:**
- Check backend logs for parallel processing indicators
- Verify ChromaDB has vectors for all documents

---

### Test P3: Dashboard Load Time
**Steps:**
1. Upload 50+ documents
2. Navigate to Dashboards Tab
3. Measure page load time (Performance tab in DevTools)

**Expected Result:**
✅ Initial load: < 3 seconds
✅ Chart rendering: < 2 seconds
✅ No browser lag during scrolling

---

## 6. Troubleshooting Common Issues

### Issue 1: Documents Stuck in 🟡 Processing
**Symptoms:** Document uploaded but status never changes to 🟢 Ready

**Debugging Steps:**
1. Check backend logs:
   ```bash
   docker-compose logs backend | tail -50
   ```
2. Look for errors related to:
   - ChromaDB connection failure
   - Embedding model loading issues
   - File parsing errors (corrupted PDF)
3. Verify ChromaDB is running:
   ```bash
   docker-compose ps chromadb
   ```
4. Check document in PostgreSQL:
   ```sql
   SELECT * FROM documents WHERE status = 'processing' ORDER BY timestamp DESC LIMIT 5;
   ```

**Solutions:**
- Restart backend: `docker-compose restart backend`
- Re-upload document (delete and upload again)
- Check file integrity (open file locally to ensure it's not corrupted)

---

### Issue 2: "No Models Available" Error
**Symptoms:** Cannot select any LLM model in dropdown

**Debugging Steps:**
1. Check Ollama service:
   ```bash
   docker-compose ps ollama
   curl http://localhost:11434/api/tags
   ```
2. Verify models are pulled:
   ```bash
   docker exec -it ollama ollama list
   ```
3. Check backend logs for model initialization errors

**Solutions:**
- Pull required Ollama models:
   ```bash
   docker exec -it ollama ollama pull llama3.2
   docker exec -it ollama ollama pull mistral
   ```
- Restart Ollama: `docker-compose restart ollama`

---

### Issue 3: API Key Not Recognized
**Symptoms:** Entered OpenAI/Anthropic API key but still getting auth errors

**Debugging Steps:**
1. Verify API key format (should start with `sk-` for OpenAI)
2. Check browser console (F12) for JavaScript errors
3. Inspect Network request to `/api/query` - verify `api_key` in request payload

**Solutions:**
- Re-enter API key (ensure no extra spaces)
- Use session-only injection (keys not persisted)
- Verify API key has sufficient quota/credits with provider

---

### Issue 4: Dashboard Charts Not Rendering
**Symptoms:** Blank space where charts should appear

**Debugging Steps:**
1. Check browser console for Plotly/Altair errors
2. Verify Streamlit version: `pip show streamlit`
3. Clear browser cache and cookies
4. Check `/api/analytics/overview` endpoint returns valid data

**Solutions:**
- Update Streamlit: `pip install --upgrade streamlit`
- Disable browser extensions (AdBlock may interfere)
- Try different browser (Chrome/Firefox)

---

### Issue 5: Slow Query Performance
**Symptoms:** Queries taking > 10 seconds consistently

**Debugging Steps:**
1. Check Redis cache status:
   ```bash
   docker-compose ps redis
   docker exec -it redis redis-cli ping
   ```
2. Verify cache hit rate in backend logs
3. Check ChromaDB vector count:
   ```bash
   curl http://localhost:8001/api/v1/collections
   ```

**Solutions:**
- Restart Redis: `docker-compose restart redis`
- Clear cache if stale: `docker exec -it redis redis-cli FLUSHALL`
- Optimize embeddings: Ensure using `bge-base-en-v1.5` (not bge-large)

---

## 7. Test Checklist

### Authentication ✓
- [ ] User registration successful
- [ ] User login successful
- [ ] Session persists after refresh
- [ ] Invalid credentials rejected

### Document Management ✓
- [ ] Single file upload (drag-and-drop)
- [ ] Single file upload (click browse)
- [ ] Batch upload (3+ files)
- [ ] Document list displays correctly
- [ ] Document status transitions: 🟡 → 🟢
- [ ] Document deletion works
- [ ] Metrics update after upload/delete
- [ ] Unsupported file types rejected

### RAG Queries ✓
- [ ] Basic query returns relevant response
- [ ] Source citations displayed
- [ ] Custom prompt template applied
- [ ] Model selection works (OpenAI/Claude/Gemini/Ollama)
- [ ] Temperature parameter affects responses
- [ ] Category filtering works
- [ ] New chat session created successfully

### Prompt Templates ✓
- [ ] Create prompt template
- [ ] Edit prompt template
- [ ] Delete prompt template
- [ ] Use prompt template in query
- [ ] Placeholders replaced correctly

### Conversations ✓
- [ ] Conversation history persists
- [ ] View conversation details
- [ ] Resume previous conversation
- [ ] Delete conversation
- [ ] Category filtering works

### Dashboards & Analytics ✓
- [ ] KPI metrics accurate
- [ ] Time series charts render
- [ ] Category distribution chart renders
- [ ] Document insights detected
- [ ] Custom chart builder works
- [ ] Data explorer search works
- [ ] Report generation successful
- [ ] CSV export downloads
- [ ] JSON export downloads
- [ ] Analytics Dashboard page loads
- [ ] Auto-refresh works

### Performance ✓
- [ ] First query < 5s
- [ ] Cached query < 100ms
- [ ] Batch upload < 10 min for 10 files
- [ ] Dashboard load < 3s

### Error Handling ✓
- [ ] Query without documents handled gracefully
- [ ] Invalid API key shows error
- [ ] Large file upload rejected/warned
- [ ] Database connection loss detected

---

## Appendix: API Endpoints Reference

| Method | Endpoint | Description | UI Tab |
|--------|----------|-------------|--------|
| `POST` | `/api/auth/register` | User registration | Login screen |
| `POST` | `/api/auth/login` | User login | Login screen |
| `POST` | `/api/upload_document` | Single file upload | Sidebar |
| `POST` | `/api/upload_batch` | Batch upload | Sidebar |
| `GET` | `/api/documents` | List documents | 📁 Documents |
| `DELETE` | `/api/documents/{id}` | Delete document | 📁 Documents |
| `POST` | `/api/query` | RAG query | 💬 Chat |
| `GET` | `/api/prompts` | List prompts | 📝 Prompts |
| `POST` | `/api/prompts` | Create prompt | 📝 Prompts |
| `PUT` | `/api/prompts/{id}` | Update prompt | 📝 Prompts |
| `DELETE` | `/api/prompts/{id}` | Delete prompt | 📝 Prompts |
| `GET` | `/api/conversations` | List conversations | 🗂️ Conversations |
| `GET` | `/api/conversations/{id}` | Get conversation | 🗂️ Conversations |
| `DELETE` | `/api/conversations/{id}` | Delete conversation | 🗂️ Conversations |
| `POST` | `/api/generate_report` | Generate report | 📊 Dashboards |
| `GET` | `/api/analytics/overview` | Analytics metrics | 📊 Dashboards |
| `GET` | `/api/analytics/content` | Content analytics | 📊 Dashboards |
| `GET` | `/api/models` | List models | 💬 Chat |
| `GET` | `/api/health` | Health check | System |

---

## Quick Start Testing Workflow

**5-Minute Smoke Test:**
1. ✅ Login with credentials
2. ✅ Upload 1 PDF document
3. ✅ Wait for 🟢 Ready status
4. ✅ Ask query: "Summarize this document"
5. ✅ Verify response with sources
6. ✅ Check Documents Tab shows uploaded file
7. ✅ Check Dashboards Tab shows metrics
8. ✅ Create 1 prompt template
9. ✅ View conversation in Conversations Tab
10. ✅ Download CSV export from Dashboards

**15-Minute Comprehensive Test:**
- All smoke test steps +
11. ✅ Batch upload 3 documents (PDF, DOCX, XLSX)
12. ✅ Test all 4 models (OpenAI, Claude, Gemini, Ollama)
13. ✅ Create custom prompt and use in query
14. ✅ Generate financial_summary report
15. ✅ Test custom chart builder (3 chart types)
16. ✅ Use data explorer search
17. ✅ Resume previous conversation
18. ✅ Delete 1 document
19. ✅ Verify metrics updated
20. ✅ Test category filtering

---

**Document Version:** 1.0
**Last Updated:** 2026-03-16
**Compatibility:** AI Documents Analyser v2.0+
**Tested Environments:** macOS, Docker Compose setup
