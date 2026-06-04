"""Token generation and hashing for auth flows.

Only hashes are persisted — raw tokens live only in transit (cookie / email link).
"""
from __future__ import annotations

import hashlib
import secrets


def generate_magic_link_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Only hash is stored."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def generate_session_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Raw token goes in the cookie; hash in DB."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_ip(ip: str, pepper: str) -> str:
    return hashlib.sha256((ip + pepper).encode()).hexdigest()
