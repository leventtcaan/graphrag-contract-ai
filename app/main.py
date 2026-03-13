"""
IT Compliance & Contract Analyzer — FastAPI Uygulama Giriş Noktası

Bu dosya tüm FastAPI uygulamasının başlangıç noktası. Burada uygulama instance'ını
oluşturuyorum, middleware'leri tanımlıyorum ve router'ları bağlıyorum.
İleride GraphRAG entegrasyonu ve AI pipeline'ları da buraya eklenecek.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — tüm ORM modelleri kayıtlı olmalı (relationship resolver)

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_postgres_connection, close_postgres_connection
from app.core.neo4j_db import neo4j_db
from app.services.document import ensure_upload_dir

# Uygulama genelinde logging yapılandırmasını burada kuruyorum.
# Tüm modüller bu konfigürasyonu miras alacak.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Uygulama Yaşam Döngüsü ──────────────────────────────────────────────────
# Lifespan context manager ile uygulama açılırken ve kapanırken ne yapacağımı
# tanımladım. Veritabanı bağlantıları burada başlıyor ve güvenle kapatılıyor.
# Bu yaklaşım eski @app.on_event("startup") dekoratörünün modern halefi.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("IT Law Analyzer baslatiliyor... Ortam: %s", settings.ENVIRONMENT)

    # Upload dizininin var olduğundan emin oluyorum — yoksa oluşturuyorum.
    # Bunu en başta yapıyorum; DB bağlantısından bağımsız, her zaman çalışmalı.
    ensure_upload_dir()

    # PostgreSQL bağlantısını kontrol ediyorum.
    # check_postgres_connection() artık tüm exception'ları yakalıyor; bu çağrı asla fırlatmaz.
    pg_ok = await check_postgres_connection()
    if not pg_ok:
        logger.warning(
            "PostgreSQL baglantisi kurulamadi! "
            "Konteynerların calısıp calısmadıgını kontrol et: docker compose ps"
        )

    # Neo4j driver'ını başlatıyor ve bağlantıyı doğruluyorum
    neo4j_ok = False
    try:
        await neo4j_db.connect()
        neo4j_ok = await neo4j_db.check_connection()
        if not neo4j_ok:
            logger.warning("Neo4j baglantisi dogrulanamadi.")
    except Exception as e:
        logger.warning("Neo4j baslatma hatasi (%s): %s — Devam ediliyor.", type(e).__name__, e)

    logger.info(
        "Baslatma tamamlandi. PostgreSQL: %s | Neo4j: %s",
        "OK" if pg_ok else "HATA",
        "OK" if neo4j_ok else "HATA",
    )

    yield  # ← Uygulama burada çalışıyor; bu satırın altı shutdown aşaması

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("IT Law Analyzer kapatiliyor...")

    # Neo4j driver'ını önce kapatıyorum — açık session'lar varsa bekleniyor
    await neo4j_db.close()

    # PostgreSQL bağlantı havuzunu temizliyorum
    await close_postgres_connection()

    logger.info("Tum baglantılar temizlendi. Güle güle.")


# ─── FastAPI Instance ─────────────────────────────────────────────────────────
# Uygulamayı metadata ile birlikte oluşturuyorum. Swagger UI bu bilgileri kullanıyor.
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────
# Burada CORS ayarlarını yapılandırdım ki frontend ile haberleşebileyim.
# Production'da ALLOWED_ORIGINS'i kısıtlayacağım; şimdilik geliştirme için açık tutuyorum.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Router Bağlantısı ────────────────────────────────────────────────────
# Tüm v1 endpoint'leri api_router üzerinden tek seferde dahil ediyorum.
# Yeni bir domain router'ı eklendiğinde sadece app/api/v1/api.py değişiyor, bu dosya değil.
app.include_router(api_router, prefix=settings.API_V1_STR)


# ─── Sistem Endpoint'leri ─────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Uygulamanın ayakta olup olmadığını kontrol eden endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
    }


@app.get("/", include_in_schema=False)
async def root():
    # Kök path'e gelen istekleri Swagger UI'a yönlendiriyorum.
    return {"message": f"Welcome to {settings.PROJECT_NAME}. Docs: {settings.API_V1_STR}/docs"}
