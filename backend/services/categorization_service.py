"""
Categorization Service – uses LLM to classify documents into business categories.
"""

import logging
import json
from typing import Optional
from backend.llm_router import LLMRouter
from config.settings import settings

logger = logging.getLogger(__name__)

class CategorizationService:
    """Service to automatically categorize documents."""

    CATEGORIES = [
        "F&B",
        "Ticketing",
        "Retail",
        "Player Sales",
        "Sponsors",
        "Financial",
        "Legal",
        "HR",
        "Operations",
        "Others"
    ]

    @staticmethod
    async def categorize_document(
        text: str,
        filename: str,
        llm: LLMRouter,
        api_keys: Optional[dict] = None
    ) -> str:
        """
        Classify a document based on its content and filename.
        """
        if not text:
            return "Others"

        # Use a small sample of the text for categorization to save tokens
        sample_text = text[:4000]

        prompt = (
            f"You are a document classifier. Classify the following document into ONE of these categories:\n"
            f"{', '.join(CategorizationService.CATEGORIES)}\n\n"
            f"Filename: {filename}\n"
            f"Content Sample: {sample_text}\n\n"
            f"Return ONLY the category name. If unsure, return 'Others'."
        )

        try:
            # Use a fast model for categorization
            category = await llm.generate(
                model_name="gpt-4o-mini", # Fallback to mini for speed/cost
                messages=[
                    {"role": "system", "content": "You are an expert document classifier for a business platform."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10,
                api_keys=api_keys
            )
            
            category = category.strip().strip("'\"")
            if category in CategorizationService.CATEGORIES:
                return category
            
            # Fuzzy match if exact match fails
            for cat in CategorizationService.CATEGORIES:
                if cat.lower() in category.lower():
                    return cat
                    
            return "Others"
        except Exception as e:
            logger.warning("Categorization failed: %s", e)
            return "Others"

    @staticmethod
    def get_category_from_keywords(filename: str, text: str) -> str:
        """Rule-based fallback for categorization."""
        combined = (filename + " " + text[:2000]).lower()
        
        if any(k in combined for k in ["food", "beverage", "catering", "restaurant", "coxa bar"]):
            return "F&B"
        if any(k in combined for k in ["ticket", "bilheteria", "ingresso", "stadium access"]):
            return "Ticketing"
        if any(k in combined for k in ["retail", "loja", "shop", "merchandise", "varejo"]):
            return "Retail"
        if any(k in combined for k in ["player", "athlete", "transfer", "jogador", "atleta"]):
            return "Player Sales"
        if any(k in combined for k in ["sponsor", "patrocínio", "parceria", "partnership"]):
            return "Sponsors"
        if any(k in combined for k in ["finance", "budget", "orçamento", "p&l", "revenue", "expense", "balanço"]):
            return "Financial"
        if any(k in combined for k in ["legal", "contrato", "contract", "judicial", "lawsuit"]):
            return "Legal"
        if any(k in combined for k in ["hr", "rh", "human resources", "salário", "salary", "payroll", "employee"]):
            return "HR"
        if any(k in combined for k in ["ops", "operations", "logistics", "logística", "infrastructure"]):
            return "Operations"
            
        return "Others"
