"""
API v1 Ana Router

Tüm v1 endpoint router'larını burada bir araya getiriyorum.
main.py sadece bu tek router'ı import ediyor; yeni bir domain eklendiğinde
(örneğin users, compliance) sadece bu dosyaya bir satır include ekliyorum.
main.py'ye dokunmak zorunda kalmıyorum — Open/Closed prensibinin küçük bir yansıması.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, contracts

# ─── v1 Ana Router ────────────────────────────────────────────────────────────
# Bu router main.py'de `/api/v1` prefix'i ile mount ediliyor.
# Her alt router kendi prefix ve tag'ini burada alıyor.
api_router = APIRouter()

# Kimlik doğrulama endpoint'leri — korumasız, public erişim
# Tam path: /api/v1/auth/login/access-token
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Sözleşme endpoint'leri — JWT koruması altında
# Tam path: /api/v1/contracts/...
api_router.include_router(
    contracts.router,
    prefix="/contracts",
    tags=["Contracts"],
)

# İleride eklenecekler:
# api_router.include_router(users.router,      prefix="/users",      tags=["Users"])
# api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
# api_router.include_router(analysis.router,   prefix="/analysis",   tags=["Analysis"])
