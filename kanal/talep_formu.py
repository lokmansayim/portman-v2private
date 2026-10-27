"""İE-20 PR-2 · Talep formu ve revizyon formu (WhatsApp Flow, uç noktasız; Kurulum Panosu satır 110 ve 61).

Formlar `kanal/formlar/talep.json` ve `revizyon.json` (Flow JSON 7.3). Meta'da bir kez kurulur (WhatsApp Manager › Flows; önce taslak
kipinde, yalnız Patron telefonunda, Lokman'ın onayıyla); kimlikleri ayara yazılır (`talep_formu.talep_flow_id`, `revizyon_flow_id`).
  - Sunuş (`kanal/worker.py`): eksik bilgi sorusu, selam, "anlayamadım" ve "Nasıl çalışır?" cevabı aynı metinle [Talep formu] düğmeli
    gider; "Neyi değiştirelim?" [Revizyon formu] düğmeli. Ek mesaj yok: düğme sorunun kendisinde; yazıyla cevap yolu açık kalır.
    Talep formu bayi kartının varsayılanları (yapı, kat, çatı, veranda; panel) ve açık taslaktaki bilgilerle dolu açılır (`ekran_verisi`).
  - Cevap (`nfm_reply`): webhook `cevap_ozeti` ile kuyruk satırına `form` yazar; satırın metni panel için özettir (`metin`); formdaki
    dosya gelen dosya kaydı olur, gönderici indirir. Talep formu LLM'siz talebe çevrilir (`talep`); dosyası PR-1'in okumasından geçer.
    Revizyon formunun açıklaması bayinin yazısı gibi okunur (bugünkü yol).
Sır ve numara tutmaz; ağ yok. Bayinin notu LLM'e gitmez (talepte özel istek olarak durur, numara maskeli)."""
from __future__ import annotations

import json
import re
from pathlib import Path

FORMLAR = Path(__file__).resolve().parent / "formlar"
EKRAN = {"talep": "TALEP", "revizyon": "REVIZYON"}
DUGME = {"talep": "Talep formu", "revizyon": "Revizyon formu"}          # flow_cta (≤ 20)
TOKEN = re.compile(r"^(tf|rv):([^:\s]{1,80})(?::([0-9]{1,3}))?$")       # tf:<iz>[:1] talep · rv:<İş Emri no>:<rev> revizyon
FLOW_ID = re.compile(r"^[0-9]{1,40}$")
MEDYA_ID = re.compile(r"^[0-9]{1,40}$")
CEVAP_EN_COK = 64 * 1024                       # response_json (dize) üst sınırı
NOT_EN_COK = 600
YAPI = {"prefabrik": "prefabrik", "celik": "çelik"}
KAT = {"1": "tek kat", "2": "iki kat"}
ODA = ("1+0", "1+1", "2+1", "3+1", "4+1", "5+1")
CATI = {"besik": "beşik çatı", "tek_egimli": "tek eğimli çatı", "kirma": "kırma çatı", "teras": "teras çatı"}
VERANDA = {"on": "önde", "yan": "yanda", "arka": "arkada", "kose": "köşede"}
NEYI = {"oda": "oda yerleşimi", "pencere": "pencere", "kapi": "kapı", "veranda": "veranda", "olcu": "ölçü", "cati": "çatı"}
# Kartta varsayılan yoksa formun seçili geleceği değer (bayi değiştirebilir). Veranda: verandasız teklif yok (Patron, 27 Ekim 2026).
SABIT_VARSAYILAN = {"yapi": "prefabrik", "kat": "1", "cati": "besik", "veranda": "on"}
KART_ALANLARI = {"yapi_turu": ("yapi", YAPI), "kat_sayisi": ("kat", KAT), "cati": ("cati", CATI), "veranda": ("veranda", VERANDA)}


def tanim(tur: str) -> dict:
    return json.loads((FORMLAR / f"{tur}.json").read_text(encoding="utf-8"))


def talep_tokeni(iz: str, taslaktan: bool = False) -> str:
    """Form açık taslağın bilgileriyle dolu sunulduysa `tf:<iz>:1` (cevabı taslağı tamamlar), değilse `tf:<iz>` (cevabı açık taslağı
    kapatır: bayi görmediği bilgiyle plan çizilmez)."""
    return f"tf:{iz}:1" if taslaktan else f"tf:{iz}"


def revizyon_tokeni(no: str, rev: int) -> str:
    return f"rv:{no}:{int(rev)}"


def _dize(v, n: int) -> str:
    return " ".join(str(v if v is not None else "").split())[:n]


def sayi(v) -> float | None:
    """"7,5" / "7.5" / 7.5 → 7.5; boş, sıfır, eksi ya da 1000'den büyükse None (ölçü uydurulmaz)."""
    s = str(v if v is not None else "").strip().replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return x if 0 < x <= 1000 else None


def _dosyalar(v) -> list[dict]:
    out = []
    for d in (v if isinstance(v, list) else [])[:10]:            # Meta: bir cevapta en çok 10 dosya
        if isinstance(d, dict) and MEDYA_ID.match(str(d.get("id") or "")):
            out.append({"id": str(d["id"]), "file_name": _dize(d.get("file_name"), 200) or None, "mime_type": _dize(d.get("mime_type"), 100) or None,
                        "sha256": _dize(d.get("sha256"), 100) or None})
    return out


def cevap_ozeti(rj) -> dict:
    """nfm_reply.response_json (dize ya da sözlük) → {tur: talep | revizyon | bilinmiyor, token, alanlar, dosyalar}. Tanınmayan alan atılır."""
    if isinstance(rj, str):
        try:
            rj = json.loads(rj[:CEVAP_EN_COK]) if len(rj) <= CEVAP_EN_COK else None
        except ValueError:
            rj = None
    rj = rj if isinstance(rj, dict) else {}
    token = _dize(rj.get("flow_token"), 120)
    m = TOKEN.match(token)
    tur = {"tf": "talep", "rv": "revizyon"}.get(m.group(1)) if m else "bilinmiyor"
    a: dict = {}
    if tur == "talep":
        for ad, izinli in (("yapi", YAPI), ("kat", KAT), ("oda", ODA), ("cati", CATI), ("veranda", VERANDA)):
            v = _dize(rj.get(ad), 20)
            if v in izinli:
                a[ad] = v
        for ad in ("alan", "en", "boy"):
            if sayi(rj.get(ad)) is not None:
                a[ad] = sayi(rj.get(ad))
        if _dize(rj.get("not"), NOT_EN_COK):
            a["not"] = str(rj.get("not")).strip()[:NOT_EN_COK]
    elif tur == "revizyon":
        neyi = rj.get("neyi") if isinstance(rj.get("neyi"), list) else []
        a["neyi"] = [x for x in NEYI if x in {str(y) for y in neyi}]
        if _dize(rj.get("aciklama"), NOT_EN_COK):
            a["aciklama"] = str(rj.get("aciklama")).strip()[:NOT_EN_COK]
    return {"tur": tur, "token": token, "alanlar": a, "dosyalar": _dosyalar(rj.get("dosya"))}


def _olcu(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def ozet(oz: dict) -> str:
    """Talep formunun tek cümlelik özeti ("Talep formu: prefabrik, tek kat, 2+1, 7 × 9 m, beşik çatı, veranda önde")."""
    a = oz.get("alanlar") or {}
    p = [YAPI[a["yapi"]] if a.get("yapi") else None, KAT.get(a.get("kat")) if a.get("kat") else None, a.get("oda")]
    if a.get("en") and a.get("boy"):
        p.append(f"{_olcu(a['en'])} × {_olcu(a['boy'])} m")
    if a.get("alan"):
        p.append(f"yaklaşık {_olcu(a['alan'])} m²")
    p += [CATI.get(a.get("cati")) if a.get("cati") else None, f"veranda {VERANDA[a['veranda']]}" if a.get("veranda") else None]
    return "Talep formu: " + (", ".join(x for x in p if x) or "boş")


def metin(oz: dict) -> str:
    """Kuyruk satırının metni (panelde görünür; çizim okumasında bayinin sözü). Revizyonda açıklama bayinin yazısıdır."""
    a = oz.get("alanlar") or {}
    dosya = " Dosya eklendi." if oz.get("dosyalar") else ""
    if oz.get("tur") == "talep":
        return ozet(oz) + "." + (f" Not: {a['not']}" if a.get("not") else "") + dosya
    if oz.get("tur") == "revizyon":
        neyi = ", ".join(NEYI[x] for x in a.get("neyi") or [])
        if a.get("aciklama"):
            return a["aciklama"] + (f" (değişecek: {neyi})" if neyi else "") + dosya
        return "Revizyon formu" + (f": {neyi}." if neyi else ".") + dosya
    return "Form cevabı."


def talep(oz: dict) -> dict:
    """Talep formu → Talep (beyin/sema.py) sözlüğü; LLM'siz. Formda olmayan alan boş kalır (karar eksik olanı sorar)."""
    from beyin import numara
    a = oz.get("alanlar") or {}
    t: dict = {"niyet": "yeni_talep", "guven": "yuksek", "ozet": ozet(oz)}
    if a.get("yapi"):
        t["yapi_turu"] = a["yapi"]
    if a.get("kat"):
        t["kat_sayisi"] = int(a["kat"])
    if a.get("oda"):
        t["oda_programi"] = a["oda"]
    if a.get("alan"):
        t["alan_m2"] = float(a["alan"])
    if a.get("en") and a.get("boy"):
        en, boy = sorted([float(a["en"]), float(a["boy"])])
        t["dis_olcu"] = {"en_m": en, "boy_m": boy}
    if a.get("cati"):
        t["cati"] = {"tip": a["cati"]}
    if a.get("veranda"):
        t["veranda"] = {"istiyor": True, "konum": a["veranda"]}
    if a.get("not"):
        t["ozel_istekler"] = [numara.maskele(a["not"])]
    return t


def kart_varsayilanlari(bayi: dict | None) -> dict:
    """Bayi kartının form varsayılanları ({yapi, kat, cati, veranda}; panelden, `bayi_varsayilanlari` tablosu); geçersiz değer atılır."""
    v = (bayi or {}).get("varsayilanlar") or {}
    out = {}
    for kolon, (ad, izinli) in KART_ALANLARI.items():
        x = str(v.get(kolon) if v.get(kolon) is not None else "")
        if x in izinli:
            out[ad] = x
    return out


def ekran_verisi(bayi: dict | None, taslak: dict | None) -> dict:
    """TALEP ekranının verisi: açık taslaktaki bilgi > kartın varsayılanı > sabit varsayılan. Değerler dize (Flow JSON `string`)."""
    ts = taslak or {}
    kart = kart_varsayilanlari(bayi)
    d = {**SABIT_VARSAYILAN, **kart, "oda": "", "alan": "", "en": "", "boy": ""}
    if ts.get("yapi_turu") in YAPI:
        d["yapi"] = ts["yapi_turu"]
    if str(ts.get("kat_sayisi") or "") in KAT:
        d["kat"] = str(ts["kat_sayisi"])
    if ts.get("oda_programi") in ODA:
        d["oda"] = ts["oda_programi"]
    if (ts.get("cati") or {}).get("tip") in CATI:
        d["cati"] = ts["cati"]["tip"]
    if (ts.get("veranda") or {}).get("konum") in VERANDA:
        d["veranda"] = ts["veranda"]["konum"]
    if ts.get("alan_m2"):
        d["alan"] = f"{float(ts['alan_m2']):g}"
    o = ts.get("dis_olcu") or {}
    if o.get("en_m") and o.get("boy_m"):
        d["en"], d["boy"] = f"{float(o['en_m']):g}", f"{float(o['boy_m']):g}"
    bilinen = [x for x in (d["oda"] or None, f"{_olcu(float(d['en']))} × {_olcu(float(d['boy']))} m" if d["en"] else None,
                           f"yaklaşık {_olcu(float(d['alan']))} m²" if d["alan"] else None) if x]
    d["bilinen"] = ("Bildiklerim: " + ", ".join(bilinen) + ". " if bilinen else "") + \
        "Bildiğiniz kadarını doldurmanız yeterli; eksik kalanı sohbette sorarım."
    return d


def etkilesim(tur: str, govde: str, flow_id: str, token: str, veri: dict, taslak_kipi: bool) -> dict:
    """Flow mesajının `interactive` gövdesi (hosting biçimi; kanal/meta_api.etkilesim_yuku yeniden denetler)."""
    p = {"flow_message_version": "3", "flow_token": token, "flow_id": str(flow_id), "flow_cta": DUGME[tur], "flow_action": "navigate",
         "flow_action_payload": {"screen": EKRAN[tur], "data": veri}}
    if taslak_kipi:
        p["mode"] = "draft"                    # Meta: yayımlanmamış (taslak) form; yalnız WhatsApp Manager'daki test numaralarında açılır
    return {"type": "flow", "body": {"text": govde}, "action": {"name": "flow", "parameters": p}}


def satir_tokeni(satir: dict | None) -> str | None:
    """Giden satırın (hosting biçimi) flow_token'ı; flow mesajı değilse None."""
    i = (satir or {}).get("interactive") or {}
    if i.get("type") != "flow":
        return None
    return str(((i.get("action") or {}).get("parameters") or {}).get("flow_token") or "") or None
