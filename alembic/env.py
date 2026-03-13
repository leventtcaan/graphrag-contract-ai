"""
Alembic Migration Ortam Yapılandırması

Bu dosyayı asenkron SQLAlchemy yapımıza uygun olarak yeniden yazdım.
Alembic normalde senkron bir araç; ama asyncpg sürücüsü senkron DBAPI değil.
Bu yüzden Alembic'in önerdiği async pattern'i uyguladım:
  - run_migrations_offline → URL üzerinden, bağlantısız (SQL betiği üretmek için)
  - run_migrations_online  → async engine üzerinden, canlı bağlantıyla

Önemli: URL'yi alembic.ini'ye yazmak yerine settings üzerinden okuyorum.
Bu sayede .env dosyasındaki değeri tek yerden yönetiyorum.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ─── Alembic Config ───────────────────────────────────────────────────────────
# alembic.ini dosyasına erişim sağlayan config nesnesi
config = context.config

# ─── Logging ──────────────────────────────────────────────────────────────────
# alembic.ini'deki [loggers] bölümünü devreye alıyorum
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── Uygulama Ayarları ve Modeller ───────────────────────────────────────────
# settings'i import edip PostgreSQL URL'sini programatik olarak set ediyorum.
# Böylece alembic.ini'deki sqlalchemy.url satırı devre dışı kalıyor.
from app.core.config import settings  # noqa: E402

# Alembic'e hangi URL'yi kullanacağını söylüyorum.
# async template kullandığımız için async_engine_from_config çağrılıyor;
# bu da asyncpg sürücüsünü gerektiriyor. POSTGRES_URL (postgresql+asyncpg://) doğru seçim.
# POSTGRES_URL_SYNC (psycopg2 formatı) senkron Alembic pattern'i için saklıyorum.
config.set_main_option("sqlalchemy.url", settings.POSTGRES_URL)

# Tüm modelleri burada import etmek ZORUNLU — Alembic autogenerate için metadata'ya bakıyor.
# Yeni model dosyası eklediğimde buraya da import eklemeliyim, yoksa tablo atlanır.
from app.models.base import Base           # noqa: E402 — DeclarativeBase
from app.models.contract import Contract  # noqa: E402 — Contract tablosu (import edilmesi metadata'ya kaydeder)

# target_metadata: Alembic bu nesneyi inceleyerek mevcut DB şeması ile farkı buluyor.
# Base.metadata tüm kayıtlı modelleri (tablolar, index'ler, enum'lar) içeriyor.
target_metadata = Base.metadata


# ─── Offline Mod ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Offline modda Alembic veritabanına bağlanmadan SQL betikleri üretiyor.
    CI/CD pipeline'larında veya migration'ı gözden geçirmek istediğimde kullanıyorum:
      alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # compare_type=True ekleyince kolon tip değişikliklerini de algılıyor
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Online Mod — Senkron Köprü ──────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    """
    Async bağlantının senkron tarafında migration'ları çalıştırıyorum.
    connection.run_sync() bu fonksiyonu çağırıyor; async event loop'un içindeyiz.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Sütun tipi değişikliklerini de takip ediyorum
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Online Mod — Async Engine ────────────────────────────────────────────────
async def run_async_migrations() -> None:
    """
    Asenkron motoru burada oluşturup migration'ı çalıştırıyorum.

    NullPool kullanmak zorundayım çünkü Alembic migration'ı tek seferlik bir işlem;
    bağlantı havuzuna ihtiyacım yok ve migration bitince motoru temizliyorum.
    Uygulama motorunu (async_engine) burada kullanmıyorum — Alembic kendi motorunu
    oluşturmalı ki uygulama bağlantı havuzunu kirletmeyeyim.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # run_sync ile async bağlantıyı senkron migration runner'a köprülüyorum
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Online mod: asyncio.run() ile async migration fonksiyonunu başlatıyorum.
    Alembic CLI senkron çalıştığı için en dış katmanda asyncio.run() gerekiyor.
    """
    asyncio.run(run_async_migrations())


# ─── Mod Seçimi ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
