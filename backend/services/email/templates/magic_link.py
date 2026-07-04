from __future__ import annotations

from backend.services.email.templates import RenderedEmail
from backend.services.email.templates.base import wrap_html, wrap_text

_BTN = 'style="display:inline-block;background:#4f46e5;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;"'


def render(context: dict) -> RenderedEmail:
    magic_url: str = context["magic_url"]
    app_name: str = context.get("app_name", "Trestle")
    ttl_minutes: int = context.get("ttl_minutes", 15)

    subject = f"Sign in to {app_name}"

    body_html = (
        f"<h2>Sign in to {app_name}</h2>"
        f'<p><a href="{magic_url}" {_BTN}>Sign in</a></p>'
        f"<p>Or copy this link into your browser:</p>"
        f'<p style="word-break:break-all;font-size:13px;color:#555555;">{magic_url}</p>'
        f'<p style="color:#999999;font-size:12px;">This link expires in {ttl_minutes} minutes. '
        f"If you didn't request this, you can safely ignore this email.</p>"
    )
    body_text = (
        f"Sign in to {app_name}:\n{magic_url}\n\n"
        f"This link expires in {ttl_minutes} minutes.\n"
        "If you didn't request this, you can safely ignore this email."
    )

    return RenderedEmail(
        subject=subject,
        html=wrap_html(body_html),
        text=wrap_text(body_text),
    )
