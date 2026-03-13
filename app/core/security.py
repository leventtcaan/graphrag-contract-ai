"""
Güvenlik Katmanı — Şifre Hash'leme ve JWT

Tüm kriptografik operasyonları tek bir yerde toplayarak
"güvenlik işini bu modül halleder" prensibini uyguluyorum.
Başka bir dosyanın jwt veya bcrypt'e doğrudan erişmesini istemiyorum;
bu katman üzerinden geçmeli — ilerleyen bir günde algoritmayı değiştirmem
gerekirse tek bir yeri düzeltmem yeterli.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# ─── JWT Yapılandırması ───────────────────────────────────────────────────────
ALGORITHM = "HS256"  # HMAC-SHA256; asimetrik (RS256) gerekirse config'e taşırım


# ─── Şifre Fonksiyonları ──────────────────────────────────────────────────────

def get_password_hash(plain_password: str) -> str:
    """
    Düz metin şifreyi bcrypt ile hash'liyorum.
    Sonuç her seferinde farklı (salt ekleniyor) — aynı şifre için aynı hash üretilmiyor.
    """
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Girilen şifreyi hash ile karşılaştırıyorum.
    bcrypt.checkpw timing-safe karşılaştırma sağlıyor.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ─── JWT Fonksiyonları ────────────────────────────────────────────────────────

def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    JWT access token oluşturuyorum.

    `subject` olarak kullanıcının email'ini veya ID'sini geçiyorum.
    Token içine hassas veri (şifre, kredi kartı vb.) koymuyorum —
    JWT imzalanmış ama şifrelenmemiş; base64 ile çözülebilir.

    expires_delta verilmezse settings'ten ACCESS_TOKEN_EXPIRE_MINUTES alıyorum.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": str(subject),  # subject: token sahibinin kimliği
        "exp": expire,        # expiration: token ne zaman geçersiz olur
        "iat": now,           # issued at: token ne zaman oluşturuldu
    }

    # SECRET_KEY ile imzalıyorum — bu anahtar sızdığında tüm token'lar geçersiz sayılır
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    JWT token'ı doğrulayıp payload'ı döndürüyorum.
    Süresi dolmuş veya imza geçersizse jwt.PyJWTError fırlatıyor;
    çağıran taraf (deps.py) bunu 401'e çeviriyor.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
