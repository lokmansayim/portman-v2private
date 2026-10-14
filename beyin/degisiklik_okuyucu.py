"""İE-14 PR-3 · LLM-önce çelik revizyon okuması (banka modelleri; Düzeltilecekler madde 1).

LLM anlar, kod karar verir: LLM bayinin revizyon mesajını açık planın numaralı tablosuna (pencereler, çatı seçenekleri, dış karkas) karşı
değişiklik işlemlerine çevirir (araç `degisiklik_kaydet`). Kod her işlemi denetler: açıklık planda var mı ve pencere mi, ölçü aralıkta mı,
çatı kodu bu modelin varyantı mı; uygulanabilirlik `varyant.tanim_uygula` ile karar anında denenir (`karar._celik_degisiklikler`).
İki aday → "1 / 2 / Hiçbiri" (bugünkü okuma sorusu); çevrilemeyen istek `uygulanamaz` → "otomatik uygulayamadım" (Lokman 13.10: sessiz
düşme yok). Yeni plan (İE-14 üretimi) bu yoldan değil, `plan_uretici.duzenle` ile yeniden planlanır.

Ayar `llm_once_revizyon.acik` (varsayılan kapalı): kapalıyken bugünkü kural okuması (`celik_okuma`, K18) aynen. `celik_okuma`, LLM-önce
yolun kayıtlı cevaplarla (S1–S7, pilot cümleleri) doğrulanmasından sonra küçülür (İE-14 › Değişiklik › PR-3).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from beyin import llm

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


def tablo_metni(pencereler: list[dict], cati_secenekleri: list[dict], dis140: bool) -> str:
    satir = ["## Açık planın tablosu", "Pencereler:"]
    for p in pencereler:
        satir.append(f"- {p['aciklik']}: {p['aciklama']}")
    if cati_secenekleri:
        satir.append("Çatı seçenekleri: " + "; ".join(f"{c['kod']} ({c.get('ad') or ''})".strip() for c in cati_secenekleri))
    satir.append(f"Dış karkas: {'140' if dis140 else '80'}'lik")
    return "\n".join(satir)


def oku(metin: str, pencereler: list[dict], cati_secenekleri: list[dict], dis140: bool, ayar: dict | None = None,
        hazir: dict | None = None) -> dict:
    """Bir çağrı. Dönüş: {durum: tamam|hata, islemler[], bilgi[], cagri, girdi_token, cikti_token, hata}. İstisna fırlatmaz."""
    a = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    mesajlar = [{"role": "user", "content": tablo_metni(pencereler, cati_secenekleri, dis140) + f"\n\n## Bayinin mesajı\n{metin.strip()}"}]
    try:
        cevap, meta = llm.arac_cagir(PROMPT, mesajlar, ARAC_ADI, ARAC_ACIKLAMA, DegisiklikListesi.model_json_schema(), backend=a["backend"],
                                     model=a.get("model"), effort=a.get("effort"), max_tokens=2000, hazir=hazir, timeout=int(a["timeout_s"]))
        d = DegisiklikListesi.model_validate(cevap)
    except Exception as e:                                   # LLM ya da şema hatası: kayda yazılır; karar bugünkü okumaya döner
        return {"durum": "hata", "islemler": [], "bilgi": [], "cagri": 0 if a["backend"] == "manuel" else 1, "hata": f"{type(e).__name__}: {str(e)[:200]}"}
    return {"durum": "tamam", "islemler": [i.model_dump() for i in d.islemler], "bilgi": list(d.bilgi),
            "cagri": 0 if a["backend"] == "manuel" else 1, "girdi_token": meta.get("girdi_token") or 0, "cikti_token": meta.get("cikti_token") or 0}


def denetle(sonuc: dict, pencereler: list[dict], cati_kodlari: set[str]) -> dict:
    """LLM işlemlerini koda göre ayıklar (LLM karar vermez). Dönüş: {ops[], sor (belirsiz: {adaylar, olcu}) | None, uygulanamaz[], bilgi[]}.
    Tabloda olmayan açıklık, pencere olmayan öğe, aralık dışı ölçü ya da seçenek dışı çatı → uygulanamaz (gerekçeyle)."""
    tablo = {p["aciklik"]: p for p in pencereler}
    ops, uyg, sor = [], [], None
    for i in sonuc.get("islemler") or []:
        tur = i.get("tur")
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
    return {"ops": ops, "sor": sor, "uygulanamaz": uyg, "bilgi": list(sonuc.get("bilgi") or [])}
