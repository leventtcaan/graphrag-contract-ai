"""
HuggingFace Lokal Embedding Yapılandırması

OpenAI embedding API'sinden HuggingFace lokal modeline geçiş kararı:

  NEDEN?
  - OpenAI'ın text-embedding-3-small'ı her vektörleme için ücretli API çağrısı
    gerektiriyor. 1000 sözleşme analizi = ciddi bir embedding faturası.
  - HuggingFace sentence-transformers modelleri tamamen lokal çalışıyor:
    API çağrısı yok, token ücreti yok, internet kesintisinde bile çalışıyor.
  - Model ilk kullanımda (~80 MB) indirilir, sonra önbelleğe alınır.

  MODEL: sentence-transformers/all-MiniLM-L6-v2
  - 384 boyutlu vektör üretiyor (OpenAI text-embedding-3-small: 1536 boyut)
  - Sözleşme metinlerindeki semantik benzerliği yakalamak için yeterince güçlü
  - normalize_embeddings=True: birim vektör — kosinüs benzerliği hesabı doğru çalışır
  - CPU üzerinde çalışır: GPU gerektirmez, deployment kolaylaşır

  ÖNEMLİ NOT — Boyut Değişikliği:
  Eğer mevcut bir pgvector veya Neo4j vector index'i 1536 boyutla oluşturulduysa,
  384 boyuta geçince bu index'lerin yeniden oluşturulması gerekir.
  Yeni kurulumda bu sorun yok; mevcut veri varsa migration gerektirir.
"""

import logging
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Embedding model sabiti — tek yerden yönetiyorum
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# 384 boyutlu vektör — Neo4j ve pgvector index'lerinde bu boyutu kullanmalıyım
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    HuggingFaceEmbeddings instance'ını döndürüyorum.

    lru_cache ile singleton davranışı — model ağırlıkları (~80 MB) bellekte
    bir kez yükleniyor, her çağrıda yeniden yüklenmesi önleniyor.

    device="cpu": GPU olmayan sunucularda (Render, Railway, Fly.io free tier)
    sorunsuz çalışıyor. GPU varsa "cuda" veya "mps" (Apple Silicon) kullanılabilir.

    normalize_embeddings=True: Vektörleri L2 normalize ediyor.
    Bu, kosinüs benzerliği hesabını iç çarpım'a indirgiyor — Neo4j GDS ve
    pgvector'ün vektör benzerlik sorgularında performans artışı sağlıyor.
    """
    logger.info("Embedding motoru hazirlaniyor: model=%s dim=%d", EMBEDDING_MODEL, EMBEDDING_DIMENSION)
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Metin listesini vektörlere dönüştüren yardımcı fonksiyon.

    HuggingFaceEmbeddings senkron çalışıyor; event loop'u bloklamak istemiyorum,
    bu yüzden asyncio.to_thread() ile thread pool'a alıyorum.
    Büyük batch'lerde (100+ chunk) sentence-transformers kendi içinde
    mini-batch işleme yapıyor — bellek taşması riski düşük.
    """
    import asyncio
    embeddings = get_embeddings()
    return await asyncio.to_thread(embeddings.embed_documents, texts)


async def embed_query(text: str) -> list[float]:
    """
    Tek bir sorgu metnini vektöre dönüştürüyorum.

    Arama sorgularında kullanacağım. embed_documents ile aynı normalize
    ayarlarını paylaşıyor — kosinüs benzerliği tutarlı kalıyor.
    """
    import asyncio
    embeddings = get_embeddings()
    return await asyncio.to_thread(embeddings.embed_query, text)
