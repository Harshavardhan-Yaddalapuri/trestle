"""Circuit breaker for LLM providers.

Tracks per-provider failure counts in a rolling window. Opens the circuit when
failures exceed a threshold within the window. After a cooldown, half-opens
(allows a probe). If the probe succeeds, the circuit closes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from backend.core.errors import UpstreamError
from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CircuitState:
    """Immutable-ish snapshot of a circuit's state."""

    name: str
    is_open: bool = False
    failures: int = 0
    last_failure_at: float = 0.0
    opened_at: float = 0.0
    half_open: bool = False
    success_count: int = 0


class CircuitBreaker:
    """Per-provider circuit breaker.

    Parameters:
        name: provider name for logging.
        failure_threshold: number of failures to open the circuit.
        window_seconds: rolling window for counting failures.
        cooldown_seconds: how long the circuit stays open before half-opening.
        half_open_max: max calls allowed while half-open before closing or re-opening.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        window_seconds: float = 60.0,
        cooldown_seconds: float = 120.0,
        half_open_max: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max = half_open_max
        self._state = CircuitState(name=name)
        self._lock: Callable | None = None  # reserved for async lock if needed

    def _now(self) -> float:
        return time.monotonic()

    def state(self) -> CircuitState:
        return self._state

    def record_success(self) -> None:
        s = self._state
        if s.half_open:
            new_success = s.success_count + 1
            if new_success >= self.half_open_max:
                logger.info("circuit_closed", provider=self.name)
                self._state = CircuitState(
                    name=self.name,
                    is_open=False,
                    failures=0,
                    success_count=0,
                    last_failure_at=0.0,
                    opened_at=0.0,
                    half_open=False,
                )
                return
            self._state = CircuitState(
                name=self.name,
                is_open=False,
                failures=s.failures,
                success_count=new_success,
                last_failure_at=s.last_failure_at,
                opened_at=s.opened_at,
                half_open=True,
            )
            return

        # Normal closed state — just reset failures on success.
        if s.failures > 0:
            self._state = CircuitState(
                name=self.name,
                is_open=False,
                failures=0,
                success_count=0,
                last_failure_at=0.0,
                opened_at=0.0,
                half_open=False,
            )

    def record_failure(self) -> None:
        now = self._now()
        s = self._state

        # If already open, check if we should half-open.
        if s.is_open:
            if now - s.opened_at >= self.cooldown_seconds:
                logger.info("circuit_half_open", provider=self.name)
                self._state = CircuitState(
                    name=self.name,
                    is_open=False,
                    failures=0,
                    last_failure_at=now,
                    opened_at=s.opened_at,
                    half_open=True,
                    success_count=0,
                )
            return

        # Expire old failures outside the window.
        if s.last_failure_at and now - s.last_failure_at > self.window_seconds:
            failures = 1
        else:
            failures = s.failures + 1

        if failures >= self.failure_threshold:
            logger.warning(
                "circuit_opened",
                provider=self.name,
                failures=failures,
                threshold=self.failure_threshold,
            )
            self._state = CircuitState(
                name=self.name,
                is_open=True,
                failures=failures,
                last_failure_at=now,
                opened_at=now,
                half_open=False,
                success_count=0,
            )
            return

        self._state = CircuitState(
            name=self.name,
            is_open=False,
            failures=failures,
            last_failure_at=now,
            opened_at=s.opened_at,
            half_open=s.half_open,
            success_count=s.success_count,
        )

    def can_call(self) -> bool:
        s = self._state
        if not s.is_open:
            return True
        now = self._now()
        if now - s.opened_at >= self.cooldown_seconds:
            # Time to half-open — allow one probe.
            return True
        return False


class CircuitOpenError(UpstreamError):
    """Raised when a provider's circuit breaker is open."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Circuit breaker open for {provider}",
            code="circuit_open",
            status_code=503,
        )
