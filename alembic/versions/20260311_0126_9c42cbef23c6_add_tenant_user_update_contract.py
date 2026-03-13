"""add_tenant_user_update_contract

Bu migration'ı Faz 5'te eklediğimiz Tenant, User modelleri ve Contract güncellemesine
bakarak elle yazdım. Docker kurulup autogenerate çalıştırılabildiğinde bu dosyanın içeriği
otomatik üretilen versiyonla karşılaştırılmalı; fark varsa otomatik versiyona güvenilmeli.

Değişiklikler:
  - CREATE TABLE tenants
  - CREATE TABLE users  (tenant_id FK → tenants)
  - ALTER TABLE contracts ADD COLUMNS tenant_id, uploader_id

Revision ID: 9c42cbef23c6
Revises: 82968821f9b1
Create Date: 2026-03-11 01:26:34.256731
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "9c42cbef23c6"
down_revision: Union[str, Sequence[str], None] = "82968821f9b1"  # contracts tablosundan sonra
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Önce Tenant, sonra User, sonra Contract güncelleme.
    Sıra önemli: User → Tenant'a FK verir, Contract → her ikisine FK verir.
    """

    # ─── 1. tenants tablosu ───────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="Benzersiz tenant kimliği (UUID v4)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Şirket adı — sistem genelinde benzersiz",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="False ise bu tenant'ın tüm kullanıcıları giriş yapamaz",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # name üzerinde unique index — sistemde aynı şirket adı iki kez olamaz
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=True)

    # ─── 2. users tablosu ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="Benzersiz kullanıcı kimliği (UUID v4)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            comment="Giriş için kullanılan e-posta; sistem genelinde benzersiz",
        ),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=False,
            comment="bcrypt ile hash'lenmiş şifre",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            comment="Kullanıcının ait olduğu şirket",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # email benzersiz ve index'li — login sorgularında kullanılıyor
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    # tenant_id üzerinde index — "bu tenant'ın tüm kullanıcıları" sorgusu için
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)

    # ─── 3. contracts tablosuna FK kolonları ekleme ───────────────────────────
    # Mevcut contracts tablosuna tenant_id ve uploader_id ekliyorum.
    op.add_column(
        "contracts",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Bu sözleşmenin ait olduğu şirket",
        ),
    )
    op.add_column(
        "contracts",
        sa.Column(
            "uploader_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Sözleşmeyi yükleyen kullanıcı (silinirse NULL)",
        ),
    )

    # FK constraint'leri ayrıca ekliyorum
    op.create_foreign_key(
        "fk_contracts_tenant_id",
        "contracts", "tenants",
        ["tenant_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_contracts_uploader_id",
        "contracts", "users",
        ["uploader_id"], ["id"],
        ondelete="SET NULL",
    )

    # Index'ler — sık filtrelenecek kolonlar
    op.create_index("ix_contracts_tenant_id", "contracts", ["tenant_id"], unique=False)
    op.create_index("ix_contracts_uploader_id", "contracts", ["uploader_id"], unique=False)


def downgrade() -> None:
    """
    Değişiklikleri tersine alıyorum. Sıra upgrade'in tersi olmalı:
    Contract kolonları → users → tenants
    """
    # contracts tablosundaki eklentileri geri alıyorum
    op.drop_index("ix_contracts_uploader_id", table_name="contracts")
    op.drop_index("ix_contracts_tenant_id", table_name="contracts")
    op.drop_constraint("fk_contracts_uploader_id", "contracts", type_="foreignkey")
    op.drop_constraint("fk_contracts_tenant_id", "contracts", type_="foreignkey")
    op.drop_column("contracts", "uploader_id")
    op.drop_column("contracts", "tenant_id")

    # users tablosunu kaldırıyorum
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # tenants tablosunu kaldırıyorum
    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")
