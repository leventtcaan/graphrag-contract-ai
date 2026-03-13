"""
Contract Servis Katmanı

İş mantığını burada tutuyorum — endpoint'ler sadece HTTP işlemlerini yönetmeli,
veritabanı sorgu mantığı bu katmana ait. Bu ayrım sayesinde:
  1. Aynı mantığı hem HTTP endpoint'inden hem de bir Celery görevinden çağırabiliyorum
  2. Servisleri FastAPI'den bağımsız test edebiliyorum
  3. Karmaşık sorgular büyüdükçe endpoint dosyası şişmiyor
"""

import uuid
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractStatus
from app.schemas.contract import ContractCreate, ContractUpdate


class ContractService:
    """
    Sözleşme CRUD operasyonlarını kapsayan servis sınıfı.

    Her metod bir AsyncSession alıyor — dependency injection ile endpoint'ten geliyor.
    Session'ı bu sınıfın içinde oluşturmak yerine dışarıdan almayı tercih ettim:
    Bu yaklaşım (dependency injection) test yazarken session'ı mock'lamayı kolaylaştırıyor.
    """

    # ─── Oluşturma ────────────────────────────────────────────────────────────
    async def create_contract(
        self,
        db: AsyncSession,
        data: ContractCreate,
        tenant_id: uuid.UUID,
        uploader_id: uuid.UUID | None = None,
    ) -> Contract:
        """
        Yeni sözleşme metadata kaydı oluşturuyorum.
        tenant_id ve uploader_id endpoint katmanından geliyor (current_user üzerinden).
        """
        contract = Contract(
            **data.model_dump(exclude_none=False),
            status=ContractStatus.UPLOADED,  # Her yeni sözleşme UPLOADED ile başlıyor
            tenant_id=tenant_id,
            uploader_id=uploader_id,
        )
        db.add(contract)
        # Commit'i burada yapmıyorum; get_db_session dependency'si bunu hallediyor.
        # Bu sayede birden fazla DB işlemini aynı transaction içinde yönetebiliyorum.
        await db.flush()   # ID'yi almak için veritabanına gönderiyorum, commit değil
        await db.refresh(contract)  # Sunucu tarafı default değerleri (created_at) alıyorum
        return contract

    # ─── ID'ye Göre Getirme ───────────────────────────────────────────────────
    async def get_contract_by_id(
        self,
        db: AsyncSession,
        contract_id: uuid.UUID,
    ) -> Contract | None:
        """
        Tek bir sözleşmeyi ID ile getiriyorum.
        Bulunamazsa None döndürüyorum; endpoint katmanı 404 kararını veriyor.
        Servis "bulunamadı mı yoksa hata mı?" diye karar vermiyor — bu endpoint'in işi.
        """
        result = await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()

    # ─── Listeleme ────────────────────────────────────────────────────────────
    async def get_contracts(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        status: ContractStatus | None = None,
    ) -> tuple[Sequence[Contract], int]:
        """
        Sözleşmeleri sayfalama destekli listeliyorum.
        İsteğe bağlı `status` filtresi ile belirli durumdaki sözleşmeleri filtreleyebiliyorum.

        Hem kayıtları hem de toplam sayıyı döndürüyorum — frontend sayfalama için ikisine de ihtiyaç duyuyor.
        İki ayrı sorgu atmak yerine `func.count` ile tek seferde hallediyorum.
        """
        # Temel sorgu — filtreleri koşullu olarak ekliyorum
        base_query = select(Contract)
        count_query = select(func.count(Contract.id))

        if status is not None:
            base_query = base_query.where(Contract.status == status)
            count_query = count_query.where(Contract.status == status)

        # Toplam sayıyı alıyorum (sayfalama için gerekli)
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Sıralama + sayfalama uyguluyorum
        # created_at desc: en yeni sözleşmeler önce gelsin
        paginated_query = (
            base_query
            .order_by(Contract.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await db.execute(paginated_query)
        items = items_result.scalars().all()

        return items, total

    # ─── Güncelleme ───────────────────────────────────────────────────────────
    async def update_contract(
        self,
        db: AsyncSession,
        contract: Contract,
        data: ContractUpdate,
    ) -> Contract:
        """
        Mevcut bir sözleşmeyi kısmen güncelliyorum (partial update).
        Sadece gönderilen alanları değiştiriyorum — None olan alanları dokunmadan bırakıyorum.
        `exclude_unset=True` ile Pydantic'e "sadece kullanıcının açıkça gönderdiği alanları ver" diyorum.
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contract, field, value)

        await db.flush()
        await db.refresh(contract)
        return contract

    # ─── Silme ────────────────────────────────────────────────────────────────
    async def delete_contract(
        self,
        db: AsyncSession,
        contract: Contract,
    ) -> None:
        """
        Sözleşmeyi veritabanından kalıcı olarak siliyor.
        Hard delete tercih ettim — soft delete (is_deleted flag) sonraki sprint'te
        gereksinimlere göre eklenebilir. Şimdilik basit tutuyorum.
        """
        await db.delete(contract)
        await db.flush()


# ─── Singleton Instance ───────────────────────────────────────────────────────
# Uygulama genelinde tek bir ContractService instance'ı kullanıyorum.
# Stateless bir sınıf olduğu için birden fazla instance oluşturmak gereksiz.
contract_service = ContractService()
