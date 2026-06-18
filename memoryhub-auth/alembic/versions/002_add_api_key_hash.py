"""Add api_key_hash column to oauth_clients.

Supports API-key-based authentication as an alternative to OAuth
client_credentials flow. The column stores a SHA-256 hex digest
of the plaintext key (prefixed ``mh-dev-``).

Revision ID: 002
Revises: 001
Create Date: 2026-06-18
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "oauth_clients", "api_key_hash"):
        op.add_column(
            "oauth_clients",
            sa.Column("api_key_hash", sa.String(64), nullable=True),
        )
        op.create_index(
            "ix_oauth_clients_api_key_hash",
            "oauth_clients",
            ["api_key_hash"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_oauth_clients_api_key_hash", table_name="oauth_clients")
    op.drop_column("oauth_clients", "api_key_hash")


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col)"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.scalar()
