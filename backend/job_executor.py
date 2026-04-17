"""
Job Executor – abstract dispatch layer for asynchronous tasks.
Allows switching from FastAPI BackgroundTasks to Celery with a single setting.
"""

import logging
from typing import Any, Callable, Dict, Optional
from fastapi import BackgroundTasks
from config.settings import settings

logger = logging.getLogger(__name__)

class JobExecutor:
    """
    Orchestrates the dispatching of long-running tasks.
    """
    
    @staticmethod
    def dispatch(
        func: Callable,
        args: tuple = (),
        kwargs: dict = {},
        background_tasks: Optional[BackgroundTasks] = None,
        job_id: Optional[str] = None
    ) -> str:
        """
        Dispatch a task. Uses Celery if use_celery=True, otherwise uses FastAPI BackgroundTasks.
        
        Parameters
        ----------
        func : Callable
            The task function to execute.
        args : tuple
            Positional arguments for the function.
        kwargs : dict
            Keyword arguments for the function.
        background_tasks : BackgroundTasks, optional
            The FastAPI background tasks object (required if not using Celery).
        job_id : str, optional
            User-provided job ID (will be returned if present).
            
        Returns
        -------
        str
            The job ID or task ID.
        """
        if settings.use_celery:
            # Future: return dispatch_celery(func, args, kwargs)
            logger.info("Dispatching task via Celery (Placeholder logic)")
            # For now, if someone tries to use Celery but it's not fully wired, 
            # we log and fallback or error depending on desired strictness.
            # In Phase 3, we will add the real .delay() call here.
            pass

        # Default fallback: FastAPI BackgroundTasks
        if background_tasks:
            logger.info("Dispatching task via FastAPI BackgroundTasks: %s", func.__name__)
            background_tasks.add_task(func, *args, **kwargs)
            return job_id or "async-bg-task"
            
        # Synchronous fallback (mainly for local testing or if background_tasks is missing)
        logger.warning("No background_tasks object provided; executing %s synchronously.", func.__name__)
        import asyncio
        if asyncio.iscoroutinefunction(func):
            # This is a bit risky in a sync call, but helps with abstraction
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(func(*args, **kwargs))
            else:
                asyncio.run(func(*args, **kwargs))
        else:
            func(*args, **kwargs)
            
        return job_id or "sync-execution"

# Global singleton
job_executor = JobExecutor()
