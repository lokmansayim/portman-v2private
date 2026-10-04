#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit) · sır ve dondurulmuş dosya koruması.

Kural kaynağı: AGENTS.md (K09 sırlar ve maskeleme, D-02 referans, dondurulmuş kayıtlar).
- Korunan dosyaya yazma: ENGEL (deny).
- İçerikte anahtar/token/özel anahtar: ENGEL.
- İçerikte telefon numarasına benzeyen sayı: SOR (ask) — gerçek numaraysa maskelenir.
Girdi stdin'den JSON (tool_input.file_path, content / new_string / edits). Çıktı: hook JSON'u, çıkış kodu 0.
"""
import json
import os
import re
import sys


def karar(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


try:
    veri = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # okunamayan girdi: karar verme, normal akış sürsün

ti = veri.get("tool_input") or {}
yol = str(ti.get("file_path") or "")
cwd = veri.get("cwd") or os.getcwd()
if os.path.isabs(yol):
    try:
        gorece = os.path.relpath(yol, cwd)
    except ValueError:
        gorece = yol
else:
    gorece = yol
gorece = gorece.replace("\\", "/")

KORUNAN = [
    # sırlar ve canlı durum (.gitignore ile aynı liste)
    (r"(^|/)[^/]*\.env$", "ortam/sır dosyası"),
    (r"(^|/)agent\.env$", "VPS ajan sırları"),
    (r"(^|/)claude_api\.json$", "hosting LLM anahtarı"),
    (r"(^|/)kanal/settings\.json$", "canlı kanal ayarı"),
    (r"(^|/)kanal/api_token\.txt$", "eşleşme anahtarı"),
    (r"(^|/)kanal/state\.json$", "canlı kuyruk durumu"),
    (r"(^|/)kanal/durum/", "canlı durum dizini"),
    (r"(^|/)kanal/lib\.snapshot\.php$", "hosting lib kopyası"),
    (r"\.(pem|key|p12|pfx)$", "anahtar dosyası"),
    (r"(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$", "SSH anahtarı"),
    # dondurulmuş kayıtlar
    (r"^SHA256SUMS$", "v1.1.1 özet kaydı (dondurulmuş)"),
    (r"^KARARLAR\.md$", "karar günlüğü (dondurulmuş; yeni karar KARARLAR/ altına yeni dosya)"),
    (r"^testler/referans/20\d\d-\d\d-\d\d[a-z]?/", "dondurulmuş referans (yeniden dondurma: dogrula.py --dondur, D-02)"),
    (r"^hosting/", "hosting kayıt kopyası (düzenlenmez, karşılaştırma için okunur)"),
]
for rx, ad in KORUNAN:
    if re.search(rx, gorece):
        karar("deny", f"'{gorece}' korunan dosya: {ad}. AGENTS.md kuralı; değişiklik gerekiyorsa Lokman'ın onayıyla ve hook dışında yapılır.")

# İçerik taraması: Write (content), Edit (new_string), MultiEdit (edits[].new_string)
parcalar = [str(ti.get("content") or ""), str(ti.get("new_string") or ""), str(ti.get("file_text") or "")]
for e in ti.get("edits") or []:
    if isinstance(e, dict):
        parcalar.append(str(e.get("new_string") or ""))
metin = "\n".join(parcalar)

SIR = [
    (r"sk-ant-[A-Za-z0-9_\-]{12,}", "Anthropic API anahtarı"),
    (r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{24,}", "OpenAI API anahtarı"),
    (r"(?<![A-Za-z0-9])EAA[A-Za-z0-9]{24,}", "Meta/WhatsApp erişim anahtarı"),
    (r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])", "AWS anahtarı"),
    (r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "özel anahtar"),
    (r"(?i)\b(api[_-]?key|access[_-]?token|secret|parola|password|sifre|şifre)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]", "sır ataması"),
]
for rx, ad in SIR:
    if re.search(rx, metin):
        karar("deny", f"İçerikte {ad} görünüyor. Sırlar koda, belgeye, commit'e ya da sohbete yazılmaz (K09). Maskele ya da ortam değişkeninden oku.")

# Türkiye cep numarası kalıbı: 5xx xxx xx xx (ondalık ve koordinat sayılarını dışlar)
TEL = r"(?<![\d.,])(?:\+90[ \-]?|0)?5\d{2}[ \-]?\d{3}[ \-]?\d{2}[ \-]?\d{2}(?![\d.,])"
if re.search(TEL, metin):
    karar("ask", "İçerikte telefon numarasına benzeyen bir sayı var. Gerçek numaraysa maskele (K09: numaralar maskelenir); değilse onayla.")

sys.exit(0)
