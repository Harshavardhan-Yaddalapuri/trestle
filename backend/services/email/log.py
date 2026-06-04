"""Log-based email client for local development and Step 18 pre-wiring."""
from __future__ import annotations

from backend.core.logging import get_logger
from backend.services.email.types import EmailSendResult

logger = get_logger(__name__)


class LogEmailClient:
    """Writes a structured log instead of sending a real email.

    The magic_link_url field is extracted from the text body (first line
    starting with "http") so developers can copy the link directly.
    """

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> EmailSendResult:
        magic_link_url: str | None = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("http"):
                magic_link_url = stripped
                break

        logger.info(
            "email_would_send",
            to=to,
            subject=subject,
            tags=tags or [],
            template_id=template_id,
            magic_link_url=magic_link_url,
        )
        return EmailSendResult(success=True)
