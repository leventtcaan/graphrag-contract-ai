"""
Otomatik Uyum Raporu Servisi — Compliance Scoring

Bu servis, sözleşmenin Neo4j bilgi grafiğini Groq LLM'e göndererek
yapılandırılmış bir denetim raporu üretiyor.

Pipeline:
  Neo4j'den grafik verisini çek (tüm varlıklar)
    → LLM'e gönder (SystemMessage + detaylı HumanMessage)
    → JSON yanıtını parse et
    → ComplianceReport döndür

Tasarım kararları:
  - Senkron Neo4j sorgusu + LLM çağrısı asyncio.to_thread() içinde çalışıyor;
    FastAPI event loop'u bloklanmıyor.
  - LLM'e 80 düğüm gönderiyorum (token limiti dengesini burada kurdum).
  - JSON parse başarısız olursa graceful fallback — servis hiçbir zaman 500 fırlatmıyor.
"""

import asyncio
import json
import logging
import re
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.graph_schema import get_neo4j_graph_safe
from app.core.llm import get_llm
from app.schemas.compliance import ComplianceReport, ComplianceRisk

logger = logging.getLogger(__name__)

# ─── LLM Sistem Promptu ───────────────────────────────────────────────────────
_COMPLIANCE_SYSTEM_PROMPT = """Sen bir kıdemli IT hukuk uyum (compliance) uzmanısın.
Görevin: verilen sözleşme grafik verisini derinlemesine inceleyerek kapsamlı bir uyum denetim raporu hazırlamak.

ÇIKTI KURALI — KESİNLİKLE SADECE ŞUNU DÖNDÜR (başka hiçbir şey yazma):
{
  "score": <0-100 arası tamsayı — yüksek değer daha iyi uyum demek>,
  "summary": "<genel uyum değerlendirmesi, 2-3 cümle, Türkçe>",
  "risks": [
    {
      "clause": "<madde adı veya konu başlığı>",
      "risk_level": "<High|Medium|Low>",
      "description": "<riskin açıklaması, Türkçe, somut ve kısa>"
    }
  ],
  "recommendations": ["<öneri 1, Türkçe>", "<öneri 2, Türkçe>", ...]
}

Değerlendirme kriterleri (her biri skoru etkiliyor):
1. GDPR / KVKK uyumu:
   - Kişisel veri kategorileri tanımlanmış mı?
   - Veri saklama süreleri belirtilmiş mi?
   - Yasal dayanak (hukuki meşruiyet) açık mı?
   - Açık rıza mekanizması var mı?
2. Üçüncü taraf veri paylaşımı:
   - Paylaşılan organizasyonlar listelenmiş mi?
   - Aktarım güvenceleri var mı?
3. Yükümlülükler (Obligation) ve cezalar (Penalty):
   - Tarafların sorumluluğu net mi?
   - İhlal durumunda yaptırımlar belirlenmiş mi?
4. Organizasyonel netlik:
   - Tarafların rolleri açık mı?
   - İletişim ve bildirim prosedürleri var mı?

Risk seviyeleri:
  High   → Yasal uyumsuzluk veya ciddi ihlal riski (KVKK/GDPR ihlali, eksik onay vb.)
  Medium → Belirsizlik veya eksik bilgi riski (süre belirtilmemiş, sorumluluk muğlak vb.)
  Low    → İyi uygulama önerisi düzeyinde (iyileştirme fırsatı)

Önemli: Grafik verisi az veya eksikse bunu score'a yansıt (düşük tut) ve ilgili maddeleri High risk olarak işaretle.
"""


def _run_compliance_sync(contract_id: uuid.UUID) -> ComplianceReport:
    """
    Neo4j grafik verisini çekip LLM ile uyum raporu üretiyorum (senkron).

    asyncio.to_thread() ile thread pool'da çalışacak — event loop bloke olmaz.
    """
    # ── Neo4j bağlantısı ──────────────────────────────────────────────────────
    graph = get_neo4j_graph_safe()
    if graph is None:
        logger.warning("Neo4j bağlantısı yok — compliance servisi çalışamıyor.")
        return ComplianceReport(
            score=0,
            summary="Neo4j bağlantısı kurulamadı. Grafik verisi olmadan uyum analizi yapılamıyor.",
            risks=[
                ComplianceRisk(
                    clause="Altyapı",
                    risk_level="High",
                    description="Neo4j veritabanına erişilemiyor; grafik bazlı analiz mümkün değil.",
                )
            ],
            recommendations=["Neo4j servisinin çalıştığını doğrulayın."],
        )

    # ── Grafik verisini çek ───────────────────────────────────────────────────
    # Tüm düğümleri getiriyorum; Contract düğümünü meta veri kalabalığı olduğu için atlıyorum.
    cypher = (
        f"MATCH (n) WHERE n.contract_id = '{contract_id}' AND NOT n:Contract "
        f"RETURN labels(n) AS tur, properties(n) AS ozellikler LIMIT 100"
    )
    try:
        rows = graph.query(cypher)
    except Exception as exc:
        logger.exception("Compliance Neo4j sorgusu başarısız: %s", exc)
        rows = []

    if not rows:
        return ComplianceReport(
            score=0,
            summary=(
                "Bu sözleşmeye ait grafik verisi bulunamadı. "
                "Analiz henüz çalıştırılmamış olabilir."
            ),
            risks=[
                ComplianceRisk(
                    clause="Genel",
                    risk_level="High",
                    description=(
                        "Neo4j'de sözleşme verisi yok. "
                        "POST /{id}/analyze endpoint'i ile önce analiz başlatın."
                    ),
                )
            ],
            recommendations=["Sözleşmeyi /analyze endpoint'i ile analiz edin."],
        )

    # ── Grafik verisini LLM için metinleştir ─────────────────────────────────
    # contract_id'yi satırdan filtreliyorum — gürültü, token harcatıyor, anlam katmıyor.
    lines: list[str] = []
    for row in rows[:80]:
        tur = row.get("tur", ["Bilinmeyen"])
        ozellikler = {
            k: v
            for k, v in row.get("ozellikler", {}).items()
            if k != "contract_id"
        }
        lines.append(f"[{', '.join(tur)}] {ozellikler}")

    graph_text = "\n".join(lines)
    node_count = len(rows)

    user_message = (
        f"Aşağıdaki Neo4j grafik verisi, analiz edilmiş bir IT sözleşmesine ait "
        f"{node_count} varlık düğümünü içeriyor.\n"
        f"Bu veriyi derinlemesine inceleyerek kapsamlı uyum raporu oluştur.\n\n"
        f"=== SÖZLEŞME GRAFİK VERİSİ ({node_count} düğüm) ===\n"
        f"{graph_text}\n\n"
        f"=== RAPORU SADECE JSON FORMATINDA DÖNDÜR ==="
    )

    # ── LLM çağrısı ───────────────────────────────────────────────────────────
    llm = get_llm()
    try:
        response = llm.invoke(
            [
                SystemMessage(content=_COMPLIANCE_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]
        )
        raw_text: str = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
    except Exception as exc:
        logger.exception("Compliance LLM çağrısı başarısız: %s", exc)
        return ComplianceReport(
            score=0,
            summary="Uyum analizi sırasında LLM hatası oluştu. Lütfen daha sonra tekrar deneyin.",
            risks=[],
            recommendations=["LLM servisini kontrol edin."],
        )

    # ── JSON parse ────────────────────────────────────────────────────────────
    # LLM bazen ```json ... ``` bloğu içinde döndürüyor — temizle
    clean = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean).strip()

    try:
        data = json.loads(clean)
        risks = [
            ComplianceRisk(
                clause=r.get("clause", "Bilinmeyen"),
                risk_level=r.get("risk_level", "Medium"),
                description=r.get("description", ""),
            )
            for r in data.get("risks", [])
            if isinstance(r, dict)
        ]
        report = ComplianceReport(
            score=max(0, min(100, int(data.get("score", 50)))),
            summary=data.get("summary", ""),
            risks=risks,
            recommendations=[
                str(r) for r in data.get("recommendations", []) if r
            ],
        )
        logger.info(
            "Compliance raporu üretildi: contract_id=%s score=%d risk_count=%d",
            contract_id,
            report.score,
            len(report.risks),
        )
        return report

    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        logger.exception(
            "Compliance JSON parse hatası: %s\nRaw (ilk 400 karakter):\n%s",
            exc,
            raw_text[:400],
        )
        # Graceful fallback: parse edemedim ama tamamen boş bırakmıyorum
        return ComplianceReport(
            score=50,
            summary=(
                "Uyum raporu oluşturuldu ancak yapılandırılamadı. "
                "Ham çıktı öneriler bölümünde görülebilir."
            ),
            risks=[],
            recommendations=[raw_text[:500]],
        )


async def generate_compliance_report(contract_id: uuid.UUID) -> ComplianceReport:
    """
    Sözleşmenin uyum raporunu asenkron olarak üretir.

    LangChain / Neo4j senkron çağrıları asyncio.to_thread() ile thread pool'a alınıyor;
    FastAPI event loop'u bloklanmıyor.
    """
    return await asyncio.to_thread(_run_compliance_sync, contract_id)
