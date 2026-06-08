from backend.services.email.base import EmailClient
from backend.services.email.log import LogEmailClient
from backend.services.email.types import EmailSendResult


def build_unsubscribe_url(settings, user, kind: str) -> str:
    token = user.alert_unsubscribe_token or ""
    return f"{settings.AUTH_BASE_URL}{settings.EMAIL_UNSUBSCRIBE_PATH}?token={token}&kind={kind}"


__all__ = ["EmailClient", "EmailSendResult", "LogEmailClient", "build_unsubscribe_url"]
