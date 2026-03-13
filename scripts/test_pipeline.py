"""
IT Law Project — Uçtan Uca Pipeline Test Betiği

Bu betik, Swagger UI üzerinden elle yapılan test akışını otomatik olarak çalıştırır:
  1. Auth   → JWT token al
  2. Create → Yeni sözleşme kaydı oluştur
  3. Upload → PDF dosyasını yükle
  4. Analyze→ GraphRAG analizini başlat (LLMGraphTransformer → Neo4j)
  5. Chat   → Doğal dil sorusu sor, yanıtı al
  6. Sonuç  → Yanıtı renkli biçimde ekrana yaz

Çalıştırma:
    python scripts/test_pipeline.py

Gereksinim: Uvicorn çalışıyor olmalı (port 8000).
"""

import sys
import time
from pathlib import Path

import requests

# ─── ANSI Renk Kodları ────────────────────────────────────────────────────────
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

# ─── Sabitler ─────────────────────────────────────────────────────────────────
BASE_URL    = "http://localhost:8000/api/v1"
USERNAME    = "admin@test.com"
PASSWORD    = "admin123"
PDF_PATH    = Path(__file__).parent.parent / "cerez_metni.pdf"
SORU        = (
    "Bu aydınlatma metnine göre, kişisel verilerin işlenmesinde 6698 sayılı Kanun'un "
    "hangi maddesine ve hukuki sebebine dayanılmaktadır? Ayrıca sistemde birinci taraf "
    "kalıcı çerez olarak hangileri kullanılmaktadır?"
)


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def baslik(numara: int, metin: str) -> None:
    """Adım başlığını renkli biçimde yazdır."""
    print(f"\n{BOLD}{CYAN}[{numara}/5] {metin}{RESET}")
    print(f"{DIM}{'─' * 55}{RESET}")


def basari(metin: str) -> None:
    print(f"  {GREEN}✓{RESET} {metin}")


def bilgi(metin: str) -> None:
    print(f"  {YELLOW}→{RESET} {metin}")


def hata(metin: str) -> None:
    print(f"  {RED}✗{RESET} {metin}")


def cevap_yazdir(cevap: str, cypher: str | None) -> None:
    """LLM yanıtını kutucuk içinde biçimli yazdır."""
    genislik = 60
    print(f"\n{BOLD}{MAGENTA}{'═' * genislik}{RESET}")
    print(f"{BOLD}{MAGENTA}  LLM CEVABI{RESET}")
    print(f"{BOLD}{MAGENTA}{'═' * genislik}{RESET}")

    # Uzun cevabı satır satır kes ve hizala
    kelimeler = cevap.split()
    satir, satirlar = [], []
    for kelime in kelimeler:
        if sum(len(k) + 1 for k in satir) + len(kelime) > genislik - 4:
            satirlar.append(" ".join(satir))
            satir = [kelime]
        else:
            satir.append(kelime)
    if satir:
        satirlar.append(" ".join(satir))

    for s in satirlar:
        print(f"  {s}")

    if cypher:
        print(f"\n{BOLD}{DIM}  Üretilen Cypher:{RESET}")
        # Cypher'ı 55 karakterde kes
        for parcа in [cypher[i:i+55] for i in range(0, min(len(cypher), 220), 55)]:
            print(f"  {DIM}{parcа}{RESET}")
        if len(cypher) > 220:
            print(f"  {DIM}... (kısaltıldı){RESET}")

    print(f"{BOLD}{MAGENTA}{'═' * genislik}{RESET}\n")


# ─── Adım Fonksiyonları ───────────────────────────────────────────────────────

def adim_auth() -> str:
    """1. Adım: Login isteği at, JWT token döndür."""
    baslik(1, "AUTH — JWT Token Al")
    try:
        yanit = requests.post(
            f"{BASE_URL}/auth/login/access-token",
            data={"username": USERNAME, "password": PASSWORD},
            timeout=10,
        )
        yanit.raise_for_status()
        token = yanit.json()["access_token"]
        basari(f"Token alındı: {token[:30]}...")
        return token
    except requests.exceptions.ConnectionError:
        hata("Sunucuya bağlanılamadı. Uvicorn çalışıyor mu? (port 8000)")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        hata(f"HTTP {yanit.status_code}: {yanit.text}")
        sys.exit(1)
    except KeyError:
        hata(f"Yanıtta 'access_token' yok: {yanit.text}")
        sys.exit(1)


def adim_create(headers: dict) -> str:
    """2. Adım: Yeni sözleşme kaydı oluştur, UUID döndür."""
    baslik(2, "CREATE — Sözleşme Kaydı Oluştur")
    try:
        yanit = requests.post(
            f"{BASE_URL}/contracts/",
            json={"title": "Çerez Aydınlatma Metni"},
            headers=headers,
            timeout=10,
        )
        yanit.raise_for_status()
        sozlesme_id = yanit.json()["id"]
        basari(f"Sözleşme oluşturuldu")
        bilgi(f"ID: {sozlesme_id}")
        bilgi(f"Durum: {yanit.json().get('status', '?')}")
        return sozlesme_id
    except requests.exceptions.HTTPError:
        hata(f"HTTP {yanit.status_code}: {yanit.text}")
        sys.exit(1)


def adim_upload(sozlesme_id: str, headers: dict) -> None:
    """3. Adım: PDF dosyasını multipart/form-data olarak yükle."""
    baslik(3, "UPLOAD — PDF Dosyasını Yükle")

    # PDF dosyasını kontrol et
    if not PDF_PATH.exists():
        hata(f"PDF bulunamadı: {PDF_PATH}")
        hata("Proje kök dizinine 'cerez_metni.pdf' dosyasını koy.")
        sys.exit(1)

    dosya_boyutu = PDF_PATH.stat().st_size
    bilgi(f"Dosya: {PDF_PATH.name} ({dosya_boyutu:,} byte)")

    try:
        with open(PDF_PATH, "rb") as pdf:
            yanit = requests.post(
                f"{BASE_URL}/contracts/{sozlesme_id}/upload",
                files={"file": (PDF_PATH.name, pdf, "application/pdf")},
                headers=headers,
                timeout=30,
            )
        yanit.raise_for_status()
        basari("PDF başarıyla yüklendi")
        bilgi(f"Yeni durum: {yanit.json().get('status', '?')}")
    except requests.exceptions.HTTPError:
        hata(f"HTTP {yanit.status_code}: {yanit.text}")
        sys.exit(1)


def adim_analyze(sozlesme_id: str, headers: dict) -> None:
    """4. Adım: GraphRAG analizini tetikle. LLM entity extraction + Neo4j yükleme."""
    baslik(4, "ANALYZE — GraphRAG Analizini Başlat")
    bilgi("Bu adım LLM çağrıları içerdiği için 30–120 saniye sürebilir...")
    bilgi("Groq rate limit: ~6000 token/dk (büyük PDF'lerde bekleme normaldir)")

    baslangic = time.time()
    try:
        yanit = requests.post(
            f"{BASE_URL}/contracts/{sozlesme_id}/analyze",
            headers=headers,
            # Büyük PDF'lerde LLM rate limit nedeniyle süre uzayabilir
            timeout=300,
        )
        sure = time.time() - baslangic
        yanit.raise_for_status()
        basari(f"Analiz tamamlandı! ({sure:.1f} saniye)")
        bilgi(f"Yeni durum: {yanit.json().get('status', '?')}")
        bilgi(f"Neo4j node ID: {yanit.json().get('neo4j_node_id', 'yok')}")
    except requests.exceptions.Timeout:
        hata("Zaman aşımı (300s). Sözleşme çok büyük olabilir veya Groq rate limit aşıldı.")
        hata("Swagger UI üzerinden durumu elle kontrol et: GET /contracts/{id}")
        sys.exit(1)
    except requests.exceptions.HTTPError:
        hata(f"HTTP {yanit.status_code}: {yanit.text}")
        sys.exit(1)


def adim_chat(sozlesme_id: str, headers: dict) -> None:
    """5. Adım: Doğal dil sorusu sor, GraphCypherQAChain ile yanıt al."""
    baslik(5, "CHAT — Doğal Dil Sorusu Sor")
    bilgi("Soru:")
    # Soruyu satırlara böl
    for parca in [SORU[i:i+55] for i in range(0, len(SORU), 55)]:
        print(f"    {DIM}{parca}{RESET}")

    try:
        yanit = requests.post(
            f"{BASE_URL}/contracts/{sozlesme_id}/chat",
            json={"question": SORU},
            headers=headers,
            timeout=60,
        )
        yanit.raise_for_status()
        veri = yanit.json()

        basari("Yanıt alındı")
        cevap_yazdir(
            cevap=veri.get("answer", "(Yanıt yok)"),
            cypher=veri.get("generated_cypher"),
        )
    except requests.exceptions.HTTPError:
        hata(f"HTTP {yanit.status_code}: {yanit.text}")
        sys.exit(1)


# ─── Ana Akış ─────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{BOLD}{'═' * 55}{RESET}")
    print(f"{BOLD}  IT Law Project — Uçtan Uca Pipeline Testi{RESET}")
    print(f"{BOLD}{'═' * 55}{RESET}")
    print(f"  Sunucu : {BASE_URL}")
    print(f"  PDF    : {PDF_PATH.name}")

    # 1. Token al
    token = adim_auth()
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Sözleşme oluştur
    sozlesme_id = adim_create(auth_headers)

    # 3. PDF yükle
    adim_upload(sozlesme_id, auth_headers)

    # 4. Analiz et
    adim_analyze(sozlesme_id, auth_headers)

    # 5. Sohbet et
    adim_chat(sozlesme_id, auth_headers)

    print(f"{BOLD}{GREEN}  ✓ Pipeline tamamlandı!{RESET}")
    print(f"{BOLD}{'═' * 55}{RESET}\n")


if __name__ == "__main__":
    main()
