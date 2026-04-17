"""
Metrics Service – tracks job telemetry, failure rates, and latencies.
Uses Redis for fast atomic increments and distribution compatibility.
"""

import time
import logging
from typing import Any, Dict, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class MetricsService:
    """
    Handles recording and retrieving system-wide observability metrics.
    """
    
    def __init__(self) -> None:
        self._redis: Any = None
        self._enabled = settings.metrics_enabled
        if self._enabled:
            self._try_connect_redis()

    def _try_connect_redis(self) -> None:
        """Attempt to connect to Redis for metrics storage."""
        try:
            import redis
            # Using same Redis DB for metrics to keep it simple, or could use settings.redis_url
            client = redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            logger.info("MetricsService: Redis connected.")
        except Exception as e:
            logger.warning("MetricsService: Redis unavailable (%s). Metrics will be local-only.", e)

    def record_job_start(self, job_type: str) -> None:
        if not self._enabled or not self._redis: return
        try:
            self._redis.hincrby("metrics:jobs:active", job_type, 1)
            self._redis.incr("metrics:jobs:total_started")
        except: pass

    def record_job_completion(self, job_type: str, duration: float, success: bool = True) -> None:
        if not self._enabled or not self._redis: return
        try:
            # Atomic counters
            self._redis.hincrby("metrics:jobs:active", job_type, -1)
            key = "metrics:jobs:success" if success else "metrics:jobs:failed"
            self._redis.hincrby(key, job_type, 1)
            
            # Record latency (keep it simple: rolling average or just list of last 100)
            if success:
                self._redis.lpush(f"metrics:latency:{job_type}", round(duration, 3))
                self._redis.ltrim(f"metrics:latency:{job_type}", 0, 99)
        except: pass

    def get_system_metrics(self) -> Dict[str, Any]:
        """Fetch all recorded metrics for the dashboard."""
        if not self._redis:
            return {"status": "metrics_unavailable", "reason": "Redis disconnected"}
            
        try:
            active = self._redis.hgetall("metrics:jobs:active")
            success = self._redis.hgetall("metrics:jobs:success")
            failed = self._redis.hgetall("metrics:jobs:failed")
            
            # Calculate avg latencies
            latencies = {}
            for key in ["financial_extraction"]: # expandable
                l_list = self._redis.lrange(f"metrics:latency:{key}", 0, -1)
                if l_list:
                    l_floats = [float(x) for x in l_list]
                    latencies[key] = sum(l_floats) / len(l_floats)
                else:
                    latencies[key] = 0.0

            return {
                "active_jobs": {k: int(v) for k, v in active.items()},
                "success_total": {k: int(v) for k, v in success.items()},
                "failed_total": {k: int(v) for k, v in failed.items()},
                "avg_latencies_sec": latencies,
                "uptime_check": "ok"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Global instance
metrics_service = MetricsService()
