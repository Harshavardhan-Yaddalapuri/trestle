from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RenderedEmail:
    subject: str
    html: str
    text: str


def render_email(template_name: str, context: dict) -> RenderedEmail:
    if template_name == "magic_link":
        from backend.services.email.templates.magic_link import render
    elif template_name == "deadline_reminder":
        from backend.services.email.templates.deadline import render
    elif template_name == "new_grant_match":
        from backend.services.email.templates.new_grant import render
    elif template_name == "check_in":
        from backend.services.email.templates.checkin import render
    else:
        raise ValueError(f"Unknown email template: {template_name!r}")
    return render(context)
