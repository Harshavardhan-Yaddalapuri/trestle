"""Registry of all arq job functions."""
from __future__ import annotations

from backend.services.jobs.checkin_alerts import (
    enqueue_checkin_alerts,
    send_checkin_alert,
)
from backend.services.jobs.deadline_alerts import (
    enqueue_deadline_alerts,
    send_deadline_alert,
)
from backend.services.jobs.new_grant_alerts import (
    enqueue_new_grant_alerts,
    send_new_grant_alert,
)

all_functions = [
    enqueue_deadline_alerts,
    send_deadline_alert,
    enqueue_new_grant_alerts,
    send_new_grant_alert,
    enqueue_checkin_alerts,
    send_checkin_alert,
]

__all__ = [
    "all_functions",
    "enqueue_checkin_alerts",
    "enqueue_deadline_alerts",
    "enqueue_new_grant_alerts",
    "send_checkin_alert",
    "send_deadline_alert",
    "send_new_grant_alert",
]
