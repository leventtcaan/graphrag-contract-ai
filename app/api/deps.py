"""
FastAPI Dependency'leri

Endpoint'lere enjekte edilecek bağımlılıkları burada tanımlıyorum.
`get_current_user` — uygulamanın tüm korumalı endpoint'lerinin güvenlik kapısı.
Yeni bir dependency gerektiğinde (örneğin get_current_superuser, get_current_tenant)
bu dosyaya ekliyorum; endpoint dosyalarını değiştirmiyorum.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_access_token
from app.models.user import User

# ─── OAuth2 Scheme ────────────────────────────────────────────────────────────
# tokenUrl: Swagger UI'ın "Authorize" butonuna tıkladığında token almak için
# hangi endpoint'i çağıracağını söylüyorum. API_V1_STR prefix'i olmadan yazıyorum
# çünkü OAuth2PasswordBearer bunu göreceli yol olarak kullanıyor.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")

# Tekrar kullanım için tip alias'ları
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
TokenStr = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    db: DbSession,
    token: TokenStr,
) -> User:
    """
    JWT token'ı doğrulayıp token'daki kullanıcıyı veritabanından getiriyorum.

    Bu dependency, korumalı her endpoint'te `Depends(get_current_user)` ile çalışıyor.
    Herhangi bir adımda hata olursa 401 döndürüyorum — hangi adımın başarısız olduğunu
    kasıtlı olarak gizliyorum (token mı geçersiz, kullanıcı mı yok?).
    Saldırgan bu ayrımı bilmemeli.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulaması başarısız. Lütfen tekrar giriş yapın.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ── Token çözme ───────────────────────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        # Süresi dolmuş, imza geçersiz veya format bozuk — hepsini aynı hatayla yanıtlıyorum
        raise credentials_exception

    # ── Kullanıcıyı veritabanında arıyorum ────────────────────────────────────
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # Token geçerli ama kullanıcı silinmiş — bu edge case'i de reddediyorum
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Token geçerli ama kullanıcı pasif mi? Bu dependency bunu kontrol ediyor.
    `get_current_user` üzerine koyulan ek bir güvenlik katmanı.
    Kullanıcı hesabını askıya aldığımda bu dependency 403 döndürür.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu hesap devre dışı bırakılmış.",
        )
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Sadece superuser'ların erişebildiği endpoint'ler için ek güvenlik katmanı.
    Tenant yönetimi ve sistem geneli admin işlemleri bu dependency'yi kullanacak.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yeterli yetkiniz yok.",
        )
    return current_user
