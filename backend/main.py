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
    Body,
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
from backend.auth.rbac import require_permission, require_mcp_tool, get_role_info
from backend.auth.dependencies import require_auth, optional_auth, require_role
from backend.services.cost_tracker import log_usage_async, get_usage_summary
from backend.services.audit_logger import audit_log, get_audit_trail
from backend.utils.validator import (
    validate_workflow_input, validate_mcp_arguments, validate_provider,
    ValidationError as InputValidationError,
)
from backend.utils.retry import with_retry, make_workflow_fallback
from config.settings import settings
from db.database import get_db, init_db
from db.models import Document, User, LLMUsage, SavedReport, AuditLog
from services.document_parser import DocumentParser
from services.currency_service import CurrencyService
from services.s3_storage import S3StorageService
from backend.services.categorization_service import CategorizationService

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

# ── Rate limiter ─────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# Per-endpoint rate limit strings
RL_CHAT      = "60/minute"   # chat / query
RL_WORKFLOW  = "10/minute"   # workflow runs
RL_MCP       = "20/minute"   # MCP tool calls
RL_SKILL     = "30/minute"   # skills
RL_DEFAULT   = settings.rate_limit

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
    if not settings.webhook_secret:
        logger.warning(
            "SECURITY WARNING: WEBHOOK_SECRET is not set. "
            "Webhook endpoints (/api/webhooks/*) are unauthenticated. "
            "Set WEBHOOK_SECRET in .env before exposing this service publicly."
        )
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
    provider: str = "openai"   # "openai" | "bedrock" — any Bedrock model ID accepted
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
    provider: str = "openai"
    top_k: int = 10
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

class FinancialDashboardRequest(BaseModel):
    model: str = "auto"
    provider: str = "openai"
    top_k: int = 24
    category: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


class SkillRunRequest(BaseModel):
    skill: str = Field(..., description="Skill name: financial_analysis | report_generation | consulting_insights")
    input: dict[str, Any] = Field(default_factory=dict, description="Skill input payload")
    provider: str = Field("openai", description="LLM provider: openai | bedrock")
    model: str = Field("auto", description="Model name/ID. Any Bedrock model ID accepted when provider=bedrock")


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
async def login(request: Request, body: UserLogin, db: Session = Depends(get_db)):
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
    token = _create_token({"sub": user.username, "role": user.role})
    try:
        audit_log(db, "login", user=user, resource="auth", request=request,
                  detail={"role": user.role})
    except Exception:
        pass
    return TokenResponse(access_token=token)


# ══════════════════════════════════════════════════════════
#  Document endpoints
# ══════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "xls", "csv", "txt", "json"}


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
    user: User = Depends(require_auth),
):
    """Send a question through the RAG pipeline with Redis caching. Requires query_documents permission."""
    require_permission(user, "query_documents")
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
                provider=body.provider,
                prompt_template=body.prompt_template,
                top_k=body.top_k,
                temperature=body.temperature,
                api_keys=api_keys,
                full_doc_list=doc_titles
            )
        except Exception as exc:
            logger.exception("Query generation failed: %s", exc)
            from backend.llm_router import _is_bedrock_provider
            if _is_bedrock_provider(body.provider):
                detail = (
                    f"Query generation failed (Bedrock provider): {exc}. "
                    "Verify AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION in .env "
                    "and that the model is enabled in your AWS account."
                )
            else:
                detail = (
                    f"Query generation failed (OpenAI provider): {exc}. "
                    "Verify OPENAI_API_KEY in .env or enter it in Chat Settings → API Keys."
                )
            raise HTTPException(status_code=502, detail=detail) from exc

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
        provider=body.provider,
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
        
        # Auto-categorization
        if not category or category == "general":
            import asyncio
            try:
                # We are in a thread pool, use a new loop for async call
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                category = loop.run_until_complete(
                    CategorizationService.categorize_document(text, filename, llm_router)
                )
                loop.close()
            except Exception as cat_exc:
                logger.warning("Auto-categorization failed, falling back to keywords: %s", cat_exc)
                category = CategorizationService.get_category_from_keywords(filename, text)

        _log_upload_stage(
            "batch_parsed",
            doc_id,
            filename,
            ext=ext,
            elapsed_ms=int((time.perf_counter() - parse_started) * 1000),
            extra=f"chars={len(text)} | category={category}",
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
        doc.category = category
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
    from backend.llm_router import _is_bedrock_provider
    resolved_model = (
        (body.model or "").strip() or settings.bedrock_default_model
        if _is_bedrock_provider(body.provider)
        else llm.resolve_model(body.model, "financial dashboard extraction", api_keys)
    )
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
            provider=body.provider,
        )
        dashboard = _normalize_financial_dashboard(_extract_json_object(raw_response))
    except Exception as exc:
        logger.warning("Financial dashboard extraction failed: %s", exc)
        dashboard = _default_financial_dashboard()
        dashboard["notes"] = ["Financial extraction could not complete with the current model backend."]

    # High-integrity fallback using actual Ledger database if totals are 0 or empty
    try:
        from backend.fpa_core.persistence import FinancialLedgerStore
        store = FinancialLedgerStore()
        
        if dashboard["totals"]["revenue_total"] == 0:
            revs = store.get_all_revenues()
            for r in revs:
                cat = "tickets" if r.category == "ticketing" else r.category
                if cat in dashboard["revenue"]:
                    dashboard["revenue"][cat] = r.amount
                else:
                    dashboard["revenue"]["f_and_b"] = dashboard["revenue"].get("f_and_b", 0.0) + r.amount

        if dashboard["totals"]["expense_total"] == 0:
            exps = store.get_all_expenses()
            for e in exps:
                dept = "player_salary" if e.department == "payroll" else e.department
                if dept in dashboard["expenses"]:
                    dashboard["expenses"][dept] = e.actual_spend
                else:
                    dashboard["expenses"]["misc"] = dashboard["expenses"].get("misc", 0.0) + e.actual_spend

        # Recalculate totals
        dashboard["totals"] = {
            "revenue_total": round(sum(dashboard["revenue"].values()), 2),
            "expense_total": round(sum(dashboard["expenses"].values()), 2),
            "net_total": round(sum(dashboard["revenue"].values()) - sum(dashboard["expenses"].values()), 2)
        }
    except Exception as fallback_err:
        logger.warning("Fallback ledger populate failed: %s", fallback_err)

    dashboard["source_documents"] = source_documents[:20]
    dashboard["model_used"] = resolved_model
    return dashboard


# ══════════════════════════════════════════════════════════
#  Utility endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/models", tags=["Utility"])
async def list_available_models():
    llm, *_ = _get_services()
    return {
        "models": llm.list_models(),          # backwards-compat: OpenAI only
        "all_models": llm.list_all_models(),   # all providers
        "providers": ["openai", "bedrock"],
        "note": "For Bedrock, any valid model ID is accepted — not limited to the listed defaults.",
    }


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
@limiter.limit(RL_SKILL)
async def run_skill(
    request: Request,
    body: SkillRunRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Run a named skill against provided input data.

    If no context/document_text is supplied in the input, the skill will
    automatically retrieve relevant context from the vector store.
    """
    require_permission(user, "run_skill")
    from backend.skills.skill_router import route_skill, SUPPORTED_SKILLS

    if body.skill not in SUPPORTED_SKILLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown skill '{body.skill}'. Supported: {sorted(SUPPORTED_SKILLS)}",
        )

    llm, *_ = _get_services()
    input_data = dict(body.input)
    # Inject provider + model so skills can forward them to the LLM router
    input_data.setdefault("provider", body.provider)
    input_data.setdefault("model", body.model)

    # Auto-fetch context from vector store when caller does not supply text
    if not input_data.get("context") and not input_data.get("document_text"):
        skill_queries = {
            "financial_analysis": "revenue expenses financial data profit loss",
            "report_generation": "business performance summary key metrics results",
            "consulting_insights": "strategy risks opportunities strengths competitive",
            "debt_analysis": "debt liabilities loans interest rates creditors maturity",
            "cashflow_analysis": "cash flow inflows outflows liquidity burn rate runway",
            "refinancing_scenario": "debt interest rates refinancing loans credit",
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

    audit_log(db, "skill_run", user=user, resource=body.skill, request=request,
              detail={"provider": body.provider, "model": body.model})
    try:
        result = await route_skill(body.skill, input_data, llm, provider=body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Skill execution error for '%s': %s", body.skill, exc)
        raise HTTPException(status_code=502, detail=f"Skill execution failed: {exc}") from exc

    await log_usage_async(
        db=db, provider=body.provider, model=body.model or "auto",
        action=f"skill_{body.skill}",
        prompt_text=str(input_data)[:2000],
        completion_text=str(result)[:2000],
        user=user,
    )
    return {"skill": body.skill, "result": result}


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOWS  (auth + RBAC + rate limit + audit + cost tracking + retry)
# ══════════════════════════════════════════════════════════════════════════════

class WorkflowRunRequest(BaseModel):
    workflow: str = Field(..., description="Workflow name: financial | consulting | report")
    input: dict = Field(default_factory=dict, description="Input data (document_text, context, etc.)")
    provider: str = Field("openai", description="LLM provider: openai | bedrock")
    model: str = Field("auto", description="Model name/ID")
    openai_api_key: str | None = None


@app.get("/api/workflows/list", tags=["Workflows"])
async def list_workflows_endpoint():
    """Return all registered workflows with their steps and output schemas."""
    from backend.workflows.workflow_engine import list_workflows
    return {"workflows": list_workflows()}


# ── Natural language classifier ───────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    query: str = Field(..., description="Natural language query to classify")


@app.post("/api/workflows/classify", tags=["Workflows"])
async def classify_workflow(body: ClassifyRequest):
    """Classify a natural-language query to the best matching workflow."""
    from backend.services.insight_engine import classify_query
    workflow = classify_query(body.query)
    return {"workflow": workflow, "query": body.query}


# ── One-click analysis: runs all 3 workflows ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    provider: str = Field("openai", description="LLM provider")
    model: str = Field("auto", description="Model name/ID")
    openai_api_key: str | None = None
    context: str = Field("", description="Optional context text (uses vector store if omitted)")


@app.post("/api/workflows/bulk-analyze", tags=["Workflows"])
@limiter.limit("5/minute")
async def one_click_analyze(
    request: Request,
    body: AnalyzeRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    One-click business analysis: runs financial + consulting + report workflows
    in sequence and returns a unified business report.
    """
    require_permission(user, "run_workflow")
    llm, *_ = _get_services()
    api_keys = {"openai_api_key": body.openai_api_key}
    from backend.workflows.workflow_engine import run_workflow
    from backend.utils.retry import with_retry, make_workflow_fallback

    audit_log(db, "one_click_analyze", user=user, request=request,
              detail={"provider": body.provider, "model": body.model})

    input_data = {"context": body.context, "document_text": body.context}
    results = {}
    for wf in ("financial", "consulting", "report"):
        try:
            results[wf] = await with_retry(
                run_workflow,
                workflow_name=wf,
                input_data=input_data,
                llm_router=llm,
                provider=body.provider,
                model=body.model,
                api_keys=api_keys,
                max_retries=1,
                timeout_s=90.0,
                fallback=make_workflow_fallback(wf),
            )
        except Exception as exc:
            logger.warning("One-click: workflow '%s' failed: %s", wf, exc)
            results[wf] = make_workflow_fallback(wf)

    # Cost tracking (bulk)
    await log_usage_async(
        db=db, provider=body.provider, model=body.model,
        action="one_click_analyze",
        prompt_text=body.context[:1000],
        completion_text=str(results)[:3000],
        user=user,
    )

    return {
        "analysis_type": "unified_business_report",
        "provider": body.provider,
        "model": body.model,
        "workflows": results,
        "summary": {
            wf: results[wf].get("business_insight", {}).get("summary", "")
            for wf in results
        },
    }


@app.post("/api/workflows/run", tags=["Workflows"])
@limiter.limit(RL_WORKFLOW)
async def run_workflow_endpoint(
    request: Request,
    body: WorkflowRunRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Execute a named multi-step workflow. Requires auth. Analyst+ role only."""
    require_permission(user, "run_workflow")

    # Validate inputs
    try:
        sanitised_input = validate_workflow_input(body.input)
        validate_provider(body.provider)
    except InputValidationError as exc:
        audit_log(db, "workflow_run", user=user, resource=body.workflow,
                  detail={"error": str(exc)}, request=request, status="error")
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    llm, *_ = _get_services()
    api_keys = {"openai_api_key": body.openai_api_key}

    from backend.workflows.workflow_engine import run_workflow
    audit_log(db, "workflow_run", user=user, resource=body.workflow,
              detail={"provider": body.provider, "model": body.model}, request=request)
    try:
        result = await with_retry(
            run_workflow,
            workflow_name=body.workflow,
            input_data=sanitised_input,
            llm_router=llm,
            provider=body.provider,
            model=body.model,
            api_keys=api_keys,
            max_retries=2,
            timeout_s=90.0,
            fallback=make_workflow_fallback(body.workflow),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Workflow '%s' failed: %s", body.workflow, exc)
        raise HTTPException(status_code=502, detail=f"Workflow execution failed: {exc}") from exc

    # Cost tracking (best-effort, using result text as proxy)
    await log_usage_async(
        db=db, provider=body.provider, model=result.get("model_used", body.model),
        action=f"workflow_{body.workflow}",
        prompt_text=str(sanitised_input)[:2000],
        completion_text=str(result.get("result", ""))[:3000],
        user=user,
    )
    return result


@app.post("/api/workflows/analyze", tags=["Workflows"])
@limiter.limit(RL_WORKFLOW)
async def analyze_business(
    request: Request,
    body: dict = Body(...), # {query: string, model: string, provider: string}
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """One-click full business analysis."""
    require_permission(user, "run_workflow")
    from backend.services.workflow_classifier import WorkflowClassifier
    from backend.workflows.workflow_engine import run_workflow
    
    query = body.get("query", "Summarize business performance and risks.")
    model = body.get("model", "gpt-4o")
    provider = body.get("provider", "openai")
    
    llm, *_ = _get_services()
    
    # 1. Classify intent
    workflow_type = await WorkflowClassifier.classify_intent(query, llm)
    
    # 2. Run workflow
    result = await run_workflow(workflow_type, {"query": query}, llm, provider=provider, model=model)
    
    # 3. Persist audit
    audit_log(db, "workflow_analyze", user=user, resource=workflow_type, request=request)
    
    return {
        "workflow_type": workflow_type,
        "query": query,
        "result": result
    }


@app.post("/api/workflows/classify", tags=["Workflows"])
async def classify_workflow(
    body: dict = Body(...),
    user: User = Depends(require_auth),
):
    """Map NL query to workflow type."""
    from backend.services.workflow_classifier import WorkflowClassifier
    llm, *_ = _get_services()
    workflow_type = await WorkflowClassifier.classify_intent(body.get("query", ""), llm)
    return {"workflow_type": workflow_type}


# ══════════════════════════════════════════════════════════════════════════════
#  MCP EXECUTE  (auth + RBAC + rate limit + per-tool permission + input validation)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/mcp/execute", tags=["MCP"])
@limiter.limit(RL_MCP)
async def mcp_execute(request: Request, db: Session = Depends(get_db)):
    """
    JSON-RPC 2.0 MCP endpoint.

    - initialize / tools/list: public (no auth needed)
    - tools/call: requires Bearer token + analyst+ role + per-tool permission check
    """
    llm, *_ = _get_services()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    method = body.get("method", "")
    rpc_id = body.get("id")

    # Public methods (no auth required)
    if method in ("initialize", "tools/list"):
        from backend.mcp.server import handle_request
        return JSONResponse(await handle_request(body, llm_router=llm))

    # tools/call — requires auth + RBAC
    if method == "tools/call":
        user = optional_auth(request, db)
        params = body.get("params", {})
        tool_name = params.get("name") or params.get("tool_name", "")

        if user is None:
            audit_log(db, "mcp_call", resource=tool_name, request=request, status="denied",
                      detail={"error": "unauthenticated"})
            return JSONResponse({
                "jsonrpc": "2.0", "id": rpc_id,
                "error": {"code": -32001, "message": "Authentication required for tool execution."}
            })

        if not require_mcp_tool.__module__:  # always true — just call it guarded
            pass
        from backend.auth.rbac import can_use_mcp_tool
        if not can_use_mcp_tool(user, tool_name):
            audit_log(db, "mcp_call", user=user, resource=tool_name, request=request, status="denied",
                      detail={"role": user.role})
            return JSONResponse({
                "jsonrpc": "2.0", "id": rpc_id,
                "error": {"code": -32002, "message": f"Role '{user.role}' cannot call tool '{tool_name}'."}
            })

        # Validate + sanitise arguments
        arguments = params.get("arguments") or params.get("input", {})
        try:
            arguments = validate_mcp_arguments(tool_name, arguments)
        except InputValidationError as exc:
            audit_log(db, "mcp_call", user=user, resource=tool_name, request=request, status="error",
                      detail={"validation_error": str(exc)})
            return JSONResponse({
                "jsonrpc": "2.0", "id": rpc_id,
                "error": {"code": -32003, "message": f"Input validation failed: {exc}"}
            })

        body["params"]["arguments"] = arguments
        audit_log(db, "mcp_call", user=user, resource=tool_name, request=request,
                  detail={"provider": arguments.get("provider", "openai")})

        from backend.mcp.server import handle_request
        result = await handle_request(body, llm_router=llm)

        await log_usage_async(
            db=db, provider=arguments.get("provider", "openai"),
            model=arguments.get("model", "auto"),
            action=f"mcp_{tool_name}",
            prompt_text=str(arguments)[:2000],
            completion_text=str(result)[:2000],
            user=user,
        )
        return JSONResponse(result)

    # Unknown method
    from backend.mcp.server import handle_request
    return JSONResponse(await handle_request(body, llm_router=llm))


# ══════════════════════════════════════════════════════════════════════════════
#  WEBHOOKS  (n8n / external automation — lightweight API key check)
# ══════════════════════════════════════════════════════════════════════════════

class WebhookRequest(BaseModel):
    provider: str = "openai"
    model: str = "auto"
    document_text: str = ""
    context: str = ""
    openai_api_key: str | None = None
    schedule: str | None = None        # e.g. "daily" | "weekly" — metadata for n8n scheduling


def _verify_webhook_secret(request: Request) -> None:
    """
    Enforce webhook authentication via the x-webhook-secret header.
    - If WEBHOOK_SECRET is configured in settings: the header MUST be present
      and match exactly → 401 on any mismatch or absence.
    - If WEBHOOK_SECRET is not configured: log a startup warning (logged once
      at app start) and allow the request through so dev environments work.
    """
    expected = settings.webhook_secret
    if not expected:
        # Already warned at startup; permissive in dev, not recommended in prod.
        return
    provided = request.headers.get("x-webhook-secret", "")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-webhook-secret header.")


@app.post("/api/webhooks/financial", tags=["Webhooks"])
async def webhook_financial(request: Request, body: WebhookRequest, db: Session = Depends(get_db)):
    """n8n-ready webhook — financial workflow. Requires x-webhook-secret header."""
    _verify_webhook_secret(request)
    llm, *_ = _get_services()
    from backend.workflows.workflow_engine import run_workflow
    try:
        result = await with_retry(
            run_workflow,
            workflow_name="financial",
            input_data={"document_text": body.document_text or body.context},
            llm_router=llm, provider=body.provider, model=body.model,
            api_keys={"openai_api_key": body.openai_api_key},
            max_retries=1, timeout_s=90.0, fallback=make_workflow_fallback("financial"),
        )
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    audit_log(db, "webhook_trigger", resource="financial", detail={"provider": body.provider})
    return result


@app.post("/api/webhooks/consulting", tags=["Webhooks"])
async def webhook_consulting(request: Request, body: WebhookRequest, db: Session = Depends(get_db)):
    """n8n-ready webhook — consulting workflow. Requires x-webhook-secret header."""
    _verify_webhook_secret(request)
    llm, *_ = _get_services()
    from backend.workflows.workflow_engine import run_workflow
    try:
        result = await with_retry(
            run_workflow,
            workflow_name="consulting",
            input_data={"context": body.context or body.document_text},
            llm_router=llm, provider=body.provider, model=body.model,
            api_keys={"openai_api_key": body.openai_api_key},
            max_retries=1, timeout_s=90.0, fallback=make_workflow_fallback("consulting"),
        )
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    audit_log(db, "webhook_trigger", resource="consulting", detail={"provider": body.provider})
    return result


@app.post("/api/webhooks/report", tags=["Webhooks"])
async def webhook_report(request: Request, body: WebhookRequest, db: Session = Depends(get_db)):
    """n8n-ready webhook — report workflow. Requires x-webhook-secret header."""
    _verify_webhook_secret(request)
    llm, *_ = _get_services()
    from backend.workflows.workflow_engine import run_workflow
    try:
        result = await with_retry(
            run_workflow,
            workflow_name="report",
            input_data={"context": body.context or body.document_text},
            llm_router=llm, provider=body.provider, model=body.model,
            api_keys={"openai_api_key": body.openai_api_key},
            max_retries=1, timeout_s=90.0, fallback=make_workflow_fallback("report"),
        )
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    audit_log(db, "webhook_trigger", resource="report", detail={"provider": body.provider})
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT  (auth + RBAC + audit)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/export/report", tags=["Export"])
async def export_report(
    body: WorkflowRunRequest,
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Run workflow and export result as JSON or CSV. Requires analyst+ role."""
    require_permission(user, "export")
    from fastapi.responses import PlainTextResponse
    import csv, io
    llm, *_ = _get_services()
    api_keys = {"openai_api_key": body.openai_api_key}
    from backend.workflows.workflow_engine import run_workflow
    audit_log(db, "export", user=user, resource=body.workflow, request=request,
              detail={"provider": body.provider, "format": body.input.get("format", "json")})
    try:
        result = await with_retry(
            run_workflow,
            workflow_name=body.workflow,
            input_data=body.input,
            llm_router=llm, provider=body.provider, model=body.model, api_keys=api_keys,
            max_retries=1, timeout_s=90.0, fallback=make_workflow_fallback(body.workflow),
        )
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc

    format_param = body.input.get("format", "json")
    if format_param == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        def _flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _flatten(v, f"{prefix}{k}.")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    _flatten(v, f"{prefix}{i}.")
            else:
                writer.writerow([prefix.rstrip("."), obj])
        _flatten(result)
        return PlainTextResponse(output.getvalue(), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=report.csv"})
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

class SaveReportRequest(BaseModel):
    report_type: str = Field(..., description="financial | consulting | report")
    title: str = Field("", description="Optional display title")
    data: dict = Field(..., description="Full workflow result data to persist")
    model_used: str = ""
    provider: str = "openai"


@app.post("/api/reports/save", tags=["Reports"])
async def save_report(
    body: SaveReportRequest,
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Persist a workflow result to the database."""
    require_permission(user, "save_report")
    record = SavedReport(
        user_id=user.id,
        username=user.username,
        report_type=body.report_type,
        title=body.title or f"{body.report_type.title()} Report",
        data=body.data,
        model_used=body.model_used,
        provider=body.provider,
    )
    db.add(record)
    db.commit()
    audit_log(db, "report_save", user=user, resource=body.report_type, request=request)
    return {"id": str(record.id), "message": "Report saved.", "report_type": body.report_type}


@app.get("/api/reports", tags=["Reports"])
async def list_reports(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """List saved reports for the current user (admin sees all)."""
    require_permission(user, "view_reports")
    query = db.query(SavedReport).order_by(SavedReport.created_at.desc()).limit(limit)
    if user.role != "admin":
        query = db.query(SavedReport).filter(
            SavedReport.username == user.username
        ).order_by(SavedReport.created_at.desc()).limit(limit)
    records = query.all()
    return {
        "reports": [
            {
                "id": str(r.id),
                "report_type": r.report_type,
                "title": r.title,
                "model_used": r.model_used,
                "provider": r.provider,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@app.get("/api/reports/{report_id}", tags=["Reports"])
async def get_report(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Retrieve a single saved report by ID."""
    require_permission(user, "view_reports")
    try:
        import uuid as _uuid
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID format.")
    record = db.query(SavedReport).filter(SavedReport.id == rid).first()
    if not record:
        raise HTTPException(404, "Report not found.")
    if user.role != "admin" and record.username != user.username:
        raise HTTPException(403, "Access denied.")
    return {
        "id": str(record.id),
        "report_type": record.report_type,
        "title": record.title,
        "data": record.data,
        "model_used": record.model_used,
        "provider": record.provider,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@app.delete("/api/reports/{report_id}", tags=["Reports"])
async def delete_report(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a saved report."""
    require_permission(user, "delete_report")
    try:
        import uuid as _uuid
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID format.")
    
    record = db.query(SavedReport).filter(SavedReport.id == rid).first()
    if not record:
        raise HTTPException(404, "Report not found.")
    
    if user.role != "admin" and record.username != user.username:
        raise HTTPException(403, "Access denied.")
    
    db.delete(record)
    db.commit()
    return {"message": "Report deleted."}


@app.post("/api/export/report", tags=["Reports"])
async def export_report(
    report_id: str,
    format: str = Query("json", enum=["json", "csv"]),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Export a report in the specified format."""
    require_permission(user, "view_reports")
    try:
        import uuid as _uuid
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID format.")
    
    record = db.query(SavedReport).filter(SavedReport.id == rid).first()
    if not record:
        raise HTTPException(404, "Report not found.")
    
    if format == "json":
        return record.data
    
    # CSV export logic (simple flattening of the JSON data)
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Simple flattening: write keys as headers and values as row
    data = record.data
    if isinstance(data, dict):
        writer.writerow(data.keys())
        writer.writerow(data.values())
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            writer.writerow(data[0].keys())
            for item in data:
                writer.writerow(item.values())
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
    )


# ══════════════════════════════════════════════════════════════════════════════
#  USAGE + AUDIT  (cost dashboard)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/usage/summary", tags=["Usage"])
async def usage_summary(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    days: int = 30,
):
    """Return LLM usage + cost summary for the current user (admin sees all)."""
    require_permission(user, "view_usage")
    return get_usage_summary(db, user=user, days=days)


@app.get("/api/audit/logs", tags=["Audit"])
async def audit_logs(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Return audit trail. Admin sees all; others see their own entries."""
    if user.role != "admin":
        require_permission(user, "view_usage")
    return {"logs": get_audit_trail(db, user=user, limit=limit)}


# ══════════════════════════════════════════════════════════════════════════════
#  RBAC INFO  (current user's role + permissions)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/auth/me", tags=["Auth"])
async def me(user: User = Depends(require_auth)):
    """Return current user info + role + permissions."""
    return {
        "username": user.username,
        "role": user.role,
        **get_role_info(user),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.patch("/api/admin/users/{username}/role", tags=["Admin"])
async def set_user_role(
    username: str,
    role: str,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: change another user's role."""
    valid_roles = {"admin", "analyst", "viewer", "user"}
    if role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, f"User '{username}' not found.")
    target.role = role
    db.commit()
    return {"username": username, "role": role, "message": "Role updated."}


# ══════════════════════════════════════════════════════════════════════════════
#  FINANCIAL OPERATING SYSTEM (FIN-OS) ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

import io
from fastapi.responses import StreamingResponse

class ExtractFinancialsRequest(BaseModel):
    document_id: Optional[str] = None
    provider: str = "openai"
    model: str = "gpt-4o"

class ForecastRequest(BaseModel):
    starting_cash: float = 5000000.0
    sponsorship_change_pct: float = 0.0
    payroll_change_pct: float = 0.0
    refinancing_rate: float = 0.05
    transfer_sales: float = 0.0
    delayed_collections_pct: float = 0.0
    revenue_growth_pct: float = 0.05
    inflation_pct: float = 0.03
    relegation_or_promotion: str = "none"
    scenario: str = "base"

class IntelligenceRequest(BaseModel):
    starting_cash: float = 5000000.0
    revenue_items: list = []
    expense_items: list = []
    debt_items: list = []
    obligations: list = []
    burn_rate_monthly: float = 500000.0
    provider: str = "openai"
    model: str = "gpt-4o"

class ExportExcelRequest(BaseModel):
    starting_cash: float = 5000000.0
    revenue_items: list = []
    expense_items: list = []
    forecast_data: dict = {}

class ExportPptxRequest(BaseModel):
    title_text: str = "Q1 Financial Strategy"
    board_summary: str = ""
    risks: list = []

@app.post("/api/financial-os/extract", tags=["Financial OS"])
async def extract_financial_os_data(
    req: ExtractFinancialsRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    from backend.financial_engine.extractor import FinancialExtractionEngine
    from db.models import Document
    import uuid

    llm, rag, _, _, _ = _get_services()
    
    # Locate document to extract from
    doc_text = "No document content found."
    filename = "SampleModel.xlsx"
    
    if req.document_id:
        try:
            doc_uuid = uuid.UUID(req.document_id)
            doc = db.query(Document).filter(Document.id == doc_uuid).first()
            if doc:
                filename = doc.title
                # Read raw text content if available via vector store / RAG
                try:
                    res = await rag.query(f"List all numeric items and financials in {filename}", limit=20)
                    doc_text = "\n".join([chunk.get("text", "") for chunk in res.get("chunks", [])])
                except Exception as e:
                    doc_text = f"Fallback text for document {filename}"
        except Exception:
            pass
            
    # Run the extraction engine
    extracted_data = await FinancialExtractionEngine.extract_structured_financials(
        text=doc_text,
        filename=filename,
        llm_router=llm,
        provider=req.provider,
        model=req.model
    )
    
    return {
        "status": "success",
        "extracted_data": extracted_data.model_dump()
    }

@app.post("/api/financial-os/forecast", tags=["Financial OS"])
async def run_financial_os_forecast(
    req: ForecastRequest,
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.driver_engine.engine import DriverForecastingEngine
    from backend.driver_engine.scenario import ScenarioDependencyGraph
    
    store = FinancialLedgerStore()
    forecaster = DriverForecastingEngine(store)
    graph = ScenarioDependencyGraph(store, forecaster)
    
    # Evaluate scenario with cascading rules
    sc_res = graph.evaluate_scenario(req.scenario, req.starting_cash)
    
    # Map back to old response shape so that existing frontend works flawlessly!
    res_metrics = sc_res["metrics"]
    return {
        "forecast_30d": res_metrics["forecast_30d"],
        "forecast_60d": res_metrics["forecast_60d"],
        "forecast_90d": res_metrics["forecast_90d"],
        "forecast_180d": res_metrics["forecast_180d"],
        "scenario": sc_res["scenario"],
        "drivers": sc_res["simulated_drivers"],
        "covenant_audits": sc_res["covenant_audits"],
        "liquidity_status": sc_res["liquidity_status"],
        "lineage": sc_res["lineage"]
    }

@app.post("/api/financial-os/intelligence", tags=["Financial OS"])
async def run_financial_os_intelligence(
    req: IntelligenceRequest,
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.driver_engine.engine import DriverForecastingEngine
    from backend.driver_engine.scenario import ScenarioDependencyGraph
    from backend.question_engine.engine import BoardGradeReportingEngine, ForensicManagementQuestionEngine
    
    store = FinancialLedgerStore()
    forecaster = DriverForecastingEngine(store)
    graph = ScenarioDependencyGraph(store, forecaster)
    reporter = BoardGradeReportingEngine(store, graph)
    question_eng = ForensicManagementQuestionEngine(store)
    
    # Compile a Board-grade pack
    pack = reporter.compile_board_report("base", req.starting_cash)
    questions = question_eng.generate_management_questions(pack)
    
    # Mock some baseline risks to match old shape
    from backend.intelligence.engine import FinancialRisk
    risks = [
        FinancialRisk(
            title="Sponsorship Delay Exposure",
            severity="critical" if req.burn_rate_monthly > 1500000 else "medium",
            description="Collections extension delays represent high working capital cash-out risks.",
            mitigation_action="Implement invoice factoring and enforce 30-day strict terms on sponsors."
        ),
        FinancialRisk(
            title="Department Budget Overruns",
            severity="high",
            description="Departmental expenses exceed allocated caps under high inflation variables.",
            mitigation_action="Enforce strict variance accountability locks on department managers."
        )
    ]
    
    return {
        "risks": [r.model_dump() for r in risks],
        "questions": questions,
        "narratives": pack["narratives"],
        "supporting_references": pack["supporting_references"],
        "confidence_level": pack["confidence_level"]
    }

@app.post("/api/financial-os/governance", tags=["Financial OS"])
async def run_financial_os_governance(
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.fpa_agents.agents import TreasuryAgent, CovenantAgent, VendorAgent
    
    store = FinancialLedgerStore()
    treasury = TreasuryAgent(store)
    covenant = CovenantAgent(store)
    vendor = VendorAgent(store)
    
    # Run active audits
    treas_res = treasury.run_audit(5000000.0)
    cov_res = covenant.run_audit()
    vend_res = vendor.run_audit()
    
    # Map back to old shape so the UI functions seamlessly
    from backend.governance.engine import GovernanceEngine
    approvals = GovernanceEngine.get_mock_approvals()
    departments = GovernanceEngine.get_mock_departments()
    
    return {
        "approvals": [a.model_dump() for a in approvals],
        "departments": [d.model_dump() for d in departments],
        "vendor_risk_summary": {
            "total_spend": sum(store.expenses[e].actual_spend for e in store.expenses),
            "concentration_risk": "HIGH" if len(vend_res["warnings"]) > 0 else "NOMINAL",
            "warnings": vend_res["warnings"]
        },
        "treasury_audits": treas_res,
        "covenant_audits": cov_res
    }

@app.post("/api/financial-os/export/excel", tags=["Financial OS"])
async def export_financial_os_excel(
    req: ExportExcelRequest,
    user: User = Depends(require_auth)
):
    from backend.fpa_core.workbook_generator import generate_fpa_workbook
    
    # Generate linked, formula-ready professional workbook
    excel_io = generate_fpa_workbook(
        starting_cash=req.starting_cash,
        attendance_rate=0.95,
        ticket_pricing=1.0,
        sponsorship_delay=0,
        payroll_growth=0.0,
        inflation=0.03,
        interest_rate=0.05
    )
    
    return StreamingResponse(
        excel_io,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Interactive_FPandA_Model.xlsx"}
    )

@app.post("/api/financial-os/export/pptx", tags=["Financial OS"])
async def export_financial_os_pptx(
    req: ExportPptxRequest,
    user: User = Depends(require_auth)
):
    from backend.financial_engine.ppt_excel_generator import ExportGenerator
    from backend.intelligence.engine import FinancialRisk
    
    risks_parsed = [FinancialRisk(**r) for r in req.risks]
    
    pptx_bytes = ExportGenerator.generate_pptx_deck(
        title_text=req.title_text,
        board_summary=req.board_summary,
        risks=risks_parsed,
        forecast_data={}
    )
    
    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": "attachment; filename=CFO_Board_Report.pptx"}
    )

@app.post("/api/financial-os/reconciliation", tags=["Financial OS"])
async def run_financial_os_reconciliation(
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.reconciliation.engine import ReconciliationEngine
    
    store = FinancialLedgerStore()
    engine = ReconciliationEngine(store)
    return engine.run_reconciliation()

@app.post("/api/financial-os/executive-reports", tags=["Financial OS"])
async def run_financial_os_executive_reports(
    req: IntelligenceRequest,
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.reconciliation.engine import ReconciliationEngine
    from backend.executive_reporting.templates import ExecutiveReportCompiler
    
    store = FinancialLedgerStore()
    recon_engine = ReconciliationEngine(store)
    recon_res = recon_engine.run_reconciliation()
    
    compiler = ExecutiveReportCompiler(store, recon_res)
    
    # Calculate some simulated metrics
    starting_cash = req.starting_cash
    ending_cash = starting_cash + 15000000.0 - 28000000.0
    burn_rate = 1200000.0
    runway_days = int((starting_cash / burn_rate) * 30.0)
    ebitda = 15000000.0 - 28000000.0
    
    return {
        "board_report": compiler.generate_board_report(starting_cash, ending_cash, burn_rate, runway_days, ebitda),
        "lender_package": compiler.generate_lender_report(0.05),
        "investor_briefing": compiler.generate_investor_report(),
        "emergency_liquidity": compiler.generate_emergency_liquidity_report(starting_cash, burn_rate),
        "treasury_briefing": compiler.generate_treasury_report()
    }

@app.post("/api/financial-os/automation", tags=["Financial OS"])
async def run_financial_os_automation(
    req: ForecastRequest,
    user: User = Depends(require_auth)
):
    from backend.fpa_core.persistence import FinancialLedgerStore
    from backend.reconciliation.engine import ReconciliationEngine
    from backend.driver_engine.engine import DriverForecastingEngine
    from backend.automation.scheduler import ScheduledWorkflowEngine
    
    store = FinancialLedgerStore()
    recon_engine = ReconciliationEngine(store)
    forecaster = DriverForecastingEngine(store)
    
    scheduler = ScheduledWorkflowEngine(store, recon_engine, forecaster)
    
    # Execute a monthly continuous recurring check
    res = scheduler.execute_recurring_workflow(req.scenario, req.starting_cash)
    return res

@app.post("/api/financial-os/governance-audit", tags=["Financial OS"])
async def run_financial_os_governance_audit(
    user: User = Depends(require_auth)
):
    from backend.approval_system.governance import ApprovalLifecycleTracker, DepartmentReviewCycle, WorkflowGovernanceLogger
    
    tracker = ApprovalLifecycleTracker()
    reviews = DepartmentReviewCycle()
    logger = WorkflowGovernanceLogger()
    
    # Seed a simulated model override log for auditing
    logger.log_governance_event(
        event_type="model_override",
        actor=user.username,
        description="Applied a 10% tactical first-team squad payroll reduction.",
        details={"payroll_growth_index_old": 0.0, "payroll_growth_index_new": -0.10}
    )
    
    return {
        "approvals": tracker.registry,
        "department_reviews": reviews.get_department_reviews(),
        "governance_logs": logger.get_governance_logs()
    }

