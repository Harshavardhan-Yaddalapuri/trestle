"""Base HTML/text wrapping for all email templates."""
from __future__ import annotations

_BASE_FONT = "font-family:Arial,sans-serif;color:#333333;line-height:1.6;"


def wrap_html(body_html: str, unsubscribe_url: str | None = None) -> str:
    footer = ""
    if unsubscribe_url:
        footer = (
            f'<p style="font-size:12px;color:#999999;margin-top:32px;border-top:1px solid #eeeeee;padding-top:16px;">'
            f'Don\'t want these emails? '
            f'<a href="{unsubscribe_url}" style="color:#999999;">Unsubscribe</a>'
            f"</p>"
        )
    return (
        "<!DOCTYPE html>"
        '<html><body style="margin:0;padding:0;background:#f5f5f5;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;">'
        "<tr><td align=\"center\">"
        '<table width="600" cellpadding="0" cellspacing="0" '
        'style="background:#ffffff;margin:40px auto;border-radius:8px;">'
        f'<tr><td style="padding:40px;{_BASE_FONT}">'
        f"{body_html}"
        f"{footer}"
        "</td></tr>"
        "</table>"
        "</td></tr>"
        "</table>"
        "</body></html>"
    )


def wrap_text(body: str, unsubscribe_url: str | None = None) -> str:
    if unsubscribe_url:
        return f"{body}\n\n---\nTo unsubscribe: {unsubscribe_url}"
    return body
