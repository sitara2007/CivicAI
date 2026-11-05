from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ModelRouter:
    """Handles dynamic model selection with automatic graceful fallback on failure or rate limits."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_response(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Attempt primary model call; fallback to secondary/mock engine on failure."""
        if self.settings.use_mock_llm:
            return {
                "content": "[Mock LLM Response]",
                "provider": "mock",
                "status": "success",
            }

        try:
            return await self._call_primary(prompt, system_prompt)
        except (TimeoutError, ConnectionError, ValueError) as primary_error:
            logger.warning(
                "primary_llm_failed_falling_back",
                extra={"error": str(primary_error)},
            )
            return await self._call_fallback(prompt, system_prompt)

    async def _call_primary(
        self, prompt: str, system_prompt: str | None
    ) -> dict[str, Any]:
        # Placeholder for primary client execution
        return {
            "content": "Primary LLM response output",
            "provider": "primary",
            "status": "success",
        }

    async def _call_fallback(
        self, prompt: str, system_prompt: str | None
    ) -> dict[str, Any]:
        """Graceful fallback mechanism when primary fails or rate limits."""
        logger.info("executing_fallback_model_routing")
        return {
            "content": "Fallback response generated via secondary local/cached mechanism.",
            "provider": "fallback",
            "status": "degraded_success",
        }
