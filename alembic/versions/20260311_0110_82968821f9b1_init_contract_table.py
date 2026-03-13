"""init_contract_table

Bu migration'ı `app/models/contract.py`'deki Contract modeline bakarak elle yazdım.
Normalde `alembic revision --autogenerate` bu içeriği otomatik üretir;
ama autogenerate canlı bir PostgreSQL bağlantısı gerektiriyor.
Docker kurulup konteynerler ayağa kalktığında `alembic upgrade head` ile
bu tabloyu veritabanına uygulayabilirim.

Revision ID: 82968821f9b1
Revises:
Create Date: 2026-03-11 01:10:44.808789
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers — Alembic bu değerleri migration zincirini kurmak için kullanıyor
revision: str = "82968821f9b1"
down_revision: Union[str, Sequence[str], None] = None  # İlk migration, öncesi yok
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    contracts tablosunu oluşturuyorum.
    Önce ContractStatus enum tipini PostgreSQL'de kayıt ediyorum,
    ardından tabloyu bu enum'a referans verecek şekilde yaratıyorum.
    """
    # ─── contracts Tablosu ────────────────────────────────────────────────────
    # Enum tipi create_type=True (varsayılan) ile op.create_table() tarafından
    # otomatik oluşturulur — ayrıca .create() çağırmak duplicate hatasına yol açar.
    op.create_table(
        "contracts",
        # UUID birincil anahtar — tahmin edilemez, dağıtık sistemlerde çakışmaz
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="Benzersiz sözleşme kimliği (UUID v4)",
        ),
        # Temel bilgiler
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            comment="Sözleşmenin başlığı veya dosya adı",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Sözleşme hakkında isteğe bağlı açıklama",
        ),
        # Durum yönetimi — native enum tipi kullanıyorum
        sa.Column(
            "status",
            sa.Enum(
                "uploaded", "processing", "analyzed", "failed", "archived",
                name="contract_status_enum",
                # create_type=True (default): op.create_table() enum'u otomatik oluşturur
            ),
            nullable=False,
            server_default="uploaded",
            comment="Sözleşmenin mevcut işlem durumu",
        ),
        # Dosya referansı — binary veriyi DB'ye koymak yerine yolu saklıyorum
        sa.Column(
            "file_path",
            sa.String(1000),
            nullable=True,
            comment="Depolama sistemindeki dosya yolu (S3 key veya lokal path)",
        ),
        sa.Column(
            "original_filename",
            sa.String(500),
            nullable=True,
            comment="Kullanıcının yüklediği orijinal dosya adı",
        ),
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=True,
            comment="Dosya boyutu (byte cinsinden)",
        ),
        # Neo4j köprüsü — PostgreSQL kaydından grafik düğümüne atlama için
        sa.Column(
            "neo4j_node_id",
            sa.String(100),
            nullable=True,
            comment="Neo4j'deki ilgili Contract düğümünün elementId'si",
        ),
        # Zaman damgaları — server_default ile DB tarafında yönetiliyorum
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

    # ─── Index'ler ────────────────────────────────────────────────────────────
    # neo4j_node_id üzerinde index — grafik-ilişkisel köprü sorguları için kritik
    op.create_index(
        "ix_contracts_neo4j_node_id",
        "contracts",
        ["neo4j_node_id"],
        unique=False,
    )


def downgrade() -> None:
    """
    contracts tablosunu ve ilgili enum tipini kaldırıyorum.
    Sıra önemli: önce tabloyu, sonra enum'u silmek gerekiyor
    çünkü enum hâlâ kullanımdayken silinemez.
    """
    op.drop_index("ix_contracts_neo4j_node_id", table_name="contracts")
    op.drop_table("contracts")

    # Enum tipini de temizliyorum — orphan tip bırakmak istemiyorum
    contract_status_enum = postgresql.ENUM(name="contract_status_enum")
    contract_status_enum.drop(op.get_bind())
