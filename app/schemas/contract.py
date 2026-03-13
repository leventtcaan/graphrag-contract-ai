"""
Contract Pydantic Şemaları

ORM modelinden (SQLAlchemy) ayrı tuttuğum bu şemalar API'nin "konuştuğu dil".
Her şema farklı bir kullanım senaryosunu temsil ediyor:
  - ContractBase     → Paylaşılan ortak alanlar
  - ContractCreate   → Kullanıcıdan gelen veri (POST body)
  - ContractUpdate   → Kısmi güncelleme (PATCH body — tüm alanlar opsiyonel)
  - ContractResponse → Dışarıya dönen veri (GET cevabı — ID ve tarihler dahil)
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.contract import ContractStatus


# ─── Temel Şema ───────────────────────────────────────────────────────────────
# Ortak alanları burada tanımlıyorum; diğer şemalar bunu miras alıyor.
# Böylece aynı alan tanımını birden fazla yerde tekrar etmiyorum.
class ContractBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Sözleşmenin başlığı veya dosya adı",
        examples=["ACME Corp. - Yazılım Lisans Sözleşmesi 2026"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Sözleşme hakkında isteğe bağlı açıklama",
    )
    original_filename: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Kullanıcının yüklediği orijinal dosya adı",
    )
    file_size_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Dosya boyutu (byte cinsinden)",
    )


# ─── Oluşturma Şeması ─────────────────────────────────────────────────────────
# POST /contracts endpoint'i bu şemayı body olarak alıyor.
# file_path'i kullanıcıdan almıyorum — sunucu tarafında belirleniyor.
# status da kullanıcı seçmiyor; her yeni sözleşme UPLOADED ile başlıyor.
class ContractCreate(ContractBase):
    pass  # Şimdilik ContractBase yeterli; ilerleyen sprint'lerde tenant_id eklenecek


# ─── Güncelleme Şeması ────────────────────────────────────────────────────────
# PATCH endpoint'i için tüm alanları opsiyonel yaptım.
# Sadece gönderilen alanlar güncelleniyor (partial update / merge patch).
# Bu sayede "sadece başlığı değiştir" gibi minimal güncellemeler destekleniyor.
class ContractUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[ContractStatus] = Field(
        default=None,
        description="Sözleşmenin yeni durumu",
    )
    neo4j_node_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Neo4j grafik düğümü bağlandıktan sonra servis tarafından doldurulur",
    )


# ─── Yanıt Şeması ─────────────────────────────────────────────────────────────
# GET endpoint'lerinin döndürdüğü şema. ORM nesnesinden doğrudan dönüştürmek için
# from_attributes=True ayarını yapıyorum — bu Pydantic v2'nin ORM mode'u.
# Eski Pydantic v1'deki orm_mode=True'nun yeni adı bu.
class ContractResponse(ContractBase):
    id: uuid.UUID = Field(description="Benzersiz sözleşme kimliği")
    status: ContractStatus = Field(description="Sözleşmenin mevcut durumu")
    file_path: Optional[str] = Field(default=None)
    neo4j_node_id: Optional[str] = Field(
        default=None,
        description="Neo4j grafik düğümü ID'si (analiz tamamlandıktan sonra dolar)",
    )
    created_at: datetime = Field(description="Oluşturulma zamanı (UTC)")
    updated_at: datetime = Field(description="Son güncellenme zamanı (UTC)")

    # from_attributes=True: SQLAlchemy ORM nesnesini doğrudan bu şemaya dönüştürmemi sağlıyor.
    # Olmadan ContractResponse(contract_orm_obj) yaparken "dict bekleniyor" hatası alırdım.
    model_config = ConfigDict(from_attributes=True)


# ─── Liste Yanıtı ─────────────────────────────────────────────────────────────
# GET /contracts endpoint'inin döndürdüğü sayfalama destekli yapı.
# İleride pagination metadata (toplam kayıt sayısı, sayfa numarası) ekleyeceğim.
class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int = Field(description="Toplam sözleşme sayısı")
    limit: int = Field(description="Bu yanıttaki maksimum kayıt sayısı")
    offset: int = Field(description="Atlatılan kayıt sayısı (sayfalama için)")
