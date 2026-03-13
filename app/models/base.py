"""
SQLAlchemy Declarative Base

Tüm ORM modellerimin türeyeceği tek Base sınıfını burada tanımladım.
Ayrıca zaman damgaları gibi her tabloda tekrarlanan ortak sütunları
bir mixin ile tek yerden yönetiyorum — DRY prensibini burada da uyguluyorum.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Tüm modellerimin atası olan bu Base sınıfını oluşturdum.
    DeclarativeBase kullanmak, SQLAlchemy 2.0'ın modern type-annotated
    mapping stilini getiriyor; Mapped[] ve mapped_column() ile tip güvenli
    sütun tanımları yapabiliyorum.
    """
    pass


class TimestampMixin:
    """
    Her tabloya created_at ve updated_at eklemek için bu mixin'i oluşturdum.
    server_default ile değerleri veritabanına bırakıyorum — uygulama katmanından
    bağımsız olarak doğru zaman damgaları alıyorum.
    onupdate ile güncelleme zamanını otomatik yönetiyorum.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """
    Birincil anahtar olarak UUID kullanmayı tercih ettim.
    Sıralı integer ID'lerin aksine UUID'ler tahmin edilemez — bu B2B SaaS
    için önemli bir güvenlik katmanı. Ayrıca dağıtık sistemlerde çakışma riski yok.
    PostgreSQL'in native UUID tipiyle saklıyorum, string olarak değil.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
