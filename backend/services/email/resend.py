"""Resend email client using direct HTTP for testability with respx."""
from __future__ import annotations

import httpx

from backend.core.errors import UpstreamError
from backend.services.email.types import EmailSendResult

_RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailClient:
    def __init__(
        self,
        api_key: str,
        from_address: str,
        from_name: str,
        reply_to: str | None = None,
    ) -> None:
        self._from = f"{from_name} <{from_address}>"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._reply_to = reply_to

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> EmailSendResult:
        payload: dict = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        if tags:
            payload["tags"] = [{"name": "category", "value": t} for t in tags]
        if self._reply_to:
            payload["reply_to"] = self._reply_to

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(_RESEND_API_URL, json=payload, headers=self._headers)

        if resp.status_code in (200, 201):
            data = resp.json()
            return EmailSendResult(success=True, message_id=data.get("id"))

        if resp.status_code == 401:
            raise UpstreamError("Resend API: invalid credentials", code="invalid_credentials")
        if resp.status_code == 422:
            raise UpstreamError("Resend API: invalid recipient", code="invalid_recipient")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise UpstreamError(
                f"Resend API: rate limited, retry after {retry_after}s",
                code="rate_limited",
            )
        raise UpstreamError(
            f"Resend API: upstream error {resp.status_code}",
            code="upstream_unavailable",
        )
