from __future__ import annotations

from backend.core.config import get_settings
from backend.services.email.base import EmailClient
from backend.services.email.log import LogEmailClient
from backend.services.email.types import EmailSendResult


class DevSafeEmailClient:
    """In dev/staging, only sends real emails to the allowed domain; others go to LogEmailClient."""

    def __init__(self, inner: EmailClient, allowed_domain: str, fallback: LogEmailClient) -> None:
        self._inner = inner
        self._domain = allowed_domain.lower().lstrip("@")
        self._fallback = fallback

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> EmailSendResult:
        recipient_domain = to.split("@")[-1].lower() if "@" in to else ""
        target = self._inner if recipient_domain == self._domain else self._fallback
        return await target.send(to, subject, html, text, tags=tags, template_id=template_id)


def get_email_client() -> EmailClient:
    settings = get_settings()
    if settings.EMAIL_PROVIDER == "resend":
        from backend.services.email.resend import ResendEmailClient

        api_key = settings.RESEND_API_KEY.get_secret_value()  # type: ignore[union-attr]
        client: EmailClient = ResendEmailClient(
            api_key=api_key,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
            reply_to=settings.EMAIL_REPLY_TO,
        )
        if settings.is_dev and settings.EMAIL_DEV_ALLOWED_DOMAIN:
            return DevSafeEmailClient(client, settings.EMAIL_DEV_ALLOWED_DOMAIN, LogEmailClient())
        return client
    return LogEmailClient()
