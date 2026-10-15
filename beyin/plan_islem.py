"""İE-14 r3 · P2: yeni planın revizyonu — LLM isteği koordinatsız işlemlere çevirir, kod uygular, denetçi karar verir.

LLM planı yeniden yazmaz (eski `plan_uretici.duzenle` kalktı). İşlemler:
- `oda_buyut` / `oda_kucult` {mahal, yon: G|K|B|D, cm}: mahalin o yandaki kenarı kayar. Kenar dış cepheyse bina o yönde büyür/küçülür
  (kenarı kesen bütün mahaller uzar, `plan_uyarlama.uzat`); iç kenarsa komşu sınır kayar (yalnız komşular o kenarı tam paylaşıyorsa).
- `kapi_ekle` / `kapi_kaldir` {mahal, mahal_b ('dis' = dış kapı)}
- `pencere_ekle` / `pencere_kaldir` {mahal, cephe?, olcu?}
- `cati_tipi` {tip: besik|kirma}; `dis_karkas_140`
Çevrilemeyen istek `uygulanamayan`'a bayinin sözüyle (sessiz düşme yok). Kodun uygulayamadığı işlem de oraya gerekçesiyle yazılır.
"Uygulanan" metni kodun hesapladığı farktır (`plan_uretici.plan_farki`).
"""
from __future__ import annotations

import copy
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from beyin import numara
from beyin.plan_denetim import denetle
from beyin.plan_cozucu import cepheler
from beyin.plan_sema import PENCERE_OLCULERI
from beyin.plan_uyarlama import _kesitler, uzat

ARAC_ADI = "plan_islemleri_kaydet"
ARAC_ACIKLAMA = "Bayinin yeni plan revizyon isteğini koordinatsız işlemlere çevir. Yalnız bu araçla cevap ver."
VARSAYILAN_AYAR = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60, "max_tokens": 2000}
YONLER = {"G": (1, -1), "K": (1, 1), "B": (0, -1), "D": (0, 1)}       # (eksen indisi, yön)
YON_SOZU = {"G": "ön", "K": "arka", "B": "sol", "D": "sağ"}           # bayiye giden gerekçede (PROMPT'taki sözcükler)
ISLEM_SOZU = {"oda_buyut": "oda büyütme", "oda_kucult": "oda küçültme", "kapi_ekle": "kapı ekleme", "kapi_kaldir": "kapı kaldırma",
              "pencere_ekle": "pencere ekleme", "pencere_kaldir": "pencere kaldırma", "cati_tipi": "çatı tipi değişikliği",
              "dis_karkas_140": "dış duvarların 140'lık olması"}


def _soz(o: dict) -> str:
    """Bayiye giden gerekçede isteğin adı: bayinin sözü; yoksa iç işlem adı değil, Türkçesi (geometri hakemi 15.10, küçük 2)."""
    return str(o.get("alinti") or ISLEM_SOZU.get(o.get("op")) or "istek")


def _dis_cepheler(p: dict) -> dict[str, list[str]]:
    """Mahal → değdiği dış cepheler (G, K, B, D sırasıyla; veranda yüzü dahil, çözücünün pencere yerleşimiyle aynı ölçüt)."""
    ce = cepheler(p["mahaller"], p["dis_olcu"]["en"], p["dis_olcu"]["boy"])
    return {ad: [c for c in "GKBD" if d.get(c)] for ad, d in ce.items()}


class Islem(BaseModel):
    op: Literal["oda_buyut", "oda_kucult", "kapi_ekle", "kapi_kaldir", "pencere_ekle", "pencere_kaldir", "cati_tipi", "dis_karkas_140"]
    mahal: Optional[str] = None
    mahal_b: Optional[str] = Field(None, description="Kapının öbür yanı; dış kapı için 'dis'")
    yon: Optional[Literal["G", "K", "B", "D"]] = Field(None, description="Hangi yana büyüsün/küçülsün: G ön, K arka, B sol, D sağ")
    cm: Optional[int] = Field(None, ge=5, le=300)
    cephe: Optional[Literal["G", "K", "B", "D"]] = None
    olcu: Optional[Literal["120x120", "120x180", "60x40", "120x100", "120x160", "160x120", "160x180", "180x180", "80x120", "120x50",
                           "80x180", "60x60"]] = None
    tip: Optional[Literal["besik", "kirma"]] = None
    alinti: str = Field("", description="Bayinin bu işleme karşılık gelen sözü")


class IslemListesi(BaseModel):
    islemler: list[Islem] = Field(default_factory=list)
    uygulanamayan: list[str] = Field(default_factory=list, description="Bu işlemlere çevrilemeyen istekler, bayinin sözüyle")


PROMPT = """Sen PortatifEv'in tek kat çelik evlerinde bayinin revizyon isteğini okuyan yardımcısın. Planı yeniden çizmezsin, koordinat
yazmazsın: isteği aşağıdaki işlemlere çevirirsin; uygulamayı ve denetimi kod yapar.

İşlemler: oda_buyut / oda_kucult (mahal, yon: G ön, K arka, B sol, D sağ; cm — bayi sayı vermediyse 50), kapi_ekle / kapi_kaldir (mahal,
mahal_b; dış kapı için mahal_b "dis"), pencere_ekle / pencere_kaldir (mahal, cephe, olcu), cati_tipi (tip), dis_karkas_140.
- Mahal adlarını tablodaki gibi yaz. Yalnız bayinin bu mesajda istediğini yaz; söylenmeyeni ekleme.
- Pencere cephesini mahalin tablodaki dış cephelerinden seç. Çatı tipi yalnız besik ya da kirma olabilir; L, cumba ve başka çatı biçimlerini
  `uygulanamayan`'a yaz.
- Olumsuz ("olmasın", "istemiyoruz") ya da soru biçimli cümle işlem değildir.
- Bu işlemlere çevrilemeyen her isteği `uygulanamayan`'a bayinin sözüyle yaz (ör. "çift kat olsun"). Renk ve malzeme istekleri plan değildir,
  onları yazma.
"""


def tablo(plan: dict) -> str:
    """LLM'e giden tablo: yalnız bu bayinin planı (mahal adı, işlev, eksenden ölçü, cepheler, pencereler, kapılar). Banka kodu yok."""
    satir = [f"Dış ölçü {plan['dis_olcu']['en']}×{plan['dis_olcu']['boy']} cm; çatı {(plan.get('cati') or {}).get('tip')}; "
             f"dış karkas {plan.get('dis_karkas') or 80}", "Mahaller:"]
    ce = _dis_cepheler(plan)
    for m in plan["mahaller"]:
        r = max(m["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
        dis = ", ".join(ce.get(m["ad"]) or [])
        ek = "" if m["islev"] == "veranda" else f"; dış cepheler: {dis}" if dis else "; dış cephesi yok"     # LLM pencere cephesini buradan seçer
        satir.append(f"- {m['ad']} ({m['islev']}): {r[2] - r[0]}×{r[3] - r[1]} cm{ek}")
    satir.append("Pencereler: " + "; ".join(f"{p['mahal']} {p['cephe']} {p['olcu']}" for p in plan["pencereler"]))
    satir.append("Kapılar: " + "; ".join(" – ".join(k["arasinda"]) for k in plan["kapilar"]))
    return "\n".join(satir)


def oku(plan: dict, metin: str, ayar: dict | None = None, hazir: dict | None = None) -> dict:
    """Tek LLM çağrısı. Dönüş: {durum: tamam|hata, islemler, uygulanamayan, cagri, girdi_token, cikti_token, hata}."""
    from beyin import llm
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    s = {"durum": "hata", "islemler": [], "uygulanamayan": [], "cagri": 0, "girdi_token": 0, "cikti_token": 0, "hata": None}
    mesaj = tablo(plan) + f"\n\n## Bayinin mesajı\n{numara.maskele(metin.strip())}"
    try:
        cevap, meta = llm.arac_cagir(PROMPT, [{"role": "user", "content": mesaj}], ARAC_ADI, ARAC_ACIKLAMA, IslemListesi.model_json_schema(),
                                     backend=a["backend"], model=a.get("model"), effort=a.get("effort"), max_tokens=int(a["max_tokens"]),
                                     hazir=hazir, timeout=int(a["timeout_s"]))
    except (llm.LLMHatasi, ValueError) as e:
        s["cagri"] = 1 if a["backend"] != "manuel" else 0
        s["hata"] = numara.maskele(str(e))[:300]
        return s
    s["cagri"] = 1 if a["backend"] != "manuel" else 0
    s["girdi_token"], s["cikti_token"] = meta.get("girdi_token") or 0, meta.get("cikti_token") or 0
    try:
        L = IslemListesi.model_validate(cevap).model_dump()
    except ValidationError as e:
        L = _tek_tek(cevap)
        if L is None:
            s["hata"] = f"işlem şeması: {str(e)[:160]}"
            return s
    s.update(durum="tamam", islemler=L["islemler"], uygulanamayan=[str(x) for x in L["uygulanamayan"]])
    return s


def _tek_tek(cevap) -> dict | None:
    """Şemaya uymayan işlem bütün okumayı düşürmez (ör. çatı "L"; canlı deneme hazırlığı, 15.10): geçerli işlemler alınır, uymayan bayinin
    sözüyle `uygulanamayan`'a gider. Cevabın kendisi liste taşımıyorsa None (eskisi gibi şema hatası)."""
    if not isinstance(cevap, dict) or not isinstance(cevap.get("islemler"), list):
        return None
    u = cevap.get("uygulanamayan") or []
    u = [u] if isinstance(u, str) else u if isinstance(u, list) else []         # metin harf harf bölünmez (hakem küçük 1)
    olmayan = [str(x) if not isinstance(x, dict) else " ".join(str(v) for v in x.values() if isinstance(v, str)) for x in u]
    olmayan = [x for x in olmayan if x.strip()]                                # nesne süzülüp atılmaz, metni alınır (küçük 2)
    islemler = []
    for o in cevap["islemler"]:
        try:
            islemler.append(Islem.model_validate(o).model_dump())
        except ValidationError:
            olmayan.append(_soz(o)[:80] if isinstance(o, dict) else "istek")
    return {"islemler": islemler, "uygulanamayan": olmayan}


# ── uygulama ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _oda_kenari(p: dict, mahal: str, yon: str, cm: int) -> tuple[dict | None, str | None]:
    """Mahalin `yon` yanındaki kenarını cm kadar dışarı (büyüt) ya da içeri (negatif cm: küçült) kaydırır."""
    m = next((x for x in p["mahaller"] if x["ad"] == mahal), None)
    if m is None:
        return None, f"'{mahal}' adlı mahal yok"
    k, s = YONLER[yon]
    ana = max(m["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
    kenar = ana[k + 2] if s > 0 else ana[k]
    ust = p["dis_olcu"]["en" if k == 0 else "boy"]
    eksen = "x" if k == 0 else "y"
    if kenar in (0, ust):                                        # dış cephe: bina o yönde büyür/küçülür
        # kesit odanın içinden geçer; verandayı kesen kesit seçilmez (köşe veranda büyümez; uyarlamadaki gibi, inceleme G10)
        ilk = kenar - 5 if s > 0 else kenar + 5                  # sol/ön kenarda da köken 0'da kalır (kesitin ötesi kayar)
        ver_keser = lambda kes: any(x["islev"] == "veranda" and r[k] < kes < r[k + 2]       # noqa: E731
                                    for x in p["mahaller"] for r in x["dikdortgenler"])
        adaylar = ([ilk] if not ver_keser(ilk) else []) + [kes for kes in _kesitler(p, eksen, cm, 10) if ana[k] < kes < ana[k + 2]]
        for kes in adaylar:
            q = uzat(p, eksen, kes, cm)
            if q:
                return q, None
        if ver_keser(ilk):
            return None, "verandayı değiştirmeden bu yöne " + ("büyütemedim" if cm > 0 else "küçültemedim")   # cm işareti işi taşır (yön değil)
        return None, "dış ölçü bu kadar küçülemez"
    # iç kenar: komşular kenarı tam paylaşmalı (dik aralıkları mahalin aralığı içinde)
    q = copy.deepcopy(p)
    lo, hi = ana[1 - k], ana[3 - k]
    yeni = kenar + s * cm
    for x in q["mahaller"]:
        for r in x["dikdortgenler"]:
            if x["ad"] == mahal and r == ana:
                if s > 0:
                    r[k + 2] = yeni
                else:
                    r[k] = yeni
                continue
            dokunur = (r[k] == kenar if s > 0 else r[k + 2] == kenar) and r[1 - k] < hi and r[3 - k] > lo
            if dokunur:
                if r[1 - k] < lo or r[3 - k] > hi:
                    return None, f"{mahal} kenarındaki komşu ({x['ad']}) başka hizada devam ediyor; bu yöne otomatik büyütemedim"
                if s > 0:
                    r[k] = yeni
                else:
                    r[k + 2] = yeni
                if r[k + 2] - r[k] <= 0:
                    return None, f"{x['ad']} bu kadar küçülemez"
    if not (0 < yeni < ust):
        return None, "kenar dış ölçüyü aşıyor"
    return q, None


def uygula(plan: dict, islemler: list[dict]) -> tuple[dict, list[str]]:
    """İşlemleri sırayla uygular. Dönüş: (yeni plan, uygulanamayan gerekçeleri). Denetim çağıranda."""
    p = copy.deepcopy(plan)
    olmayan: list[str] = []
    adlar = lambda: {m["ad"] for m in p["mahaller"]}       # noqa: E731
    for o in islemler:
        op = o["op"]
        if op in ("oda_buyut", "oda_kucult"):
            if not (o.get("mahal") and o.get("yon")):
                olmayan.append(f"{_soz(o)}: hangi oda ve hangi yön belli değil")
                continue
            cm = int(o.get("cm") or 50)
            cm = (cm if op == "oda_buyut" else -cm)
            if cm % 5:
                olmayan.append(f"{_soz(o)}: ölçü 5 cm katı olmalı")
                continue
            q, neden = _oda_kenari(p, o["mahal"], o["yon"], cm)
            if q is None:
                olmayan.append(f"{_soz(o)}: {neden}")
            else:
                p = q
        elif op in ("kapi_ekle", "kapi_kaldir"):
            a, b = o.get("mahal"), o.get("mahal_b") or "dis"
            if a not in adlar() or (b != "dis" and b not in adlar()):
                olmayan.append(f"{_soz(o)}: mahal bulunamadı")
                continue
            cift = sorted([a, b])
            var = [k for k in p["kapilar"] if sorted(k["arasinda"]) == cift]
            if op == "kapi_ekle" and not var:
                p["kapilar"].append({"arasinda": [b, a] if b == "dis" else [a, b]})
            elif op == "kapi_kaldir":
                if not var:
                    olmayan.append(f"{_soz(o)}: o iki mahal arasında kapı yok")
                else:
                    p["kapilar"].remove(var[0])
        elif op in ("pencere_ekle", "pencere_kaldir"):
            if o.get("mahal") not in adlar():
                olmayan.append(f"{_soz(o)}: mahal bulunamadı")
                continue
            if op == "pencere_ekle":
                if not (o.get("cephe") and o.get("olcu") in PENCERE_OLCULERI):
                    olmayan.append(f"{_soz(o)}: cephe ve ölçü belli değil")
                    continue
                if o["cephe"] not in _dis_cepheler(p).get(o["mahal"], []):
                    # denetçi bütün revizyonu reddederdi (geçerli öteki işlemler de düşer); yalnız bu istek düşer (canlı deneme hazırlığı, 15.10)
                    olmayan.append(f"{_soz(o)}: {o['mahal']} {YON_SOZU[o['cephe']]} cepheye değmiyor")
                    continue
                p["pencereler"].append({"mahal": o["mahal"], "cephe": o["cephe"], "olcu": o["olcu"], "adet": 1})
            else:
                uy = [x for x in p["pencereler"] if x["mahal"] == o["mahal"] and (not o.get("cephe") or x["cephe"] == o["cephe"])
                      and (not o.get("olcu") or x["olcu"] == o["olcu"])]
                if len(uy) != 1:
                    olmayan.append(f"{_soz(o)}: " + ("o pencere yok" if not uy else "birden çok pencere uyuyor; hangisi?"))
                else:
                    p["pencereler"].remove(uy[0])
        elif op == "cati_tipi":
            if o.get("tip") not in ("besik", "kirma"):
                olmayan.append(f"{_soz(o)}: çatı tipi belli değil")
                continue
            p["cati"] = {**(p.get("cati") or {}), "tip": o["tip"]}
            p["cati"].pop("mahya_yonu", None)
        elif op == "dis_karkas_140":
            p["dis_karkas"] = 140
    return p, olmayan


def _kisa(ihlal: str, sinir: int) -> str:
    """Denetçi ihlalinin bayiye giden kısa biçimi: baştaki tür ("kapı: ") ve parantezli ayrıntı atılır, sözcük sınırında kesilir."""
    t = re.sub(r"^\w+:\s*", "", ihlal.split(" (")[0]).strip()
    return t if len(t) <= sinir else t[:sinir].rsplit(" ", 1)[0] + "…"


def _sirayla(plan: dict, islemler: list[dict], talep: dict, kod: str) -> tuple[dict, dict | None, list[str], list[dict]]:
    """İşlemleri sırayla tek tek uygular ve denetler. Dönüş: (plan, son geçen denetim ya da None, uygulanamayan, uygulanan işlemler)."""
    p, son, olmayan, kalan = plan, None, [], []
    for o in islemler:
        q, neden = uygula(p, [o])
        if neden or q == p:
            olmayan += neden
            continue
        d = denetle(q, {"oda_programi": talep.get("oda_programi")}, kod=kod)
        if d["gecerli"]:
            p, son = q, d
            kalan.append(o)
        else:
            soz = _soz(o)[:40]
            olmayan.append(f"{soz}: {_kisa((d['ihlaller'] or ['kurallara uymuyor'])[0], max(20, 78 - len(soz)))}")
    return p, son, olmayan, kalan


def duzenle(plan: dict, metin: str, talep: dict, ayar: dict | None = None, hazir: dict | None = None, kod: str = "YENI") -> dict:
    """Yeni planın revizyonu: oku → uygula → denetle (alan ±%10 revizyonda aranmaz; oda programı korunur). Dönüş (karar sözleşmesi):
    {durum: gecerli|gecersiz|bos|uygulanamadi|hata, plan, tanim, ozet, fark, uygulanamayan, islemler, cagri, girdi_token, cikti_token, hata, ihlaller}."""
    from beyin.plan_uretici import plan_farki
    o = oku(plan, metin, ayar, hazir)
    s = {"durum": "hata" if o["durum"] != "tamam" else "gecersiz", "plan": None, "tanim": None, "ozet": {}, "fark": [], "islemler": o["islemler"],
         "uygulanamayan": list(o["uygulanamayan"]), "cagri": o["cagri"], "girdi_token": o["girdi_token"], "cikti_token": o["cikti_token"],
         "hata": o["hata"], "ihlaller": [], "denemeler": []}
    if o["durum"] != "tamam":
        return s
    yeni, olmayan = uygula(plan, o["islemler"])
    s["uygulanamayan"] += olmayan
    if yeni == plan:
        s["ihlaller"] = ["uygulanacak işlem kalmadı"]
        # plan değişmedi: istek yoksa "bos" (karar sorar, inceleme C2); istek anlaşıldı ama uygulanamadıysa (L/cumba çatı, çift kat, belirsiz
        # cephe) "uygulanamadi" — bayiye istek adıyla yazılır, plan aynen geçerli ve onaylanabilir kalır (Lokman 15.10, karar 3)
        s["durum"] = "uygulanamadi" if s["uygulanamayan"] else "bos"
        return s
    d = denetle(yeni, {"oda_programi": talep.get("oda_programi")}, kod=kod)
    s["denemeler"] = [{"plan": yeni, "gecerli": d["gecerli"], "ihlaller": d["ihlaller"]}]
    kalan = o["islemler"]
    if not d["gecerli"]:
        s["ihlaller"] = d["ihlaller"][:8]
        # birlikte kurallara uymadı: işlemler sırayla tek tek denenir; geçen uygulanır, geçmeyen bayinin sözü ve kısa gerekçesiyle yazılır
        # (geometri hakemi 15.10, Önemli 2: pencere cepheye değer ama sığmaz; büyütme bir kapıyı sığmaz kılar). Hiçbiri geçmezse eskisi gibi.
        if len(o["islemler"]) < 2:
            return s
        yeni, d, olmayan, kalan = _sirayla(plan, o["islemler"], talep, kod)
        if d is None:
            return s
        s["denemeler"].append({"plan": yeni, "gecerli": True, "ihlaller": [], "sirayla": True})
        s["uygulanamayan"], s["ihlaller"] = list(o["uygulanamayan"]) + olmayan, []
    s.update(durum="gecerli", plan=yeni, tanim=d["tanim"], ozet=d["ozet"], fark=plan_farki(plan, yeni))
    if any(x["op"] in ("oda_buyut", "oda_kucult") and not x.get("cm") for x in kalan):
        s["fark"].append("ölçü söylenmediği için 50 cm alındı")       # varsayım bayiye yazılır (inceleme G10)
    return s
