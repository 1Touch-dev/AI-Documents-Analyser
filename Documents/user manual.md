# AI Knowledge Platform — User Manual

Welcome to the AI Knowledge Platform. This system empowers you to upload hundreds of large documents (PDFs, PPTXs, CSVs, etc.), extract meaning from them automatically, and query them using state-of-the-art AI.

---

## 1. Starting and Stopping the Platform

If the platform is running on your local machine, use these commands to control it. *(If deployed on a remote cloud server, your IT admin has likely configured it to run 24/7).*

**To Start the Application (Docker via Terminal):**
```bash
cd "/Volumes/Seagate/AI Documents Analyser"
docker compose up -d
```
*The UI will be available at [http://localhost:8501](http://localhost:8501) within 30 seconds.*

**To Stop the Application:**
```bash
docker compose down
```

---

## 2. Authentication & Model Selection

### Logging In
1. The first time you use the system, click the **Register** radio button on the left sidebar. Enter a Username and Password.
2. Click **Submit**. Your session will be securely saved.

### Injecting API Keys (Optional)
By default, the system uses a fully private, internal AI model (`Llama 3.2 3B`) running on your machine. This guarantees 100% data privacy.

However, if you wish to use incredibly powerful Cloud AI models:
1. Expand the **⚙️ Provider API Keys** menu in the sidebar.
2. Paste your OpenAI, Anthropic, or Gemini API keys.
3. Your keys are **never** saved to the database. They temporarily live in your local browser session and are cleared when you exit.

---

## 3. Uploading Documents

The system supports massive files (up to **500 MB** per file) and batch processing. Supported formats: `PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON`.

1. Go to the **Documents** tab, or use the uploader in the left sidebar.
2. Drag and drop multiple files.
3. While files upload, you can type a **Custom Category** (e.g., `Financials Q3`, `Legal Docs`).
4. Hit Upload.

**Important Note on Processing:** Large documents (like a 300-page PDF) take time to process. The system reads the document, splits it into hundreds of chunks, and mathematically translates the text into "vector embeddings." You can track the real-time progress of this in the sidebar. Once complete, the file status will change to `ready`.

---

## 4. Chatting With Your Documents (RAG)

The core feature of this platform is the **Retrieval-Augmented Generation (RAG)** engine.

1. Navigate to the **💬 Chat** tab.
2. Select an **LLM Provider** from the dropdown (`GPT-5.4`, `Claude 4.6`, `Gemini 3.1 Pro`, or `Local Llama`). *Note: Cloud models require you to have pasted an API key in the sidebar.*
3. Ask a question. For example: *"What were the Q3 operational risks mentioned across our board presentations?"*

**How it works:** The system instantly searches through *every* uploaded document, finds the 5-10 most highly relevant paragraphs, and feeds them to the AI to construct an accurate, citation-backed answer. The AI is fully aware of your entire document library ("Global Context").

---

## 5. Dashboards and Visualizations

Navigate to the **📊 Dashboards** tab to view professional, content-driven intelligence about your documents. The dashboard does more than just show file sizes; it reads your documents and extracts deep insights.

*   **Topic Intelligence:** Extracts automatic "Bigram Themes" (e.g., `ticket médio`, `risco operacional`) showing the fundamental topics of your corporate library.
*   **Financial Data:** Automatically scans documents for `R$`, `$`, `%`, and `mil/milhões` to highlight crucial financial variables floating in the text.
*   **Per-Document Insights:** Expand any document panel to see a clean preview, its dominant themes, and the exact currencies detected within it.
*   **Filters:** Use the interactive filters at the top to slice your dashboards by Category, File Type, or specific Users.

---

## 6. managing Prompts & Conversations

*   **Save Reusable Prompts:** Frequently write the same complex prompt? Go to the **Prompts** tab. Create templates like *"Act as a CFO and summarize the key CAPEX takeaways from this document."* You can load these instantly in the Chat view.
*   **Persistent Threads:** Every chat interaction is automatically saved. Navigate to the **Conversations** tab to resume a discussion from yesterday right where you left off.
