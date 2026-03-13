"""
Neo4j Grafik Şema ve LangChain Köprüsü

Bu modül iki görevi üstleniyor:
  1. LangChain'in Neo4jGraph nesnesini başlatmak — GraphRAG sorgu zincirlerinin bağlandığı nokta
  2. Grafik şemasını (node labels, relationship types) tek bir yerde tanımlamak

Neo4jGraph ile resmi neo4j driver (neo4j_db.py) arasındaki fark:
  - neo4j_db.py: Düşük seviye async driver — CRUD, custom Cypher sorguları
  - Neo4jGraph (LangChain): Yüksek seviye sarmalayıcı — LLMGraphTransformer çıktısını
    alıp grafiğe yazmak, GraphCypherQAChain ile doğal dil sorgusu çalıştırmak

İkisini birlikte kullanıyorum; çakışmıyorlar.
"""

import logging
from functools import lru_cache

from langchain_neo4j import Neo4jGraph

from app.core.config import settings

logger = logging.getLogger(__name__)

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

# LLMGraphTransformer için whitelist — çerez aydınlatma metni odaklı.
ALLOWED_NODES = [
    NODE_CONTRACT, NODE_CLAUSE, NODE_ORGANIZATION, NODE_PERSON,
    NODE_OBLIGATION, NODE_PENALTY, NODE_REGULATION, NODE_RISK_AREA,
    NODE_COOKIE, NODE_PURPOSE, NODE_LEGAL_BASIS, NODE_DATA_CATEGORY,
]

ALLOWED_RELATIONSHIPS = [
    REL_HAS_CLAUSE, REL_HAS_OBLIGATION, REL_PENALIZED_BY,
    REL_AGREED_TO, REL_REFERENCES, REL_INVOLVES, REL_CREATES_RISK,
    REL_HAS_COOKIE, REL_PROCESSED_FOR, REL_BASED_ON, REL_USES, REL_PROCESSES,
]


@lru_cache(maxsize=1)
def get_neo4j_graph() -> Neo4jGraph:
    """
    LangChain Neo4jGraph instance'ını döndürüyorum.

    Bu nesne senkron çalışıyor — LangChain'in Neo4j entegrasyonu şu an
    fully async değil. graph_builder.py içinde asyncio.to_thread() ile
    thread pool'a alarak event loop'u bloklamıyorum.

    lru_cache ile singleton yapıyorum: her sorgu için yeniden bağlantı açmak istemiyorum.
    """
    logger.info("LangChain Neo4jGraph baslatiliyor: %s", settings.NEO4J_URI)
    graph = Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
        # refresh_schema=False: başlangıçta yükleme, _save_to_neo4j ve _build_chain
        # içinde graph.refresh_schema() ile manuel yeniliyoruz.
        refresh_schema=False,
    )
    return graph


def get_neo4j_graph_safe() -> Neo4jGraph | None:
    """
    Neo4j bağlantısı olmadığında None döndüren güvenli versiyon.
    graph_builder.py'de Docker olmadan test ederken None kontrolü yapabiliyorum.
    """
    try:
        return get_neo4j_graph()
    except Exception as e:
        logger.warning("Neo4jGraph baslatma hatasi: %s", e)
        return None
