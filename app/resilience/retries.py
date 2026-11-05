"""Tenacity retry policies — PRD §7.2 exponential backoff."""

from __future__ import annotations

import logging

from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy.exc import OperationalError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


def _log_retry(retry_state: RetryCallState) -> None:
    fn_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    logger.warning(
        "retry_attempt",
        extra={
            "function": fn_name,
            "attempt": retry_state.attempt_number,
        },
    )


openai_retry = retry(
    retry=retry_if_exception_type(
        (RateLimitError, APITimeoutError, APIConnectionError)
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    before_sleep=_log_retry,
    reraise=True,
)

db_retry = retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=5),
    before_sleep=_log_retry,
    reraise=True,
)
