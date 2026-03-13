"""
Authentication Endpoint'leri

Kullanıcı girişi ve token yönetimini burada yapıyorum.
Şimdilik sadece access token endpoint'i var; ilerleyen sprint'lerde
refresh token ve logout eklenecek.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import create_access_token, verify_password
from app.models.user import User

router = APIRouter()

# Tip alias'ı — dependency injection'ı her endpoint'te tekrar yazmamak için
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ─── Token Yanıt Şeması ───────────────────────────────────────────────────────
# OAuth2 standardı bu yapıyı bekliyor: access_token ve token_type zorunlu alanlar.
# token_type her zaman "bearer" — OAuth2 Bearer Token spesifikasyonu böyle gerektiriyor.
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── POST /login/access-token ─────────────────────────────────────────────────
@router.post(
    "/login/access-token",
    response_model=TokenResponse,
    summary="Giriş yap ve JWT token al",
    description=(
        "Email ve şifre ile kimlik doğrulaması yapar. "
        "Başarılıysa Bearer token döndürür. "
        "Swagger UI'daki 'Authorize' butonu bu endpoint'i kullanır."
    ),
)
async def login_access_token(
    db: DbSession,
    # OAuth2PasswordRequestForm: username ve password alanlarını form-data olarak alıyor.
    # FastAPI standardı bu; email alsam da field adı "username" olmak zorunda (OAuth2 spec).
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """
    Kullanıcı girişini doğrulayıp JWT token döndürüyorum.

    Güvenlik notu: Kullanıcı bulunamadı mı, yoksa şifre yanlış mı?
    Bu ayrımı dışarıya sızdırmıyorum — her iki durumda da aynı hatayı döndürüyorum.
    "Email bulunamadı" mesajı, saldırgana hangi email'lerin kayıtlı olduğunu söyler.
    """
    # ── Kullanıcıyı bul ───────────────────────────────────────────────────────
    # form_data.username aslında email — OAuth2 spec'te alan adı username olarak geçiyor
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # ── Kimlik doğrulama ──────────────────────────────────────────────────────
    # Kasıtlı olarak iki koşulu birleştiriyorum: "kullanıcı yok" ile "şifre yanlış"
    # aynı hata mesajını veriyor — bilgi sızdırmama prensibi.
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Hesap aktif mi? ───────────────────────────────────────────────────────
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu hesap devre dışı bırakılmış. Yöneticinizle iletişime geçin.",
        )

    # ── Token oluştur ─────────────────────────────────────────────────────────
    # Token'ın subject alanına email'i koyuyorum; get_current_user bunu okuyacak.
    # Alternatif olarak user.id kullanılabilir — email değişebileceği için
    # ilerleyen sprint'te ID'ye geçmeyi düşünüyorum.
    access_token = create_access_token(subject=user.email)

    return TokenResponse(access_token=access_token)
