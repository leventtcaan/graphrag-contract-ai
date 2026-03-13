"""
PostgreSQL Asenkron Bağlantı Katmanı

Bu modülde SQLAlchemy'nin asenkron motorunu ve oturum fabrikasını kuruyorum.
asyncpg sürücüsü üzerinden PostgreSQL'e bağlanıyorum; bu kombinasyon
FastAPI'nin async yapısıyla mükemmel uyum sağlıyor.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Asenkron Motor ───────────────────────────────────────────────────────────
# pool_pre_ping ile her bağlantıyı kullanmadan önce test ediyorum.
# Bu sayede uzun süre boşta kalan bağlantılar yüzünden "bağlantı koptu" hatası almıyorum.
# pool_size ve max_overflow'u şimdilik geliştirme değerlerinde bırakıyorum; prod'da artırırım.
async_engine: AsyncEngine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.ENVIRONMENT == "development",  # Geliştirmede SQL sorgularını logluyorum
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # 1 saatte bir bağlantıları yeniliyorum
)

# ─── Oturum Fabrikası ─────────────────────────────────────────────────────────
# Her HTTP isteği için bağımsız bir AsyncSession oluşturacak fabrikayı burada kurdum.
# expire_on_commit=False ayarını yaptım çünkü commit sonrası nesneye erişmek istiyorum
# ve lazy loading async ortamda beklenmedik hatalara yol açabiliyor.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── Dependency Injection için Session Üreteci ───────────────────────────────
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI endpoint'lerinde `Depends(get_db_session)` ile kullanacağım
    dependency. Her istek için yeni bir session açıyor, işlem bitince
    (hata olsa bile) session'ı güvenle kapatıyor.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Bağlantı Sağlık Kontrolü ────────────────────────────────────────────────
async def check_postgres_connection() -> bool:
    """
    Uygulama başlarken ve health check endpoint'inde PostgreSQL bağlantısını
    doğrulamak için bu fonksiyonu yazıyorum. Basit bir SELECT 1 sorgusu yeterli.
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL baglantisi basarili.")
        return True
    except Exception as e:
        # OperationalError dışında asyncpg'nin kendi exception'larını da yakalıyorum.
        # Örneğin konteyner yokken InvalidAuthorizationSpecificationError fırlatıyor;
        # bu hatanın lifespan'ı çökertmesini istemiyorum, sadece loglanmalı.
        logger.warning("PostgreSQL baglantisi basarisiz (%s): %s", type(e).__name__, e)
        return False


# ─── Motor Kapatma ────────────────────────────────────────────────────────────
async def close_postgres_connection() -> None:
    """
    Uygulama kapanırken bağlantı havuzunu temiz bir şekilde kapatıyorum.
    Bu yapılmazsa açık bağlantılar bir süre PostgreSQL tarafında asılı kalıyor.
    """
    await async_engine.dispose()
    logger.info("PostgreSQL baglanti havuzu kapatildi.")
