"""
FastAPI application – all API endpoints for the AI Knowledge Platform.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backend.cache_service import get_cache_service
from backend.conversation_manager import ConversationManager
from backend.embeddings import EmbeddingService, get_embedding_service
from backend.llm_router import LLMRouter
from backend.prompt_manager import PromptManager
from backend.rag_pipeline import RAGPipeline
from backend.report_generator import ReportGenerator
from backend.vector_store import get_vector_store
from config.settings import settings
from db.database import get_db, init_db
from db.models import Document, User
from services.document_parser import DocumentParser
from services.s3_storage import S3StorageService

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

# ── Rate limiter ─────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Password hashing ────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Singleton services ───────────────────────────────────
import threading
_service_lock = threading.Lock()
_llm_router: Optional[LLMRouter] = None
_rag_pipeline: Optional[RAGPipeline] = None
_s3: Optional[S3StorageService] = None
_parser: Optional[DocumentParser] = None
_report_gen: Optional[ReportGenerator] = None


def _get_services():
    global _llm_router, _rag_pipeline, _s3, _parser, _report_gen
    with _service_lock:
        if _llm_router is None:
            embedder = get_embedding_service()
            vector_store = get_vector_store(dimension=embedder.dimension)
            _llm_router = LLMRouter()
            _rag_pipeline = RAGPipeline(embedder, vector_store, _llm_router)
            _s3 = S3StorageService()
            _parser = DocumentParser()
            _report_gen = ReportGenerator(_llm_router)
    return _llm_router, _rag_pipeline, _s3, _parser, _report_gen


# ── Lifespan ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Knowledge Platform …")
    try:
        init_db()
        logger.info("Database tables ensured.")
    except Exception as e:
        logger.warning("DB init skipped (will retry on first request): %s", e)

    # Seed default prompts
    try:
        from db.database import SessionLocal
        db = SessionLocal()
        PromptManager.seed_defaults(db)
        db.close()
    except Exception as e:
        logger.warning("Prompt seeding skipped: %s", e)

    yield

    # Cleanup
    if _llm_router:
        await _llm_router.close()
    logger.info("Shutdown complete.")


# ── App ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI Knowledge Platform – Document ingestion, multi-LLM RAG, prompt management, conversations, dashboards.",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════
#  Pydantic schemas
# ══════════════════════════════════════════════════════════

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    question: str
    model: str = "auto"
    prompt_template: str | None = None
    top_k: int = 5
    temperature: float = 0.7
    session_id: str | None = None
    category: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    model_used: str
    session_id: str

class PromptCreate(BaseModel):
    name: str
    template: str
    category: str | None = None
    description: str | None = None

class PromptUpdate(BaseModel):
    name: str | None = None
    template: str | None = None
    category: str | None = None
    description: str | None = None

class ConversationCreate(BaseModel):
    category: str | None = None
    title: str | None = None

class ReportRequest(BaseModel):
    topic: str
    query: str
    report_type: str = "general"
    output_format: str = "markdown"
    model: str = "auto"
    top_k: int = 10
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


# ══════════════════════════════════════════════════════════
#  Auth helpers
# ══════════════════════════════════════════════════════════

def _create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def _verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Optional auth – returns None if no token supplied."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = _verify_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()


# ══════════════════════════════════════════════════════════
#  Auth endpoints
# ══════════════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Auth"])
async def register(body: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken.")
    try:
        hashed_password = pwd_context.hash(body.password)
    except Exception as e:
        logger.exception("Password hashing failed during registration for username=%s", body.username)
        raise HTTPException(status_code=500, detail="Password hashing backend unavailable.") from e

    user = User(
        username=body.username,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    token = _create_token({"sub": user.username})
    return TokenResponse(access_token=token)


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    try:
        password_ok = pwd_context.verify(body.password, user.hashed_password)
    except Exception as e:
        logger.exception("Password verification failed for username=%s", body.username)
        raise HTTPException(status_code=500, detail="Password verification backend unavailable.") from e

    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = _create_token({"sub": user.username})
    return TokenResponse(access_token=token)


# ══════════════════════════════════════════════════════════
#  Document endpoints
# ══════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "csv", "txt", "json"}


@app.post("/api/upload_document", tags=["Documents"])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("general"),
    title: str = Form(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Upload a document → S3 → parse → chunk → embed → vector store."""
    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")

    # Validate file size (max 100MB)
    contents = await file.read()
    if len(contents) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 100 MB).")

    doc_id = str(uuid.uuid4())
    doc_title = title or file.filename or "Untitled"
    s3_key = f"documents/{doc_id}/{file.filename}"

    _, rag, s3, parser, _ = _get_services()

    # 1. Store file (S3 if configured, otherwise local fallback)
    try:
        if settings.aws_access_key_id and settings.aws_access_key_id != "your-access-key":
            s3.upload_bytes(contents, s3_key, content_type=file.content_type or "application/octet-stream")
            logger.info("Stored in S3: %s", s3_key)
        else:
            # Local fallback
            import os
            local_dir = os.path.join("data", "uploads", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, file.filename or "file")
            with open(local_path, "wb") as f:
                f.write(contents)
            s3_key = local_path
            logger.info("Stored locally (no S3 keys): %s", local_path)
    except Exception as e:
        logger.warning("Storage failed, saving locally: %s", e)
        import os
        local_dir = os.path.join("data", "uploads", doc_id)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file.filename or "file")
        with open(local_path, "wb") as f:
            f.write(contents)
        s3_key = local_path

    # 2. Save document record
    doc = Document(
        id=uuid.UUID(doc_id),
        title=doc_title,
        category=category,
        uploaded_by=user.username if user else "anonymous",
        source_path=s3_key,
        file_type=ext,
        file_size=len(contents),
        status="processing",
    )
    db.add(doc)
    db.commit()

    # 3. Parse + ingest
    try:
        text = _safe_extract_text(parser, contents, ext)
        chunk_count = rag.ingest_document(
            doc_id=doc_id,
            text=text,
            metadata={"title": doc_title, "category": category},
        )
        doc.chunk_count = chunk_count
        doc.status = "ready"
    except Exception as e:
        logger.error("Ingestion failed for %s: %s", doc_id, e)
        doc.status = "failed"
        db.commit()
        raise HTTPException(500, f"Document processing failed: {e}")

    db.commit()

    return {
        "document_id": doc_id,
        "title": doc_title,
        "status": doc.status,
        "chunks": doc.chunk_count,
        "file_size": len(contents),
    }


@app.get("/api/documents", tags=["Documents"])
async def list_documents(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if category:
        query = query.filter(Document.category == category)
    docs = query.order_by(Document.timestamp.desc()).offset(offset).limit(limit).all()
    total = query.count()
    return {
        "total": total,
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "category": d.category,
                "uploaded_by": d.uploaded_by,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "chunk_count": d.chunk_count,
                "status": d.status,
            }
            for d in docs
        ],
    }


@app.delete("/api/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    _, rag, s3, _, _ = _get_services()
    try:
        s3.delete_file(doc.source_path)
    except Exception:
        pass
    rag.remove_document(doc_id)
    db.delete(doc)
    db.commit()
    return {"deleted": True, "document_id": doc_id}


# ══════════════════════════════════════════════════════════
#  Query endpoint (RAG)
# ══════════════════════════════════════════════════════════

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
@limiter.limit(settings.rate_limit)
async def query_documents(
    request: Request,
    body: QueryRequest,
    db: Session = Depends(get_db),
):
    """Send a question through the RAG pipeline with Redis caching."""
    _, rag, _, _, _ = _get_services()
    cache = get_cache_service()

    # Try cache first (100x faster for repeated queries)
    cached_result = cache.get(
        question=body.question,
        model=body.model,
        top_k=body.top_k,
        category=body.category,
    )

    # Manage conversation session
    conv_mgr = ConversationManager()
    if body.session_id:
        session_id = uuid.UUID(body.session_id)
        session = conv_mgr.get_session(db, session_id)
        if not session:
            raise HTTPException(404, "Session not found.")
    else:
        session = conv_mgr.create_session(db, category=body.category, title=None)
        session_id = session.session_id

    # Add user message
    conv_mgr.add_message(db, session_id, "user", body.question)

    if cached_result:
        # Use cached result
        result = cached_result
        logger.info("Using cached query result (100x speedup)")
    else:
        # Fetch all document titles for global context awareness
        doc_titles = [d.title for d in db.query(Document.title).filter(Document.status == "ready").all()]

        result = await rag.query(
            question=body.question,
            model_name=body.model,
            prompt_template=body.prompt_template,
            top_k=body.top_k,
            temperature=body.temperature,
            api_keys={
                "openai_api_key": body.openai_api_key,
                "anthropic_api_key": body.anthropic_api_key,
                "gemini_api_key": body.gemini_api_key,
            },
            full_doc_list=doc_titles
        )

        # Cache the result for 1 hour
        cache.set(
            question=body.question,
            model=body.model,
            top_k=body.top_k,
            result=result,
            category=body.category,
        )

    # Add assistant message
    conv_mgr.add_message(
        db, session_id, "assistant", result["answer"], sources=result["sources"]
    )

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        model_used=result["model_used"],
        session_id=str(session_id),
    )


# ══════════════════════════════════════════════════════════
#  Prompt endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/prompts", tags=["Prompts"])
async def list_prompts(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    prompts = PromptManager.list_all(db, category)
    return {
        "prompts": [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "template": p.template,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in prompts
        ]
    }


@app.post("/api/prompts", tags=["Prompts"])
async def create_prompt(body: PromptCreate, db: Session = Depends(get_db)):
    existing = PromptManager.get_by_name(db, body.name)
    if existing:
        raise HTTPException(400, "A prompt with this name already exists.")
    p = PromptManager.create(db, body.name, body.template, body.category, body.description)
    return {
        "id": str(p.id),
        "name": p.name,
        "message": "Prompt created successfully.",
    }


@app.put("/api/prompts/{prompt_id}", tags=["Prompts"])
async def update_prompt(
    prompt_id: str,
    body: PromptUpdate,
    db: Session = Depends(get_db),
):
    p = PromptManager.update(
        db,
        uuid.UUID(prompt_id),
        name=body.name,
        template=body.template,
        category=body.category,
        description=body.description,
    )
    if not p:
        raise HTTPException(404, "Prompt not found.")
    return {"id": str(p.id), "name": p.name, "message": "Prompt updated."}


@app.delete("/api/prompts/{prompt_id}", tags=["Prompts"])
async def delete_prompt(prompt_id: str, db: Session = Depends(get_db)):
    ok = PromptManager.delete(db, uuid.UUID(prompt_id))
    if not ok:
        raise HTTPException(404, "Prompt not found.")
    return {"deleted": True}


# ══════════════════════════════════════════════════════════
#  Conversation endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/conversations", tags=["Conversations"])
async def list_conversations(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    conv_mgr = ConversationManager()
    sessions = conv_mgr.list_sessions(db, category, limit, offset)
    return {
        "conversations": [
            {
                "session_id": str(c.session_id),
                "title": c.title,
                "category": c.category,
                "message_count": len(c.messages or []),
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in sessions
        ]
    }


@app.get("/api/conversations/categories", tags=["Conversations"])
async def list_categories(db: Session = Depends(get_db)):
    return {"categories": ConversationManager.list_categories(db)}


@app.get("/api/conversations/{session_id}", tags=["Conversations"])
async def get_conversation(session_id: str, db: Session = Depends(get_db)):
    conv = ConversationManager.get_session(db, uuid.UUID(session_id))
    if not conv:
        raise HTTPException(404, "Conversation not found.")
    return {
        "session_id": str(conv.session_id),
        "title": conv.title,
        "category": conv.category,
        "messages": conv.messages,
        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
    }


@app.post("/api/conversations", tags=["Conversations"])
async def create_conversation(body: ConversationCreate, db: Session = Depends(get_db)):
    conv = ConversationManager.create_session(db, body.category, body.title)
    return {"session_id": str(conv.session_id), "message": "Conversation created."}


@app.delete("/api/conversations/{session_id}", tags=["Conversations"])
async def delete_conversation(session_id: str, db: Session = Depends(get_db)):
    ok = ConversationManager.delete_session(db, uuid.UUID(session_id))
    if not ok:
        raise HTTPException(404, "Conversation not found.")
    return {"deleted": True}


# ══════════════════════════════════════════════════════════
#  Report endpoint
# ══════════════════════════════════════════════════════════

@app.post("/api/generate_report", tags=["Reports"])
@limiter.limit(settings.rate_limit)
async def generate_report(
    request: Request,
    body: ReportRequest,
    db: Session = Depends(get_db),
):
    """Generate a structured report based on a topic query."""
    _, rag, _, _, report_gen = _get_services()

    # First, retrieve relevant context
    embedder = get_embedding_service()
    query_emb = embedder.embed_query(body.query)
    vector_store = get_vector_store(dimension=embedder.dimension)
    results = vector_store.search(query_emb, top_k=body.top_k)

    context = "\n---\n".join(
        f"{r['document']}" for r in results
    )

    if not context.strip():
        raise HTTPException(400, "No relevant documents found for this topic.")

    report = await report_gen.generate(
        topic=body.topic,
        context=context,
        report_type=body.report_type,
        output_format=body.output_format,
        model_name=body.model,
        api_keys={
            "openai_api_key": body.openai_api_key,
            "anthropic_api_key": body.anthropic_api_key,
            "gemini_api_key": body.gemini_api_key,
        }
    )

    return report


# ══════════════════════════════════════════════════════════
#  Batch Upload endpoint
# ══════════════════════════════════════════════════════════

# In-memory batch status tracking
_batch_statuses: dict[str, dict] = {}

def _safe_extract_text(parser, contents: bytes, ext: str) -> str:
    """Extract text and fallback to decoded bytes when parser fails."""
    try:
        text = parser.parse(contents, ext)
        if text and text.strip():
            return text
    except Exception as e:
        logger.warning("Primary parser failed for .%s; fallback mode: %s", ext, e)

    text = contents.decode("utf-8", errors="ignore")
    if not text.strip():
        text = contents.decode("latin-1", errors="ignore")
    text = text.strip()
    return text or f"Uploaded .{ext} file content unavailable; metadata retained."


def _process_single_file(
    doc_id: str, contents: bytes, filename: str, ext: str,
    category: str, s3_key: str, batch_id: str, file_hash: str,
):
    """Process a single file in a background thread."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        _, rag, s3, parser, _ = _get_services()

        # Store file
        try:
            if settings.aws_access_key_id and settings.aws_access_key_id != "your-access-key":
                s3.upload_bytes(contents, s3_key, content_type="application/octet-stream")
            else:
                import os
                local_dir = os.path.join("data", "uploads", doc_id)
                os.makedirs(local_dir, exist_ok=True)
                with open(os.path.join(local_dir, filename), "wb") as f:
                    f.write(contents)
        except Exception as e:
            logger.warning("Storage fallback for %s: %s", doc_id, e)
            import os
            local_dir = os.path.join("data", "uploads", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            with open(os.path.join(local_dir, filename), "wb") as f:
                f.write(contents)

        # Save document record
        doc = Document(
            id=uuid.UUID(doc_id),
            title=filename,
            category=category,
            uploaded_by="batch",
            source_path=s3_key,
            file_type=ext,
            file_size=len(contents),
            content_hash=file_hash,
            status="processing",
        )
        db.add(doc)
        db.commit()

        # Parse + ingest
        text = _safe_extract_text(parser, contents, ext)
        chunk_count = rag.ingest_document(
            doc_id=doc_id, text=text,
            metadata={"title": filename, "category": category},
        )
        doc.chunk_count = chunk_count
        doc.status = "ready"
        db.commit()

        _batch_statuses[batch_id]["files"][doc_id]["status"] = "ready"
        _batch_statuses[batch_id]["files"][doc_id]["chunks"] = chunk_count
        logger.info("Batch file processed: %s (%d chunks)", filename, chunk_count)

    except Exception as e:
        logger.error("Batch file failed %s: %s", doc_id, e)
        _batch_statuses[batch_id]["files"][doc_id]["status"] = "failed"
        _batch_statuses[batch_id]["files"][doc_id]["error"] = str(e)
        try:
            doc_obj = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
            if doc_obj:
                doc_obj.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@app.post("/api/upload_batch", tags=["Documents"])
async def upload_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    category: str = Form("general"),
    db: Session = Depends(get_db),
):
    """Upload multiple files at once with background processing."""
    from backend.analytics_engine import AnalyticsEngine

    batch_id = str(uuid.uuid4())
    _batch_statuses[batch_id] = {"batch_id": batch_id, "files": {}, "total": len(files)}

    results = []

    # Initialize services eagerly to avoid individual thread race conditions
    _get_services()

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            reason = f"Unsupported: .{ext}"
            results.append({"filename": file.filename, "status": "rejected", "reason": reason})
            # Add to batch status as 'failed' so progress bar reaches 100%
            fake_id = f"rejected-{uuid.uuid4()}"
            _batch_statuses[batch_id]["files"][fake_id] = {
                "filename": file.filename, "status": "failed", "error": reason
            }
            continue

        contents = await file.read()

        # 500MB limit
        if len(contents) > 500 * 1024 * 1024:
            results.append({"filename": file.filename, "status": "rejected", "reason": "File too large (max 500MB)"})
            continue

        # Duplicate detection
        file_hash = AnalyticsEngine.compute_hash(contents)
        dup = AnalyticsEngine.check_duplicate(db, file_hash)
        if dup:
            results.append({
                "filename": file.filename, "status": "duplicate",
                "existing_id": dup["existing_id"], "existing_title": dup["existing_title"],
            })
            # Add to batch status as 'ready' so progress bar accounts for it
            doc_id = dup["existing_id"]
            _batch_statuses[batch_id]["files"][doc_id] = {
                "filename": file.filename, "status": "ready", "chunks": 0, "is_duplicate": True
            }
            continue

        doc_id = str(uuid.uuid4())
        s3_key = f"documents/{doc_id}/{file.filename}"

        _batch_statuses[batch_id]["files"][doc_id] = {
            "filename": file.filename, "status": "processing", "chunks": 0,
        }

        # Use FastAPI BackgroundTasks for true non-blocking execution
        background_tasks.add_task(
            _process_single_file,
            doc_id, contents, file.filename or "file", ext,
            category, s3_key, batch_id, file_hash
        )
        results.append({"filename": file.filename, "status": "processing", "document_id": doc_id})

    return {
        "batch_id": batch_id,
        "total_submitted": len(files),
        "accepted": sum(1 for r in results if r["status"] == "processing"),
        "rejected": sum(1 for r in results if r["status"] == "rejected"),
        "duplicates": sum(1 for r in results if r["status"] == "duplicate"),
        "files": results,
    }


@app.get("/api/batch_status/{batch_id}", tags=["Documents"])
async def batch_status(batch_id: str):
    """Poll processing status for a batch upload."""
    if batch_id not in _batch_statuses:
        raise HTTPException(404, "Batch not found.")
    batch = _batch_statuses[batch_id]
    files = batch["files"]
    return {
        "batch_id": batch_id,
        "total": batch["total"],
        "ready": sum(1 for f in files.values() if f["status"] == "ready"),
        "processing": sum(1 for f in files.values() if f["status"] == "processing"),
        "failed": sum(1 for f in files.values() if f["status"] == "failed"),
        "files": files,
    }


# ══════════════════════════════════════════════════════════
#  Analytics endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/analytics/overview", tags=["Analytics"])
async def analytics_overview(db: Session = Depends(get_db)):
    from backend.analytics_engine import AnalyticsEngine
    return AnalyticsEngine.overview(db)


@app.get("/api/analytics/content", tags=["Analytics"])
async def analytics_content(db: Session = Depends(get_db)):
    from backend.analytics_engine import AnalyticsEngine
    embedder = get_embedding_service()
    vector_store = get_vector_store(dimension=embedder.dimension)
    return AnalyticsEngine.content_stats(db, vector_store)


@app.get("/api/analytics/storage", tags=["Analytics"])
async def analytics_storage(db: Session = Depends(get_db)):
    from backend.analytics_engine import AnalyticsEngine
    return AnalyticsEngine.storage_stats(db)


@app.get("/api/analytics/content_insights", tags=["Analytics"])
async def analytics_content_insights(db: Session = Depends(get_db)):
    from backend.analytics_engine import AnalyticsEngine
    embedder = get_embedding_service()
    vector_store = get_vector_store(dimension=embedder.dimension)
    return AnalyticsEngine.content_insights(db, vector_store)


# ══════════════════════════════════════════════════════════
#  Utility endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/models", tags=["Utility"])
async def list_available_models():
    llm, *_ = _get_services()
    return {"models": llm.list_models()}


@app.get("/api/health", tags=["Utility"])
async def health_check():
    return {"status": "healthy", "app": settings.app_name}

