"""pybreaker circuit breakers — PRD §6: 5 failures, 30s half-open."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import pybreaker
from openai import APIConnectionError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

OPENAI_TRANSIENT = (RateLimitError, APITimeoutError, APIConnectionError)


class _StateChangeListener(pybreaker.CircuitBreakerListener):
    def state_change(
        self,
        breaker: pybreaker.CircuitBreaker,
        old: pybreaker.CircuitBreakerState,
        new: pybreaker.CircuitBreakerState,
    ) -> None:
        logger.warning(
            "circuit_breaker_state_change",
            extra={
                "breaker": breaker.name,
                "old_state": old.name,
                "new_state": new.name,
            },
        )


_listener = _StateChangeListener()

openai_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="openai_api",
    listeners=[_listener],
)

presidio_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    name="presidio_analyze",
    listeners=[_listener],
)


def with_openai_breaker[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return openai_breaker.call(func, *args, **kwargs)

    return wrapper
