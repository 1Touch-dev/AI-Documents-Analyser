"""
FastAPI application – all API endpoints for the AI Knowledge Platform.
"""

import logging
import json
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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
from services.currency_service import CurrencyService
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

# ── Upload thread pool ────────────────────────────────────
# Files are processed in parallel — GIL releases during ONNX/numpy embedding,
# so multiple files genuinely embed concurrently. 4 workers on 2-core EC2
# cuts batch wait time by ~3-4× vs sequential BackgroundTasks.
_UPLOAD_WORKERS = max(4, (os.cpu_count() or 2) * 2)
_upload_executor = ThreadPoolExecutor(max_workers=_UPLOAD_WORKERS, thread_name_prefix="upload")

# Lock protecting writes to _batch_statuses from concurrent upload threads
_batch_status_lock = threading.Lock()


def _log_upload_stage(
    stage: str,
    doc_id: str,
    filename: str,
    *,
    ext: str | None = None,
    size_bytes: int | None = None,
    elapsed_ms: int | None = None,
    extra: str | None = None,
) -> None:
    parts = [f"stage={stage}", f"doc_id={doc_id}", f"file={filename}"]
    if ext:
        parts.append(f"ext={ext}")
    if size_bytes is not None:
        parts.append(f"size={size_bytes}")
    if elapsed_ms is not None:
        parts.append(f"elapsed_ms={elapsed_ms}")
    if extra:
        parts.append(extra)
    logger.info("[UPLOAD] %s", " | ".join(parts))


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


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start : end + 1])


def _default_financial_dashboard() -> dict[str, Any]:
    revenue = {
        "f_and_b": 0.0,
        "sponsorship": 0.0,
        "tickets": 0.0,
        "retail": 0.0,
        "player_sales": 0.0,
    }
    expenses = {
        "player_salary": 0.0,
        "coach_salary": 0.0,
        "travel": 0.0,
        "stadium": 0.0,
        "retail": 0.0,
        "f_and_b": 0.0,
        "back_office": 0.0,
        "misc": 0.0,
    }
    return {
        "revenue": revenue,
        "expenses": expenses,
        "totals": {
            "revenue_total": round(sum(revenue.values()), 2),
            "expense_total": round(sum(expenses.values()), 2),
            "net_total": round(sum(revenue.values()) - sum(expenses.values()), 2),
        },
        "notes": [],
        "source_documents": [],
    }


def _normalize_financial_dashboard(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _default_financial_dashboard()
    for section in ("revenue", "expenses"):
        section_data = payload.get(section, {})
        if isinstance(section_data, dict):
            for key in normalized[section]:
                value = section_data.get(key, 0)
                try:
                    normalized[section][key] = round(float(value or 0), 2)
                except (TypeError, ValueError):
                    normalized[section][key] = 0.0

    notes = payload.get("notes", [])
    if isinstance(notes, list):
        normalized["notes"] = [str(item) for item in notes[:10]]

    source_documents = payload.get("source_documents", [])
    if isinstance(source_documents, list):
        normalized["source_documents"] = [str(item) for item in source_documents[:20]]

    normalized["totals"] = {
        "revenue_total": round(sum(normalized["revenue"].values()), 2),
        "expense_total": round(sum(normalized["expenses"].values()), 2),
        "net_total": round(
            sum(normalized["revenue"].values()) - sum(normalized["expenses"].values()),
            2,
        ),
    }
    return normalized


async def _translate_to_english(
    text: str,
    model_name: str,
    api_keys: dict[str, str | None] | None = None,
) -> str:
    if not text.strip():
        return text
    llm, *_ = _get_services()
    try:
        translated = await llm.generate(
            model_name=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the user's content into clear professional English. "
                        "Preserve citations like [1], [2], bullet structure, and all numeric values. "
                        "Return only the translated text."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=4096,
            api_keys=api_keys,
        )
        return translated.strip() or text
    except Exception as exc:
        logger.warning("Translation step failed, returning original answer: %s", exc)
        return text


def _extract_storage_doc_ids(db: Session) -> set[str]:
    storage_doc_ids: set[str] = set()

    try:
        docs = db.query(Document.id, Document.source_path).all()
    except Exception:
        docs = []

    for doc_id, source_path in docs:
        source = str(source_path or "")
        if source.startswith("documents/"):
            storage_doc_ids.add(str(doc_id))
            continue
        if source and not source.startswith("documents/"):
            try:
                import os

                if os.path.exists(source):
                    storage_doc_ids.add(str(doc_id))
            except Exception:
                pass

    if settings.aws_access_key_id and settings.aws_access_key_id != "your-access-key":
        try:
            _, _, s3, _, _ = _get_services()
            for key in s3.list_files(prefix="documents/"):
                match = re.match(r"documents/([0-9a-fA-F-]{36})/", key)
                if match:
                    storage_doc_ids.add(match.group(1))
        except Exception as exc:
            logger.warning("Storage listing skipped for document status endpoint: %s", exc)

    return storage_doc_ids


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

    # Pre-warm embedding model + services so the first upload/query has no cold-start delay
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _get_services)
        logger.info("Services pre-warmed: embedding model loaded and ready.")
    except Exception as e:
        logger.warning("Pre-warm skipped (will load on first request): %s", e)

    yield

    # Cleanup
    _upload_executor.shutdown(wait=False)
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
    translate_to_english: bool = False
    target_currency: str = "BRL"

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

class FinancialDashboardRequest(BaseModel):
    model: str = "auto"
    top_k: int = 24
    category: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


class SkillRunRequest(BaseModel):
    skill: str = Field(..., description="Skill name: financial_analysis | report_generation | consulting_insights")
    input: dict[str, Any] = Field(default_factory=dict, description="Skill input payload")


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
    started_at = time.perf_counter()
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
    _log_upload_stage("received", doc_id, doc_title, ext=ext, size_bytes=len(contents))

    _, rag, s3, parser, _ = _get_services()

    # 1. Store file (S3 if configured, otherwise local fallback)
    try:
        store_started = time.perf_counter()
        if settings.aws_access_key_id and settings.aws_access_key_id != "your-access-key":
            s3.upload_bytes(contents, s3_key, content_type=file.content_type or "application/octet-stream")
            _log_upload_stage(
                "stored_s3",
                doc_id,
                doc_title,
                ext=ext,
                elapsed_ms=int((time.perf_counter() - store_started) * 1000),
                extra=f"path={s3_key}",
            )
        else:
            # Local fallback
            import os
            local_dir = os.path.join("data", "uploads", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, file.filename or "file")
            with open(local_path, "wb") as f:
                f.write(contents)
            s3_key = local_path
            _log_upload_stage(
                "stored_local",
                doc_id,
                doc_title,
                ext=ext,
                elapsed_ms=int((time.perf_counter() - store_started) * 1000),
                extra=f"path={local_path}",
            )
    except Exception as e:
        logger.warning("[UPLOAD] stage=store_failed | doc_id=%s | file=%s | reason=%s", doc_id, doc_title, e)
        import os
        local_dir = os.path.join("data", "uploads", doc_id)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file.filename or "file")
        with open(local_path, "wb") as f:
            f.write(contents)
        s3_key = local_path
        _log_upload_stage("stored_local_fallback", doc_id, doc_title, ext=ext, extra=f"path={local_path}")

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
    _log_upload_stage("db_record_created", doc_id, doc_title, ext=ext, extra="status=processing")

    # 3. Parse + ingest
    try:
        parse_started = time.perf_counter()
        text = _safe_extract_text(parser, contents, ext)
        _log_upload_stage(
            "parsed",
            doc_id,
            doc_title,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - parse_started) * 1000),
            extra=f"chars={len(text)}",
        )
        ingest_started = time.perf_counter()
        chunk_count = rag.ingest_document(
            doc_id=doc_id,
            text=text,
            metadata={"title": doc_title, "category": category},
        )
        _log_upload_stage(
            "ingested",
            doc_id,
            doc_title,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - ingest_started) * 1000),
            extra=f"chunks={chunk_count}",
        )
        doc.chunk_count = chunk_count
        doc.status = "ready"
    except Exception as e:
        logger.exception("[UPLOAD] stage=failed | doc_id=%s | file=%s | reason=%s", doc_id, doc_title, e)
        doc.status = "failed"
        db.commit()
        raise HTTPException(500, f"Document processing failed: {e}")

    db.commit()
    _log_upload_stage(
        "completed",
        doc_id,
        doc_title,
        ext=ext,
        elapsed_ms=int((time.perf_counter() - started_at) * 1000),
        extra=f"status={doc.status}|chunks={doc.chunk_count}",
    )

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
    target_currency = (body.target_currency or "BRL").upper()
    if target_currency not in CurrencyService.SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency: {target_currency}")
    api_keys = {
        "openai_api_key": body.openai_api_key,
        "anthropic_api_key": body.anthropic_api_key,
        "gemini_api_key": body.gemini_api_key,
    }
    use_cache = not body.translate_to_english and target_currency == "BRL"

    # Try cache first (100x faster for repeated queries)
    cached_result = None
    if use_cache:
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
        try:
            result = await rag.query(
                question=body.question,
                model_name=body.model,
                prompt_template=body.prompt_template,
                top_k=body.top_k,
                temperature=body.temperature,
                api_keys=api_keys,
                full_doc_list=doc_titles
            )
        except Exception as exc:
            logger.exception("Query generation failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="Query generation failed. Please verify OPENAI_API_KEY and outbound API access.",
            ) from exc

        # Cache the result for 1 hour
        if use_cache:
            cache.set(
                question=body.question,
                model=body.model,
                top_k=body.top_k,
                result=result,
                category=body.category,
            )

    answer = result["answer"]
    if target_currency != "BRL":
        answer = CurrencyService.convert_text(answer, target_currency)

    if body.translate_to_english:
        answer = await _translate_to_english(
            answer,
            model_name=result["model_used"],
            api_keys=api_keys,
        )
    result["answer"] = answer

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
MAX_SAFE_EXTRACT_CHARS = 180_000


def _normalize_extracted_text(text: str, max_chars: int = MAX_SAFE_EXTRACT_CHARS) -> str:
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if len(text) > max_chars:
        logger.warning("Extracted text too large (%d chars). Truncating to %d.", len(text), max_chars)
        text = text[:max_chars]
    return text

def _safe_extract_text(parser, contents: bytes, ext: str) -> str:
    """Extract text and fallback to decoded bytes when parser fails."""
    try:
        text = parser.parse(contents, ext)
        if text and text.strip():
            logger.info("[UPLOAD] parser=primary | ext=%s | chars=%d", ext, len(text))
            return _normalize_extracted_text(text)
    except Exception as e:
        logger.warning("Primary parser failed for .%s; fallback mode: %s", ext, e)

    text = contents.decode("utf-8", errors="ignore")
    if not text.strip():
        text = contents.decode("latin-1", errors="ignore")
    text = _normalize_extracted_text(text)
    logger.info("[UPLOAD] parser=fallback | ext=%s | chars=%d", ext, len(text))
    return text or f"Uploaded .{ext} file content unavailable; metadata retained."


def _process_single_file(
    doc_id: str, contents: bytes, filename: str, ext: str,
    category: str, s3_key: str, batch_id: str, file_hash: str,
):
    """Process a single file in a background thread."""
    started_at = time.perf_counter()
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        _, rag, s3, parser, _ = _get_services()
        _log_upload_stage("batch_started", doc_id, filename, ext=ext, size_bytes=len(contents), extra=f"batch_id={batch_id}")

        # Store file
        try:
            store_started = time.perf_counter()
            if settings.aws_access_key_id and settings.aws_access_key_id != "your-access-key":
                s3.upload_bytes(contents, s3_key, content_type="application/octet-stream")
                _log_upload_stage(
                    "batch_stored_s3",
                    doc_id,
                    filename,
                    ext=ext,
                    elapsed_ms=int((time.perf_counter() - store_started) * 1000),
                    extra=f"path={s3_key}",
                )
            else:
                import os
                local_dir = os.path.join("data", "uploads", doc_id)
                os.makedirs(local_dir, exist_ok=True)
                with open(os.path.join(local_dir, filename), "wb") as f:
                    f.write(contents)
                _log_upload_stage(
                    "batch_stored_local",
                    doc_id,
                    filename,
                    ext=ext,
                    elapsed_ms=int((time.perf_counter() - store_started) * 1000),
                )
        except Exception as e:
            logger.warning("Storage fallback for %s: %s", doc_id, e)
            import os
            local_dir = os.path.join("data", "uploads", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            with open(os.path.join(local_dir, filename), "wb") as f:
                f.write(contents)
            _log_upload_stage("batch_stored_local_fallback", doc_id, filename, ext=ext)

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
        _log_upload_stage("batch_db_record_created", doc_id, filename, ext=ext, extra="status=processing")

        # Parse + ingest
        parse_started = time.perf_counter()
        text = _safe_extract_text(parser, contents, ext)
        _log_upload_stage(
            "batch_parsed",
            doc_id,
            filename,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - parse_started) * 1000),
            extra=f"chars={len(text)}",
        )
        ingest_started = time.perf_counter()
        chunk_count = rag.ingest_document(
            doc_id=doc_id, text=text,
            metadata={"title": filename, "category": category},
        )
        _log_upload_stage(
            "batch_ingested",
            doc_id,
            filename,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - ingest_started) * 1000),
            extra=f"chunks={chunk_count}",
        )
        doc.chunk_count = chunk_count
        doc.status = "ready"
        db.commit()

        with _batch_status_lock:
            _batch_statuses[batch_id]["files"][doc_id]["status"] = "ready"
            _batch_statuses[batch_id]["files"][doc_id]["chunks"] = chunk_count
        _log_upload_stage(
            "batch_completed",
            doc_id,
            filename,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            extra=f"chunks={chunk_count}|batch_id={batch_id}",
        )

    except Exception as e:
        logger.exception("[UPLOAD] stage=batch_failed | doc_id=%s | file=%s | reason=%s", doc_id, filename, e)
        with _batch_status_lock:
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

        # Submit to dedicated thread pool — files process in parallel, not sequentially.
        # The GIL releases during ONNX/numpy embedding, so threads genuinely run concurrently.
        _upload_executor.submit(
            _process_single_file,
            doc_id, contents, file.filename or "file", ext,
            category, s3_key, batch_id, file_hash,
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


@app.get("/api/documents/status", tags=["Documents"])
async def document_index_status(db: Session = Depends(get_db)):
    """Compare uploaded documents with the indexed vector store state."""
    embedder = get_embedding_service()
    vector_store = get_vector_store(dimension=embedder.dimension)
    vector_docs = vector_store.get_all_documents(limit=5000)
    indexed_doc_ids = {
        str(item.get("metadata", {}).get("doc_id"))
        for item in vector_docs
        if item.get("metadata", {}).get("doc_id")
    }
    storage_doc_ids = _extract_storage_doc_ids(db)

    def serialize(doc: Document) -> dict[str, Any]:
        doc_id = str(doc.id)
        return {
            "document_id": doc_id,
            "title": doc.title,
            "file_type": doc.file_type,
            "db_status": doc.status,
            "uploaded_at": doc.timestamp.isoformat() if doc.timestamp else None,
            "source_path": doc.source_path,
            "storage_present": doc_id in storage_doc_ids if storage_doc_ids else bool(doc.source_path),
            "indexed": doc_id in indexed_doc_ids,
        }

    docs = db.query(Document).order_by(Document.timestamp.desc()).all()
    indexed = []
    not_indexed = []
    for doc in docs:
        row = serialize(doc)
        if row["indexed"]:
            indexed.append(row)
        else:
            not_indexed.append(row)

    return {
        "indexed": indexed,
        "not_indexed": not_indexed,
        "indexed_count": len(indexed),
        "not_indexed_count": len(not_indexed),
        "total_documents": len(docs),
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


@app.post("/api/analytics/financial_dashboard", tags=["Analytics"])
async def analytics_financial_dashboard(
    body: FinancialDashboardRequest,
    db: Session = Depends(get_db),
):
    """Extract a lightweight revenue/expense dashboard from indexed documents."""
    llm, *_ = _get_services()
    embedder = get_embedding_service()
    vector_store = get_vector_store(dimension=embedder.dimension)

    filter_metadata = {"category": body.category} if body.category else None
    query_embedding = embedder.embed_query(
        "financial data revenue expenses sponsorship tickets retail player sales salary travel stadium back office"
    )
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=max(8, min(body.top_k, 40)),
        filter_metadata=filter_metadata,
    )
    if not results:
        raise HTTPException(400, "No indexed document context available for financial extraction.")

    source_documents = list(
        dict.fromkeys(
            [
                result.get("metadata", {}).get("title", "")
                for result in results
                if result.get("metadata", {}).get("title")
            ]
        )
    )
    context = "\n\n".join(
        f"[{idx + 1}] {result.get('document', '')[:1200]}"
        for idx, result in enumerate(results)
    )

    prompt = (
        "Extract financial data into JSON with revenue and expenses categories.\n"
        "Use only the supplied document context. If a value is missing, use 0.\n"
        "Return valid JSON only using this exact schema:\n"
        "{\n"
        '  "revenue": {\n'
        '    "f_and_b": number,\n'
        '    "sponsorship": number,\n'
        '    "tickets": number,\n'
        '    "retail": number,\n'
        '    "player_sales": number\n'
        "  },\n"
        '  "expenses": {\n'
        '    "player_salary": number,\n'
        '    "coach_salary": number,\n'
        '    "travel": number,\n'
        '    "stadium": number,\n'
        '    "retail": number,\n'
        '    "f_and_b": number,\n'
        '    "back_office": number,\n'
        '    "misc": number\n'
        "  },\n"
        '  "notes": ["short note"]\n'
        "}\n\n"
        f"Context:\n{context}"
    )

    api_keys = {
        "openai_api_key": body.openai_api_key,
        "anthropic_api_key": body.anthropic_api_key,
        "gemini_api_key": body.gemini_api_key,
    }
    resolved_model = llm.resolve_model(body.model, "financial dashboard extraction", api_keys)
    try:
        raw_response = await llm.generate(
            model_name=resolved_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract finance data from documents. Return only valid JSON. "
                        "Do not add commentary or markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
            api_keys=api_keys,
        )
        dashboard = _normalize_financial_dashboard(_extract_json_object(raw_response))
    except Exception as exc:
        logger.warning("Financial dashboard extraction failed: %s", exc)
        dashboard = _default_financial_dashboard()
        dashboard["notes"] = ["Financial extraction could not complete with the current model backend."]

    dashboard["source_documents"] = source_documents[:20]
    dashboard["model_used"] = resolved_model
    return dashboard


# ══════════════════════════════════════════════════════════
#  Utility endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/models", tags=["Utility"])
async def list_available_models():
    llm, *_ = _get_services()
    return {"models": llm.list_models()}


@app.get("/api/detect_currency", tags=["Utility"])
async def detect_currency():
    """Heuristically detect the dominant currency in indexed document chunks.

    Scans stored text for symbol patterns (R$, $, €, £, ¥, …) and ISO-code
    patterns (100 USD, 200 EUR) — no LLM, no hallucination.
    Returns the most frequent currency code and a confidence level.
    """
    embedder = get_embedding_service()
    vector_store = get_vector_store(dimension=embedder.dimension)
    docs = vector_store.get_all_documents(limit=300)

    counts: dict[str, int] = {}

    for doc in docs:
        text = doc.get("document", "")
        if not text:
            continue

        # BRL with optional multiplier — count separately since _BRL_PATTERN is specific
        for _ in CurrencyService._BRL_PATTERN.finditer(text):
            counts["BRL"] = counts.get("BRL", 0) + 1

        # Generic symbol patterns ($, €, £, ¥, …)
        for m in CurrencyService._SYMBOL_PATTERN.finditer(text):
            code = CurrencyService._symbol_to_code(m.group("symbol"))
            if code:
                counts[code] = counts.get(code, 0) + 1

        # ISO-code suffix patterns (100 USD, 200 EUR)
        for m in CurrencyService._ISO_PATTERN.finditer(text):
            code = m.group("code").upper()
            if code in CurrencyService.SUPPORTED_CURRENCIES:
                counts[code] = counts.get(code, 0) + 1

    if not counts:
        return {"currency": "BRL", "confidence": "none", "counts": {}}

    top = max(counts, key=lambda k: counts[k])
    total = sum(counts.values())
    ratio = counts[top] / total
    confidence = "high" if ratio >= 0.60 else "medium" if ratio >= 0.35 else "low"

    return {"currency": top, "confidence": confidence, "counts": counts}


@app.get("/api/health", tags=["Utility"])
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# ══════════════════════════════════════════════════════════
#  Skills endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/skills", tags=["Skills"])
async def list_skills():
    """List all available skills with descriptions."""
    return {
        "skills": [
            {
                "name": "financial_analysis",
                "description": "Extract structured revenue, expense, and insight data from document text.",
                "input_fields": ["document_text or context", "model (optional)", "openai_api_key (optional)"],
            },
            {
                "name": "report_generation",
                "description": "Generate a structured business report (summary, metrics, recommendations) from context.",
                "input_fields": ["context or document_text", "model (optional)", "openai_api_key (optional)"],
            },
            {
                "name": "consulting_insights",
                "description": "Apply strategic consulting frameworks (SWOT + priorities) to document context.",
                "input_fields": ["context or document_text", "model (optional)", "openai_api_key (optional)"],
            },
        ]
    }


@app.post("/api/skills/run", tags=["Skills"])
@limiter.limit(settings.rate_limit)
async def run_skill(
    request: Request,
    body: SkillRunRequest,
    db: Session = Depends(get_db),
):
    """
    Run a named skill against provided input data.

    If no context/document_text is supplied in the input, the skill will
    automatically retrieve relevant context from the vector store.
    """
    from backend.skills.skill_router import route_skill, SUPPORTED_SKILLS

    if body.skill not in SUPPORTED_SKILLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown skill '{body.skill}'. Supported: {sorted(SUPPORTED_SKILLS)}",
        )

    llm, *_ = _get_services()
    input_data = dict(body.input)

    # Auto-fetch context from vector store when caller does not supply text
    if not input_data.get("context") and not input_data.get("document_text"):
        skill_queries = {
            "financial_analysis": "revenue expenses financial data profit loss",
            "report_generation": "business performance summary key metrics results",
            "consulting_insights": "strategy risks opportunities strengths competitive",
        }
        query_text = skill_queries.get(body.skill, body.skill)
        try:
            embedder = get_embedding_service()
            vector_store = get_vector_store(dimension=embedder.dimension)
            query_emb = embedder.embed_query(query_text)
            results = vector_store.search(query_emb, top_k=10)
            if results:
                input_data["context"] = "\n\n---\n\n".join(
                    r.get("document", "")[:1500] for r in results
                )
        except Exception as exc:
            logger.warning("Skills auto-context retrieval failed: %s", exc)

    try:
        result = await route_skill(body.skill, input_data, llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Skill execution error for '%s': %s", body.skill, exc)
        raise HTTPException(status_code=502, detail=f"Skill execution failed: {exc}") from exc

    return {"skill": body.skill, "result": result}
