"""
Chat / Q&A Şemaları

Kullanıcının sözleşme üzerinde doğal dilde soru sorabileceği
endpoint için request ve response şemalarını burada tanımlıyorum.
"""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Kullanıcıdan alınan soru.

    question'a min/max uzunluk koyuyorum:
      - 3 karakter minimum: "?" gibi anlamsız sorgular eleniyor
      - 500 karakter maksimum: Prompt injection saldırılarını boyut olarak da sınırlıyorum;
        gerçek bir soru 500 karakteri nadiren geçer
    """
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Sözleşme hakkında sorulmak istenen doğal dil sorusu",
        examples=["Bu sözleşmede hangi ceza maddeleri var?"],
    )


class ChatResponse(BaseModel):
    """
    LLM'in sözleşme grafiğini sorguladıktan sonra ürettiği cevap.

    answer: Kullanıcıya döndürülen doğal dil cevabı
    context_nodes: Cevabı destekleyen Neo4j düğüm verileri (şeffaflık için)
    generated_cypher: LLM'in ürettiği Cypher sorgusu (debug/audit için)
    """
    answer: str = Field(description="Sözleşmeye dayalı doğal dil cevabı")
    context_nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Cevabı destekleyen grafik düğümleri; boş olabilir",
    )
    generated_cypher: str | None = Field(
        default=None,
        description="LLM'in ürettiği Cypher sorgusu — audit ve debug için",
    )
