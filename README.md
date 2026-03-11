# 🧠 AI Knowledge Platform

A production-ready AI-powered document analysis and knowledge management platform.  
Upload documents, query them using multiple LLMs, manage prompts and conversations, generate reports, and visualize data — all from a unified interface.

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Streamlit  │─────▶│   FastAPI    │─────▶│  PostgreSQL  │
│   Frontend   │      │   Backend    │      │   Database   │
│   :8501      │      │   :8000      │      │   :5432      │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                    ┌────────┼────────┐
                    ▼        ▼        ▼
              ┌─────────┐ ┌──────┐ ┌──────────┐
              │ ChromaDB│ │Ollama│ │  AWS S3   │
              │  :8001  │ │:11434│ │  Storage  │
              └─────────┘ └──────┘ └──────────┘
```

## Features

| Feature | Description |
|---|---|
| 📄 Document Ingestion | Upload PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON |
| 🔍 RAG Query | Retrieval-augmented generation with source citations |
| 🤖 Multi-LLM | Ollama (Llama 3, Mistral, Mixtral, Gemma), OpenAI, Claude |
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

### Prerequisites

- **Docker** & **Docker Compose**
- **Ollama** (for local LLMs) — [install guide](https://ollama.ai)
- **AWS S3 bucket** (for document storage)

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
#   - AWS S3 keys
#   - OpenAI / Anthropic API keys (optional)
#   - PostgreSQL password
```

### 2. Pull an Ollama Model

```bash
ollama pull llama3
```

### 3. Launch

```bash
docker compose up --build -d
```

### 4. Access

| Service | URL |
|---|---|
| 🖥️ Streamlit UI | [http://localhost:8501](http://localhost:8501) |
| ⚡ FastAPI Docs | [http://localhost:8000/docs](http://localhost:8000/docs) |
| 🗄️ PostgreSQL | `localhost:5432` |
| 🔷 ChromaDB | `localhost:8001` |

---

## Local Development (without Docker)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start PostgreSQL (e.g. via brew or docker)
docker run -d --name pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine

# Start backend
uvicorn backend.main:app --reload --port 8000

# Start frontend (separate terminal)
streamlit run frontend/streamlit_app.py
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
│   └── streamlit_app.py         # Streamlit web UI
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
| `POST` | `/api/upload_document` | Upload & ingest document |
| `GET` | `/api/documents` | List documents |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `POST` | `/api/query` | RAG query with source citations |
| `GET` | `/api/prompts` | List prompt templates |
| `POST` | `/api/prompts` | Create prompt template |
| `PUT` | `/api/prompts/{id}` | Update prompt template |
| `DELETE` | `/api/prompts/{id}` | Delete prompt template |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation detail |
| `POST` | `/api/conversations` | Create conversation |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `POST` | `/api/generate_report` | Generate structured report |
| `GET` | `/api/models` | List available LLM models |
| `GET` | `/api/health` | Health check |

Full interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Configuration

All configuration is managed via environment variables (`.env`). See `.env.example` for all available options.

### Key Settings

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `S3_BUCKET_NAME` | — | AWS S3 bucket for documents |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Embedding model |
| `VECTOR_STORE_TYPE` | `chroma` | `chroma` or `qdrant` |
| `CHUNK_SIZE` | `1000` | Document chunk size (chars) |
| `TOP_K` | `5` | Number of chunks to retrieve |

---

## License

MIT
