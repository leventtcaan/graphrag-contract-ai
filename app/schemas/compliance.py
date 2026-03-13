"""
Uyum Raporu Şemaları — Compliance Scoring

LLM'den gelen yapılandırılmış uyum verisi için Pydantic modelleri.
Backend → Frontend arasındaki sözleşme (contract) bu şemalar üzerinden kuruluyor.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ComplianceRisk(BaseModel):
    """Tespit edilen tek bir uyum riski."""

    clause: str = Field(..., description="İlgili madde veya konu başlığı")
    risk_level: Literal["High", "Medium", "Low"] = Field(
        ..., description="Risk seviyesi: High (Kırmızı), Medium (Sarı), Low (Yeşil)"
    )
    description: str = Field(..., description="Riskin kısa açıklaması")


class ComplianceReport(BaseModel):
    """
    Bir sözleşme için tam uyum raporu.

    score: 0-100 arası tamsayı — yüksek değer daha iyi uyum demek.
    summary: Genel değerlendirme özeti.
    risks: Tespit edilen madde bazlı riskler listesi.
    recommendations: Uyumu iyileştirmeye yönelik öneriler.
    """

    score: int = Field(..., ge=0, le=100, description="Uyum skoru (0-100)")
    summary: str = Field(..., description="Genel uyum özeti")
    risks: list[ComplianceRisk] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
