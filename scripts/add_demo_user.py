"""
Demo Kullanıcısı Ekleme Betiği

CV ve portfolyo paylaşımı için güvenli bir demo hesabı oluşturur.
Admin hesabına dokunmaz.

Çalıştırma:
    python scripts/add_demo_user.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.contract import Contract  # noqa: E402,F401
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

TENANT_NAME = "Test Hukuk Bürosu"
DEMO_EMAIL  = "demo@itlaw.com"
DEMO_PASS   = "Demo2025!"


async def main() -> None:
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  IT Law Project — Demo Kullanıcısı Ekleme{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}\n")

    try:
        async with AsyncSessionLocal() as session:
            # Mevcut tenant'ı bul
            result = await session.execute(
                select(Tenant).where(Tenant.name == TENANT_NAME)
            )
            tenant = result.scalar_one_or_none()

            if tenant is None:
                print(f"  {RED}✗ Tenant bulunamadı. Önce seed_db.py çalıştırın.{RESET}")
                sys.exit(1)

            print(f"  {YELLOW}~ Tenant:{RESET} {tenant.name}")

            # Demo kullanıcı zaten var mı?
            result = await session.execute(
                select(User).where(User.email == DEMO_EMAIL)
            )
            user = result.scalar_one_or_none()

            if user is not None:
                # Şifreyi güncelle
                user.hashed_password = get_password_hash(DEMO_PASS)
                await session.commit()
                print(f"  {YELLOW}~ Demo kullanıcı zaten vardı, şifre güncellendi.{RESET}")
            else:
                user = User(
                    email=DEMO_EMAIL,
                    hashed_password=get_password_hash(DEMO_PASS),
                    is_active=True,
                    is_superuser=False,
                    tenant_id=tenant.id,
                )
                session.add(user)
                await session.commit()
                print(f"  {GREEN}✓ Demo kullanıcı oluşturuldu.{RESET}")

    except Exception as exc:
        print(f"\n  {RED}✗ Hata:{RESET} {exc}")
        sys.exit(1)

    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{GREEN}{BOLD}  ✓ Tamamlandı!{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    print(f"\n  {BOLD}CV / Portfolyo Bilgileri:{RESET}")
    print(f"  {BOLD}Kullanıcı adı:{RESET} {DEMO_EMAIL}")
    print(f"  {BOLD}Şifre:{RESET}         {DEMO_PASS}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
