"""
LLM Motor Yapılandırması — Groq / Llama-3.3-70b

Bu modül, projedeki tüm LLM işlemlerinin geçtiği merkezi nokta.

OpenAI'dan Groq'a geçiş kararı bilinçli bir maliyet optimizasyonu:
  - Groq ücretsiz tier ile production deployment'ta sıfır LLM maliyeti
  - Groq'un LPU (Language Processing Unit) donanımı OpenAI API'sinden
    10-20x daha hızlı token üretiyor — kullanıcı deneyimi için kritik
  - Llama-3.3-70b tool calling destekliyor — LLMGraphTransformer ile uyumlu
  - Açık kaynak model: vendor lock-in yok, istediğimde self-host'a geçebilirim

Model seçimi: llama-3.3-70b-versatile
  - 128K context window: büyük sözleşmeler tek çağrıda işlenebilir
  - Tool calling desteği: LLMGraphTransformer'ın structured output'u çalışıyor
  - Entity extraction ve JSON formatlama'da gpt-4o-mini ile rekabet edebilir kalite
  - Groq'un Ocak 2025 önerisi; güncel benchmark'larda Llama-3.1-70b'yi geçiyor
"""

import logging
from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import settings

logger = logging.getLogger(__name__)

# Groq'un desteklediği ve entity extraction konusunda en başarılı modeli.
# Alternatif: "mixtral-8x7b-32768" — daha hızlı ama doğrulukta biraz geride.
DEFAULT_MODEL = "llama-3.3-70b-versatile"


@lru_cache(maxsize=4)
def get_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> ChatGroq:
    """
    LangChain ChatGroq instance'ı döndürüyorum.

    lru_cache ile (model, temperature) çiftine göre önbelleğe alıyorum —
    her çağrıda yeni nesne oluşturmak gereksiz. maxsize=4: farklı parametre
    kombinasyonları için slot açık bıraktım.

    temperature=0.0: Sözleşme analizi deterministik olmalı; halüsinasyon
    sözleşme hukukunda kabul edilemez.

    Groq API anahtarı yoksa veya geçersizse, LangChain çağrı anında
    AuthenticationError fırlatır — başlatma sırasında değil (lazy init).
    """
    if settings.GROQ_API_KEY == "gsk_change-me-in-env":
        logger.warning(
            "GROQ_API_KEY ayarlanmamis! LLM cagrilari basarisiz olacak. "
            ".env dosyasina gercek Groq API anahtarini ekle. "
            "Ucretsiz anahtar: https://console.groq.com"
        )

    llm = ChatGroq(
        model=model,
        temperature=temperature,
        api_key=settings.GROQ_API_KEY,
        # max_retries: Geçici API hatalarında otomatik yeniden deneme
        max_retries=2,
    )

    logger.info(
        "LLM motoru hazir: provider=groq model=%s temperature=%.1f",
        model, temperature,
    )
    return llm


def get_llm_for_extraction() -> ChatGroq:
    """
    Madde çıkarma ve sınıflandırma için özel ayarlanmış LLM.

    temperature=0.0 ile tamamen deterministik — aynı sözleşme her analizde
    aynı entity/relation kümesini üretmeli.

    LLMGraphTransformer uyumluluğu: Llama-3.3-70b, Groq üzerinde tool calling
    destekliyor. LLMGraphTransformer'ın structured output (function calling)
    modu bu sayede sorunsuz çalışıyor — ignore_tool_usage=False varsayılanı
    korunuyor, ekstra prompt mühendisliği gerekmiyor.
    """
    return get_llm(model=DEFAULT_MODEL, temperature=0.0)


def get_llm_for_summary() -> ChatGroq:
    """
    Sözleşme özetleme için hafif yaratıcılığa izin verilen LLM.
    temperature=0.1 ile sonuç biraz daha doğal ve okunabilir oluyor.
    """
    return get_llm(model=DEFAULT_MODEL, temperature=0.1)
