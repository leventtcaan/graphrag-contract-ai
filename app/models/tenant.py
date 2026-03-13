"""
Tenant ORM Modeli

B2B SaaS mimarisinin temel taşı bu model. Her "tenant" bir müşteri şirketini temsil ediyor.
Tüm veriler (kullanıcılar, sözleşmeler, analizler) bir tenant'a bağlı —
bu izolasyon hem hukuki zorunluluk hem de güven meselesi.
"""

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """
    Müşteri şirketini temsil eden tablo.

    İleride eklenecek alanlar (şimdilik basit tutuyorum):
    - plan: Subscription planı (free, pro, enterprise)
    - max_users: Tenant'ın kullanabileceği maksimum kullanıcı sayısı
    - custom_domain: White-label müşteriler için
    """
    __tablename__ = "tenants"

    # ─── Temel Bilgiler ───────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Şirket adı — sistem genelinde benzersiz olmalı",
    )

    # is_active ile şirketin erişimini tek yerden açıp kapayabiliyorum.
    # Şifre sıfırlama veya ödeme gecikmeleri gibi durumlar için kritik.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False ise bu tenant'ın tüm kullanıcıları giriş yapamaz",
    )

    # ─── İlişkiler ────────────────────────────────────────────────────────────
    # back_populates ile çift yönlü ilişki kuruyorum — hem User'dan hem Tenant'tan erişebiliyorum.
    # lazy="noload" ile N+1 sorgusunu engelliyorum; ilişkiyi yüklemek explicit olmalı.
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="tenant",
        lazy="noload",
    )
    contracts: Mapped[list["Contract"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contract",
        back_populates="tenant",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} active={self.is_active}>"
