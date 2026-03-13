# SQLAlchemy ORM modellerini bu pakette tutuyorum. PostgreSQL tablolarının Python yansımaları burada.
# Tüm modelleri burada import ediyorum — SQLAlchemy'nin relationship() string referanslarını
# çözebilmesi için her modelin mapper konfigürasyonu öncesinde kayıtlı olması gerekiyor.
from app.models.base import Base  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["Base", "Contract", "Tenant", "User"]
