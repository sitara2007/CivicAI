"""LLM service boundary used by the document pipeline."""

from __future__ import annotations

import instructor
from openai import OpenAI

from app.core.config import get_settings
from app.schemas.process import DecisionOutput
from app.services.llm.prompts import build_classification_messages
from app.services.mock_classifier import classify_mock


class AgenticHopExhausted(Exception):
    """Raised when an agentic classification loop exceeds its hop budget."""

    def __init__(self, hop_count: int) -> None:
        super().__init__("Agentic classification hop limit exceeded")
        self.hop_count = hop_count


class LLMService:
    """Classification facade; replace internals without touching the pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    def classify(
        self, redacted_text: str, policy_context: str = ""
    ) -> tuple[DecisionOutput, int]:
        if self._settings.use_mock_llm:
            return classify_mock(redacted_text), 1

        if self._client is None:
            # TOP-1 FIX: Patch the OpenAI client with Instructor for Groq
            self._client = instructor.from_openai(
                OpenAI(
                    api_key=self._settings.openai_api_key,
                    base_url="https://api.groq.com/openai/v1",
                )
            )

        # TOP-1 FIX: Force the LLM to return the exact Pydantic model.
        decision = self._client.chat.completions.create(
            model=self._settings.openai_model,
            messages=build_classification_messages(
                redacted_text=redacted_text,
                policy_context=policy_context,
            ),
            response_model=DecisionOutput,
            max_retries=3,
        )

        return decision, 1
