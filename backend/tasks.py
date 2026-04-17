"""
Task Runner – decoupled execution logic with monitoring, metrics, and safety.
"""

import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable

from db.database import SessionLocal
from db.models import AnalyticsJob, LLMUsage, FinancialReport, FinancialMetric
from backend.analytics_service import FinancialAnalyticsService
from backend.metrics_service import metrics_service
from config.settings import settings

# Structured logging setup
logger = logging.getLogger("backend.tasks")

def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator-like wrapper for exponential backoff retries."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_err = None
            while attempt < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    last_err = e
                    if attempt >= max_retries:
                        break
                    delay = base_delay * (2 ** attempt)
                    logger.warning("Retrying %s in %.1fs (Attempt %d/%d) due to: %s", 
                                   func.__name__, delay, attempt, max_retries, e)
                    await asyncio.sleep(delay)
            raise last_err
        return wrapper
    return decorator

async def run_financial_extraction(
    job_id: str,
    doc_id: str,
    doc_text: str,
    doc_title: str,
    llm_router: Any,
    overwrite: bool = False
):
    """
    Decoupled task for financial extraction with deep monitoring.
    """
    start_time = time.time()
    db = SessionLocal()
    metrics_service.record_job_start("financial_extraction")
    
    # 1. Update Job Start
    job = db.query(AnalyticsJob).filter(AnalyticsJob.id == job_id).first()
    if job:
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

    logger.info("Starting job %s for document %s", job_id, doc_id, extra={
        "job_id": job_id, "doc_id": doc_id
    })

    try:
        # 2. Execution with internal retry wrap
        @retry_with_backoff(max_retries=3)
        async def do_extract():
            svc = FinancialAnalyticsService(llm_router)
            # Internal logic inside svc already handles timeout 30s
            return await svc.extract_financials(
                doc_id=doc_id, doc_text=doc_text, db=db, 
                doc_title=doc_title, overwrite=overwrite, job_id=job_id
            )

        report_dict = await do_extract()
        
        # 3. Post-Process Monitoring
        end_time = time.time()
        duration = end_time - start_time
        
        if job:
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            job.execution_time = duration
            job.progress = 100
            # Track Usage (mock token counts - API models report usage differently)
            token_data = {"prompt": len(doc_text)//4, "completion": 500}
            job.token_usage = token_data
            job.model_used = settings.financial_extraction_model
            
            # Simple Cost Estimate (e.g. $0 if local, but we track logic)
            job.cost_estimate = 0.0 # Change if using API models
            
            # Record LLM Usage record
            usage = LLMUsage(
                job_id=job_id, model_name=job.model_used,
                prompt_tokens=token_data["prompt"], 
                completion_tokens=token_data["completion"],
                estimated_cost=job.cost_estimate
            )
            db.add(usage)
            db.commit()

        metrics_service.record_job_completion("financial_extraction", duration, success=True)
        logger.info("Job %s completed successfully in %.2fs", job_id, duration)

    except Exception as e:
        logger.exception("Job %s failed after retries: %s", job_id, e)
        duration = time.time() - start_time
        if job:
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.execution_time = duration
            job.error_message = str(e)
            db.commit()
        
        metrics_service.record_job_completion("financial_extraction", duration, success=False)
    
    finally:
        db.close()
