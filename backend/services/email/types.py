from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmailSendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
