"""
Neo4j Grafik Veritabanı Bağlantı Katmanı

GraphRAG mimarisinin kalbi olan Neo4j bağlantısını burada yönetiyorum.
Resmi `neo4j` Python sürücüsünü kullanıyorum. Sürücü async session desteği
sunuyor; FastAPI'nin async yapısıyla uyumlu çalışıyorum.
"""

import logging
from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession as Neo4jAsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jDatabase:
    """
    Neo4j bağlantısını bir sınıf içinde kapsüllemeyi tercih ettim.
    Böylece driver'ı tek bir yerde tutup uygulama genelinde paylaşıyorum —
    her bağlantıda yeni bir driver oluşturmak hem pahalı hem de gereksiz.

    Kullanım:
        neo4j_db = Neo4jDatabase()
        await neo4j_db.connect()
        # ... kullanım ...
        await neo4j_db.close()
    """

    def __init__(self) -> None:
        # Driver'ı başlangıçta None yapıyorum; connect() çağrısıyla başlatılacak
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """
        Neo4j driver'ını başlatıyorum. AsyncGraphDatabase.driver() çağrısı
        hemen bağlanmaz — ilk sorgu veya verify_connectivity() anında bağlanır.
        Bu yüzden verify_connectivity() ile bağlantıyı açıkça test ediyorum.
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                # Bağlantı havuzunu geliştirme ortamına uygun tutuyorum
                max_connection_pool_size=10,
                connection_timeout=10.0,
            )
            # Gerçek bağlantı testi — driver sadece config doğrulamaz, sunucuya ping atar
            await self._driver.verify_connectivity()
            logger.info("Neo4j baglantisi basarili. URI: %s", settings.NEO4J_URI)
        except ServiceUnavailable as e:
            logger.error("Neo4j sunucusuna ulasilamiyor: %s", e)
            raise
        except AuthError as e:
            logger.error("Neo4j kimlik dogrulama hatasi: %s", e)
            raise

    async def close(self) -> None:
        """
        Uygulama kapanırken driver'ı güvenle kapatıyorum.
        Açık session'lar varsa driver bunları bekleyerek kapatıyor.
        """
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver kapatildi.")

    async def check_connection(self) -> bool:
        """
        Health check ve uygulama başlangıcında bağlantıyı doğrulayan yardımcı metod.
        Basit bir Cypher sorgusuyla veritabanının cevap verip vermediğini kontrol ediyorum.
        """
        if self._driver is None:
            logger.warning("Neo4j driver henuz baslatilmadi.")
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ping")
                record = await result.single()
                return record is not None and record["ping"] == 1
        except Exception as e:
            logger.error("Neo4j saglik kontrolu basarisiz: %s", e)
            return False

    async def get_session(self) -> AsyncGenerator[Neo4jAsyncSession, None]:
        """
        FastAPI dependency injection için async generator.
        Her çağrıda yeni bir Neo4j session'ı açıyorum ve işlem bitince kapatıyorum.

        Kullanım:
            async def my_endpoint(neo4j: Neo4jAsyncSession = Depends(neo4j_db.get_session)):
                ...
        """
        if self._driver is None:
            raise RuntimeError("Neo4j driver baslatilmamis. Lifespan'i kontrol et.")

        async with self._driver.session(database="neo4j") as session:
            try:
                yield session
            except Exception:
                # Neo4j transaction rollback burada otomatik gerçekleşiyor
                raise

    @property
    def driver(self) -> AsyncDriver:
        """Doğrudan driver erişimi gerektiğinde bu property'yi kullanıyorum."""
        if self._driver is None:
            raise RuntimeError("Neo4j driver baslatilmamis.")
        return self._driver


# ─── Singleton Instance ───────────────────────────────────────────────────────
# Uygulama genelinde tek bir Neo4jDatabase instance'ı kullanıyorum.
# main.py lifespan'ında connect() ve close() çağrıları yapılacak.
neo4j_db = Neo4jDatabase()
