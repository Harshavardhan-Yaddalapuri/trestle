"""Multi-provider LLM client with fallback chain and circuit breaker.

Implements the LLMClient protocol so it can be used anywhere a single client
is expected. On any call, it tries the primary provider first; if that fails
(and the circuit breaker allows), it walks through the fallback chain.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from backend.core.config import get_settings
from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.services.llm.base import LLMClient
from backend.services.llm.circuit import CircuitBreaker, CircuitOpenError
from backend.services.llm.deepseek import DeepseekClient
from backend.services.llm.gemini import GeminiClient
from backend.services.llm.nvidia import NvidiaClient
from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk

logger = get_logger(__name__)

_PROVIDER_MAP: dict[str, type] = {
    "deepseek": DeepseekClient,
    "gemini": GeminiClient,
    "nvidia": NvidiaClient,
}


class MultiProviderClient:
    """Wraps a primary + ordered fallback list of LLM clients.

    Each provider gets its own circuit breaker. If the primary's circuit is
    open, we skip straight to the next available provider.
    """

    def __init__(
        self,
        *,
        primary: LLMClient,
        fallbacks: list[LLMClient],
        primary_name: str = "primary",
        fallback_names: list[str] | None = None,
    ) -> None:
        self._primary = primary
        self._fallbacks = fallbacks
        self._primary_name = primary_name
        self._fallback_names = fallback_names or [f"fallback_{i}" for i in range(len(fallbacks))]

        # Circuit breaker per provider (primary + each fallback)
        all_names = [self._primary_name, *self._fallback_names]
        self._circuits: dict[str, CircuitBreaker] = {
            name: CircuitBreaker(name=name) for name in all_names
        }

    def _circuit(self, name: str) -> CircuitBreaker:
        return self._circuits[name]

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        errors: list[UpstreamError] = []

        providers = [(self._primary_name, self._primary), *zip(self._fallback_names, self._fallbacks)]

        for name, client in providers:
            circuit = self._circuit(name)
            if not circuit.can_call():
                errors.append(CircuitOpenError(name))
                continue

            try:
                result = await client.complete(
                    messages,
                    tools=tools,
                    response_format=response_format,
                    **kwargs,
                )
            except UpstreamError as exc:
                logger.warning(
                    "llm_provider_failed",
                    provider=name,
                    code=exc.code,
                    detail=exc.detail,
                )
                circuit.record_failure()
                errors.append(exc)
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("llm_provider_unexpected_error", provider=name)
                wrapped = UpstreamError(f"{name} unexpected error: {exc}", code="upstream_error")
                circuit.record_failure()
                errors.append(wrapped)
                continue

            circuit.record_success()
            logger.info("llm_provider_success", provider=name)
            return result

        # All providers exhausted.
        raise UpstreamError(
            f"All LLM providers failed: {[e.detail for e in errors]}",
            code="all_providers_failed",
            extra={"errors": [{"provider": n, "detail": e.detail, "code": e.code} for n, e in zip([p[0] for p in providers], errors)]},
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream through the first available provider.

        If a provider fails mid-stream we cannot safely swap providers because
        the caller may already have yielded partial tokens. We therefore fail
        hard with an UpstreamError and let the caller (orchestrator) decide
        whether to retry the whole turn.
        """
        errors: list[UpstreamError] = []

        providers = [(self._primary_name, self._primary), *zip(self._fallback_names, self._fallbacks)]

        for name, client in providers:
            circuit = self._circuit(name)
            if not circuit.can_call():
                errors.append(CircuitOpenError(name))
                continue

            try:
                # Initiate the stream.
                stream_iter = await client.stream(messages, **kwargs)
            except UpstreamError as exc:
                logger.warning(
                    "llm_provider_stream_init_failed",
                    provider=name,
                    code=exc.code,
                    detail=exc.detail,
                )
                circuit.record_failure()
                errors.append(exc)
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("llm_provider_stream_init_error", provider=name)
                wrapped = UpstreamError(f"{name} unexpected error: {exc}", code="upstream_error")
                circuit.record_failure()
                errors.append(wrapped)
                continue

            # Stream proxy that records success only if we yield at least one
            # non-error chunk.
            async def _wrapped_stream(
                inner: AsyncIterator[LLMStreamChunk],
                provider_name: str,
            ) -> AsyncIterator[LLMStreamChunk]:
                got_any = False
                try:
                    async for chunk in inner:
                        got_any = True
                        yield chunk
                except UpstreamError:
                    # Mid-stream failure — we don't record success.
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.exception("llm_provider_stream_error", provider=provider_name)
                    raise UpstreamError(
                        f"{provider_name} stream error: {exc}",
                        code="upstream_error",
                    ) from exc
                finally:
                    if got_any:
                        self._circuit(provider_name).record_success()
                    else:
                        self._circuit(provider_name).record_failure()

            return _wrapped_stream(stream_iter, name)

        raise UpstreamError(
            f"All LLM providers failed: {[e.detail for e in errors]}",
            code="all_providers_failed",
            extra={"errors": [{"provider": n, "detail": e.detail, "code": e.code} for n, e in zip([p[0] for p in providers], errors)]},
        )


def build_multi_provider_client() -> MultiProviderClient:
    """Build a MultiProviderClient from settings.

    Reads LLM_PRIMARY and LLM_FALLBACKS to determine the chain.
    Only instantiates clients whose API keys are non-empty.
    """
    settings = get_settings()
    primary_name = settings.LLM_PRIMARY.lower()

    # Build primary if key available.
    primary: LLMClient | None = None
    if primary_name == "deepseek":
        if settings.DEEPSEEK_API_KEY.get_secret_value():
            primary = DeepseekClient()
    elif primary_name == "gemini":
        if settings.GEMINI_API_KEY.get_secret_value():
            primary = GeminiClient()
    elif primary_name == "nvidia":
        if settings.NVIDIA_API_KEY.get_secret_value():
            primary = NvidiaClient()

    if primary is None:
        raise UpstreamError(
            f"Primary LLM provider '{primary_name}' is not configured (missing API key).",
            code="provider_not_configured",
        )

    # Build fallbacks in order.
    fallbacks: list[LLMClient] = []
    fallback_names: list[str] = []
    for fb_name in settings.llm_fallback_list:
        fb = fb_name.lower()
        if fb == "deepseek":
            if settings.DEEPSEEK_API_KEY.get_secret_value():
                fallbacks.append(DeepseekClient())
                fallback_names.append("deepseek")
        elif fb == "gemini":
            if settings.GEMINI_API_KEY.get_secret_value():
                fallbacks.append(GeminiClient())
                fallback_names.append("gemini")
        elif fb == "nvidia":
            if settings.NVIDIA_API_KEY.get_secret_value():
                fallbacks.append(NvidiaClient())
                fallback_names.append("nvidia")

    if not fallbacks:
        logger.warning("no_llm_fallbacks_configured", primary=primary_name)

    return MultiProviderClient(
        primary=primary,
        fallbacks=fallbacks,
        primary_name=primary_name,
        fallback_names=fallback_names,
    )
