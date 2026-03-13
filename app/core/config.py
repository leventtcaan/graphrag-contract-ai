"""
Uygulama Yapılandırması

Tüm ortam değişkenlerini ve sabit ayarları burada tek bir yerden yönetiyorum.
Pydantic BaseSettings kullanarak .env dosyasından otomatik okuma ve tip doğrulaması
sağlıyorum — bu sayede yanlış yapılandırılmış bir ortamda uygulama başlamadan hata alıyorum.
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─── Proje Meta Bilgileri ─────────────────────────────────────────────────
    PROJECT_NAME: str = "IT Compliance & Contract Analyzer"
    PROJECT_DESCRIPTION: str = (
        "B2B SaaS platformu: IT uyum gereksinimlerini ve sözleşmeleri "
        "GraphRAG mimarisiyle analiz eden yapay zeka destekli bir sistem."
    )
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # ─── Güvenlik ─────────────────────────────────────────────────────────────
    # SECRET_KEY'i .env'den okuyorum; production'da güçlü rastgele bir değer kullanmak zorundayım
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_STRONG_RANDOM_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ─── CORS ─────────────────────────────────────────────────────────────────
    # Frontend URL'lerini buraya ekliyorum; prod'da kesin domainleri yazacağım
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # ─── PostgreSQL ───────────────────────────────────────────────────────────
    # Kullanıcı yönetimi ve ilişkisel veriler için bağlantı ayarları
    POSTGRES_USER: str = "itlaw_user"
    POSTGRES_PASSWORD: str = "itlaw_secret"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "itlaw_db"

    @property
    def POSTGRES_URL(self) -> str:
        # SQLAlchemy async bağlantı URL'sini dinamik olarak oluşturuyorum
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def POSTGRES_URL_SYNC(self) -> str:
        # Alembic migration'ları için senkron URL gerekiyor
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Neo4j ────────────────────────────────────────────────────────────────
    # GraphRAG için grafik veritabanı bağlantı ayarları
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "itlaw_neo4j_secret"

    # ─── Groq / LLM ───────────────────────────────────────────────────────────
    # Groq ücretsiz tier: console.groq.com — OpenAI'a kıyasla sıfır maliyet
    # API anahtarını .env'den okuyorum; None ise LLM işlemleri devre dışı kalır
    GROQ_API_KEY: str = "gsk_change-me-in-env"

    # ─── Dosya Depolama ───────────────────────────────────────────────────────
    # Yüklenen sözleşmelerin diske yazılacağı dizin; uygulama başlarken oluşturuyorum
    UPLOAD_DIR: str = "downloads/contracts"

    # ─── Pydantic Settings Yapılandırması ─────────────────────────────────────
    # .env dosyasını otomatik olarak okuyorum; değişken adları büyük/küçük harfe duyarsız
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Uygulama genelinde tek bir settings instance'ı kullanıyorum (singleton pattern)
settings = Settings()
