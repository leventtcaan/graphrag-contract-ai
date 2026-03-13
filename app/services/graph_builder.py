"""
GraphRAG Motor Servisi — Sözleşmeden Bilgi Grafiği İnşası

Bu dosya projenin kalbi. Ham sözleşme metnini alıyor, onu anlamlı
grafik düğümlerine ve ilişkilerine dönüştürüyor, ardından Neo4j'e yazıyor.

Süreç şöyle ilerliyor:
  PDF metni → Chunk'lar → LLMGraphTransformer → GraphDocument → Neo4j

Bu pipeline tamamlandığında sözleşme artık "okunabilir bir metin" değil,
sorgulanabilir bir bilgi grafiği. "Bu sözleşmede hangi cezai maddeler var?"
sorusunu artık Cypher ile milisaniyeler içinde yanıtlayabilirim.
"""

import asyncio
import logging
import unicodedata
import uuid
from pathlib import Path

import pymupdf  # PyMuPDF — pypdf'e göre çok daha güvenilir UTF-8/Türkçe desteği
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer

from app.core.config import settings
from app.core.graph_schema import (
    ALLOWED_NODES,
    ALLOWED_RELATIONSHIPS,
    NODE_CONTRACT,
    REL_HAS_CLAUSE,
    REL_HAS_ENTITY,
    get_neo4j_graph_safe,
)
from app.core.llm import get_llm_for_extraction

logger = logging.getLogger(__name__)

# ─── LLMGraphTransformer Ek Talimatlar ────────────────────────────────────────
# Bu talimatlar doğrudan extraction system prompt'una ekleniyor.
# Üç kritik sorunu çözüyor:
#   1. Property boş kalıyor: LLM entity adını sadece `id`'ye yazıp `name`'i NULL bırakıyor.
#   2. Aydınlatma metnindeki yasal atıflar ContractClause olarak çıkarılmıyor.
#   3. Adres bilgisi Organization/Person düğümüne yazılmıyor.
_EXTRACTION_INSTRUCTIONS = """
=== KRİTİK PROPERTY KURALLARI ===

KURAL 1 — `name` property her zaman dolu olmalı:
Her düğüm için `id` alanına ne yazıyorsan, aynı değeri `name` alanına da MUTLAKA yaz.
`name` alanını ASLA boş bırakma. Örnekler:
  - Organization: id="Örnek A.Ş.", name="Örnek A.Ş."
  - Person: id="Veri Sahibi", name="Veri Sahibi"
  - ContractClause: id="Madde_5_2_f", name="Madde 5(2)(f)"

KURAL 2 — Adres bilgisini mutlaka çıkar:
Metinde bir kurum veya kişinin adresi geçiyorsa (posta adresi, şehir, MERSİS adresi vb.)
bunu Organization veya Person düğümünün `address` property'sine MUTLAKA yaz.
Adres metni yoksa `address`'i boş bırakabilirsin.

KURAL 3 — Aydınlatma metni ve yasal atıflar için ÖNEMLİ:
Bu metin bir KVKK/GDPR Aydınlatma Metni olabilir. "Madde 1/2/3" formatında geleneksel
madde başlıkları olmayabilir. Bunun yerine şu formatlardaki yasal atıfları çıkar:

  a) Türk kanun maddesi atıfları → LegalReference düğümü olarak çıkar:
     Örnekler: "6698 sayılı Kanun'un 10'uncu maddesi"
               "KVKK madde 11"
               "5(2)(f) bendi"
               "Kanunun 5. maddesi kapsamında"
     → LegalReference düğümü: id="KVKK_m10", name="6698 sk. m.10",
       number="10", article="5(2)(f)"

  b) Aydınlatma metni bölümleri → ContractClause düğümü olarak çıkar:
     Örnekler: "Veri Sorumlusunun Kimliği", "Kişisel Verilerin İşlenme Amaçları",
               "Aktarılan Taraflar ve Aktarım Amaçları", "Haklarınız"
     → ContractClause düğümü: id="Veri_Sorumlusu_Kimligi",
       name="Veri Sorumlusunun Kimliği"

  c) LegalBasis (hukuki dayanak) ifadeleri → LegalBasis düğümü:
     Örnekler: "açık rıza", "kanuni yükümlülük", "meşru menfaat",
               "sözleşmenin ifası için zorunluluk"
     → LegalBasis düğümü: id="Acik_Riza", name="Açık Rıza",
       basis="KVKK m.5/1"

KURAL 4 — Veri kategorilerini çıkar:
"ad-soyad", "TC kimlik numarası", "e-posta", "telefon", "IP adresi",
"çerez verisi", "konum verisi" gibi ifadeler → DataCategory düğümü.
"""

# ─── Metin Bölücü Yapılandırması ──────────────────────────────────────────────
# chunk_size=1000 token: LLMGraphTransformer'ın bağlam penceresi içinde kalması için.
# chunk_overlap=100: Madde sınırlarında kopan bilgiyi yakalamak için örtüşme bırakıyorum.
# separators sırası: önce çift satır atlama (paragraf), sonra tek satır, son çare nokta.
_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


def _normalize_text(text: str) -> str:
    """
    PDF'den gelen metni temizliyor ve UTF-8 bütünlüğünü garanti altına alıyorum.

    PyMuPDF zaten UTF-8 döndürüyor ama bazı embedded font'lu PDF'lerde
    Unicode birleştirme karakterleri (combining marks) ayrı kod noktaları
    olarak gelebiliyor. NFC normalizasyonu bunları birleştirir:
    örneğin "I\u0307" (I + combining dot) → "İ"
    """
    # NFC: Türkçe İ, Ğ, Ş, Ü, Ö, Ç karakterlerini tek kod noktasına indirger
    return unicodedata.normalize("NFC", text)


def _load_documents_from_path(file_path: Path) -> list[Document]:
    """
    PDF'den LangChain Document listesi yüklüyorum — tam eager load.

    Tasarım ilkesi: Bu fonksiyondan dönen listede PyMuPDF'e ait hiçbir
    obje (Document, Page, Pixmap vb.) bulunmaz. Her Document.page_content
    değeri saf Python str'dir; PDF kapatıldıktan sonra güvenle okunabilir.

    Neden with + del + str():
      - with: Document.__exit__ pdf.close() garantiler, finally unutulamaz
      - del page: Page objesi her iterasyon sonunda Python heap'ten düşer
      - str(raw): get_text() zaten str döndürür ama açık kopya isteği
        PyMuPDF'in gelecekteki buffer optimizasyonlarına karşı sigorta
    """
    documents: list[Document] = []
    total_pages = 0

    with pymupdf.open(str(file_path)) as pdf:
        total_pages = len(pdf)
        for page_num in range(total_pages):
            page = pdf[page_num]
            raw_text = str(page.get_text("text"))   # kesin str kopyası
            del page                                 # PyMuPDF Page referansını bırak
            clean_text = _normalize_text(raw_text)
            if clean_text.strip():
                documents.append(Document(
                    page_content=clean_text,
                    metadata={"page": page_num, "source": str(file_path)},
                ))
    # with bloğu kapandı → pdf.close() çağrıldı.
    # documents içinde artık yalnızca plain Python str ve dict var.

    logger.info(
        "PDF yuklendi (PyMuPDF): %s — %d sayfa, %d dolu sayfa",
        file_path.name, total_pages, len(documents),
    )
    return documents


def _split_documents(documents: list[Document]) -> list[Document]:
    """
    Document listesini chunk'lara bölüyorum.
    Her chunk'a kaynak sayfası metadata olarak ekleniyor — kökenini kaybetmiyorum.
    """
    chunks = _text_splitter.split_documents(documents)
    logger.info("Metin bolundu: %d sayfa → %d chunk", len(documents), len(chunks))
    return chunks


def _extract_graph_documents(
    chunks: list[Document],
    contract_id: uuid.UUID,
) -> list:
    """
    LLMGraphTransformer ile her chunk'tan düğüm ve ilişki çıkarıyorum.
    Bu fonksiyon senkron ve LLM çağrısı yaptığı için yavaş —
    asyncio.to_thread() ile thread pool'da çalıştırılıyor.

    allowed_nodes ve allowed_relationships ile transformer'ı sözleşme
    domenine kilitliyorum. Kısıtlama olmazsa "color", "size" gibi anlamsız
    düğümler de üretilir.

    GROQ UYUMLULUĞU:
    LLMGraphTransformer iki modda çalışabilir:
      1. Tool calling (function calling) — varsayılan, yapılandırılmış output için
      2. Prompt tabanlı — tool calling desteklemeyen modeller için

    Llama-3.3-70b Groq üzerinde tool calling DESTEKLİYOR. Bu nedenle
    ignore_tool_usage=False (varsayılan) kalıyor; ekstra prompt mühendisliği
    veya fallback parser gerekmiyor.

    GROQ RATE LIMIT NOTU (ücretsiz tier):
    llama-3.3-70b-versatile: ~6000 token/dakika sınırı var.
    Büyük sözleşmelerde (30+ chunk) rate limit hatası alınabilir.
    Production'da Groq Developer tier (ücretli, yüksek limit) veya
    chunk'lar arası kısa sleep() eklenebilir.
    """
    llm = get_llm_for_extraction()

    transformer = LLMGraphTransformer(
        llm=llm,
        allowed_nodes=ALLOWED_NODES,
        allowed_relationships=ALLOWED_RELATIONSHIPS,
        # strict_mode=True: sadece whitelist'teki tip ve ilişkileri kabul et
        strict_mode=True,
        # node_properties: hangi özelliklerin çıkarılacağını açıkça belirtiyorum.
        # True yerine liste kullanmak LLM'e hangi alanları araması gerektiğini gösteriyor.
        node_properties=[
            "name", "type", "duration", "provider", "description", "basis",
            # Adres bilgileri: Organization ve Person düğümleri için
            "address", "location",
            # Madde numaraları: "5(2)(f)", "8.1.b" gibi parantezli/noktalı formatlar
            "number", "clause_number", "article",
            # Sayısal değerler: ceza miktarı, süre vb.
            "value", "amount",
        ],
        additional_instructions=_EXTRACTION_INSTRUCTIONS,
    )

    logger.info(
        "LLMGraphTransformer calistiriliyor: %d chunk, contract_id=%s",
        len(chunks), contract_id,
    )

    graph_documents = transformer.convert_to_graph_documents(chunks)

    # ── Çıkarılan varlıkları logla ────────────────────────────────────────────
    total_nodes = sum(len(gd.nodes) for gd in graph_documents)
    total_rels  = sum(len(gd.relationships) for gd in graph_documents)
    logger.info(
        "Extraction tamamlandi: %d grafik belgesi, %d dugum, %d iliski",
        len(graph_documents), total_nodes, total_rels,
    )
    for gd in graph_documents:
        for node in gd.nodes:
            logger.debug(
                "  DUGUM  %-20s  id=%-30s  props=%s",
                node.type, node.id, node.properties,
            )
        for rel in gd.relationships:
            logger.debug(
                "  ILISKI (%s)-[%s]->(%s)",
                rel.source.id, rel.type, rel.target.id,
            )

    return graph_documents


def _save_to_neo4j(
    graph_documents: list,
    contract_id: uuid.UUID,
) -> str:
    """
    Çıkarılan grafik belgelerini Neo4j'e yazıyorum ve ana Contract düğümünü bağlıyorum.
    Senkron — çağıran taraf asyncio.to_thread() içinde çalıştırıyor.

    Döndürdüğüm değer: Neo4j'deki ana Contract düğümünün ID'si (PostgreSQL'e kaydedilecek).
    """
    graph = get_neo4j_graph_safe()
    if graph is None:
        logger.warning("Neo4j bağlantısı yok — graf kaydı atlanıyor.")
        return ""

    # ── Ana Contract düğümünü oluştur veya güncelle ───────────────────────────
    # MERGE: Aynı ID'li düğüm zaten varsa yenisini oluşturma, sadece property güncelle.
    # Bu idempotent davranış: aynı sözleşmeyi iki kez analiz etmek çift düğüm yaratmaz.
    contract_node_id = f"contract_{contract_id}"
    graph.query(
        f"""
        MERGE (c:{NODE_CONTRACT} {{contract_db_id: $contract_id}})
        SET c.node_id = $node_id, c.updated_at = datetime()
        RETURN c
        """,
        params={"contract_id": str(contract_id), "node_id": contract_node_id},
    )

    # ── Her entity düğümüne contract_id property ekle ────────────────────────
    # NEDEN: add_graph_documents ID'leri normalize edebilir (büyük/küçük harf,
    # boşluk kırpma vb.), bu yüzden sonradan "node.id ile MATCH" güvenilir değil.
    # Property tabanlı eşleşme her koşulda çalışır ve multi-tenant izolasyonu sağlar.
    # Bu döngü add_graph_documents ÇAĞRILMADAN önce çalışmalı.
    contract_id_str = str(contract_id)
    for gd in graph_documents:
        for node in gd.nodes:
            node.properties["contract_id"] = contract_id_str

    # ── Chunk'lardan çıkarılan grafik belgelerini Neo4j'e ekle ────────────────
    # add_graph_documents her GraphDocument'ı Neo4j node/edge'e dönüştürür.
    # baseEntityLabel=True: tüm düğümlere "__Entity__" etiketi de ekler — şema sorgularında faydalı.
    # include_source=False: kaynak chunk düğümlerini ekleme — şemayı sade tutmak için.
    graph.add_graph_documents(
        graph_documents,
        baseEntityLabel=True,
        include_source=False,
    )

    # ── ContractClause düğümlerini Contract'a bağla ──────────────────────────
    graph.query(
        f"""
        MATCH (c:{NODE_CONTRACT} {{contract_db_id: $contract_id}})
        MATCH (clause:ContractClause {{contract_id: $contract_id}})
        WHERE NOT (c)-[:{REL_HAS_CLAUSE}]->(clause)
        MERGE (c)-[:{REL_HAS_CLAUSE}]->(clause)
        """,
        params={"contract_id": contract_id_str},
    )

    # ── Tüm entity'leri Contract'a bağla — property tabanlı MATCH ─────────────
    # ÖNCEKİ YÖNTEMİN SORUNU: MATCH (e:__Entity__) WHERE e.id = eid
    #   → add_graph_documents ID'yi normalize edebiliyor (trim, toLower vb.)
    #   → Eşleşme başarısız olunca HAS_ENTITY oluşmuyor → chat boş dönüyor.
    # YENİ YÖNTEM: az önce eklediğimiz contract_id property üzerinden MATCH.
    #   → ID uyumsuzluğu riski yok; property Neo4j'e olduğu gibi yazılıyor.
    link_result = graph.query(
        f"""
        MATCH (c:{NODE_CONTRACT} {{contract_db_id: $contract_id}})
        MATCH (e:__Entity__ {{contract_id: $contract_id}})
        WHERE NOT e:Contract AND NOT (c)-[:{REL_HAS_ENTITY}]->(e)
        MERGE (c)-[:{REL_HAS_ENTITY}]->(e)
        RETURN count(e) AS linked
        """,
        params={"contract_id": contract_id_str},
    )
    linked_count = link_result[0]["linked"] if link_result else 0
    logger.info(
        "Entity linking tamamlandi: %d entity Contract'a baglandi. contract_id=%s",
        linked_count, contract_id,
    )

    # ── Şemayı yenile: chat zinciri güncel şemayı görsün ─────────────────────
    # lru_cache'li Neo4jGraph instance'ı stale schema tutabilir.
    # Yeni düğüm/ilişki tipleri eklendikten hemen sonra refresh yapıyoruz.
    graph.refresh_schema()
    logger.info("Neo4j şeması yenilendi.")

    logger.info("Graf Neo4j'e kaydedildi. contract_node_id=%s", contract_node_id)
    return contract_node_id


async def build_contract_graph(
    contract_id: uuid.UUID,
    file_path: str,
) -> str:
    """
    Sözleşmeden tam bilgi grafiği inşa eden ana async fonksiyon.

    Bu fonksiyon üç ağır iş yapıyor:
      1. PDF'i yükle ve chunk'lara böl   (IO-bound → to_thread)
      2. LLM ile entity extraction       (IO-bound + CPU → to_thread)
      3. Neo4j'e kaydet                  (IO-bound → to_thread)

    Her adım thread pool'da çalışıyor çünkü LangChain'in bu sınıfları senkron.
    asyncio.to_thread() ile event loop'u bloklamıyorum — FastAPI diğer isteklere
    yanıt vermeye devam edebiliyor.

    Döndürdüğü değer: Neo4j'deki Contract düğümünün node_id'si.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Sözleşme dosyası bulunamadı: {file_path}")

    logger.info(
        "Graf inşası başlıyor: contract_id=%s dosya=%s",
        contract_id, path.name,
    )

    # ── Adım 1: PDF yükle ve chunk'la ─────────────────────────────────────────
    documents = await asyncio.to_thread(_load_documents_from_path, path)
    if not documents:
        raise ValueError(f"PDF'den içerik çıkarılamadı: {file_path}")

    chunks = await asyncio.to_thread(_split_documents, documents)

    # ── Adım 2: LLM ile entity/relation extraction ────────────────────────────
    # Bu adım en yavaş ve en pahalı adım — her chunk bir LLM çağrısı.
    # Büyük sözleşmeler için Celery task'a taşımayı planlıyorum.
    graph_documents = await asyncio.to_thread(
        _extract_graph_documents, chunks, contract_id
    )

    if not graph_documents:
        logger.warning("Hiç graf belgesi üretilemedi: contract_id=%s", contract_id)
        return ""

    # ── Adım 3: Neo4j'e kaydet ────────────────────────────────────────────────
    node_id = await asyncio.to_thread(_save_to_neo4j, graph_documents, contract_id)

    logger.info(
        "Graf inşası tamamlandi: contract_id=%s node_id=%s",
        contract_id, node_id,
    )
    return node_id
