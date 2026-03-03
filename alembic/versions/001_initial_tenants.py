"""Initial tenants table

Revision ID: 001
Revises: 
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("subdomain", sa.String(63), nullable=False, unique=True),
        sa.Column("tier", sa.String(20), nullable=False, default="starter"),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("config", sa.JSON, nullable=False, default=dict),
        sa.Column("container_id", sa.String(64), nullable=True),
        sa.Column("gateway_url", sa.String(255), nullable=True),
        sa.Column("gateway_token", sa.Text, nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("provisioned_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tenants")
