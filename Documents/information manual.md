# AI Knowledge Platform — Information & Architecture Manual

This document provides a deep-dive analysis into the core components that power the AI Knowledge Platform. It is intended for software engineers, IT administrators, or curious stakeholders who want to understand _how_ the system achieves its results.

The platform is built on four core pillars.

---

## 1. Document Ingestion & Processing Pipeline

The ingestion pipeline transforms unstructured text (like a messy PDF or a PowerPoint deck) into mathematically searchable data.

- **S3 Blob Storage:** When a user uploads a document, the original raw file (up to 500MB) is immediately piped into an **AWS S3 Bucket**. This keeps the application server's disk space free and ensures files are resiliently stored.
- **Multi-Parser Text Extraction:** The system uses `PyPDF2`, `python-docx`, and `pandas` to scrape raw text from various proprietary file formats.
- **Adaptive Chunking:** An AI cannot read a 1,000-page book in one go. The system splits documents into overlapping "chunks" (default: 1,000 characters). The 100-character overlap ensures that sentences broken between chunks don't lose their context.
- **Vectorization (Embeddings):** Each text chunk is passed through the `BAAI/bge-large-en-v1.5` sentence-transformer model. This converts the english/portuguese text into a 1024-dimensional array of numbers (a vector).
- **ChromaDB Vector Store:** These vectors are saved into a high-performance database called ChromaDB. ChromaDB allows the system to perform blazing-fast nearest-neighbor mathematical searches.

---

## 2. Multi-Model RAG Chat Engine (LLM Router)

Retrieval-Augmented Generation (RAG) is the methodology used to stop an AI from "hallucinating" (making things up) by forcing it to answer based _only_ on searched evidence.

- **The LLM Router:** The platform does not rely on just one AI. The `LLMRouter` class acts as a traffic director. Depending on user selection, it dynamically routes the prompt execution to:
  - **Local Backend:** Contacts the `Ollama` container running `Llama 3.2 3B`. Used for highly sensitive data where API transmission is forbidden.
  - **Cloud Vendors:** Formats the request for OpenAI's `gpt-5.4`, Anthropic's `claude-4.5-opus`, or Google's `gemini-3.1` using HTTP REST requests.
- **Global Context Awareness:** Before the user even asks a question, the LLM Router injects a dynamically generated index of _every file currently uploaded to the system_ into the system prompt. If you ask "What documents do you have?", the AI actually knows the answer.

---

## 3. Analytics & the Content Engine

Unlike basic file managers that only show pie charts of "File Types", this platform features an advanced `analytics_engine.py` that generates Business Intelligence directly from the unstructured text.

- **Bigram Extraction:** The backend analyzes the thousands of text chunks and counts the highest-frequency 2-word pairs (Bigrams). It filters out noisy "Stop Words" (both English and Portuguese: "o", "the", "para", "with") to isolate true themes (e.g., "Operação interna", "Ticket médio").
- **Financial Context Identification:** The engine uses complex Regex patterns (`(?:R\$|US\$|\$|€|£)\s*[\d.,]+(?:\s*(?:mil|milhões|M|K|B))?`) to scan the raw text for specific financial markers (currencies and percentages) and pulls them into the Dashboard for immediate auditing.
- **Jaccard Similarity Matrix:** To build the "Document Similarity" heatmap, the system compares the extracted key-phrases of Document A against Document B using Jaccard computation, generating a matrix score from 0.0 to 1.0.

---

## 4. Frontend-Backend Decoupling

The platform adheres to strict microservice boundaries to ensure scalability.

- **FastAPI Backend:** Handles all heavy compute. Built asynchronously (`async def`), it allows multiple users to upload massive files simultaneously without blocking API requests for other users.
- **Streamlit Frontend:** A pure, stateless UI layer. It holds no database connections and performs no complex math. It exclusively communicates via HTTP REST requests to the FastAPI backend. This means you could theoretically replace Streamlit with a React or Vue frontend in the future with zero changes to the backend engine.
- **PostgreSQL Persistence:** All relational states—such as User tracking, Document metadata mapping, Conversation histories, and Prompt libraries—are stored resiliently in a traditional PostgreSQL relational database wrapper in SQLAlchemy ORM.
