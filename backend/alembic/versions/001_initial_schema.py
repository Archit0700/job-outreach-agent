"""Initial schema for all SPEC §17 tables.

Revision ID: 001
Revises:
Create Date: 2026-09-18

Note: App also calls Base.metadata.create_all on startup for MVP bootstrap.
This revision documents the intended schema for Alembic-managed environments.
"""
from typing import Sequence, Union

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are created via SQLAlchemy metadata.create_all in app lifespan
    # for portable sqlite/postgres MVP. Run `alembic revision --autogenerate`
    # against a live Postgres to produce dialect-specific DDL if preferred.
    pass


def downgrade() -> None:
    pass
