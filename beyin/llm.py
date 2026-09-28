"""LLM adaptörü: mesaj → Talep. Model bağımsız sözleşme (JSON şeması). Anahtar hiçbir yere yazılmaz/loglanmaz.

Arka uçlar:
- "openai_chat": Chat Completions + response_format json_schema (hosting'deki sohbet botunun kullandığı, kanıtlı API yolu).
- "openai":      Responses API, json_schema çıktı.
- "anthropic":   Messages API, zorunlu araç çağrısıyla şema.
- "manuel":      hazır çıktı sözlüğü (test koşumu; LLM çağrısı yok).
Anahtar: çağıranın verdiği `anahtar` → ortam değişkeni (OPENAI_API_KEY / ANTHROPIC_API_KEY) → PORTMAN_AYARLAR_JSON dosyası.
Bu sürümde canlı anahtarla yalnız manuel yol test edildi; openai_chat/openai/anthropic yolları kurulum öz-testinde denenecek.
"""
from __future__ import annotations
import json, os, re, time, urllib.request, urllib.error
from pathlib import Path

from .sema import Talep, json_schema

PROMPT = (Path(__file__).resolve().parent / "prompt.md").read_text(encoding="utf-8")
VARSAYILAN_MODEL = {"openai_chat": "gpt-4o-mini", "openai": "gpt-4o-mini", "anthropic": "claude-haiku-4-5-20251001"}


class LLMHatasi(RuntimeError):
    pass


def _anahtar_dosyadan(yol: str | None, alan: str) -> str | None:
    """Sunucudaki mevcut ayar dosyasından anahtarı okur (panelin ayarlar.json'u); anahtar hiçbir yere yazılmaz/loglanmaz."""
    if not yol or not Path(yol).exists():
        return None
    try:
        return (json.loads(Path(yol).read_text(encoding="utf-8")).get(alan) or "").strip() or None
    except Exception:
        return None


def anahtar_bul(backend: str, anahtar: str | None = None, ayarlar_json: str | None = None) -> str:
    alan, env = ("anthropic_key", "ANTHROPIC_API_KEY") if backend == "anthropic" else ("openai_key", "OPENAI_API_KEY")
    key = (anahtar or "").strip() or os.environ.get(env) or _anahtar_dosyadan(ayarlar_json or os.environ.get("PORTMAN_AYARLAR_JSON"), alan)
    if not key:
        raise LLMHatasi(f"{backend} anahtarı bulunamadı (parametre, {env} ya da ayarlar dosyası)")
    return key


def _maskele(s: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[GIZLI]", s)


def _post(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        govde = e.read().decode("utf-8", "replace")[:600]
        try:
            mesaj = json.loads(govde).get("error", {}).get("message", govde)
        except Exception:
            mesaj = govde
        raise LLMHatasi(f"HTTP {e.code}: {_maskele(str(mesaj))[:300]}") from None
    except urllib.error.URLError as e:
        raise LLMHatasi(f"bağlantı: {str(e.reason)[:200]}") from None


def _json_ayikla(metin: str) -> dict:
    metin = metin.strip()
    if metin.startswith("```"):
        metin = re.sub(r"^```(?:json)?\s*|\s*```$", "", metin, flags=re.S)
    return json.loads(metin)


def cikar_detayli(mesaj: str, baglam: str = "", backend: str = "manuel", model: str | None = None, hazir: dict | None = None,
                  anahtar: str | None = None, ayarlar_json: str | None = None, timeout: int = 60) -> tuple[Talep, dict]:
    """Bayi mesajını Talep'e çevirir; ikinci değer ölçüm: {backend, model, girdi_token, cikti_token, sure_ms}."""
    t0 = time.time()
    if backend == "manuel":
        if hazir is None:
            raise ValueError("manuel arka uç için hazır çıktı gerekli")
        return Talep.model_validate(hazir), {"backend": "manuel", "model": None, "girdi_token": 0, "cikti_token": 0, "sure_ms": 0}

    kullanici = (f"Önceki konuşma özeti: {baglam}\n\n" if baglam else "") + f"Bayi mesajı: {mesaj}"
    schema = json_schema()
    model = model or VARSAYILAN_MODEL.get(backend)
    meta = {"backend": backend, "model": model, "girdi_token": None, "cikti_token": None, "sure_ms": None}

    if backend == "openai_chat":
        key = anahtar_bul(backend, anahtar, ayarlar_json)
        out = _post("https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {key}"},
                    {"model": model, "temperature": 0,
                     "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": kullanici}],
                     "response_format": {"type": "json_schema", "json_schema": {"name": "talep", "schema": schema, "strict": False}}},
                    timeout)
        secim = (out.get("choices") or [{}])[0]
        if secim.get("message", {}).get("refusal"):
            raise LLMHatasi("model reddetti: " + str(secim["message"]["refusal"])[:200])
        metin = secim.get("message", {}).get("content") or ""
        kullanim = out.get("usage") or {}
        meta.update(model=out.get("model") or model, girdi_token=kullanim.get("prompt_tokens"), cikti_token=kullanim.get("completion_tokens"))
        talep = Talep.model_validate(_json_ayikla(metin))
    elif backend == "openai":
        key = anahtar_bul(backend, anahtar, ayarlar_json)
        out = _post("https://api.openai.com/v1/responses", {"Authorization": f"Bearer {key}"},
                    {"model": model, "instructions": PROMPT, "input": kullanici,
                     "text": {"format": {"type": "json_schema", "name": "talep", "schema": schema, "strict": False}}}, timeout)
        metin = "".join(c.get("text", "") for o in out.get("output", []) for c in o.get("content", []) if c.get("type") == "output_text")
        kullanim = out.get("usage") or {}
        meta.update(model=out.get("model") or model, girdi_token=kullanim.get("input_tokens"), cikti_token=kullanim.get("output_tokens"))
        talep = Talep.model_validate(_json_ayikla(metin))
    elif backend == "anthropic":
        key = anahtar_bul(backend, anahtar, ayarlar_json)
        opus55 = model == "claude-opus-5-5"
        govde = {"model": model, "max_tokens": 4096 if opus55 else 1500,
                 "system": PROMPT + ("\nTalebi yalnız talep_kaydet aracını bir kez çağırarak bildir." if opus55 else ""),
                 "tools": [{"name": "talep_kaydet", "description": "Yapılandırılmış talep", "input_schema": schema}],
                 "tool_choice": {"type": "auto", "disable_parallel_tool_use": True} if opus55 else {"type": "tool", "name": "talep_kaydet"},
                 "messages": [{"role": "user", "content": kullanici}]}
        if opus55:
            govde["output_config"] = {"effort": "low"}
        out = _post("https://api.anthropic.com/v1/messages",
                    {"x-api-key": key, "anthropic-version": "2023-06-01"}, govde, timeout)
        if opus55:
            calls = [b for b in out.get("content", []) if b.get("type") == "tool_use"]
            if out.get("stop_reason") != "tool_use" or len(calls) != 1 or calls[0].get("name") != "talep_kaydet":
                raise LLMHatasi("Opus talep yanıtı tamamlanmadı veya beklenen araç çağrısı dönmedi")
        kullanim = out.get("usage") or {}
        meta.update(model=out.get("model") or model, girdi_token=kullanim.get("input_tokens"), cikti_token=kullanim.get("output_tokens"))
        talep = None
        for blok in out.get("content", []):
            if blok.get("type") == "tool_use":
                talep = Talep.model_validate(blok["input"]); break
        if talep is None:
            raise LLMHatasi("araç çağrısı dönmedi")
    else:
        raise ValueError(f"bilinmeyen arka uç: {backend}")
    meta["sure_ms"] = int((time.time() - t0) * 1000)
    return talep, meta


def cikar_guvenli(mesaj: str, baglam: str = "", backend: str = "manuel", model: str | None = None, hazir: dict | None = None,
                  **kw) -> tuple[Talep, dict]:
    """cikar_detayli + şema doğrulama hatasında tek tekrar (hata mesajı bağlama eklenir). Manuel arka uçta tekrar yok."""
    from pydantic import ValidationError
    try:
        return cikar_detayli(mesaj, baglam, backend, model, hazir, **kw)
    except ValidationError as e:
        if backend == "manuel":
            raise
        hata = "; ".join(f"{'.'.join(str(x) for x in h['loc'])}: {h['msg']}" for h in e.errors()[:4])[:400]
        ek = (baglam + " | " if baglam else "") + f"ÖNCEKİ ÇIKTIN ŞEMAYA UYMADI ({hata}); yalnız şemadaki izinli değerleri kullan, uymayanı null bırak ve belirsizliklere yaz"
        talep, meta = cikar_detayli(mesaj, ek, backend, model, hazir, **kw)
        meta["tekrar"] = 1; meta["ilk_hata"] = hata
        return talep, meta


def cikar(mesaj: str, baglam: str = "", backend: str = "manuel", model: str | None = None, hazir: dict | None = None, **kw) -> Talep:
    return cikar_detayli(mesaj, baglam, backend, model, hazir, **kw)[0]
