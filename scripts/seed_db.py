"""
Veritabanı Tohumlama (Seeding) Betiği

Bu betik, geliştirme ve test ortamı için gerekli temel kayıtları PostgreSQL'e yazar.
İlk çalıştırmada:
  - "Test Hukuk Bürosu" tenant'ını oluşturur
  - Bu tenant'a bağlı bir admin kullanıcısı oluşturur

Kayıtlar zaten mevcutsa sessizce atlar (idempotent davranış) —
birden fazla çalıştırmak güvenli.

Çalıştırma:
    python scripts/seed_db.py

Gereksinim: PostgreSQL çalışıyor olmalı ve .env dosyası dolu olmalı.
"""

import asyncio
import sys
from pathlib import Path

# ─── Proje kök dizinini Python path'ine ekliyorum ─────────────────────────────
# Bu betik scripts/ altında çalışıyor; app/ modüllerini import edebilmek için
# proje kökünü path'e eklemem gerekiyor.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.contract import Contract  # noqa: E402,F401 — ilişki resolver için gerekli
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402

# ─── Terminal Renk Kodları (ANSI) ─────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─── Seed Sabitleri ───────────────────────────────────────────────────────────
TENANT_NAME  = "Test Hukuk Bürosu"
ADMIN_EMAIL  = "admin@test.com"
ADMIN_PASS   = "admin123"


async def seed_tenant(session) -> Tenant:
    """
    Tenant kaydını oluşturuyorum ya da mevcutu döndürüyorum.
    Aynı isimde tenant varsa tekrar oluşturma, sadece bildir.
    """
    result = await session.execute(
        select(Tenant).where(Tenant.name == TENANT_NAME)
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        tenant = Tenant(name=TENANT_NAME, is_active=True)
        session.add(tenant)
        # flush(): commit olmadan ID üretiyorum — User'a tenant.id gerekiyor
        await session.flush()
        print(f"  {GREEN}✓ Tenant oluşturuldu:{RESET} {tenant.name}")
        print(f"    {BOLD}id:{RESET} {tenant.id}")
    else:
        print(f"  {YELLOW}~ Tenant zaten mevcut:{RESET} {tenant.name}")
        print(f"    {BOLD}id:{RESET} {tenant.id}")

    return tenant


async def seed_admin_user(session, tenant: Tenant) -> User:
    """
    Admin kullanıcısını oluşturuyorum ya da mevcutu döndürüyorum.
    Şifreyi düz metin olarak saklamıyorum — bcrypt hash'ini kaydediyorum.
    """
    result = await session.execute(
        select(User).where(User.email == ADMIN_EMAIL)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=ADMIN_EMAIL,
            # bcrypt ile hash'liyorum; salt otomatik ekleniyor
            hashed_password=get_password_hash(ADMIN_PASS),
            is_active=True,
            # Swagger UI testleri için superuser yapıyorum — prod'da kaldırılmalı
            is_superuser=True,
            tenant_id=tenant.id,
        )
        session.add(user)
        await session.flush()
        print(f"  {GREEN}✓ Admin kullanıcı oluşturuldu:{RESET} {user.email}")
        print(f"    {BOLD}id:{RESET}     {user.id}")
        print(f"    {BOLD}tenant:{RESET} {tenant.name}")
    else:
        print(f"  {YELLOW}~ Kullanıcı zaten mevcut:{RESET} {user.email}")
        print(f"    {BOLD}id:{RESET} {user.id}")

    return user


async def main() -> None:
    """
    Ana seeding akışı. Tüm işlemleri tek bir transaction içinde yapıyorum:
    tenant veya user oluşturma sırasında hata çıkarsa ikisi de rollback ediliyor.
    """
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  IT Law Project — Veritabanı Tohumlama{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}\n")

    try:
        async with AsyncSessionLocal() as session:
            # ── Tenant oluştur ─────────────────────────────────────────────────
            print(f"{BOLD}[1/2] Tenant{RESET}")
            tenant = await seed_tenant(session)

            print()

            # ── Admin kullanıcısı oluştur ──────────────────────────────────────
            print(f"{BOLD}[2/2] Admin Kullanıcı{RESET}")
            await seed_admin_user(session, tenant)

            # ── Commit: her iki kayıt birlikte yazılıyor ───────────────────────
            await session.commit()

    except Exception as exc:
        print(f"\n  {RED}✗ Seeding başarısız:{RESET} {exc}")
        print(f"    PostgreSQL çalışıyor mu? .env dosyası dolu mu?")
        sys.exit(1)

    # ─── Başarı mesajı ────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{GREEN}{BOLD}  ✓ Seeding tamamlandı!{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    print(f"\n  {BOLD}Swagger UI:{RESET}  http://localhost:8000/api/v1/docs")
    print(f"  {BOLD}Login endpoint:{RESET} POST /api/v1/auth/login/access-token")
    print(f"  {BOLD}Kullanıcı adı:{RESET} {ADMIN_EMAIL}")
    print(f"  {BOLD}Şifre:{RESET}        {ADMIN_PASS}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
