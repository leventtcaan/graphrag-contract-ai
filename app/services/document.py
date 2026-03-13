"""
Doküman İşleme Servisi

Dosya yükleme ve metin çıkarma işlemlerini burada yönetiyorum.
Bu servis, ham dosyadan metin elde etme sürecinin tamamından sorumlu.
İlerleyen sprint'te bu metin GraphRAG pipeline'ına beslenecek.
"""

import logging
import unicodedata
import uuid
from pathlib import Path

import aiofiles
import pymupdf  # PyMuPDF — Türkçe PDF encoding için pypdf'ten daha güvenilir
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# İzin verilen dosya uzantıları — şimdilik sadece PDF, ileride docx eklenecek
ALLOWED_EXTENSIONS = {".pdf"}
# Maksimum dosya boyutu: 50 MB — büyük sözleşme PDF'leri için makul bir sınır
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def _get_upload_dir() -> Path:
    """
    Upload dizinini Path nesnesi olarak döndürüyorum.
    settings.UPLOAD_DIR göreceli bir yol — çalışma dizinine göre çözümlüyorum.
    """
    upload_path = Path(settings.UPLOAD_DIR)
    # Dizin yoksa oluşturuyorum — exist_ok=True ile "zaten var" hatasını görmezden geliyorum
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_upload_file(upload_file: UploadFile) -> tuple[Path, str]:
    """
    Gelen UploadFile'ı diske asenkron olarak kaydediyorum.

    Dosya adını kullanıcının verdiği isimle saklamıyorum:
    - Güvenlik: Path traversal saldırısını önler ("../../etc/passwd" gibi isimler)
    - Çakışma: Aynı isimli iki dosya birbirinin üzerine yazamaz
    UUID ile isimlendirme bu iki problemi birden çözüyor.

    Döndürdüğüm değerler:
    - saved_path: Dosyanın tam yolu (DB'ye kaydedilecek)
    - original_filename: Kullanıcının orijinal dosya adı (gösterim için)
    """
    # ── Dosya uzantısı kontrolü ───────────────────────────────────────────────
    original_filename = upload_file.filename or "unknown"
    file_ext = Path(original_filename).suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Desteklenmeyen dosya türü: '{file_ext}'. Kabul edilen: {ALLOWED_EXTENSIONS}",
        )

    # ── Dosya boyutu kontrolü ─────────────────────────────────────────────────
    # Önce sonu okuyup boyutu kontrol ediyorum; büyük dosyaları diske yazmadan reddediyorum.
    # UploadFile content-length header'ı her zaman güvenilir değil — bu yüzden okuyarak kontrol ediyorum.
    contents = await upload_file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dosya çok büyük. Maksimum: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
        )

    # ── UUID ile yeni dosya adı oluşturuyorum ─────────────────────────────────
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = _get_upload_dir()
    saved_path = upload_dir / unique_filename

    # ── Asenkron yazma ────────────────────────────────────────────────────────
    # aiofiles ile dosyayı async olarak yazıyorum — event loop'u bloklamıyorum.
    # Büyük PDF'lerde senkron open() çağrısı tüm isteği durdurabilir.
    async with aiofiles.open(saved_path, "wb") as f:
        await f.write(contents)

    logger.info(
        "Dosya kaydedildi: %s (%d bytes) → %s",
        original_filename, len(contents), saved_path,
    )

    return saved_path, original_filename


async def extract_text_from_pdf(file_path: Path) -> str:
    """
    Kaydedilen PDF'den ham metni çıkarıyorum.

    PyMuPDF kullanıyorum — pypdf'in yerine.
    Neden: pypdf bazı Türkçe PDF'lerde font-to-unicode mapping'i yanlış
    yorumluyor ve 'Kişisel' → 'Ki?isel', 'İnternet' → '?nternet' gibi
    bozuk metin üretiyor.
    PyMuPDF PDF spec'teki ToUnicode CMap tablosunu doğru parse ediyor;
    her sayfayı garantili UTF-8 string olarak döndürüyor.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF dosyası bulunamadı: {file_path}")

    try:
        pdf = pymupdf.open(str(file_path))
        pages_text: list[str] = []
        try:
            for page in pdf:
                raw = page.get_text("text")
                # NFC normalizasyonu: combining Unicode karakterlerini birleştirir
                # örn. "I\u0307" (I + dot above) → "İ"
                clean = unicodedata.normalize("NFC", raw)
                if clean.strip():
                    pages_text.append(clean)
        finally:
            pdf.close()

        if not pages_text:
            logger.warning("PDF bos gorunuyor: %s", file_path)
            return ""

        full_text = "\n\n".join(pages_text)
        logger.info(
            "PDF islendi (PyMuPDF): %s — %d sayfa, %d karakter",
            file_path.name, len(pages_text), len(full_text),
        )
        return full_text

    except Exception as e:
        logger.error("PDF metin cikartma hatasi (%s): %s", file_path, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PDF işlenemedi: {e}",
        )


# ─── Upload dizini hazırlama (startup için) ────────────────────────────────────
def ensure_upload_dir() -> Path:
    """
    Uygulama başlarken upload dizininin var olduğundan emin oluyorum.
    main.py lifespan'ında çağrılacak.
    """
    upload_path = _get_upload_dir()
    logger.info("Upload dizini hazir: %s", upload_path.resolve())
    return upload_path
