"""
Contract API Endpoint'leri

Bu dosya sadece HTTP katmanını yönetiyor: gelen isteği parse et,
servisi çağır, uygun HTTP response'u döndür. İş mantığı burada yok.
Endpoint'ler ince tutmak bakım kolaylığı sağlıyor ve test yazmayı
önemli ölçüde basitleştiriyor.
"""

import logging
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.deps import get_current_active_user
from app.core.database import get_db_session
from app.models.contract import ContractStatus
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractListResponse,
    ContractResponse,
    ContractUpdate,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.compliance import ComplianceReport
from app.services.chat import ask_contract_question
from app.services.compliance import generate_compliance_report
from app.services.contract import contract_service
from app.services.document import save_upload_file, extract_text_from_pdf
from app.services.graph_builder import build_contract_graph

# ─── Router Tanımı ────────────────────────────────────────────────────────────
# prefix ve tags'i burada değil, api.py'de tanımlıyorum.
# Bu sayede router'ı farklı prefix'lerle farklı yerlere mount edebilirim.
router = APIRouter()

# Tip alias'ları: dependency injection'ı her endpoint'te tekrar yazmamak için
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
# CurrentUser: her korumalı endpoint bu dependency ile giriş yapmış kullanıcıyı alıyor
CurrentUser = Annotated[User, Depends(get_current_active_user)]


# ─── POST / — Yeni Sözleşme Oluştur ──────────────────────────────────────────
@router.post(
    "/",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni sözleşme metadata'sı kaydet",
    description=(
        "Sözleşmenin başlık, açıklama ve dosya bilgilerini kaydeder. "
        "Dosya içeriği bu endpoint'ten değil, ayrı bir upload endpoint'inden alınacak."
    ),
)
async def create_contract(
    payload: ContractCreate,
    db: DbSession,
    current_user: CurrentUser,  # JWT koruması: geçersiz token → 401 otomatik fırlatılır
) -> ContractResponse:
    """
    Yeni sözleşme oluşturuyorum.
    current_user dependency'si hem token'ı doğruluyor hem de yükleyen kişiyi biliyor.
    """
    contract = await contract_service.create_contract(
        db=db,
        data=payload,
        tenant_id=current_user.tenant_id,
        uploader_id=current_user.id,
    )
    return ContractResponse.model_validate(contract)


# ─── GET / — Sözleşmeleri Listele ─────────────────────────────────────────────
@router.get(
    "/",
    response_model=ContractListResponse,
    summary="Sözleşmeleri listele",
    description="Sayfalama ve opsiyonel durum filtresi ile sözleşmeleri getir.",
)
async def list_contracts(
    db: DbSession,
    current_user: CurrentUser,  # JWT koruması
    offset: Annotated[int, Query(ge=0, description="Atlatılacak kayıt sayısı")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Sayfa başına maksimum kayıt")] = 20,
    status: Annotated[
        Optional[ContractStatus],
        Query(description="Bu durumla filtrele (opsiyonel)"),
    ] = None,
) -> ContractListResponse:
    """
    Sözleşmeleri sayfalama ile listeliyorum.
    Query parametrelerini Annotated + Query() ile tanımladım;
    bu sayede Swagger UI'da açıklamalar ve validasyon otomatik geliyor.
    """
    items, total = await contract_service.get_contracts(
        db=db,
        offset=offset,
        limit=limit,
        status=status,
    )
    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ─── GET /{contract_id} — Tek Sözleşme Getir ─────────────────────────────────
@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Sözleşme detayını getir",
)
async def get_contract(
    contract_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,  # JWT koruması
) -> ContractResponse:
    """
    ID'ye göre tek sözleşme getiriyorum.
    UUID formatı geçersizse FastAPI path parametresi aşamasında 422 fırlatıyor.
    Kayıt bulunamazsa 404 döndürüyorum — bu karar endpoint'e ait.
    """
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )
    return ContractResponse.model_validate(contract)


# ─── PATCH /{contract_id} — Sözleşmeyi Güncelle ──────────────────────────────
@router.patch(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Sözleşme bilgilerini güncelle",
    description="Sadece gönderilen alanlar güncellenir (partial update).",
)
async def update_contract(
    contract_id: uuid.UUID,
    payload: ContractUpdate,
    db: DbSession,
    current_user: CurrentUser,  # JWT koruması
) -> ContractResponse:
    """
    Sözleşmeyi kısmen güncelliyorum.
    Önce kaydın var olup olmadığını kontrol ediyorum; sonra servisi çağırıyorum.
    """
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )
    updated = await contract_service.update_contract(db=db, contract=contract, data=payload)
    return ContractResponse.model_validate(updated)


# ─── DELETE /{contract_id} — Sözleşmeyi Sil ──────────────────────────────────
@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sözleşmeyi kalıcı olarak sil",
)
async def delete_contract(
    contract_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,  # JWT koruması
) -> None:
    """
    Sözleşmeyi hard delete ile siliyorum: önce diskten, sonra veritabanından.

    Dosya silme başarısız olursa (dosya zaten silinmiş, izin hatası vb.)
    sadece logluyorum ve DB silmeye devam ediyorum — tutarsız durum yerine
    "DB temiz, disk kirli" tercih edilebilir bir trade-off.
    204 No Content döndürüyorum — silme başarılıysa body yok.
    """
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Tenant izolasyonu ─────────────────────────────────────────────────────
    if contract.tenant_id is not None and contract.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Diskten dosyayı sil (varsa) ───────────────────────────────────────────
    if contract.file_path:
        try:
            file_path = Path(contract.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info("Sözleşme dosyası diskten silindi: %s", contract.file_path)
            else:
                logger.warning("Dosya bulunamadı (zaten silinmiş?): %s", contract.file_path)
        except OSError as exc:
            # Dosya silme hatası DB silmesini engellemiyoruz — sadece logluyoruz
            logger.warning(
                "Dosya silinirken hata oluştu, DB silmeye devam ediliyor: %s — %s",
                contract.file_path,
                exc,
            )

    await contract_service.delete_contract(db=db, contract=contract)


# ─── POST /{contract_id}/upload — PDF Yükle ───────────────────────────────────
@router.post(
    "/{contract_id}/upload",
    response_model=ContractResponse,
    summary="Sözleşme PDF'i yükle",
    description=(
        "Mevcut bir sözleşme kaydına PDF dosyası ekler. "
        "Dosya diske kaydedilir, metin çıkarılır ve sözleşme durumu güncellenir. "
        "Sadece sözleşmenin sahibi tenant'ın kullanıcıları bu işlemi yapabilir."
    ),
)
async def upload_contract_file(
    contract_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(description="Yüklenecek PDF dosyası")],
) -> ContractResponse:
    """
    PDF dosyasını alıp diske kaydediyorum, metnini çıkarıyorum ve Contract kaydını güncelliyorum.

    Güvenlik kontrolü: Sözleşmenin tenant_id'si ile oturum açan kullanıcının tenant_id'si
    eşleşmeli. Başka bir tenant'ın sözleşmesine dosya yüklenemez.
    """
    # ── Sözleşmeyi bul ────────────────────────────────────────────────────────
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Tenant izolasyonu kontrolü ────────────────────────────────────────────
    # Bu kontrolü endpoint katmanında yapıyorum çünkü current_user burada mevcut.
    # Servis katmanında current_user yoktur — bu tasarım kararı bilinçli.
    if contract.tenant_id is not None and contract.tenant_id != current_user.tenant_id:
        # 403 yerine 404 dönmek daha güvenli — sözleşmenin varlığını sızdırmıyorum
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Dosyayı kaydet ────────────────────────────────────────────────────────
    saved_path, original_filename = await save_upload_file(file)

    # ── Metin çıkar (ileride GraphRAG'a beslenecek) ───────────────────────────
    # Şimdilik sadece çıkarıyorum; bir sonraki sprint'te bu metni işleyeceğim
    extracted_text = await extract_text_from_pdf(saved_path)

    # ── Contract kaydını güncelle ─────────────────────────────────────────────
    # file_path, original_filename, file_size_bytes ContractUpdate şemasında yok;
    # doğrudan ORM nesnesine yazıyoruz. status ise ContractUpdate üzerinden geliyor.
    contract.file_path = str(saved_path)
    contract.original_filename = original_filename
    contract.file_size_bytes = saved_path.stat().st_size

    update_data = ContractUpdate(
        status=ContractStatus.PROCESSING if extracted_text else ContractStatus.FAILED,
    )
    updated = await contract_service.update_contract(db=db, contract=contract, data=update_data)
    return ContractResponse.model_validate(updated)


# ─── POST /{contract_id}/analyze — GraphRAG Analizi Başlat ────────────────────
@router.post(
    "/{contract_id}/analyze",
    response_model=ContractResponse,
    summary="Sözleşmeyi GraphRAG ile analiz et",
    description=(
        "Yüklenmiş PDF'i LLMGraphTransformer ile işler: maddeleri, tarafları, "
        "yükümlülükleri ve yasal referansları çıkararak Neo4j'e bilgi grafiği oluşturur. "
        "İşlem dakikalar alabilir — production'da arka plan görevi olacak."
    ),
)
async def analyze_contract(
    contract_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ContractResponse:
    """
    GraphRAG pipeline'ını tetikliyorum.

    Akış:
      1. Sözleşmeyi ve yetkiyi doğrula
      2. Durumu PROCESSING yap ve kaydet (kullanıcıya anlık geri bildirim)
      3. build_contract_graph() ile LLM entity extraction + Neo4j yazma
      4. Durumu ANALYZED yap, neo4j_node_id'yi kaydet
      5. Güncel Contract'ı döndür

    Hata senaryosunda durumu FAILED yapıyorum ki sözleşme "analyzing" olarak takılı kalmasın.
    """
    # ── Sözleşmeyi bul ve tenant kontrolü yap ────────────────────────────────
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    if contract.tenant_id is not None and contract.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Dosya yüklü mü kontrol et ────────────────────────────────────────────
    if not contract.file_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Önce sözleşmeye PDF yükleyin: POST /{id}/upload",
        )

    # ── Durumu PROCESSING yap (commit edilsin, kullanıcı statüyü görebilsin) ──
    # Bunu analiz başlamadan önce kayıt altına alıyorum; analiz uzun sürebilir.
    await contract_service.update_contract(
        db=db,
        contract=contract,
        data=ContractUpdate(status=ContractStatus.PROCESSING),
    )

    # ── GraphRAG pipeline'ı çalıştır ──────────────────────────────────────────
    try:
        neo4j_node_id = await build_contract_graph(
            contract_id=contract.id,
            file_path=contract.file_path,
        )

        # ── Başarı: ANALYZED durumuna geç ve Neo4j node ID'sini sakla ─────────
        final = await contract_service.update_contract(
            db=db,
            contract=contract,
            data=ContractUpdate(
                status=ContractStatus.ANALYZED,
                neo4j_node_id=neo4j_node_id or None,
            ),
        )
        return ContractResponse.model_validate(final)

    except Exception as e:
        # ── Hata: FAILED olarak işaretle ve exception'ı yeniden fırlat ────────
        # Durumu kaydetmek için yeni bir işlem açmak gerekebilir;
        # şimdilik aynı session üzerinden deniyorum.
        await contract_service.update_contract(
            db=db,
            contract=contract,
            data=ContractUpdate(status=ContractStatus.FAILED),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analiz sırasında hata oluştu: {e}",
        )


# ─── POST /{contract_id}/chat — Sözleşme Üzerinde Soru Sor ───────────────────
@router.post(
    "/{contract_id}/chat",
    response_model=ChatResponse,
    summary="Sözleşme hakkında doğal dilde soru sor",
    description=(
        "GraphCypherQAChain ile sözleşmenin Neo4j bilgi grafiğini sorgular. "
        "LLM soruyu Cypher sorgusuna çevirir, Neo4j'de çalıştırır ve "
        "sonucu doğal dilde yanıtlar. Sözleşme önce /analyze endpoint'iyle "
        "işlenmiş olmalıdır."
    ),
)
async def chat_with_contract(
    contract_id: uuid.UUID,
    payload: ChatRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ChatResponse:
    """
    Kullanıcının sorusunu GraphRAG pipeline'ına iletiyorum.

    Akış:
      1. Sözleşmenin varlığını ve tenant izolasyonunu doğrula
      2. Sözleşmenin analiz edilip edilmediğini kontrol et
      3. ask_contract_question() ile Text-to-Cypher → Neo4j → doğal dil
      4. ChatResponse döndür

    404 kararı güvenlik stratejisi: "bu sözleşme var ama senin değil" yerine
    "böyle bir sözleşme yok" mesajı veriyorum — enumeration attack'ı engelliyorum.
    """
    # ── Sözleşmeyi bul ────────────────────────────────────────────────────────
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Tenant izolasyonu ─────────────────────────────────────────────────────
    if contract.tenant_id is not None and contract.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Sözleşmenin analiz edilip edilmediğini kontrol et ─────────────────────
    # Neo4j'de veri yoksa chat zinciri boş sonuç döndürür; kullanıcıya
    # önceden anlamlı bir mesaj vermek daha iyi deneyim sağlıyor.
    if contract.status != ContractStatus.ANALYZED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Sözleşme henüz analiz edilmemiş (durum: {contract.status.value}). "
                "Önce POST /{id}/analyze endpoint'ini çalıştırın."
            ),
        )

    # ── Text-to-Cypher → Neo4j → doğal dil cevabı ────────────────────────────
    result = await ask_contract_question(
        question=payload.question,
        contract_id=contract_id,
    )

    return ChatResponse(
        answer=result["answer"],
        context_nodes=result["context_nodes"],
        generated_cypher=result.get("generated_cypher"),
    )


# ─── GET /{contract_id}/compliance — Otomatik Uyum Raporu ─────────────────────
@router.get(
    "/{contract_id}/compliance",
    response_model=ComplianceReport,
    summary="Sözleşme uyum raporu üret",
    description=(
        "Neo4j bilgi grafiğindeki tüm varlıkları Groq LLM'e göndererek "
        "otomatik uyum skoru, madde bazlı risk analizi ve öneriler üretir. "
        "Sözleşme önce /analyze endpoint'iyle işlenmiş olmalıdır. "
        "İşlem 15-30 saniye alabilir."
    ),
)
async def get_compliance_report(
    contract_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ComplianceReport:
    """
    Sözleşmenin otomatik uyum raporunu üretiyorum.

    Akış:
      1. Sözleşmeyi bul ve tenant izolasyonunu doğrula
      2. ANALYZED statüsünde olduğunu kontrol et
      3. generate_compliance_report() → Neo4j sorgusu + Groq LLM analizi
      4. Yapılandırılmış ComplianceReport döndür

    Bu endpoint saf GET — sözleşmeyi veya grafik verisini değiştirmiyor.
    Her çağrıda yeni bir LLM analizi yapılıyor; sonuç önbelleğe alınmıyor.
    """
    # ── Sözleşmeyi bul ────────────────────────────────────────────────────────
    contract = await contract_service.get_contract_by_id(db=db, contract_id=contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Tenant izolasyonu ─────────────────────────────────────────────────────
    if contract.tenant_id is not None and contract.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sözleşme bulunamadı: {contract_id}",
        )

    # ── Analiz edilmiş mi? ────────────────────────────────────────────────────
    if contract.status != ContractStatus.ANALYZED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Sözleşme henüz analiz edilmemiş (durum: {contract.status.value}). "
                "Önce POST /{id}/analyze endpoint'ini çalıştırın."
            ),
        )

    # ── Neo4j → LLM → ComplianceReport ───────────────────────────────────────
    return await generate_compliance_report(contract_id=contract_id)
