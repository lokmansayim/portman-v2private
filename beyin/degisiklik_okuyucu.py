"""İE-14 PR-3 · LLM-önce çelik revizyon okuması (banka modelleri; Düzeltilecekler madde 1).

LLM anlar, kod karar verir: LLM bayinin revizyon mesajını açık planın numaralı tablosuna (pencereler, çatı seçenekleri, dış karkas) karşı
değişiklik işlemlerine çevirir (araç `degisiklik_kaydet`). Kod her işlemi denetler: açıklık planda var mı ve pencere mi, ölçü aralıkta mı,
çatı kodu bu modelin varyantı mı; uygulanabilirlik `varyant.tanim_uygula` ile karar anında denenir (`karar._celik_degisiklikler`).
İki aday → "1 / 2 / Hiçbiri" (bugünkü okuma sorusu); çevrilemeyen istek `uygulanamaz` → "otomatik uygulayamadım" (Lokman 13.10: sessiz
düşme yok). Yeni plan (İE-14 üretimi) bu yoldan değil, `plan_uretici.duzenle` ile yeniden planlanır.

Ayar `llm_once_revizyon.acik` (varsayılan kapalı): kapalıyken bugünkü kural okuması (`celik_okuma`, K18) aynen. `celik_okuma`, LLM-önce
yolun kayıtlı cevaplarla (S1–S7, pilot cümleleri) doğrulanmasından sonra küçülür (İE-14 › Değişiklik › PR-3).

İE-23 PR-2a · banka germe (ayar `banka_germe.acik`, varsayılan kapalı; LLM-önce yol açıkken): tabloya yapı kimliğinden odalar (ad, işlev,
ölçü, dış cepheler; model kodu yok) eklenir ve işlem dili `oda_buyut` / `oda_kucult` {mahal, yon: G|K|B|D, cm} ile genişler
(`plan_islem.Islem` ile aynı). Uygulama ve hakem `beyin/tanim_germe.py`'de. Ayar kapalıyken istem, şema ve tablo bugünküyle aynıdır.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from beyin import llm, numara

YON_SOZU = {"G": "öne", "K": "arkaya", "B": "sola", "D": "sağa"}
YAN_SOZU = {"G": "ön", "K": "arka", "B": "sol", "D": "sağ"}
ODA_CM = (5, 300)
ODA_CM_VARSAYILAN = 50

ARAC_ADI = "degisiklik_kaydet"
ARAC_ACIKLAMA = "Bayinin revizyon isteğini planın tablosuna göre değişiklik işlemlerine çevir. Yalnız bu araçla cevap ver."
PROMPT = """Sen PortatifEv'in çelik ev planlarında bayinin revizyon isteğini okuyan yardımcısın. Karar vermezsin: isteği, açık planın
tablosundaki öğelere bağlı değişiklik işlemlerine çevirirsin; kod denetler ve uygular.

Kurallar:
- Yalnız bayinin bu mesajda istediği değişiklikleri yaz. Söylenmeyeni ekleme; olumsuz ("olmasın", "istemiyoruz") ya da soru biçimli cümle
  değişiklik değildir (öyleyse işlem yazma ya da `belirsiz_pencere`/`uygulanamaz` kullan).
- Pencere ölçüsü: hangi pencere olduğu tablodan tekse `pencere_olcu` (aciklik + en + yuk). İki ya da daha çok pencere uyuyorsa
  `belirsiz_pencere` ve `adaylar` (tablodaki numaralar); ölçü söylenmediyse en/yuk boş.
- Çatı: tablodaki seçeneklerden biri açıkça istendiyse `cati` + `cati_kodu`. Seçenek dışı çatı isteği `uygulanamaz`.
- Dış duvarların 140'lık karkası istendiyse `dis_karkas_140`.
- Bu planda otomatik yapılamayanlar (kapı, oda büyütme/küçültme, oda ekleme, veranda, pencere ekleme/kaldırma, yükseklik …):
  `uygulanamaz`, `alinti` bayinin kendi sözü.
- Renk, malzeme, müşteri adı, adres gibi bilgi: `bilgi` listesine (işlem değil).
Her işlemde `alinti`: bayinin o isteği söylediği sözler (kısa)."""


class Islem(BaseModel):
    tur: Literal["pencere_olcu", "belirsiz_pencere", "cati", "dis_karkas_140", "uygulanamaz"]
    aciklik: Optional[str] = Field(None, description="Tablodaki pencere numarası (ör. P5); pencere_olcu için")
    adaylar: list[str] = Field(default_factory=list, description="belirsiz_pencere: tablodaki aday pencere numaraları")
    en: Optional[float] = Field(None, description="Yeni pencere eni, cm (bayinin yazdığı gibi; yuvarlama)")
    yuk: Optional[float] = Field(None, description="Yeni pencere yüksekliği, cm (bayinin yazdığı gibi; yuvarlama)")
    cati_kodu: Optional[str] = Field(None, description="cati: tablodaki çatı seçeneğinin kodu")
    alinti: str = Field("", description="Bayinin bu istek için kullandığı sözler")


class DegisiklikListesi(BaseModel):
    islemler: list[Islem] = Field(default_factory=list)
    bilgi: list[str] = Field(default_factory=list, description="Değişiklik olmayan bilgi cümleleri (renk, malzeme, ad, adres)")


# İE-23 PR-2a: banka germe açıkken istem ve şema (kapalıyken yukarıdakiler aynen gider)
PROMPT_GERME = PROMPT.replace(
    "- Bu planda otomatik yapılamayanlar (kapı, oda büyütme/küçültme, oda ekleme,",
    """- Oda büyütme / küçültme: `oda_buyut` ya da `oda_kucult`; `mahal` tablodaki oda adı, `yon` bayinin söylediği yön (G ön, K arka,
  B sol, D sağ: "öne" G, "arkaya" K, "sola" B, "sağa" D), `cm` bayinin yazdığı sayı (yazmadıysa boş). Yön söylenmediyse `yon` boş.
  Hangi oda olduğu tablodan tek değilse `uygulanamaz`.
- Bu planda otomatik yapılamayanlar (kapı, oda ekleme,""")


class IslemGerme(Islem):
    tur: Literal["pencere_olcu", "belirsiz_pencere", "cati", "dis_karkas_140", "oda_buyut", "oda_kucult", "uygulanamaz"]
    mahal: Optional[str] = Field(None, description="oda_buyut/oda_kucult: tablodaki oda adı")
    yon: Optional[Literal["G", "K", "B", "D"]] = Field(None, description="oda_buyut/oda_kucult: G ön, K arka, B sol, D sağ")
    cm: Optional[float] = Field(None, description="oda_buyut/oda_kucult: bayinin yazdığı ölçü, cm (yazmadıysa boş)")


class DegisiklikListesiGerme(BaseModel):
    islemler: list[IslemGerme] = Field(default_factory=list)
    bilgi: list[str] = Field(default_factory=list, description="Değişiklik olmayan bilgi cümleleri (renk, malzeme, ad, adres)")


def tablo_metni(pencereler: list[dict], cati_secenekleri: list[dict], dis140: bool, odalar: list[dict] | None = None) -> str:
    satir = ["## Açık planın tablosu", "Pencereler:"]
    for p in pencereler:
        satir.append(f"- {p['aciklik']}: {p['aciklama']}")
    if cati_secenekleri:
        satir.append("Çatı seçenekleri: " + "; ".join(f"{c['kod']} ({c.get('ad') or ''})".strip() for c in cati_secenekleri))
    satir.append(f"Dış karkas: {'140' if dis140 else '80'}'lik")
    if odalar is not None:
        satir += oda_tablosu(odalar)
    return "\n".join(satir)


def oda_tablosu(odalar: list[dict]) -> list[str]:
    """İE-23 PR-2a: yapı kimliğinin mahalleri (`anlamsal.mahaller`): ad, işlev, net ölçü (en × derinlik), dış cepheler, verandaya bakan
    yanlar. Koordinat ve model kodu yok; kararı kod verir (kilitli kenar tabloda yazmaz)."""
    satir = ["Odalar (yönler bayinin planındaki gibi: ön planda ÖN yazan alt kenar, arka üst kenar, sol ve sağ plana önden bakınca; "
             "ölçü net en × derinlik):"]
    for m in odalar:
        islev = ", ".join(str(i).replace("_", " ") for i in m.get("islev") or []) or m.get("sinif") or ""
        en, der = (m.get("olcu_cm") or [0, 0])[:2]
        ek = ""
        if m.get("cepheler"):
            ek += "; dış cepheler: " + ", ".join(YAN_SOZU.get(c, c) for c in m["cepheler"])
        if m.get("verandaya"):
            ek += "; verandaya bakan: " + ", ".join(YAN_SOZU.get(c, c) for c in m["verandaya"])
        satir.append(f"- {m['ad']} ({islev}): {en:.0f} × {der:.0f} cm{ek}")
    return satir


def oku(metin: str, pencereler: list[dict], cati_secenekleri: list[dict], dis140: bool, ayar: dict | None = None,
        hazir: dict | None = None, odalar: list[dict] | None = None) -> dict:
    """Bir çağrı. Dönüş: {durum: tamam|hata, islemler[], bilgi[], cagri, girdi_token, cikti_token, hata}. İstisna fırlatmaz.
    `odalar` (İE-23 PR-2a, ayar `banka_germe.acik`): kimliğin mahalleri; verilirse istem, şema ve tablo germeli olur, sonuçta `germe: true`."""
    a = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    germe = odalar is not None
    istem, sema = (PROMPT_GERME, DegisiklikListesiGerme) if germe else (PROMPT, DegisiklikListesi)
    mesajlar = [{"role": "user", "content": tablo_metni(pencereler, cati_secenekleri, dis140, odalar) + f"\n\n## Bayinin mesajı\n{metin.strip()}"}]
    try:
        cevap, meta = llm.arac_cagir(istem, mesajlar, ARAC_ADI, ARAC_ACIKLAMA, sema.model_json_schema(), backend=a["backend"],
                                     model=a.get("model"), effort=a.get("effort"), max_tokens=2000, hazir=hazir, timeout=int(a["timeout_s"]))
        d = sema.model_validate(cevap)
    except Exception as e:                                   # LLM ya da şema hatası: kayda yazılır; karar bugünkü okumaya döner
        return {"durum": "hata", "islemler": [], "bilgi": [], "cagri": 0 if a["backend"] == "manuel" else 1,
                "hata": f"{type(e).__name__}: {numara.maskele(str(e))[:200]}", **({"germe": True} if germe else {})}
    return {"durum": "tamam", "islemler": [i.model_dump() for i in d.islemler], "bilgi": list(d.bilgi),
            "cagri": 0 if a["backend"] == "manuel" else 1, "girdi_token": meta.get("girdi_token") or 0, "cikti_token": meta.get("cikti_token") or 0,
            **({"germe": True} if germe else {})}


def denetle(sonuc: dict, pencereler: list[dict], cati_kodlari: set[str], odalar: list[str] | None = None) -> dict:
    """LLM işlemlerini koda göre ayıklar (LLM karar vermez). Dönüş: {ops[], sor (belirsiz: {adaylar, olcu}) | None, uygulanamaz[], bilgi[],
    yon_sor[]}. Tabloda olmayan açıklık, pencere olmayan öğe, aralık dışı ölçü ya da seçenek dışı çatı → uygulanamaz (gerekçeyle).
    `odalar` (İE-23 PR-2a; okuma germeli yapıldıysa planın mahal adları): oda_buyut / oda_kucult ayıklanır (oda tabloda, ölçü tam sayı
    ve aralıkta; ölçü yoksa 50 cm, bayiye yazılır; yön yoksa `yon_sor`). `odalar` yoksa bu işlemler uygulanamaz."""
    tablo = {p["aciklik"]: p for p in pencereler}
    ops, uyg, sor, yon_sor = [], [], None, []
    for i in sonuc.get("islemler") or []:
        tur = i.get("tur")
        if tur in ("oda_buyut", "oda_kucult"):
            o = _oda_islemi(i, odalar)
            if isinstance(o, dict):
                ops.append(o)
            elif o == "yon":
                yon_sor.append(i.get("alinti") or f"{i.get('mahal') or 'oda'} {'büyütme' if tur == 'oda_buyut' else 'küçültme'}")
            else:
                uyg.append(o)
            continue
        if any(i.get(a) is not None and float(i[a]) != int(float(i[a])) for a in ("en", "yuk")):
            uyg.append(f"{i.get('alinti') or 'pencere'} (ondalıklı ölçü; sessiz yuvarlama yok, K16)")     # S7
            continue
        if tur == "pencere_olcu":
            p = tablo.get(str(i.get("aciklik") or ""))
            if p is None or not i.get("en") or not i.get("yuk"):
                uyg.append(i.get("alinti") or "pencere ölçüsü")
                continue
            if not (30 <= int(i["en"]) <= 400 and 30 <= int(i["yuk"]) <= 250):
                uyg.append(f"{i.get('alinti') or p['aciklama']} ({int(i['en'])}x{int(i['yuk'])} ölçü aralığı dışında)")
                continue
            ops.append({"op": "pencere_olcu", "aciklik": p["aciklik"], "en": int(i["en"]), "yuk": int(i["yuk"]),
                        "aciklama": f"{p['aciklama']} → {int(i['en'])}/{int(i['yuk'])}"})
        elif tur == "belirsiz_pencere":
            adaylar = [tablo[a] for a in i.get("adaylar") or [] if a in tablo]
            if len(adaylar) >= 2 and sor is None:
                sor = {"adaylar": adaylar, "olcu": [int(i["en"]), int(i["yuk"])] if i.get("en") and i.get("yuk") else None}
            elif len(adaylar) == 1 and i.get("en") and i.get("yuk"):
                ops.append({"op": "pencere_olcu", "aciklik": adaylar[0]["aciklik"], "en": int(i["en"]), "yuk": int(i["yuk"]),
                            "aciklama": f"{adaylar[0]['aciklama']} → {int(i['en'])}/{int(i['yuk'])}"})
            else:
                uyg.append(i.get("alinti") or "pencere")
        elif tur == "cati":
            kod = str(i.get("cati_kodu") or "").upper().replace("-", "")
            if kod in {c.upper().replace("-", "") for c in cati_kodlari}:
                ops.append({"op": "cati_varyanti", "kod": next(c for c in cati_kodlari if c.upper().replace("-", "") == kod)})
            else:
                uyg.append(i.get("alinti") or "çatı")
        elif tur == "dis_karkas_140":
            ops.append({"op": "dis_karkas_140", "aciklama": "dış duvarlar 140'lık karkas"})
        else:
            uyg.append(i.get("alinti") or "istek")
    return {"ops": ops, "sor": sor, "uygulanamaz": uyg, "bilgi": list(sonuc.get("bilgi") or []), "yon_sor": yon_sor}


def _oda_islemi(i: dict, odalar: list[str] | None) -> dict | str:
    """oda_buyut / oda_kucult → işlem; yapılamıyorsa bayiye gidecek gerekçeli söz ya da "yon" (yön sorulur)."""
    tur = i.get("tur")
    soz = i.get("alinti") or ("oda büyütme" if tur == "oda_buyut" else "oda küçültme")
    if odalar is None:
        return soz
    ad = next((m for m in odalar if m == i.get("mahal")), None) or \
        next((m for m in odalar if _norm(m) == _norm(i.get("mahal") or "")), None)
    if ad is None:
        return f"{soz} (planda \"{i.get('mahal') or ''}\" adlı oda yok)" if i.get("mahal") else f"{soz} (hangi oda?)"
    cm = i.get("cm")
    varsayilan = cm is None
    if varsayilan:
        cm = ODA_CM_VARSAYILAN
    if float(cm) != int(float(cm)):
        return f"{soz} (ondalıklı ölçü; sessiz yuvarlama yok, K16)"
    cm = int(float(cm))
    if not (ODA_CM[0] <= cm <= ODA_CM[1]):
        return f"{soz} ({cm} cm; {ODA_CM[0]}–{ODA_CM[1]} cm arasında olmalı)"
    if i.get("yon") not in YON_SOZU:
        return "yon"
    o = {"op": tur, "mahal": ad, "yon": i["yon"], "cm": cm,
         "aciklama": f"{ad} {YON_SOZU[i['yon']]} {cm} cm {'büyütme' if tur == 'oda_buyut' else 'küçültme'}"}
    if varsayilan:
        o["cm_varsayilan"] = True
    return o


def _norm(s: str) -> str:
    return " ".join(str(s).lower().replace("ı", "i").replace("İ", "i").replace("-", " ").split())
