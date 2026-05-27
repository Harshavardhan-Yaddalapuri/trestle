"""initial empty revision

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-26

"""
from __future__ import annotations

from typing import Sequence, Union


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
