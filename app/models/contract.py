"""
Contract ORM Modeli

Sözleşme metadata'sını PostgreSQL'de saklayan tablo tanımı.
Ham metin ve dosya içeriği burada değil — bunlar ileride ayrı bir
blob/storage katmanında (S3 veya benzeri) tutulacak. Burada sadece
metadata, durum bilgisi ve grafik veritabanıyla bağlantı referansı var.
"""

import enum
import uuid

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ContractStatus(str, enum.Enum):
    """
    Bir sözleşmenin yaşam döngüsündeki durumları burada modelliyorum.
    str mixin'ini ekledim çünkü JSON serileştirmede enum değeri yerine
    string değerini görmeyi tercih ediyorum.
    """
    UPLOADED = "uploaded"       # Henüz işlenmedi, sadece yüklendi
    PROCESSING = "processing"   # AI pipeline analiz ediyor
    ANALYZED = "analyzed"       # Analiz tamamlandı, sonuçlar hazır
    FAILED = "failed"           # İşleme sırasında hata oluştu
    ARCHIVED = "archived"       # Kullanıcı arşivledi


class Contract(UUIDMixin, TimestampMixin, Base):
    """
    Sözleşme tablosu. Her satır bir sözleşme belgesini temsil ediyor.

    İlişkiler (ilerleyen sprint'lerde eklenecek):
    - User: Bu sözleşmeyi kimin yüklediği
    - Tenant: Hangi şirkete ait olduğu
    - Neo4j'deki karşılığı: neo4j_node_id ile eşleşiyor
    """
    __tablename__ = "contracts"

    # ─── Temel Bilgiler ───────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Sözleşmenin başlığı veya dosya adı",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Sözleşme hakkında isteğe bağlı açıklama",
    )

    # ─── Durum Yönetimi ───────────────────────────────────────────────────────
    # SAEnum ile PostgreSQL'de native enum tipi oluşturuyorum.
    # Bu hem veri bütünlüğünü sağlıyor hem de ORM sorgularında tip güvenliği veriyor.
    status: Mapped[ContractStatus] = mapped_column(
        # values_callable: SQLAlchemy enum adını (UPLOADED) değil değerini (uploaded)
        # PostgreSQL'e yazar. DB'deki contract_status_enum küçük harfli tanımlandı.
        SAEnum(
            ContractStatus,
            name="contract_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ContractStatus.UPLOADED,
        comment="Sözleşmenin mevcut işlem durumu",
    )

    # ─── Dosya Referansı ──────────────────────────────────────────────────────
    # Dosyanın kendisini burada saklamıyorum — sadece nerede olduğunu tutuyorum.
    # Bu sayede PostgreSQL'i binary dosyalarla şişirmiyorum.
    file_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Depolama sistemindeki dosya yolu (S3 key veya lokal path)",
    )

    original_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Kullanıcının yüklediği orijinal dosya adı",
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Dosya boyutu (byte cinsinden)",
    )

    # ─── Neo4j Köprüsü ────────────────────────────────────────────────────────
    # Bu sözleşmenin Neo4j grafik veritabanındaki düğüm ID'sini burada tutuyorum.
    # Bu sayede PostgreSQL metadata'sından grafik düğümüne hızlıca atlayabiliyorum.
    neo4j_node_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Neo4j'deki ilgili Contract düğümünün elementId'si",
    )

    # ─── Tenant İlişkisi (Multi-Tenancy) ─────────────────────────────────────
    # Hangi şirkete ait olduğu — bu alan veri izolasyonunun temelidir.
    # Sorgularda her zaman tenant_id filtresi eklenmeli; aksi halde
    # bir kiracı başka kiracının sözleşmesini görebilir.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Bu sözleşmenin ait olduğu şirket (tenant)",
    )

    # ─── Yükleyen Kullanıcı ───────────────────────────────────────────────────
    # Kimin yüklediğini audit trail için tutuyorum.
    # SET NULL: Kullanıcı silinirse sözleşme yetim kalmıyor, sadece uploader_id NULL oluyor.
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sözleşmeyi yükleyen kullanıcı (silinirse NULL)",
    )

    # ─── İlişkiler ────────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Tenant",
        back_populates="contracts",
        lazy="noload",
    )
    uploader: Mapped["User | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="uploaded_contracts",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} title={self.title!r} status={self.status}>"
