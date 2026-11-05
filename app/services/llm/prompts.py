"""Prompt builders for LLM-backed document decisions."""

from __future__ import annotations


def build_classification_messages(
    redacted_text: str, policy_context: str = ""
) -> list[dict[str, str]]:
    context = policy_context.strip() or "No relevant policy context was retrieved."
    return [
        {
            "role": "system",
            "content": (
                "You classify government intake documents. Return only valid JSON with "
                "category, priority, department, confidence, decision_rationale, and summary. "
                "Use the supplied policy context to improve routing, but do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": (
                "Relevant policy context:\n"
                f"{context}\n\n"
                "Document to classify:\n"
                f"{redacted_text}"
            ),
        },
    ]
