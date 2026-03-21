"""
Neo4j Grafik Şema ve LangChain Köprüsü

Bu modül iki görevi üstleniyor:
  1. LangChain'in Neo4jGraph nesnesini başlatmak — GraphRAG sorgu zincirlerinin bağlandığı nokta
  2. Grafik şemasını (node labels, relationship types) tek bir yerde tanımlamak

Neo4jGraph (LangChain) tek bağlantı kaynağı olarak kullanılıyor:
  - LLMGraphTransformer çıktısını grafiğe yazmak
  - GraphCypherQAChain ile doğal dil sorgusu çalıştırmak

Lifecycle main.py lifespan'ı tarafından yönetiliyor (init_neo4j_graph / close_neo4j_graph).
"""

import logging

from langchain_neo4j import Neo4jGraph

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lifespan tarafından yönetilen singleton — lru_cache değil.
# init_neo4j_graph() / close_neo4j_graph() yalnızca main.py lifespan'ından çağrılır.
_graph: Neo4jGraph | None = None

# ─── Grafik Şema Sabitleri ────────────────────────────────────────────────────
# Bu etiketleri ve ilişki tiplerini tek bir yerde tanımladım ki
# hem graph_builder.py hem de gelecekteki sorgu servisleri aynı isimleri kullansın.

# Düğüm etiketleri (Node Labels)
NODE_CONTRACT        = "Contract"          # Ana sözleşme düğümü
NODE_CLAUSE          = "ContractClause"    # Sözleşme maddesi
NODE_ORGANIZATION    = "Organization"      # Şirket, kurum, taraf (veri sorumlusu dahil)
NODE_PERSON          = "Person"            # Gerçek kişi / ilgili kişi
NODE_OBLIGATION      = "Obligation"        # Yükümlülük
NODE_PENALTY         = "Penalty"           # Ceza / yaptırım
NODE_REGULATION      = "Regulation"        # Yasal düzenleme referansı (GDPR, KVKK vb.)
NODE_RISK_AREA       = "RiskArea"          # Risk alanı
# ── Çerez / Kişisel Veri metinleri için ek düğümler ──────────────────────────
NODE_COOKIE          = "Cookie"            # Çerez (adı, tipi, süresi)
NODE_PURPOSE         = "Purpose"           # Veri/çerez işleme amacı
NODE_LEGAL_BASIS     = "LegalBasis"        # Hukuki dayanak (kanun maddesi)
NODE_DATA_CATEGORY   = "DataCategory"      # İşlenen kişisel veri kategorisi
NODE_LEGAL_REFERENCE = "LegalReference"    # Yasal mevzuat atfı: "6698 sk. m.10", "5(2)(f)" vb.

# İlişki tipleri (Relationship Types)
REL_HAS_CLAUSE       = "HAS_CLAUSE"        # Contract → ContractClause
REL_HAS_OBLIGATION   = "HAS_OBLIGATION"    # ContractClause → Obligation
REL_PENALIZED_BY     = "PENALIZED_BY"      # Obligation → Penalty
REL_AGREED_TO        = "AGREED_TO"         # Organization → Obligation
REL_REFERENCES       = "REFERENCES"        # ContractClause → Regulation
REL_INVOLVES         = "INVOLVES"          # Contract → Organization/Person
REL_CREATES_RISK     = "CREATES_RISK"      # ContractClause → RiskArea
REL_HAS_ENTITY       = "HAS_ENTITY"        # Contract → (her türlü entity) — traversal köprüsü
# ── Çerez / Kişisel Veri ilişkileri ──────────────────────────────────────────
REL_HAS_COOKIE       = "HAS_COOKIE"        # Contract/ContractClause → Cookie
REL_PROCESSED_FOR    = "PROCESSED_FOR"     # Cookie/DataCategory → Purpose
REL_BASED_ON         = "BASED_ON"          # Purpose/Obligation → LegalBasis
REL_USES             = "USES"              # Organization → Cookie
REL_PROCESSES        = "PROCESSES"         # Organization → DataCategory
REL_CITES            = "CITES"             # LegalBasis/Obligation/Purpose → LegalReference

# LLMGraphTransformer için whitelist — aydınlatma metni + sözleşme odaklı.
ALLOWED_NODES = [
    NODE_CONTRACT, NODE_CLAUSE, NODE_ORGANIZATION, NODE_PERSON,
    NODE_OBLIGATION, NODE_PENALTY, NODE_REGULATION, NODE_RISK_AREA,
    NODE_COOKIE, NODE_PURPOSE, NODE_LEGAL_BASIS, NODE_DATA_CATEGORY,
    NODE_LEGAL_REFERENCE,
]

ALLOWED_RELATIONSHIPS = [
    REL_HAS_CLAUSE, REL_HAS_OBLIGATION, REL_PENALIZED_BY,
    REL_AGREED_TO, REL_REFERENCES, REL_INVOLVES, REL_CREATES_RISK,
    REL_HAS_COOKIE, REL_PROCESSED_FOR, REL_BASED_ON, REL_USES, REL_PROCESSES,
    REL_CITES,
]


def init_neo4j_graph() -> None:
    """
    LangChain Neo4jGraph'ı başlatıyor. Yalnızca main.py lifespan startup'ında çağrılır.

    Neo4jGraph senkron bir sürücü kullanıyor (langchain_neo4j 0.5.0'da AsyncNeo4jGraph
    mevcut değil). Servisler bu nesneyi asyncio.to_thread() içinde çağırıyor.
    """
    global _graph
    logger.info("LangChain Neo4jGraph baslatiliyor: %s", settings.NEO4J_URI)
    _graph = Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
        refresh_schema=False,
    )


def close_neo4j_graph() -> None:
    """Lifespan shutdown'da çağrılır. İç bağlantı havuzunu temizler."""
    global _graph
    if _graph is not None:
        # langchain_neo4j Neo4jGraph, _driver üzerinden resmi sürücüyü tutar.
        if hasattr(_graph, "_driver"):
            _graph._driver.close()
        _graph = None
        logger.info("Neo4jGraph kapatildi.")


def get_neo4j_graph() -> Neo4jGraph:
    if _graph is None:
        raise RuntimeError("Neo4jGraph baslatilmamis. Lifespan'i kontrol et.")
    return _graph


def get_neo4j_graph_safe() -> Neo4jGraph | None:
    """Bağlantı yoksa None döndürür; servisler bunu None kontrolüyle kullanır."""
    return _graph
