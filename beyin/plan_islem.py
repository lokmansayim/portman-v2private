"""İE-14 r3 · P2: yeni planın revizyonu — LLM isteği koordinatsız işlemlere çevirir, kod uygular, denetçi karar verir.

LLM planı yeniden yazmaz (eski `plan_uretici.duzenle` kalktı). İşlemler:
- `oda_buyut` / `oda_kucult` {mahal, yon: G|K|B|D, cm}: mahalin o yandaki kenarı kayar. Kenar dış cepheyse bina o yönde büyür/küçülür
  (kenarı kesen bütün mahaller uzar, `plan_uyarlama.uzat`); iç kenarsa komşu sınır kayar (yalnız komşular o kenarı tam paylaşıyorsa).
- `kapi_ekle` / `kapi_kaldir` {mahal, mahal_b ('dis' = dış kapı)}
- `pencere_ekle` / `pencere_kaldir` {mahal, cephe?, olcu?}
- `cati_tipi` {tip: besik|kirma}; `dis_karkas_140`
- `oda_ekle` {islev, mahal?}: yalnız ebeveyn banyosu (BK-15): banyo yatak odasının köşesinden kesilir, kapısı o odadan; sığmazsa oda bir
  kenarından büyütülüp yeniden denenir (ev en az büyüyen yönde). Öteki oda istekleri gerekçesiyle `uygulanamayan`'a.
Çevrilemeyen istek `uygulanamayan`'a bayinin sözüyle (sessiz düşme yok). Kodun uygulayamadığı işlem de oraya gerekçesiyle yazılır.
"Uygulanan" metni kodun hesapladığı farktır (`plan_uretici.plan_farki`).
"""
from __future__ import annotations

import copy
import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from beyin import numara
from beyin.plan_denetim import ISLEV_ADI, denetle, kurallar
from beyin.plan_cozucu import cepheler
from beyin.plan_sema import PENCERE_OLCULERI
from beyin.plan_uyarlama import _kesitler, _komsu_mu, _yeniden_ac, uzat

ARAC_ADI = "plan_islemleri_kaydet"
ARAC_ACIKLAMA = "Bayinin yeni plan revizyon isteğini koordinatsız işlemlere çevir. Yalnız bu araçla cevap ver."
VARSAYILAN_AYAR = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60, "max_tokens": 2000}
YONLER = {"G": (1, -1), "K": (1, 1), "B": (0, -1), "D": (0, 1)}       # (eksen indisi, yön)
YON_SOZU = {"G": "ön", "K": "arka", "B": "sol", "D": "sağ"}           # bayiye giden gerekçede (PROMPT'taki sözcükler)
ISLEM_SOZU = {"oda_buyut": "oda büyütme", "oda_kucult": "oda küçültme", "kapi_ekle": "kapı ekleme", "kapi_kaldir": "kapı kaldırma",
              "pencere_ekle": "pencere ekleme", "pencere_kaldir": "pencere kaldırma", "cati_tipi": "çatı tipi değişikliği",
              "dis_karkas_140": "dış duvarların 140'lık olması", "oda_ekle": "oda ekleme"}


def _soz(o: dict) -> str:
    """Bayiye giden gerekçede isteğin adı: bayinin sözü; yoksa iç işlem adı değil, Türkçesi (geometri hakemi 15.10, küçük 2)."""
    return str(o.get("alinti") or ISLEM_SOZU.get(o.get("op")) or "istek")


def _dis_cepheler(p: dict) -> dict[str, list[str]]:
    """Mahal → değdiği dış cepheler (G, K, B, D sırasıyla; veranda yüzü dahil, çözücünün pencere yerleşimiyle aynı ölçüt)."""
    ce = cepheler(p["mahaller"], p["dis_olcu"]["en"], p["dis_olcu"]["boy"])
    return {ad: [c for c in "GKBD" if d.get(c)] for ad, d in ce.items()}


class Islem(BaseModel):
    op: Literal["oda_buyut", "oda_kucult", "kapi_ekle", "kapi_kaldir", "pencere_ekle", "pencere_kaldir", "cati_tipi", "dis_karkas_140",
                "oda_ekle"]
    mahal: Optional[str] = None
    mahal_b: Optional[str] = Field(None, description="Kapının öbür yanı; dış kapı için 'dis'")
    yon: Optional[Literal["G", "K", "B", "D"]] = Field(None, description="Hangi yana büyüsün/küçülsün: G ön, K arka, B sol, D sağ")
    cm: Optional[int] = Field(None, ge=5, le=300)
    cephe: Optional[Literal["G", "K", "B", "D"]] = None
    olcu: Optional[Literal["120x120", "120x180", "60x40", "120x100", "120x160", "160x120", "160x180", "180x180", "80x120", "120x50",
                           "80x180", "60x60"]] = None
    tip: Optional[Literal["besik", "kirma"]] = None
    islev: Optional[Literal["banyo", "yatak_odasi", "salon", "mutfak", "hol", "depo"]] = Field(None, description="oda_ekle: yeni odanın işlevi")
    alinti: str = Field("", description="Bayinin bu işleme karşılık gelen sözü")


class IslemListesi(BaseModel):
    islemler: list[Islem] = Field(default_factory=list)
    uygulanamayan: list[str] = Field(default_factory=list, description="Bu işlemlere çevrilemeyen istekler, bayinin sözüyle")


PROMPT = """Sen PortatifEv'in tek kat çelik evlerinde bayinin revizyon isteğini okuyan yardımcısın. Planı yeniden çizmezsin, koordinat
yazmazsın: isteği aşağıdaki işlemlere çevirirsin; uygulamayı ve denetimi kod yapar.

İşlemler: oda_buyut / oda_kucult (mahal, yon: G ön, K arka, B sol, D sağ; cm — bayi sayı vermediyse 50), kapi_ekle / kapi_kaldir (mahal,
mahal_b; dış kapı için mahal_b "dis" ve istenirse cephe — dış kapıyı başka cepheye almak da kapi_ekle'dir), pencere_ekle / pencere_kaldir
(mahal, cephe, olcu), cati_tipi (tip), dis_karkas_140, oda_ekle (islev, mahal).
- oda_ekle: ebeveyn banyosu (yatak odasının içinden açılan banyo) için islev banyo, mahal o yatak odası; bayi hangi oda demediyse mahal'i
  boş bırak. Başka oda istenirse (yatak odası, mutfak, kiler, holden açılan ortak banyo) de oda_ekle yaz: islev'i ve odanın açılacağı
  mahali (ör. Hol) yaz.
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
    u = [u] if isinstance(u, (str, dict)) else u if isinstance(u, list) else []    # metin harf harf bölünmez (hakem küçük 1)
    olmayan = [str(x) if not isinstance(x, dict) else " ".join(str(v) for v in x.values() if isinstance(v, str)) for x in u if x is not None]
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
            if not (o.get("mahal") and o.get("yon")):                 # canlı deneme 16.10 (D): eksik olanı ayrı söyler
                fiil = "büyütüleceği" if op == "oda_buyut" else "küçültüleceği"
                eksik = ["hangi oda"] * (not o.get("mahal")) + [f"hangi yöne (ön, arka, sol, sağ) {fiil}"] * (not o.get("yon"))
                olmayan.append(f"{_soz(o)}: {' ve '.join(eksik)} belli değil")
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
            c = o.get("cephe") if b == "dis" else None             # dış kapının istenen cephesi (geometri hakemi 16.10: önceden yok sayılıyordu)
            if op == "kapi_ekle" and c and c not in _dis_cepheler(p).get(a, []):
                olmayan.append(f"{_soz(o)}: {a} {YON_SOZU[c]} cepheye değmiyor")
                continue
            if op == "kapi_ekle" and not var:
                p["kapilar"].append({"arasinda": [b, a] if b == "dis" else [a, b], **({"cephe": c} if c else {})})
            elif op == "kapi_ekle" and c and var[0].get("cephe") != c:
                var[0]["cephe"] = c                                    # var olan dış kapı istenen cepheye taşınır
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
                elif int(uy[0].get("adet") or 1) > 1:                   # adetli girdiden biri kaldırılır (hakem 16.10; önceden hepsi siliniyordu)
                    uy[0]["adet"] = int(uy[0]["adet"]) - 1
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
        elif op == "oda_ekle":
            q, neden = _ebeveyn_banyosu(p, o)
            if q is None:
                olmayan.append(f"{_soz(o)}: {neden}")
            else:
                p = q
    return p, olmayan


# ── oda ekleme: ebeveyn banyosu (BK-15) ──────────────────────────────────────────────────────────────────────────────────
IC_PAY = 5.25                           # eksen → net, iç duvar yüzü (yarım karkas 8 + alçıpan 1,25; denetçideki 10,5'in yarısı)
KISA_PARCA_CM = 15                      # "çelikte 15 cm parça çıkmaz" (D-10; denetçideki sınır)
BANYO_OLCULERI = sorted(((w, h) for w in range(200, 265, 5) for h in range(200, 265, 5)), key=lambda t: (t[0] * t[1], abs(t[0] - t[1]), t))
KOSELER = ((0, 0), (1, 0), (0, 1), (1, 1))  # (x0 | x1, y0 | y1) köşesi; sabit sıra
KOL_CM = 100                            # banyonun yanında kalan yatak odası kolu (eksenden; geçit)
KAPI_DUVARI_CM = 100                    # yatak odasının var olan kapısı için kalan ortak duvar (iç kapı 90)
PENCERE_PAYI_CM = 35                    # cephe koşusundan pencereye kalan (köşe ve duvar payları; denetçide 130 cm koşuya 97 cm sığar)
BUYUME = tuple((yon, cm) for yon in "GKBD" for cm in (100, 150, 200, 250))
EN_COK_DENETIM = 12                     # bir yerleşimde denetçiye giden en çok aday (denetim ~0,15 sn)
EBEVEYN_SOZU = ("ebeveyn", "yatak", "oda", "master")  # oda söylenmediyse bayinin sözünde yatak odası banyosu geçmeli ("bir banyo daha"
                                                     # ortak ikinci banyo olabilir; geometri hakemi 27.10 ikinci tur)
EBEVEYN_ADI = "Ebeveyn Banyo"           # "Ebeveyn Banyosu" ~2 m'lik banyoda plan görselinin sabit yazısına sığmıyor, duvarı aşıyordu


def _alan(r: list) -> int:
    return (r[2] - r[0]) * (r[3] - r[1])


def _netci(p: dict, ad: str):
    """`ad` mahalinin içindeki eksenden bir dikdörtgenin net eni ve boyu: her yüzün payı o yüzün ötesine göre — mahalin kendisi 0, başka iç
    mahal 5,25, dışarısı ya da veranda dış duvar yüzü (karkas/10 + 2,5: 80'likte 10,5, 140'lıkta 16,5); karışık yüzde büyüğü. `ayri`: mahalin
    içinden ayrılacak (banyo) kutu, ona bakan yüz iç duvardır; `oda=False`: dikdörtgen mahalden ayrı bir oda (banyo), mahale bakan yüzü de iç
    duvar. Önceki tahmin yalnız 0, en ve boy çizgisini dış sayıyordu; verandaya bakan yüz iç sayılınca gövde 5–11 cm fazla çıkıyordu
    (geometri hakemi 27.10 ikinci tur, B2)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    dis_pay = (p.get("dis_karkas") or 80) / 10 + 2 * 1.25
    kendi = unary_union([box(*r) for x in p["mahaller"] if x["ad"] == ad for r in x["dikdortgenler"]])
    ic = unary_union([box(*r) for x in p["mahaller"] if x["ad"] != ad and x["islev"] != "veranda" for r in x["dikdortgenler"]])

    def pay(s, ayri, oda: bool) -> float:
        a, k, i = s.area, s.intersection(kendi).area, s.intersection(ic).area
        if ayri is not None:
            j = s.intersection(ayri).area
            k, i = k - j, i + j
        if not oda:
            k, i = 0.0, i + k
        return max(0.0, IC_PAY if i > 0.01 else 0.0, dis_pay if a - k - i > 0.01 else 0.0)

    def net(r, ayri=None, oda: bool = True) -> tuple[float, float]:
        x0, y0, x1, y1 = r
        bb = box(*ayri) if ayri is not None else None
        return (x1 - x0 - pay(box(x0 - 1, y0, x0, y1), bb, oda) - pay(box(x1, y0, x1 + 1, y1), bb, oda),
                y1 - y0 - pay(box(x0, y0 - 1, x1, y0), bb, oda) - pay(box(x0, y1, x1, y1 + 1), bb, oda))
    return net


def _govde(p: dict, ad: str) -> float:
    """Mahalin gövdesi: içine sığan eksenden dikdörtgenlerin (köşeler mahalin kendi çizgilerinde) en büyük net dar kenarı. Denetçi dar kenarı
    net bölgenin sınır kutusundan ölçer; L odada bu, kesmeden önceki ölçüdür."""
    from itertools import combinations
    from shapely.geometry import box
    from shapely.ops import unary_union
    rs = next(x for x in p["mahaller"] if x["ad"] == ad)["dikdortgenler"]
    oda, net = unary_union([box(*r) for r in rs]), _netci(p, ad)
    xs, ys = sorted({r[0] for r in rs} | {r[2] for r in rs}), sorted({r[1] for r in rs} | {r[3] for r in rs})
    return max((min(net([x0, y0, x1, y1])) for x0, x1 in combinations(xs, 2) for y0, y1 in combinations(ys, 2)
                if box(x0, y0, x1, y1).difference(oda).area <= 0.01), default=0.0)


def _banyo_kes(p: dict, yatak: str, ad: str) -> dict | None:
    """Banyoyu yatak odasının ana dikdörtgeninin bir köşesinden keser (oda L olur, kapı odadan, vasistas `_yeniden_ac`'tan). Adaylar ucuz ön
    elemeden (oda en küçüğü ve kollar, dış cephe, banyonun net alanı ve dar kenarı, 15 cm parça) geçer ve sıralanır: önce var olan banyoya
    bitişik (ıslak hacimler yan yana, tesisat), sonra penceresi giriş cephesinde olmayan, sonra küçük ölçü; eşitlikte köşe sırası. Kapı duvarı
    ve pencere denetiminden sonra denetçiden geçen ilk aday alınır. Yatak odasının pencereleri yerinde kalır: penceresinin cephesini daraltan
    aday atılır (pencere başka cepheye taşınmaz). Kalan L odanın gövdesi (en büyük iç dikdörtgeni) yatak odasının dar kenar kuralını netten
    sağlar: denetçi dar kenarı sınır kutusundan ölçer, kesmeden önceki ölçüyü görürdü (geometri hakemi 27.10, bulgu 1; bankadaki L yatak
    odalarında da gövde ≥ 305 cm)."""
    k = kurallar()["odalar"]
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    net = _netci(p, yatak)
    cizgi = [{r[e] for x in p["mahaller"] for r in x["dikdortgenler"]} | {r[e + 2] for x in p["mahaller"] for r in x["dikdortgenler"]}
             | {0, (W, H)[e]} for e in (0, 1)]
    giris = {kp.get("cephe") for kp in p["kapilar"] if "dis" in kp["arasinda"] and kp.get("cephe")}
    banyolar = [x for x in p["mahaller"] if x["islev"] == "banyo"]
    m = next(x for x in p["mahaller"] if x["ad"] == yatak)
    i = max(range(len(m["dikdortgenler"])), key=lambda j: _alan(m["dikdortgenler"][j]))
    x0, y0, x1, y1 = m["dikdortgenler"][i]
    toplam = sum(_alan(r) for r in m["dikdortgenler"])
    adaylar = []
    for w, h in BANYO_OLCULERI:
        if x1 - x0 - w < KOL_CM or y1 - y0 - h < KOL_CM or toplam - w * h < k["yatak_odasi"]["en_az_m2"] * 1e4:
            continue
        for sira, (kx, ky) in enumerate(KOSELER):
            b = [x0 if kx == 0 else x1 - w, y0 if ky == 0 else y1 - h]
            b += [b[0] + w, b[1] + h]
            cephe = {c for c, var in zip("BDGK", (b[0] == 0, b[2] == W, b[1] == 0, b[3] == H)) if var}
            if not cephe:                                                         # vasistas dış cepheden
                continue
            nw, nh = net(b, oda=False)
            if nw * nh < k["banyo"]["en_az_m2"] * 1e4 or min(nw, nh) < k["banyo"]["dar_kenar_cm"]:
                continue
            serit = [x0, y0 + h, x1, y1] if ky == 0 else [x0, y0, x1, y1 - h]      # L'nin iki iç dikdörtgeni: banyo satırları dışı,
            kolon = [x0 + w, y0, x1, y1] if kx == 0 else [x0, y0, x1 - w, y1]      # banyo sütunları dışı
            if max(min(net(r, ayri=b)) for r in (serit, kolon)) < k["yatak_odasi"]["dar_kenar_cm"]:
                continue
            if any(0 < abs(a - c) <= KISA_PARCA_CM for e in (0, 1) for a in (b[e], b[e + 2]) for c in cizgi[e]):
                continue
            islak = any(_komsu_mu({"dikdortgenler": [b]}, x, 60) for x in banyolar)
            adaylar.append(((not islak, bool(cephe & giris), w * h, abs(w - h), w, sira), b, kx, ky))
    n = 0
    for _, b, kx, ky in sorted(adaylar, key=lambda t: t[0]):
        w, h = b[2] - b[0], b[3] - b[1]
        q = copy.deepcopy(p)
        mm = next(x for x in q["mahaller"] if x["ad"] == yatak)
        serit = [x0, y0 + h, x1, y1] if ky == 0 else [x0, y0, x1, y1 - h]          # banyo satırları dışında tam en
        yan = [b[2], b[1], x1, b[3]] if kx == 0 else [x0, b[1], b[0], b[3]]         # banyonun yanı
        mm["dikdortgenler"] = mm["dikdortgenler"][:i] + mm["dikdortgenler"][i + 1:] + [serit, yan]
        q["mahaller"].append({"ad": ad, "islev": "banyo", "dikdortgenler": [b]})
        q["kapilar"].append({"arasinda": [yatak, ad]})
        komsular = {x for kp in p["kapilar"] if yatak in kp["arasinda"] for x in kp["arasinda"] if x not in ("dis", yatak)}
        if any(not _komsu_mu(mm, x, KAPI_DUVARI_CM) for x in q["mahaller"] if x["ad"] in komsular):
            continue
        ce = cepheler(q["mahaller"], W, H).get(yatak, {})
        if any(ce.get(pc["cephe"], 0) < int(pc["olcu"].split("x")[0]) * int(pc.get("adet") or 1) + PENCERE_PAYI_CM
               for pc in p["pencereler"] if pc["mahal"] == yatak):
            continue
        _yeniden_ac(q)
        if not {yatak, ad} <= {pc["mahal"] for pc in q["pencereler"]} or _govde(q, yatak) < k["yatak_odasi"]["dar_kenar_cm"]:
            continue
        n += 1
        if denetle(q)["gecerli"]:
            return q
        if n >= EN_COK_DENETIM:
            return None
    return None


ORTAK_BANYO = "ortak banyo kalmıyor: banyolardan birine yatak odasından geçmeden ulaşılmalı"


def _ortak_banyo(p: dict) -> bool:
    """Banyolardan en az birine girişten yatak odasından geçmeden ulaşılıyor mu (kapı grafiği, veranda dış; denetçinin erişim ölçütü). Denetçi
    bunu yalnız tek banyoda arar; revizyon ikinci banyo eklediğinde ortak banyo kapı işlemleriyle kaybolmasın (geometri hakemi 27.10, bulgu 2)."""
    ver = {m["ad"] for m in p["mahaller"] if m["islev"] == "veranda"}
    yatak = {m["ad"] for m in p["mahaller"] if m["islev"] == "yatak_odasi"}
    banyo = {m["ad"] for m in p["mahaller"] if m["islev"] == "banyo"}
    komsu: dict[str, set[str]] = {}
    for kp in p["kapilar"]:
        a, b = ["dis" if x in ver else x for x in (kp["arasinda"] + ["", ""])[:2]]
        komsu.setdefault(a, set()).add(b)
        komsu.setdefault(b, set()).add(a)
    gor, sira = {"dis"}, ["dis"]
    while sira:
        u = sira.pop()
        if u in banyo:
            return True
        for v in sorted(komsu.get(u, ())):
            if v not in gor and v not in yatak:
                gor.add(v)
                sira.append(v)
    return False


def _dar_govdeler(q: dict, onceki: dict) -> list[str]:
    """Birden çok dikdörtgenli (L) yatak odasının gövdesi dar kenar kuralının altındaysa ve revizyonla daraldıysa (ya da oda yeniyse) ihlal.
    Denetçi dar kenarı sınır kutusundan ölçer; banyo kesildikten sonra gelen işlem (ör. ön şeridi kısaltan `oda_kucult`) L odanın gövdesini
    daraltabiliyordu (geometri hakemi 27.10 ikinci tur, B1). Tek dikdörtgenli odayı denetçi doğru ölçer."""
    sinir = kurallar()["odalar"]["yatak_odasi"]["dar_kenar_cm"]
    out = []
    for m in q["mahaller"]:
        if m["islev"] != "yatak_odasi" or len(m["dikdortgenler"]) < 2:
            continue
        g = _govde(q, m["ad"])
        o = next((x for x in onceki["mahaller"] if x["ad"] == m["ad"] and x["islev"] == "yatak_odasi"), None)
        if g + 1e-6 < sinir and (o is None or _govde(onceki, m["ad"]) > g + 1e-6):
            out.append(f"{m['ad']} gövdesi {g:.0f} cm, en az {sinir} cm (net; L odanın en geniş iç dikdörtgeni, yatak odası kuralı)")
    return out


def _denetle(q: dict, talep: dict, kod: str, onceki: dict) -> dict:
    """Revizyonun denetimi: denetçi (oda programıyla), ortak banyonun korunması ve L yatak odasının gövdesi."""
    d = denetle(q, {"oda_programi": talep.get("oda_programi")}, kod=kod)
    if d["gecerli"]:
        ihlal = ([ORTAK_BANYO] if _ortak_banyo(onceki) and not _ortak_banyo(q) else []) + _dar_govdeler(q, onceki)
        if ihlal:
            d = {**d, "gecerli": False, "tanim": None, "ihlaller": ihlal}
    return d


def _ebeveyn_banyosu(p: dict, o: dict) -> tuple[dict | None, str | None]:
    """`oda_ekle`: yalnız banyo ve yalnız yatak odasının içinden. Oda söylenmediyse en büyük yatak odası (eşitlikte plandaki ilk). Odaya
    sığmazsa (oda en küçüğün altına düşer, kollar daralır, pencere ya da kapı yeri kalmaz) oda bir kenarından 100–250 cm büyütülüp yeniden
    denenir (`_oda_kenari`: dış cephede ev büyür, iç kenarda komşu küçülür); geçenlerden evi en az büyüten, eşitlikte G, K, B, D sırası."""
    islev = o.get("islev")
    if islev != "banyo":
        return None, f"{ISLEV_ADI.get(islev, 'yeni oda')} ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"
    if o.get("mahal"):
        m = next((x for x in p["mahaller"] if x["ad"] == o["mahal"]), None)
        if m is None:
            return None, f"'{o['mahal']}' adlı mahal yok"
        if m["islev"] != "yatak_odasi":
            return None, f"banyo yalnız bir yatak odasının içinden eklenebiliyor ({m['ad']} yatak odası değil)"
    else:
        if not any(s in (o.get("alinti") or "").casefold() for s in EBEVEYN_SOZU):
            return None, "banyonun hangi odadan açılacağı belli değil (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"
        yataklar = [x for x in p["mahaller"] if x["islev"] == "yatak_odasi"]
        if not yataklar:
            return None, "planda yatak odası yok"
        m = max(yataklar, key=lambda x: sum(_alan(r) for r in x["dikdortgenler"]))
    adlar = {x["ad"] for x in p["mahaller"]}
    ad = next(a for a in [EBEVEYN_ADI] + [f"{EBEVEYN_ADI} {j}" for j in range(2, 10)] if a not in adlar)
    if not denetle(p)["gecerli"]:             # başlangıç kurallara uymuyorsa hiçbir aday uymaz; arama boşuna bir dakikayı buluyordu (aynı mesajdaki
        return None, "planın bu hâli kurallara uymadığı için banyo eklenemedi"     # önceki işlemin ara hâli; geometri hakemi ikinci tur, süre)
    q = _banyo_kes(p, m["ad"], ad)
    if q is not None:
        return q, None
    brut = lambda x: x["dis_olcu"]["en"] * x["dis_olcu"]["boy"]       # noqa: E731
    buyutulmus = [(brut(g) - brut(p), sira, g) for sira, (yon, cm) in enumerate(BUYUME) for g in [_oda_kenari(p, m["ad"], yon, cm)[0]]
                  if g is not None]
    for _, _, g in sorted(buyutulmus, key=lambda t: t[:2]):            # evi en az büyüten (eşitlikte G, K, B, D ve küçük cm) ilk geçen
        q = _banyo_kes(g, m["ad"], ad)
        if q is not None:
            return q, None
    return None, f"{m['ad']} içine sığmıyor; odayı büyüterek de yerleştiremedim"


IHLAL_TURU = re.compile(r"^(dış kapı|kapı|pencere|çatı|geometri):\s*")       # yalnız tek ad; "kapı yayları çakışıyor:" cümledir, kalır


def _ayni(a: dict, b: dict) -> bool:
    """İki plan içerikçe aynı mı: pencereler (mahal, cephe, ölçü) başına adet toplamıyla, kapılar sırasız (bütün alanlarıyla). Kaldır + aynı ölçüde ekle
    (girdi sırası ve `adet` anahtarı değişir) aynı plandır; revizyon hakkı yakılmaz."""
    def kanon(p):
        say: dict = {}
        for x in p.get("pencereler") or []:
            k = (x["mahal"], x["cephe"], x["olcu"]); say[k] = say.get(k, 0) + int(x.get("adet") or 1)
        kapilar = sorted(json.dumps({**k, "arasinda": sorted(k["arasinda"])}, sort_keys=True, ensure_ascii=False) for k in p.get("kapilar") or [])
        return json.dumps({**p, "pencereler": sorted(say.items()), "kapilar": kapilar}, sort_keys=True, ensure_ascii=False, default=str)
    return kanon(a) == kanon(b)


def _kisa(ihlal: str, sinir: int) -> str:
    """Denetçi ihlalinin bayiye giden kısa biçimi: baştaki tür ("kapı: ") ve parantezli ayrıntı atılır, sözcük sınırında kesilir."""
    t = IHLAL_TURU.sub("", ihlal.split(" (")[0]).strip()                         # tür adı atılır, mahal adı ("Banyo: …") kalır
    return t if len(t) <= sinir else t[:sinir].rsplit(" ", 1)[0] + "…"


def _sirayla(plan: dict, islemler: list[dict], talep: dict, kod: str,
             buyume: dict | None = None) -> tuple[dict, dict | None, list[str], list[dict], bool]:
    """İşlemleri sırayla tek tek uygular ve denetler; geçmeyenler bir tur daha denenir (sonraki işlemin mümkün kıldığı erken işlem, ör. hol
    genişleyince sığan pencere; hakem ikinci tur). Dönüş: (plan, son geçen denetim ya da None, uygulanamayan, uygulanan işlemler,
    denetçiden geçmeyen işlem var mı). `buyume` verilirse uygulanan oda eklemesinin dış ölçüye etkisi işleme göre yazılır."""
    p, son, kalan, bekleyen, olmayan, kurala = plan, None, [], list(islemler), [], False
    for _ in range(2):
        olmayan, sonraki, kurala = [], [], False                 # son turun sonucu geçerli
        for o in bekleyen:
            q, neden = uygula(p, [o])
            if neden:
                olmayan += neden
                sonraki.append(o)
                continue
            if _ayni(q, p):                                      # plan zaten öyle: düşen istek değil
                continue
            d = _denetle(q, talep, kod, plan)
            if d["gecerli"]:
                if buyume is not None and o["op"] == "oda_ekle":
                    buyume[id(o)] = _buyume(p, q)
                p, son = q, d
                kalan.append(o)
            else:
                soz = _soz(o)[:40]
                olmayan.append(f"{soz}: {_kisa((d['ihlaller'] or ['kurallara uymuyor'])[0], max(20, 78 - len(soz)))}")
                sonraki.append(o)
                kurala = True
        if not sonraki or len(sonraki) == len(bekleyen):
            break
        bekleyen = sonraki
    return p, son, olmayan, kalan, kurala


def _buyume(once: dict, sonra: dict) -> tuple[str, int, int] | None:
    """Oda eklemenin evi büyütmesi: (en|boy, önce, sonra) cm; büyümediyse None."""
    for e in ("en", "boy"):
        if sonra["dis_olcu"][e] != once["dis_olcu"][e]:
            return e, once["dis_olcu"][e], sonra["dis_olcu"][e]
    return None


def _duzenlenen_odalar(eski: dict, yeni: dict, fark: list[str], buyumeler: list | None = None) -> list[str]:
    """Oda eklemenin farkı: ev büyüdüyse nedeni dış ölçü satırının ardına açıkça yazılır ("ebeveyn banyosu için ev 100 cm büyüdü"; CIO
    27.10: fiyatı teklif adımı yeniden hesaplar). Biçimi değişen ama alanı `plan_farki` eşiğinin (0,25 m²) altında değişen oda da yazılır
    (büyütmede duvarı kayıp L olan yatak odası; geometri hakemi 27.10, bulgu 3); bu satır mahal satırlarının ardına girer."""
    from beyin.plan_uretici import _tr
    i = next((j + 1 for j, f in enumerate(fark) if f.startswith("dış ölçü ")), 0)
    kalan, satir = {e: yeni["dis_olcu"][e] - eski["dis_olcu"][e] for e in ("en", "boy")}, []
    for e, a, c in filter(None, buyumeler or []):
        if 0 < c - a <= kalan[e]:                       # büyüme son planda duruyorsa (sonraki işlem geri almadıysa; hakem ikinci tur B3)
            satir.append(f"ebeveyn banyosu için ev {c - a} cm büyüdü ({e} {a} → {c} cm)")
            kalan[e] -= c - a
    fark = fark[:i] + satir + fark[i:]
    em = {m["ad"]: m for m in eski["mahaller"]}
    olcu = lambda m: sorted((r[2] - r[0], r[3] - r[1]) for r in m["dikdortgenler"])        # noqa: E731
    ek = [f"{m['ad']} yeniden düzenlendi ({_tr(sum(_alan(r) for r in m['dikdortgenler']) / 1e4)} m²)" for m in yeni["mahaller"]
          if m["ad"] in em and olcu(m) != olcu(em[m["ad"]]) and not any(f.startswith(m["ad"] + " ") for f in fark)]
    i = next((j for j, f in enumerate(fark) if f.startswith(("pencere ", "kapı ", "dış kapı", "dış duvarlar", "çatı "))), len(fark))
    return fark[:i] + ek + fark[i:]


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
    yeni, olmayan, kalan, buyume = plan, [], [], {}          # işlem işlem (uygula(plan, hepsi) ile aynı sonuç): uygulanan kimlikle izlenir
    for x in o["islemler"]:
        once = yeni
        yeni, n = uygula(yeni, [x])
        olmayan += n
        if not n:
            kalan.append(x)
            if x["op"] == "oda_ekle":
                buyume[id(x)] = _buyume(once, yeni)
    s["uygulanamayan"] += olmayan
    if _ayni(yeni, plan):                                       # yazılışı farklı, içeriği aynı plan yeniden çizilmez (hakem 16.10)
        s["ihlaller"] = ["uygulanacak işlem kalmadı"]
        # plan değişmedi: istek yoksa "bos" (karar sorar, inceleme C2); istek anlaşıldı ama uygulanamadıysa (L/cumba çatı, çift kat, belirsiz
        # cephe) "uygulanamadi" — bayiye istek adıyla yazılır, plan aynen geçerli ve onaylanabilir kalır (Lokman 15.10, karar 3)
        s["durum"] = "uygulanamadi" if s["uygulanamayan"] else "bos"
        return s
    d = _denetle(yeni, talep, kod, plan)
    s["denemeler"] = [{"plan": yeni, "gecerli": d["gecerli"], "ihlaller": d["ihlaller"]}]
    if not d["gecerli"]:
        s["ihlaller"] = d["ihlaller"][:8]
        # birlikte kurallara uymadı: işlemler sırayla tek tek denenir; geçen uygulanır, geçmeyen bayinin sözü ve kısa gerekçesiyle yazılır
        # (geometri hakemi 15.10, Önemli 2: pencere cepheye değer ama sığmaz; büyütme bir kapıyı sığmaz kılar). Hiçbiri geçmezse plan aynen,
        # istek gerekçesiyle "uygulanamadi" (Lokman 16.10, canlı deneme G: konuşma kapanmaz; `kurala_uymayan` ile karar Patron'a bilgi verir)
        buyume = {}
        yeni, d, olmayan, kalan, kurala = _sirayla(plan, o["islemler"], talep, kod, buyume)
        s["uygulanamayan"], s["kurala_uymayan"] = list(o["uygulanamayan"]) + olmayan, kurala
        if d is None:
            s["durum"] = "uygulanamadi" if s["uygulanamayan"] else "gecersiz"
            return s
        s["denemeler"].append({"plan": yeni, "gecerli": True, "ihlaller": [], "sirayla": True})
        s["ihlaller"] = []
    s.update(durum="gecerli", plan=yeni, tanim=d["tanim"], ozet=d["ozet"], fark=plan_farki(plan, yeni))
    if any(x["op"] == "oda_ekle" for x in kalan):
        s["fark"] = _duzenlenen_odalar(plan, yeni, s["fark"], [buyume.get(id(x)) for x in kalan if x["op"] == "oda_ekle"])
    if any(x["op"] in ("oda_buyut", "oda_kucult") and not x.get("cm") for x in kalan):
        s["fark"].append("ölçü söylenmediği için 50 cm alındı")       # varsayım bayiye yazılır (inceleme G10)
    return s
