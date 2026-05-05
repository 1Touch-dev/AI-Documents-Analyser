"""
Workflow Classifier – uses LLM to map natural language intent to a specific workflow.
"""

import logging
from typing import Optional
from backend.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class WorkflowClassifier:
    """Classifies user intent into workflows."""

    WORKFLOWS = {
        "financial": "Analyze financial data, revenue, expenses, and P&L.",
        "consulting": "Provide strategic insights, risks, and business recommendations.",
        "report": "Generate a comprehensive business performance report.",
        "debt": "Analyze liabilities, interest rates, and refinancing options."
    }

    @staticmethod
    async def classify_intent(
        query: str,
        llm: LLMRouter,
        api_keys: Optional[dict] = None
    ) -> str:
        """Map query to workflow type."""
        prompt = (
            f"You are a workflow router. Map the following user query to one of these workflows:\n"
            f"{json.dumps(WorkflowClassifier.WORKFLOWS, indent=2)}\n\n"
            f"Query: {query}\n\n"
            f"Return ONLY the workflow key (financial, consulting, report, or debt)."
        )

        try:
            import json
            result = await llm.generate(
                model_name="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that routes business analysis requests."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10,
                api_keys=api_keys
            )
            
            intent = result.strip().lower()
            if intent in WorkflowClassifier.WORKFLOWS:
                return intent
            return "consulting" # Default
        except Exception as e:
            logger.warning("Workflow classification failed: %s", e)
            return "consulting"
