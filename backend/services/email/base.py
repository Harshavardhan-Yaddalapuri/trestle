from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.services.email.types import EmailSendResult


@runtime_checkable
class EmailClient(Protocol):
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> EmailSendResult: ...
