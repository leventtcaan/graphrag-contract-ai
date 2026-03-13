"""
User ORM Modeli

Sisteme giriş yapacak kullanıcıları temsil eden bu model; her kullanıcı
bir tenant'a bağlı. Şifreyi düz metin olarak saklamak yerine hash'ini tutuyorum
— bu temel bir güvenlik zorunluluğu, seçenek değil.
"""

import uuid

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """
    Kullanıcı tablosu. Her kullanıcı zorunlu olarak bir tenant'a ait.

    is_superuser: Tenant'a bağlı olmaksızın sistem genelinde yetkili admin.
    Şimdilik basit tutuyorum; ilerleyen sprint'lerde RBAC (Role Based Access Control)
    eklenecek — örneğin tenant admin, analyst, viewer rolleri.
    """
    __tablename__ = "users"

    # ─── Kimlik Bilgileri ─────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Giriş için kullanılan e-posta; sistem genelinde benzersiz",
    )

    # Şifreyi asla düz metin saklamıyorum — bu alan her zaman bcrypt hash değerini tutuyor.
    # "hashed_password" adı bilerek seçildi: ileride kodu okuyan birinin yanılmasını engeller.
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt ile hash'lenmiş şifre — asla düz metin değil",
    )

    # ─── Durum Bayrakları ─────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False ise kullanıcı giriş yapamaz; soft delete gibi kullanılabilir",
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True ise tenant sınırı olmadan tüm sisteme erişebilir",
    )

    # ─── Tenant İlişkisi (Foreign Key) ───────────────────────────────────────
    # Her kullanıcı bir şirkete ait olmak zorunda — izolasyon garantisi burada başlıyor.
    # ondelete="RESTRICT": Tenant silinmeden önce tüm kullanıcıların silinmesi gerekiyor.
    # Bu kasıtlı bir kısıtlama — şirket kaydını yanlışlıkla silip tüm kullanıcıları
    # yetim bırakmak istemiyorum.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Kullanıcının ait olduğu şirket (tenant)",
    )

    # ─── İlişkiler ────────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Tenant",
        back_populates="users",
        lazy="noload",
    )

    # Yüklediği sözleşmeler — bir kullanıcı birden fazla sözleşme yükleyebilir
    uploaded_contracts: Mapped[list["Contract"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contract",
        back_populates="uploader",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} tenant_id={self.tenant_id}>"
