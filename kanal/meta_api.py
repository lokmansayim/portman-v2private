"""İE-06 · Meta WhatsApp Cloud API: webhook imzası, hub doğrulaması, gelen olayın çözümü, mesaj yükleri, medya ve gönderim.

Hosting'teki lib.php (pm_valid_signature, pm_graph, pm_remote, pm_contact) ve feature.php'nin (pm_kanal_text, pm_kanal_reply,
pm_kanal_dosya, pm_kanal_medya, pm_kanal_interactive, kabul koşulu) Python karşılığı. Sınırlar ve hata adları feature.php ile
aynıdır; testler/kalici/test_meta_api.py bunları sınar. Ağa yalnız GraphIstemci çıkar ve `http` parametresiyle sahtelenir.
Sır tutmaz: anahtarlar MetaAyar ile dışarıdan gelir; hata metinlerinde anahtar maskelenir, günlüğe yazılmaz.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

GRAPH = "https://graph.facebook.com"
GRAPH_SURUM_VARSAYILAN = "v23.0"
# WhatsApp Cloud API sınırları (feature.php PM_KANAL_WA ile aynı)
SINIR = {"buton": 3, "buton_baslik": 20, "buton_id": 256, "liste_dugme": 20, "liste_satir": 10, "satir_baslik": 24,
         "satir_aciklama": 72, "satir_id": 200, "bolum_baslik": 24, "govde": 1024, "altbilgi": 60, "baslik_metin": 60, "cta_metin": 20}
METIN_EN_COK = 4000
BELGE_ALTYAZI = 1000
GORSEL_ALTYAZI = 1024
PDF_EN_COK = 25 * 1024 * 1024
GORSEL_EN_COK = 5 * 1024 * 1024
MEDYA_INDIRME_EN_COK = 25 * 1024 * 1024
GOVDE_EN_COK = 2 * 1024 * 1024                  # webhook gövdesi (feature.php: 2 MiB)
DURUMLAR = ("sent", "delivered", "read", "failed")
TESLIM_SIRASI = {"accepted": 0, "sent": 1, "failed": 2, "delivered": 3, "read": 4}
MEDYA_TURLERI = ("image", "document", "video", "audio", "sticker")
_NUMARA = re.compile(r"^[1-9][0-9]{7,14}$")      # pm_contact: ülke koduyla 8–15 hane, yalnız rakam
_WAMID = re.compile(r"^wamid\.[A-Za-z0-9=_\-+/]{1,294}$")
_CTA_URL = re.compile(r"^https://[^\s\"'<>]{4,1900}$")
_MEDYA_ID = re.compile(r"^[0-9]{1,40}$")


class MetaHatasi(RuntimeError):
    """Graph API hatası ya da beklenmeyen cevap. kod: HTTP durum kodu (ağ hatasında None). Metin maskelidir."""

    def __init__(self, mesaj: str, kod: int | None = None):
        super().__init__(mesaj)
        self.kod = kod


class EtkilesimGecersiz(ValueError):
    """Etkileşimli satır Cloud API sınırlarını aşıyor (feature.php: interactive_invalid: <alan>). Gönderilmez, yeniden denenmez."""


class DosyaGecersiz(ValueError):
    """Satırın dosyası yok, değişmiş, türü izinli değil ya da çok büyük (feature.php pm_kanal_dosya hata adları)."""


class SablonGecersiz(ValueError):
    """Şablon satırı Meta kurallarına uymuyor (template_invalid: <alan>): ad, dil, boş ya da satır sonlu değişken, düğme. Gönderilmez."""


# ───────────────────────── imza, doğrulama, numara ─────────────────────────
def numara_gecerli(numara) -> bool:
    return bool(_NUMARA.match(str(numara or "")))


def wamid_gecerli(kimlik) -> bool:
    return bool(_WAMID.match(str(kimlik or "")))


def imza_gecerli(govde: bytes, baslik: str | None, app_secret: str) -> bool:
    """X-Hub-Signature-256: 'sha256=' + HMAC-SHA256(gövde, app secret). Sabit zamanlı karşılaştırma."""
    if not app_secret or not baslik or not str(baslik).startswith("sha256="):
        return False
    beklenen = hmac.new(app_secret.encode("utf-8"), govde, hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(baslik)[7:].strip().lower().encode("utf-8"), beklenen.encode("ascii"))   # bayt: ASCII dışı başlık TypeError vermesin


def imzala(govde: bytes, app_secret: str) -> str:
    """Testler ve kuru koşu için: Meta'nın üreteceği başlık."""
    return "sha256=" + hmac.new(app_secret.encode("utf-8"), govde, hashlib.sha256).hexdigest()


def hub_cevabi(sorgu: dict, verify_token: str) -> str | None:
    """Meta'nın webhook kaydı: GET ?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…  → challenge metni; değilse None."""
    if not verify_token or str(sorgu.get("hub.mode") or "") != "subscribe":
        return None
    if not hmac.compare_digest(str(sorgu.get("hub.verify_token") or "").encode("utf-8"), str(verify_token).encode("utf-8")):
        return None
    return str(sorgu.get("hub.challenge") or "")


def maskele(metin: str, *sirlar: str) -> str:
    """Hata metinlerinden anahtarları çıkarır: verilen değerler ve anahtara benzeyen diziler."""
    m = str(metin or "")
    for s in sirlar:
        if s and len(s) >= 8:
            m = m.replace(s, "[GİZLİ]")
    m = re.sub(r"EAA[A-Za-z0-9]{20,}", "[GİZLİ]", m)
    m = re.sub(r"sk-ant-[A-Za-z0-9_\-]{10,}", "[GİZLİ]", m)
    return m


# ───────────────────────── gelen olayın çözümü (feature.php pm_kanal_text, pm_kanal_reply) ─────────────────────────
def gelen_metin(m: dict) -> str:
    kind = str(m.get("type") or "")
    medya = m.get(kind) if isinstance(m.get(kind), dict) else {}
    if kind == "text":
        return str((m.get("text") or {}).get("body") or "")
    if kind == "button":
        return str((m.get("button") or {}).get("text") or "")
    if kind == "interactive":
        i = m.get("interactive") or {}
        return str((i.get("button_reply") or {}).get("title") or (i.get("list_reply") or {}).get("title") or "")
    if kind in MEDYA_TURLERI:
        return str(medya.get("caption") or medya.get("filename") or "")
    if kind == "location":
        return f"Konum: {medya.get('name') or medya.get('address') or ''} {medya.get('latitude') or ''}, {medya.get('longitude') or ''}"
    return ""


def cevap_kimligi(m: dict) -> tuple[str | None, str | None]:
    """(reply_id, reply_kind): interactive.button_reply.id | interactive.list_reply.id (ikisi de varsa list_reply) | button.payload."""
    kind = str(m.get("type") or ""); kimlik = None; tur = None
    if kind == "interactive" and isinstance(m.get("interactive"), dict):
        for k in ("button_reply", "list_reply"):
            v = m["interactive"].get(k)
            if isinstance(v, dict) and v.get("id") is not None:
                kimlik, tur = str(v["id"]), k
    elif kind == "button" and isinstance(m.get("button"), dict) and m["button"].get("payload") is not None:
        kimlik, tur = str(m["button"]["payload"]), "button"
    if kimlik is None or kimlik == "" or len(kimlik.encode("utf-8")) > 256 or re.search(r"[\x00-\x1f]", kimlik):
        return None, None
    return kimlik, tur


def medya_bilgisi(m: dict) -> tuple[str | None, str | None, str | None]:
    """(media_id, filename, mime) — gelen medya mesajı için; başka türde (None, None, None)."""
    kind = str(m.get("type") or "")
    medya = m.get(kind) if isinstance(m.get(kind), dict) else {}
    if kind not in MEDYA_TURLERI:
        return None, None, None
    mid = medya.get("id")
    return (str(mid) if mid is not None else None), medya.get("filename"), medya.get("mime_type")


# ───────────────────────── dosya ve yükler (feature.php pm_kanal_dosya, pm_kanal_interactive, pm_kanal_send) ─────────────────────────
def _kes(metin, n: int) -> str:
    return str(metin or "")[:n]


def dosya_denetle(yol, izinli: tuple[str, ...], kok: Path, sha256: str | None = None) -> tuple[Path, str]:
    """Satırın dosyası: <kok>/projects/ altında, boş değil, kayıtlı özetle aynı, türü ilk baytlardan; sınır: PDF 25 MB, görsel 5 MB."""
    try:
        gercek = Path(str(yol or "")).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise DosyaGecersiz("local_file_invalid") from None
    kok_r = (Path(kok) / "projects").resolve()
    if kok_r not in gercek.parents or not gercek.is_file() or gercek.stat().st_size < 1:
        raise DosyaGecersiz("local_file_invalid")
    veri = gercek.read_bytes()
    if sha256 and not hmac.compare_digest(str(sha256).encode("utf-8"), hashlib.sha256(veri).hexdigest().encode("ascii")):
        raise DosyaGecersiz("local_file_changed")
    bas = veri[:8]
    mime = "application/pdf" if bas.startswith(b"%PDF-") else ("image/png" if bas.startswith(b"\x89PNG\r\n\x1a\n")
                                                              else ("image/jpeg" if bas.startswith(b"\xff\xd8\xff") else ""))
    if mime == "":
        raise DosyaGecersiz("file_type_unknown")
    if mime not in izinli:
        raise DosyaGecersiz("file_type_not_allowed")
    if mime == "application/pdf" and len(veri) > PDF_EN_COK:
        raise DosyaGecersiz("pdf_too_large")
    if mime != "application/pdf" and len(veri) > GORSEL_EN_COK:
        raise DosyaGecersiz("image_too_large")
    return gercek, mime


def etkilesim_yuku(satir: dict, baslik_medya_id: str | None) -> dict:
    """Etkileşimli mesajın Meta yükü; sınırlar burada da denetlenir (aşan satır gönderilmez: EtkilesimGecersiz)."""
    L = SINIR
    i = satir.get("interactive") if isinstance(satir.get("interactive"), dict) else {}
    tip = str(i.get("type") or "")
    govde = str(((i.get("body") or {}).get("text") if isinstance(i.get("body"), dict) else None) or satir.get("body") or "").strip()
    if tip not in ("button", "list", "cta_url"):
        raise EtkilesimGecersiz("interactive_invalid: type")
    if govde == "" or len(govde) > L["govde"]:
        raise EtkilesimGecersiz("interactive_invalid: body")
    out: dict = {"type": tip, "body": {"text": govde}}
    altbilgi = (i.get("footer") or {}).get("text") if isinstance(i.get("footer"), dict) else None
    if altbilgi is not None and str(altbilgi).strip() != "":
        if len(str(altbilgi)) > L["altbilgi"]:
            raise EtkilesimGecersiz("interactive_invalid: footer")
        out["footer"] = {"text": str(altbilgi)}
    h = i.get("header") if isinstance(i.get("header"), dict) else None
    if h is not None:
        if h.get("type") == "image":
            if tip == "list":
                raise EtkilesimGecersiz("interactive_invalid: list header image")
            if baslik_medya_id is None:
                raise EtkilesimGecersiz("interactive_invalid: header media")
            out["header"] = {"type": "image", "image": {"id": baslik_medya_id}}
        elif h.get("type") == "text":
            if len(str(h.get("text") or "")) > L["baslik_metin"]:
                raise EtkilesimGecersiz("interactive_invalid: header text")
            out["header"] = {"type": "text", "text": str(h.get("text") or "")}
        else:
            raise EtkilesimGecersiz("interactive_invalid: header type")
    a = i.get("action") if isinstance(i.get("action"), dict) else {}
    if tip == "button":
        butonlar = a.get("buttons") if isinstance(a.get("buttons"), list) else []
        if not 1 <= len(butonlar) <= L["buton"]:
            raise EtkilesimGecersiz("interactive_invalid: buttons")
        ids: set[str] = set(); out["action"] = {"buttons": []}
        for b in butonlar:
            b = b if isinstance(b, dict) else {}
            r = b.get("reply") if isinstance(b.get("reply"), dict) else {}
            rid = str(r.get("id") if r.get("id") is not None else (b.get("id") if b.get("id") is not None else ""))
            baslik = str(r.get("title") if r.get("title") is not None else (b.get("title") if b.get("title") is not None else ""))
            if rid == "" or len(rid) > L["buton_id"] or baslik == "" or len(baslik) > L["buton_baslik"] or rid in ids:
                raise EtkilesimGecersiz("interactive_invalid: button")
            ids.add(rid); out["action"]["buttons"].append({"type": "reply", "reply": {"id": rid, "title": baslik}})
    elif tip == "list":
        dugme = str(a.get("button") or ""); n = 0; ids = set(); bolumler = []
        if dugme == "" or len(dugme) > L["liste_dugme"]:
            raise EtkilesimGecersiz("interactive_invalid: list button")
        for sec in (a.get("sections") if isinstance(a.get("sections"), list) else []):
            sec = sec if isinstance(sec, dict) else {}; rows = []
            for row in (sec.get("rows") if isinstance(sec.get("rows"), list) else []):
                row = row if isinstance(row, dict) else {}
                rid = str(row.get("id") or ""); baslik = str(row.get("title") or ""); ac = str(row.get("description") or "")
                if rid == "" or len(rid) > L["satir_id"] or baslik == "" or len(baslik) > L["satir_baslik"] or len(ac) > L["satir_aciklama"] or rid in ids:
                    raise EtkilesimGecersiz("interactive_invalid: row")
                ids.add(rid); n += 1
                x = {"id": rid, "title": baslik}
                if ac != "":
                    x["description"] = ac
                rows.append(x)
            if rows:
                t = str(sec.get("title") or "")
                if len(t) > L["bolum_baslik"]:
                    raise EtkilesimGecersiz("interactive_invalid: section")
                bolumler.append(({"title": t} if t != "" else {}) | {"rows": rows})
        if not 1 <= n <= L["liste_satir"]:
            raise EtkilesimGecersiz("interactive_invalid: rows")
        out["action"] = {"button": dugme, "sections": bolumler}
    else:
        p = a.get("parameters") if isinstance(a.get("parameters"), dict) else {}
        url = str(p.get("url") or ""); metin = str(p.get("display_text") or "")
        if metin == "" or len(metin) > L["cta_metin"] or not _CTA_URL.match(url):
            raise EtkilesimGecersiz("interactive_invalid: cta_url")
        out["action"] = {"name": "cta_url", "parameters": {"display_text": metin, "url": url}}
    return out


SABLON_AD_KALIBI = re.compile(r"^[a-z0-9_]{1,512}$")       # Meta şablon adı (kanal/ayarlar.py de bununla denetler)
SABLON_DIL_KALIBI = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?$")
_SABLON_AD, _SABLON_DIL = SABLON_AD_KALIBI, SABLON_DIL_KALIBI
_SABLON_BOSLUK = re.compile(r"\s{4,}")
SABLON_DEGISKEN_EN_COK = 1024
SABLON_DUGME_EN_COK = 10
SABLON_URL_SONEK_EN_COK = 1000
SABLON_YUK_EN_COK = 128                       # quick_reply payload


def sablon_metni(kalip: str, parametreler: list) -> str:
    """{{1}}, {{2}} … yer tutucularını sırayla doldurur (panelde ve günlük kaydında okunan düz metin; Meta'ya kalıp gitmez)."""
    out = kalip
    for i, p in enumerate(parametreler, 1):
        out = out.replace("{{%d}}" % i, str(p))
    return out


def sablon_yuku(satir: dict) -> dict:
    """İE-07: giden satırının `sablon` alanından Meta `template` nesnesi. satir["sablon"] = {"ad": <Meta şablon adı>, "dil": "tr",
    "govde": ["değişken 1", …], "dugmeler": [{"sub_type": "url" | "quick_reply", "index": 0, "text" | "payload": …}]}.
    Meta kuralları: ad [a-z0-9_]; her gövde değişkeni dolu, ≤1024, satır sonu ve 4+ ardışık boşluk yok; url düğmesi dinamik
    sonek (text), quick_reply düğmesi payload. İhlal → SablonGecersiz (Gonderilmedi; yeniden denenmez)."""
    s = satir.get("sablon") if isinstance(satir.get("sablon"), dict) else {}
    ad = str(s.get("ad") or "")
    if not _SABLON_AD.match(ad):
        raise SablonGecersiz("template_invalid: name")
    dil = str(s.get("dil") or "tr")
    if not _SABLON_DIL.match(dil):
        raise SablonGecersiz("template_invalid: language")
    govde = s.get("govde") if isinstance(s.get("govde"), list) else []
    parametreler = []
    for i, p in enumerate(govde, 1):
        p = str(p if p is not None else "")
        if p.strip() == "" or len(p) > SABLON_DEGISKEN_EN_COK or "\n" in p or "\t" in p or _SABLON_BOSLUK.search(p):
            raise SablonGecersiz(f"template_invalid: body {i}")
        parametreler.append({"type": "text", "text": p})
    bilesenler: list[dict] = []
    if parametreler:
        bilesenler.append({"type": "body", "parameters": parametreler})
    dugmeler = s.get("dugmeler") if isinstance(s.get("dugmeler"), list) else []
    if len(dugmeler) > SABLON_DUGME_EN_COK:
        raise SablonGecersiz("template_invalid: buttons")
    for d in dugmeler:
        d = d if isinstance(d, dict) else {}
        tur = str(d.get("sub_type") or ""); idx = d.get("index", 0)
        if type(idx) is not int or not 0 <= idx < SABLON_DUGME_EN_COK:
            raise SablonGecersiz("template_invalid: button index")
        if tur == "url":
            sonek = str(d.get("text") or "")
            if sonek == "" or len(sonek) > SABLON_URL_SONEK_EN_COK or re.search(r"[\s\"'<>]", sonek):
                raise SablonGecersiz("template_invalid: button url")
            bilesenler.append({"type": "button", "sub_type": "url", "index": str(idx), "parameters": [{"type": "text", "text": sonek}]})
        elif tur == "quick_reply":
            yuk_ = str(d.get("payload") or "")
            if yuk_ == "" or len(yuk_) > SABLON_YUK_EN_COK or "\n" in yuk_:
                raise SablonGecersiz("template_invalid: button payload")
            bilesenler.append({"type": "button", "sub_type": "quick_reply", "index": str(idx), "parameters": [{"type": "payload", "payload": yuk_}]})
        else:
            raise SablonGecersiz("template_invalid: button type")
    out: dict = {"name": ad, "language": {"code": dil}}
    if bilesenler:
        out["components"] = bilesenler
    return out


def mesaj_yuku(satir: dict, alici: str, medya_id: str | None = None, baslik_medya_id: str | None = None) -> dict:
    """Giden satırın (hosting biçimi: kind, body, filename, interactive) Meta messages yükü. biz_opaque_callback_data = satır id:
    Meta durum bildiriminde geri gelir, wamid yazılamamış satır bununla eşlenir. kind 'template' (İE-07): Meta onaylı şablon,
    24 saat penceresi dışında da gider (utility; ücretli)."""
    kind = str(satir.get("kind") or "text")
    yuk: dict = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": alici, "biz_opaque_callback_data": satir["id"]}
    govde = str(satir.get("body") or "")
    if kind == "template":
        yuk["type"] = "template"; yuk["template"] = sablon_yuku(satir)
    elif kind == "document":
        if not medya_id:
            raise ValueError("media_id")
        yuk["type"] = "document"; yuk["document"] = {"id": medya_id, "filename": str(satir.get("filename") or "belge.pdf")}
        if govde.strip() != "":
            yuk["document"]["caption"] = _kes(govde, BELGE_ALTYAZI)
    elif kind == "image":
        if not medya_id:
            raise ValueError("media_id")
        yuk["type"] = "image"; yuk["image"] = {"id": medya_id}
        if govde.strip() != "":
            yuk["image"]["caption"] = _kes(govde, GORSEL_ALTYAZI)
    elif kind == "interactive":
        yuk["type"] = "interactive"; yuk["interactive"] = etkilesim_yuku(satir, baslik_medya_id)
    else:
        if govde.strip() == "":
            raise ValueError("empty_text")
        yuk["type"] = "text"; yuk["text"] = {"body": _kes(govde, METIN_EN_COK), "preview_url": False}
    return yuk


def kabul_edilen_wamid(cevap: dict, alici: str) -> str:
    """messages POST cevabı: messages[0].id 'wamid.' ile başlamalı ve contacts[].input == alıcı olan geçerli bir wa_id olmalı."""
    wamid = ((cevap.get("messages") or [{}])[0] if isinstance(cevap.get("messages"), list) and cevap["messages"] else {}).get("id")
    ok = any(isinstance(c, dict) and c.get("input") == alici and numara_gecerli(c.get("wa_id")) for c in (cevap.get("contacts") or []))
    if not isinstance(wamid, str) or not wamid.startswith("wamid.") or not ok:
        raise MetaHatasi("send_response_uncertain")
    return wamid


def baslik_gorseli_var(satir: dict) -> bool:
    i = satir.get("interactive") if isinstance(satir.get("interactive"), dict) else {}
    h = i.get("header") if isinstance(i.get("header"), dict) else {}
    return h.get("type") == "image"


# ───────────────────────── Graph API istemcisi ─────────────────────────
@dataclass
class MetaAyar:
    phone_number_id: str
    access_token: str
    app_secret: str
    verify_token: str
    graph_version: str = GRAPH_SURUM_VARSAYILAN

    @classmethod
    def ortamdan(cls, env=None) -> "MetaAyar":
        """/etc/portman/whatsapp.env (systemd EnvironmentFile): WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, WA_APP_SECRET, WA_VERIFY_TOKEN, WA_GRAPH_VERSION."""
        e = os.environ if env is None else env
        return cls(phone_number_id=str(e.get("WA_PHONE_NUMBER_ID") or ""), access_token=str(e.get("WA_ACCESS_TOKEN") or ""),
                   app_secret=str(e.get("WA_APP_SECRET") or ""), verify_token=str(e.get("WA_VERIFY_TOKEN") or ""),
                   graph_version=str(e.get("WA_GRAPH_VERSION") or GRAPH_SURUM_VARSAYILAN))

    def tam_mi(self) -> bool:
        return bool(self.phone_number_id and self.access_token and self.app_secret and self.verify_token)


def _multipart(alanlar: dict, dosya: tuple[str, str, str, bytes]) -> tuple[str, bytes]:
    """alanlar: {ad: değer}; dosya: (alan, dosya_adı, mime, içerik)."""
    sinir = "----PortmanMeta" + uuid.uuid4().hex
    b = io.BytesIO()
    for ad, deger in alanlar.items():
        b.write(f"--{sinir}\r\nContent-Disposition: form-data; name=\"{ad}\"\r\n\r\n".encode()); b.write(str(deger).encode("utf-8")); b.write(b"\r\n")
    alan, dosya_adi, mime, icerik = dosya
    b.write(f"--{sinir}\r\nContent-Disposition: form-data; name=\"{alan}\"; filename=\"{dosya_adi}\"\r\nContent-Type: {mime}\r\n\r\n".encode())
    b.write(icerik); b.write(b"\r\n"); b.write(f"--{sinir}--\r\n".encode())
    return f"multipart/form-data; boundary={sinir}", b.getvalue()


class GraphIstemci:
    """Graph API: gönderim, medya yükleme ve indirme, numara bilgisi. http(method, url, headers, data, timeout) → (durum, başlıklar, gövde)."""

    def __init__(self, ayar: MetaAyar, http=None, zaman_asimi: int = 60):
        self.ayar = ayar
        self.http = http or self._urllib
        self.zaman_asimi = zaman_asimi

    @staticmethod
    def _urllib(method: str, url: str, headers: dict, data: bytes | None, timeout: int) -> tuple[int, dict, bytes]:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()
        except urllib.error.URLError as e:
            raise MetaHatasi(f"bağlantı: {str(e.reason)[:160]}") from None
        except OSError as e:
            raise MetaHatasi(f"bağlantı: {type(e).__name__}: {str(e)[:160]}") from None

    def _url(self, yol: str) -> str:
        return f"{GRAPH}/{self.ayar.graph_version}/{yol}"

    def _basliklar(self, ek: dict | None = None) -> dict:
        return {"Authorization": f"Bearer {self.ayar.access_token}", "User-Agent": "portman-kanal", **(ek or {})}

    def _json(self, method: str, yol: str, body: dict | None = None, multipart: tuple[str, bytes] | None = None, timeout: int | None = None) -> dict:
        headers = self._basliklar(); data = None
        if multipart is not None:
            headers["Content-Type"], data = multipart
        elif body is not None:
            headers["Content-Type"] = "application/json"; data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        durum, _hdr, govde = self.http(method, self._url(yol), headers, data, timeout or self.zaman_asimi)
        metin = govde.decode("utf-8", "replace") if isinstance(govde, (bytes, bytearray)) else str(govde)
        if durum >= 400:
            try:
                hata = json.loads(metin).get("error") or {}
                ozet = f"{hata.get('type') or ''} {hata.get('code') or ''} {hata.get('message') or ''}".strip()
            except Exception:
                ozet = metin[:200]
            raise MetaHatasi(f"HTTP {durum}: {maskele(ozet, self.ayar.access_token)[:300]}", durum)
        try:
            return json.loads(metin) if metin else {}
        except ValueError:
            raise MetaHatasi(f"HTTP {durum}: JSON değil", durum) from None

    def gonder(self, yuk: dict) -> dict:
        return self._json("POST", f"{self.ayar.phone_number_id}/messages", body=yuk)

    def medya_yukle(self, yol: Path, mime: str, dosya_adi: str) -> str:
        ctype, govde = _multipart({"messaging_product": "whatsapp", "type": mime}, ("file", dosya_adi, mime, Path(yol).read_bytes()))
        cevap = self._json("POST", f"{self.ayar.phone_number_id}/media", multipart=(ctype, govde), timeout=max(self.zaman_asimi, 120))
        mid = str(cevap.get("id") or "")
        if not _MEDYA_ID.match(mid):
            raise MetaHatasi("media_response")
        return mid

    def medya_indir(self, medya_id: str) -> tuple[bytes, str]:
        """Gelen medya: GET /<id> → {url, mime_type}; sonra o adresten içerik (Bearer ile). Dönen: (içerik, mime)."""
        if not _MEDYA_ID.match(str(medya_id or "")):
            raise MetaHatasi("media_id")
        bilgi = self._json("GET", str(medya_id))
        url = str(bilgi.get("url") or ""); mime = str(bilgi.get("mime_type") or "application/octet-stream")
        if not url.startswith("https://"):
            raise MetaHatasi("media_url")
        boyut = int(bilgi.get("file_size") or 0)
        if boyut > MEDYA_INDIRME_EN_COK:
            raise MetaHatasi("media_too_large")
        durum, _hdr, govde = self.http("GET", url, self._basliklar(), None, max(self.zaman_asimi, 120))
        if durum >= 400:
            raise MetaHatasi(f"HTTP {durum}: medya indirilemedi", durum)
        if len(govde) > MEDYA_INDIRME_EN_COK:
            raise MetaHatasi("media_too_large")
        return bytes(govde), mime

    def telefon(self) -> dict:
        """Doğrulama (Kapı 3, Kapı 5): numara kaydı okunabiliyor mu. Çıktıda anahtar yok."""
        return self._json("GET", f"{self.ayar.phone_number_id}?fields=display_phone_number,verified_name,quality_rating")
