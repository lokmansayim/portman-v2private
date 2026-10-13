"""Prefabrik kör test serisi · kendi yükleme listemiz, sürüm 2 (İE-11 PR-2; protokol `docs/sartname/prefabrik_kor_test.md` adım 3).

    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py <İş Emri.json> <çıktı klasörü> [--pafta <pafta_katmani.json>]

Gerçek liste AÇILMADAN yazılır ve depoya kaydedilir; kıyas ondan sonra. Hiçbir adet elle yazılmaz. Üç sütun:
  - **adet** (varsayılan): canlı pano Motor'unun planından sayım + kural kitabı (`kurallar/liste/kurallar.json`) + aşağıdaki
    "PK-01 dersleri" (yalnız PK-01'de bizim hatamız çıkanlar; protokol §5) + liste açılmadan paftadan düzeltilenler.
  - **pafta**: o projenin montaj paftasından okunan adet (`--pafta`); varsayılanı değiştirmez.
  - **aday**: karar bekleyen kural adayı — fabrika şablonunun formül sütunu ("PORTATİFEV YÜKLEME LİSTESİ", Ubeydullah, 1 Ekim 2026)
    ve PK-01'den çıkan hipotezler (Lokman'ın 13 Ekim soruları 1–6). Kıyasta varsayılanla yan yana sınanır; varsayılanı değiştirmez.

Sürüm 1 (`deneme/2026-10-13_pk_01/yukleme_listesi.py`, PK-01 için commit `aebcfca`) olduğu gibi durur. Sürüm 2'deki değişiklikler:

PK-01 dersleri (PK-01 kıyası "Bizim hatalarımız" 1–10; `deneme/2026-10-13_pk_01/sonuc/PK01_kiyas.md`):
  1. `alici_ait` içinde "pencere" geçiyorsa pencere grubunun tamamı alıcıya ait (pencere, karkas ve U'lar listeye girmez).
  2. Pano sipariş boyu: net boy − 2,5 mm, 5 mm'ye aşağı (1255 → 1250, 1225 → 1220, 1205 → 1200, 1115 → 1110); P6001'in
     "T panosu listede 1250" kuralı kalktı.
  3. Her pencereye (120'lik) özel pencere karkası; "kör kasa yalnız 120/180" satırı kalktı. Vasistasa karkas yok.
  4. 60'lık alt çerçeve L 2500: iç duvar ÷ 2,5.
  5. Baş makas Z'si yok (0); baş makas omegası = kalkan duvar boyları ÷ 2,5.
  6. Köşebent prefabrikte 0.
  7. Dere kapağı beşikte 4; iniş borusu iniş başına L 2500 + L 500.
  8. Tavan "asma dizme tavan": 60'lık duvar omegası, tavan H'ı, PVC omega kapak, betopan haşı; yöntem B tavan omegası yok.
  9. Vida takımı prefabrik: alçıpan ve pencere vidası yok; betopan / kapı kolu, sandviç panel trapez vidası, uçlar, inox taş.
 10. İç kapı 82 × 196, sağ / sol Motor'un D-13 menteşesinden (PK-01'de 3 sağ + 2 sol tuttu).
  Ayrıca PK-01'de tutan: saçak omegası toplam saçak boyu ÷ 2,5 bir kez yukarı (9).
Liste açılmadan PK-02 paftasından düzelenler (pafta girdidir; gerçek liste değil):
  P1. Makas sayısı: saçak duvarının pano koşusu (dış ölçü − 2 duvar) ÷ 125,5 yukarı + 1 (773'te 7; eski formül 8 veriyordu).
  P2. Aşık sırası yüz başına ⌈(eğik − 0,20) ÷ 0,60⌉ + 1 ("aşık 60 cm'de bir, mahya aşığı 20 cm'de"; PK-01 7, PK-02 8).
  P3. Sandviç panel: iki yüz birlikte ⌈2 × mahya boyu ÷ kapatma⌉ (kesilen panel paylaşılır; PK-01 22, PK-02 17); boy eğik boy
      100 mm'ye yukarı (3475 → 3500, 4240 → 4300).
LLM yok, ağ yok.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor import geometry as G  # noqa: E402

SURUM = "2 (13 Ekim 2026; PK-01 dersleri + PK-02 paftası)"
GRUPLAR = {"1001": "Panel", "1002": "Metal aksam", "1003": "Kapı ve pencere", "1004": "Tavan", "1005": "Makas", "1006": "Çatı",
           "1007": "Elektrik", "1008": "Vida", "1009": "Depo", "1010": "Sıhhi tesisat", "1011": "Dere", "1012": "Boya"}
TAVAN = lambda x: int(math.ceil(x - 1e-9))
PENCERE_UST_KOTU_CM = 200.0           # Motor: pencere üst kotu / kapı üstü 200 (lento = h − 200)
PENCERE_ESIK_CM = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}
ASMA_OMEGA_ARALIK_M = 1.255           # PK-02 tavan omega planı notu: "omega profiller 125 cm'de bir"; PK-01: "125,5 cm'de bir"
TAVAN_H_ARALIK_M = 0.625              # PK-01 şablonu: "duvar omegalarına dik, 62,5 cm'de bir"


def _kural(k: dict, *yol):
    v = k
    for a in yol:
        v = v[a]
        if isinstance(v, dict) and "deger" in v and a == yol[-1]:
            return v["deger"]
        if isinstance(v, dict) and "deger" in v:
            v = v["deger"]
    return v


def siparis(cm: float) -> int:
    """Pano sipariş boyu (PK-01 dersi 2): net boy − 2,5 mm, 5 mm'ye aşağı. 50 / 50 pano tuttu."""
    return int(math.floor((cm * 10 - 2.5) / 5 + 1e-6) * 5)


def mm(cm: float) -> str:
    v = round(cm * 10, 1)
    return f"{v:g}".replace(".", ",")


def pano_ekleri(plan, eave_yon: str) -> list:
    """Bir duvardaki ardışık iki panonun her eki; ekte üçlü H varsa "uclu", yoksa "pano_eki". `saçak` = ek saçak duvarında (makas
    ayakları orada; PK-01 hipotezi: kulaklı H = makasa denk gelen dış ek)."""
    cik = []
    for d in plan.duvarlar:
        for a, _b in zip(d.panolar, d.panolar[1:]):
            x, y = (a.a1, d.c) if d.yon == "x" else (d.c, a.a1)
            uclu = any(abs(h.x - x) <= d.h + 3.5 and abs(h.y - y) <= d.h + 3.5 for h in plan.h_baglantilar)
            cik.append({"duvar": d.tur, "cins": "uclu" if uclu else "pano_eki", "sacak": d.yon == eave_yon})
    return cik


def model(ie: dict) -> dict:
    plan = G.kur(json.loads(json.dumps(ie)))
    y = ie["yapi"]
    H0 = float(y.get("duvar_yuksekligi_cm", 250))
    dis = [d for d in plan.duvarlar if d.tur == "dis"]; ic = [d for d in plan.duvarlar if d.tur == "ic"]
    t_dis = 2 * dis[0].h
    from shapely.geometry import box
    from shapely.ops import unary_union
    kapali = [m for m in plan.mahaller.values() if not (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    acik = [m for m in plan.mahaller.values() if (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    g = unary_union([plan.footprint()] + [m.poly for m in plan.mahaller.values() if m.poly is not None] + [box(*r) for r in plan.dikmeler])
    bx0, by0, bx1, by1 = g.bounds
    c = ie.get("cati") or {}
    mx = c.get("makas_ekseni", "x") == "x"                     # makaslar x'i geçiyorsa saçak duvarları y yönünde koşar
    return {"plan": plan, "H0": H0, "t_dis": t_dis, "dis": dis, "ic": ic, "kapali": kapali, "acik": acik, "mx": mx,
            "ekler": pano_ekleri(plan, "y" if mx else "x"), "W": bx1 - bx0, "D": by1 - by0, "brut_m2": round((bx1 - bx0) * (by1 - by0) / 1e4, 3)}


def asma_tavan_hatlari(kapali, mx: bool) -> tuple[float, list]:
    """Asma dizme tavan omega hatları: her kapalı odada, mahyaya paralel, 125,5 cm'de bir (PK-02 tavan omega planı: banyo 2, yatak 2,
    hol 1, mutfak 2, salon 3 hat; hat sayısı = oda net derinliği ÷ 1,255 en yakın tamsayıya, en az 1; hat boyu oda net genişliği).
    Döner: (toplam m, hat boyları m)."""
    hatlar = []
    for m in kapali:
        x0, y0, x1, y1 = m.poly.bounds
        en, derin = ((y1 - y0), (x1 - x0)) if mx else ((x1 - x0), (y1 - y0))
        n = max(1, int(math.floor(derin / 100 / ASMA_OMEGA_ARALIK_M + 0.5)))
        hatlar += [en / 100] * n
    return sum(hatlar), hatlar


def liste(ie: dict, k: dict, pafta: dict | None = None) -> dict:
    m = model(ie)
    plan, H0 = m["plan"], m["H0"]
    kucuk = lambda x: str(x).replace("İ", "i").replace("I", "ı").lower()
    oz = {kucuk(kk): kucuk(v) for kk, v in (ie.get("ozellikler") or {}).items()}
    alici = [kucuk(x) for x in ((ie.get("alici_ait") or {}).get("kalemler") or [])]
    pencere_alici = any("pencere" in x for x in alici) or "alıcı" in oz.get("pencere rengi", "")
    satirlar = []
    P = pafta or {}

    def pk(*yol):
        v = P
        for a in yol:
            v = (v or {}).get(a)
        return (v or {}).get("adet"), (v or {}).get("not", "")

    def ekle(grup, kalem, olcu, adet, dayanak, formul, kaynak="", birim="adet", pafta=None, aday=None, aday_notu=""):
        pa, pn = pk(*pafta) if pafta else (None, "")
        satirlar.append({"grup": grup, "grup_adi": GRUPLAR[grup], "kalem": kalem, "olcu": olcu, "adet": adet, "birim": birim, "dayanak": dayanak,
                         "formul": formul, "kaynak": kaynak, "pafta": pa, "pafta_notu": pn, "aday": aday, "aday_notu": aday_notu})

    # ── ortak çatı ölçüleri ─────────────────────────────────────────────────
    c = ie.get("cati") or {}
    sac = float(c.get("sacak_cm", 30)) / 100; eg = float(c.get("egim_yuzde", 33)) / 100
    mx = m["mx"]
    aciklik, bina_boyu = (m["W"], m["D"]) if mx else (m["D"], m["W"])
    egik = (aciklik / 200 + sac) * math.sqrt(1 + eg * eg)
    mahya_boy = bina_boyu / 100 + 2 * sac
    bina_m2 = m["brut_m2"]
    tavan_kuru = sum(x.alan_m2 for x in m["kapali"] if x.tur not in ("banyo", "wc", "islak"))
    tavan_islak = sum(x.alan_m2 for x in m["kapali"] if x.tur in ("banyo", "wc", "islak"))
    tavan_net = tavan_kuru + tavan_islak

    # ── 1001 Panel ──────────────────────────────────────────────────────────
    sayac = Counter()
    for d in plan.duvarlar:
        kal = "100'lük" if d.tur == "dis" else "60'lık"
        kal_mm = round(2 * d.h * 10)
        for p in d.panolar:
            L = siparis(p.boy); a = p.acilim
            if a is None:
                sayac[(f"{kal} yapıştırma dolu pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", f"sipariş boyu (PK-01 dersi 2)")] += 1
            elif a.tur == "pencere":
                en, boy = G.PENCERE_OLCULERI[a.olcu]
                if a.olcu == "60x40":
                    sayac[(f"{kal} yapıştırma dolu vasistaslı pano (60/40)", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "vasistaslı pano")] += 1
                else:
                    ust = H0 - PENCERE_UST_KOTU_CM
                    sayac[("Pencere üst panel", f"{kal_mm} × {L} × {mm(ust)}", "Liste kuralı", "pencereli pano listede üst + alt panel")] += 1
                    sayac[(f"Pencere alt panel ({en}/{boy})", f"{kal_mm} × {L} × {mm(PENCERE_ESIK_CM[a.olcu])}", "Liste kuralı", "alt panel yüksekliği pencere eşiği")] += 1
            elif a.tur == "dis_kapi":
                sayac[("Karkaslı çelik kapı panosu", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "dış kapı boşluklu pano")] += 1
            elif a.tur == "ic_kapi":
                sayac[(f"{kal} karkaslı + kasalı pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "iç kapı boşluklu pano")] += 1
            else:
                sayac[(f"{kal} geçişli pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "kapısız geçiş")] += 1
    for (kalem, olcu, dayanak, kaynak), n in sorted(sayac.items(), key=lambda x: (x[0][0], -int(x[0][1].split(" × ")[1]))):
        ekle("1001", kalem, olcu, n, dayanak, "Motor planından sayım", kaynak)

    # ── 1002 Metal aksam ────────────────────────────────────────────────────
    kc = Counter("dis" if kk.tur == "dis" else "ic" for kk in plan.koseler)
    ekle("1002", "10'luk köşe direği 100 × 100", f"100 × 100 × {mm(H0)}", kc["dis"], "Sayım", "Motor köşe parçası",
         "PK-01'de 3 standart + özel B, C, D (soru 2: özel köşenin kuralı)")
    ekle("1002", "6'lık köşe direği 60 × 60", f"60 × 60 × {mm(H0)}", kc["ic"], "Sayım", "Motor iç köşe")
    ekle("1002", "Köşebent", "L 2500", 0, "Kural (PK-01)", "prefabrikte 0 (PK-01 dersi 6)", "", aday=7, aday_notu="şablon: \"tek kat için 7 adet yazılır\" (PK-01'de 0 girildi)")
    if plan.dikmeler:
        ekle("1002", "Özel kutu profil (kolon) 100 × 100", f"L {mm(H0)}", len(plan.dikmeler), "Sayım", "İş Emri `dikmeler`")
        ekle("1002", "Profil vidalama aparatı", "adet", 2, "Kural (PK-01)", "özel profil varsa 2 (PK-01: \"ekstradan ekledik\")")
    if plan.dikmeler and m["acik"]:
        from shapely.geometry import LineString
        for v in m["acik"]:
            vx0, vy0, vx1, vy1 = v.poly.bounds
            yanlar = set()
            for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
                if v.poly.buffer(1.0).contains(LineString([(x0, y0), (x1, y1)])):
                    yanlar.add("x" if abs(y1 - y0) < 1e-6 else "y")
            for eks in sorted(yanlar):
                dis_sinir = (vx1 - vx0) if eks == "x" else (vy1 - vy0)
                ekle("1002", "Kutu profil (kiriş) 100 × 100", f"L {mm(dis_sinir - 10)}", 1, "Liste kuralı", f"açık kenar dış ölçüsü {mm(dis_sinir)} − 100", "PK-01'de tuttu")
    ec = Counter((e["duvar"], e["cins"]) for e in m["ekler"])
    ek_s = Counter((e["duvar"], e["cins"]) for e in m["ekler"] if e["sacak"])
    ekle("1002", "H 100 (dış pano eki)", f"100 × 100 × {mm(H0)}", ec[("dis", "pano_eki")], "Sayım", "her dış ekte bir H", "kulaklı / dübelli ayrımı: soru 3",
         aday=f"kulaklı {ek_s[('dis', 'pano_eki')]} / dübelli {ec[('dis', 'pano_eki')] - ek_s[('dis', 'pano_eki')]}", aday_notu="hipotez: saçak duvarındaki (makas ayağı) ek kulaklı (PK-01 paftasında 12 / 7 tuttu)")
    ekle("1002", "H standart 60 (iç pano eki)", f"60 × 60 × {mm(H0)}", ec[("ic", "pano_eki")], "Sayım", "her iç ekte bir H")
    ekle("1002", "3'lü H 100 × 100 × 60 (dış duvar T'si)", f"L {mm(H0)}", ec[("dis", "uclu")], "Sayım", "iç duvarın dış duvara geldiği T", "soru 3",
         aday=f"kulaklı {ek_s[('dis', 'uclu')]} / dübelli {ec[('dis', 'uclu')] - ek_s[('dis', 'uclu')]}", aday_notu="aynı hipotez")
    ekle("1002", "3'lü H standart 60 (iç T)", f"L {mm(H0)}", ec[("ic", "uclu")], "Sayım", "iç–iç T birleşimi")
    dubelli = ec[("dis", "pano_eki")] + ec[("dis", "uclu")]
    if pencere_alici:
        ekle("1002", "Çektirme U'su / pencere U'su / pencere karkası", "—", 0, "İş Emri", "pencere grubu alıcıya ait (PK-01 dersi 1)")
    else:
        pen = [p.acilim for p in plan.panolar if p.acilim and p.acilim.tur == "pencere"]
        for olcu, n in sorted(Counter(a.olcu for a in pen if a.olcu != "60x40").items()):
            en, boy = G.PENCERE_OLCULERI[olcu]
            ekle("1002", f"Özel pencere karkası ({en}×{boy}) (100'lük çektirme U'su + 100'lük H geçen)", f"{en * 10} × {boy * 10}", n, "Sayım",
                 "her 120'lik pencereye bir karkas (PK-01 dersi 3)")
        ekle("1002", "Çektirme U'su 100", "100 × 2440", 2, "Kural (PK-01)", "pencere karkaslı gidince 2 sabit (PK-01: \"pencere özel iletiliyor, 2 adet fix yaz\")",
             aday=TAVAN(sum(2 * G.PENCERE_OLCULERI[a.olcu][0] for a in pen) / 244 + 2), aday_notu="şablon: (pencere × 2 × pencere eni) ÷ 244 + 2")
        ekle("1002", "100'lük pencere U'su H geçen", "L 2500", 1, "Kural (PK-01)", "PK-01'de 1",
             aday=TAVAN(sum(2 * G.PENCERE_OLCULERI[a.olcu][1] for a in pen) / 250), aday_notu="şablon: (pencere × 2 × pencere boyu) ÷ 250")
    ekle("1002", "Çektirme U'su 60", "60 × 2440", 2, "Kural (PK-01)", "PK-01'de 2 (şablon: \"duvarların ortasına gelen adet + 2\")")
    # tavan (asma dizme; PK-01 dersi 8)
    L_hat, hatlar = asma_tavan_hatlari(m["kapali"], mx)
    L_duvar = sum(p.boy for d in m["ic"] for p in d.panolar) / 100
    omega_adet = TAVAN((L_hat + L_duvar) / 3.65 + 5)
    ekle("1002", "60'lık duvar omegası (asma dizme tavan)", "60 × 3750", omega_adet, "Şablon formülü",
         f"(oda içi hatlar {L_hat:.2f} m [{len(hatlar)} hat, 125,5'te bir] + iç duvar üstleri {L_duvar:.2f} m) ÷ 3,65 + 5",
         "PK-01'de formül 21, girilen 8 (soru 1)", pafta=("duvar_omegasi_asma",))
    ekle("1002", "100'lük duvar omegası", "100 × 2500", 0, "Kural", "beşikte bütün dış duvarlar saçak ya da baş makas omegası alır", "PK-01'de 0")
    ekle("1002", "100'lük saçak omegası", "100 × 2500", TAVAN(2 * mahya_boy / 2.5), "Kural (PK-01)", f"saçak kenarları {2 * mahya_boy:.2f} m ÷ 2,5, bir kez yukarı",
         "PK-01'de 9 tuttu", aday=TAVAN(2 * bina_boyu / 100 / 2.5), aday_notu="şablon kaba hesabı: saçaklı olmayan duvar boyu ÷ 2,5 (PK-01: 20 ÷ 2,5 = 8)")
    ps, bs = _kural(k, "parca_boyu_m", "sacak_saci"), _kural(k, "bindirme_m", "sacak_saci")
    ekle("1002", "Saçak sacı (30'luk, 3'ü menfezli)", "300 × 2500", TAVAN(2 * mahya_boy / (ps - bs)), "Kural", f"saçak kenarları {2 * mahya_boy:.2f} m ÷ 2,3",
         "PK-01'de tuttu", aday=TAVAN(2 * mahya_boy / (ps - bs) + 2), aday_notu="şablon açıklaması \"+2\" (PK-01'de girilmedi)")
    alin = 4 * egik
    ekle("1002", "Alın sacı (30'luk)", "300 × 2500", TAVAN(alin / (_kural(k, "parca_boyu_m", "alin_saci") - _kural(k, "bindirme_m", "alin_saci"))), "Kural",
         f"alın boyu 4 × {egik:.3f} = {alin:.2f} m ÷ 2,3", "PK-01'de tuttu")
    kalkan = 2 * aciklik / 100
    ekle("1002", "Baş makas omegası", "L 2500", TAVAN(kalkan / 2.5), "Kural (PK-01)", f"kalkan duvarları 2 × {aciklik / 100:.2f} m ÷ 2,5 (PK-01 dersi 5)")
    ekle("1002", "Baş makas Z'si", "L 2800", 0, "Kural (PK-01)", "prefabrikte yok (PK-01 dersi 5)", aday=TAVAN(alin / 2.8), aday_notu="şablon: alın kenarları ÷ 2,8")
    yuks = (aciklik / 200 + sac) * eg
    ucgen = 0.5 * (aciklik / 100 + 2 * sac) * yuks
    ekle("1002", "Baş makas betopanı", "1250 × 2500", 2 * TAVAN(ucgen / 3.125), "Kural (uydurma)",
         f"iki baş makas üçgeni (saçakla), her biri {ucgen:.2f} m² ÷ 3,125 yukarı", "PK-01'de 4 (AutoCAD'den); bu formül PK-01'de 4 verir")
    dis_cevre = 2 * (m["W"] + m["D"]) / 100
    dis_boy = sum(p.boy for d in m["dis"] for p in d.panolar) / 100
    ekle("1002", "100'lük alt çerçeve", "100 × 3750", TAVAN(dis_boy / 3.75), "Liste kuralı", f"dış pano boyları {dis_boy:.2f} m ÷ 3,75",
         "PK-01'de tuttu", aday=TAVAN(dis_cevre / 3.75), aday_notu=f"şablon: dış çevre {dis_cevre:.2f} m ÷ 3,75")
    ekle("1002", "60'lık alt çerçeve", "60 × 2500", TAVAN(L_duvar / 2.5), "Kural (PK-01)", f"iç duvarlar {L_duvar:.2f} m ÷ 2,5 (PK-01 dersi 4)")

    # ── 1003 Kapı ve pencere ────────────────────────────────────────────────
    acl = [p.acilim for p in plan.panolar if p.acilim]
    for a in (a for a in acl if a.tur == "dis_kapi"):
        kapi_alici = a.dograma == "alıcıya ait" or "alıcı" in oz.get("dış kapı", "")
        ekle("1003", "Prefabrik çelik kapı", f"{mm(a.genislik)} × 2000", 0 if kapi_alici else 1, "Sayım", "Motor planı" + ("; alıcıya ait" if kapi_alici else ""))
    kapilar = Counter((a.genislik, a.mentese) for a in acl if a.tur == "ic_kapi")
    for (gen, ment), n in sorted(kapilar.items()):
        olcu = "82 × 196" if abs(gen - 82) < 0.1 else f"{gen:g} × 196"
        ad = "80'lik kanat" if abs(gen - 82) < 0.1 else f"{gen:g} cm boşluk"
        ekle("1003", f"Amerikan kapı ({ad}) ({'SAĞ' if ment == 'sag' else 'SOL'})", olcu, n, "Sayım", "Motor planı; menteşe D-13 (PK-01 dersi 10)")
    if pencere_alici:
        ekle("1003", "Pencere grubu", "—", 0, "İş Emri", "alıcıya ait (PK-01 dersi 1)")
    else:
        for olcu, n in sorted(Counter(a.olcu for a in acl if a.tur == "pencere").items()):
            en, boy = G.PENCERE_OLCULERI[olcu]
            ekle("1003", "PVC vasistas" if olcu == "60x40" else "PVC pencere", f"{en}/{boy}", n, "Sayım", "Motor planı")

    # ── 1004 Tavan ──────────────────────────────────────────────────────────
    lev = _kural(k, "levha_m2", "alcipan")
    toplam = TAVAN(bina_m2 / lev)
    yesil = TAVAN(sum(x.alan_m2 for x in m["acik"]) / lev) if m["acik"] else 0
    ekle("1004", "(Asma / ters) tavan beyaz alçıpan", "1200 × 2500", toplam - yesil, "Liste kuralı", f"brüt {bina_m2:.2f} m² ÷ 3 = {toplam}, yeşil düşülür",
         "P6001 kuralı; PK-01'de 17 ↔ 8 (soru 1)", aday=TAVAN(tavan_kuru * 1.05 / 3 + 2), aday_notu=f"şablon: kuru tavan {tavan_kuru:.2f} m² × 1,05 ÷ 3 + 2")
    ekle("1004", "(Asma / ters) tavan yeşil alçıpan", "1200 × 2500", yesil, "Kural", "veranda tavanı ÷ 3 (Lokman 7 Ekim)", "soru 5",
         aday=TAVAN(tavan_islak * 1.05 / 3 + 1) if tavan_islak else 0, aday_notu=f"şablon: ıslak hacim {tavan_islak:.2f} m² × 1,05 ÷ 3 + 1")
    if m["acik"]:
        ver = sum(x.alan_m2 for x in m["acik"])
        ekle("1004", "Veranda tavan Boardex", "8 × 1200 × 2400", 0, "Kural (PK-01)", "PK-01'de 0", aday=TAVAN(ver * 1.08 / 2.88), aday_notu="şablon: veranda × 1,08 ÷ 2,88")
    tav_h = TAVAN(tavan_net / (ASMA_OMEGA_ARALIK_M * TAVAN_H_ARALIK_M) + 5)
    ekle("1004", "Tavan H'ı L 1185 (asma dizme tavan)", "adet", tav_h, "Şablon formülü",
         f"net tavan {tavan_net:.2f} m² ÷ (1,255 × 0,625) + 5 (H omegalara dik, 62,5'te bir)", "PK-01'de 66 (formül 65)")
    ekle("1004", "PVC omega kapak L 3750 (asma dizme tavan)", "adet", TAVAN(L_hat / 3.65 + 3), "Şablon formülü",
         f"oda içi omega hatları {L_hat:.2f} m (duvar üstleri hariç) ÷ 3,65 + 3", "PK-01'de 10 (formül 10,03)")
    ekle("1004", "PVC plastik betopan haşı (asma dizme tavan)", "adet", 5, "Kural (PK-01)", "standart 3–5; PK-01'de 5")
    ekle("1004", "Çatı izolasyonu 100 mm (9,6 m²/paket)", "paket", TAVAN(bina_m2 / _kural(k, "silte_adet_m2")), "Liste kuralı", f"brüt {bina_m2:.2f} ÷ 9,6",
         "PK-01'de 7 ↔ 4 (soru 1)", aday=TAVAN((m["W"] / 100 + 0.6) * (m["D"] / 100 + 0.6) / 9.6), aday_notu="şablon: 30 cm paylı taban ÷ 9,6")

    # ── 1005 Makas ──────────────────────────────────────────────────────────
    kosu = bina_boyu - 2 * m["t_dis"]
    n_makas = TAVAN(kosu / G.MOD - 1e-6) + 1
    ekle("1005", "Makas (baş)", f"açıklık {mm(aciklik)}", 2, "Kural", "iki kalkan duvarının üstünde", "", pafta=("makas_bas",))
    ekle("1005", "Makas (orta)", f"açıklık {mm(aciklik)}", n_makas - 2, "Kural (P1)",
         f"saçak duvarının pano koşusu {mm(kosu)} ÷ 1255 yukarı + 1 = {n_makas}, − 2 baş", "PK-01 9, PK-02 paftası 7", pafta=("makas_orta",))
    sira = TAVAN((egik - 0.20) / _kural(k, "asik", "aralik_m") - 1e-6) + 1
    asik_boy = 2 * sira * mahya_boy
    ekle("1005", "Aşık", "L 4200", TAVAN(asik_boy * (1 + _kural(k, "asik", "zayiat")) / _kural(k, "parca_boyu_m", "asik")), "Kural (P2)",
         f"yüz başına ⌈({egik:.3f} − 0,20) ÷ 0,60⌉ + 1 = {sira} sıra × 2 yüz × {mahya_boy:.2f} m = {asik_boy:.1f} m × 1,05 ÷ 4,2",
         "PK-01'de 36 (soru 1)", pafta=("asik",), aday=TAVAN(asik_boy / 4.1 + 5), aday_notu="şablon: aşık boyları ÷ 4,1 + 5")

    # ── 1006 Çatı ───────────────────────────────────────────────────────────
    kap = oz.get("çatı kaplaması", "")
    sandvic = "sandvi" in kap
    kap_m = _kural(k, "sandvic_panel_kapatma_m" if sandvic else "tek_kat_panel_kapatma_m")
    L_pan = int(math.ceil(egik * 10 - 1e-9) * 100)
    ekle("1006", "Sandviç panel (100 cm kapatır)" if sandvic else "Tek kat çatı paneli", f"L {L_pan}", TAVAN(2 * mahya_boy / kap_m), "Kural (P3)",
         f"iki yüz {2 * mahya_boy:.2f} m ÷ {kap_m:g}; boy eğik {egik:.3f} m 100 mm'ye yukarı", "PK-01 22 / 3500 tuttu", pafta=("sandvic_panel",))
    pm, bm = _kural(k, "parca_boyu_m", "mahya"), _kural(k, "bindirme_m", "mahya")
    mahya = TAVAN(mahya_boy / (pm - bm))
    ekle("1006", "Metal kiremit mahyası", "L 2800", mahya, "Kural", f"mahya {mahya_boy:.2f} ÷ 2,6", "PK-01'de tuttu")
    ekle("1006", "Sandviç panel kapaması", "L 2800", 0, "Kural (PK-01)", "PK-01'de 0", aday=TAVAN(2 * mahya_boy / 2.6), aday_notu="şablon kaba hesabı: saçak boyu ÷ 2,6")
    ekle("1006", "Mahya bandı", "rulo 10 m", TAVAN(mahya * 2.8 / 10), "Şablon formülü", f"mahya {mahya} × 2,8 ÷ 10", "PK-01'de tuttu (2)")

    # ── 1007 Elektrik (montaj paftasındaki elektrik planından; kurallar.json › elektrik) ──
    el = P.get("elektrik") or {}
    if el:
        def es(a):
            return (el.get(a) or {}).get("adet")
        isik = (es("tavan_armaturu") or 0) + (es("glop") or 0) + (es("dis_aplik") or 0)
        priz = (es("priz_tekli") or 0) + 2 * (es("priz_cift") or 0)
        anah = (es("anahtar_tekli") or 0) + 2 * (es("anahtar_cift") or 0)
        for kalem, adet, formul in (("Tijli duy", es("tavan_armaturu"), "tavan armatürü"), ("Yuvarlak glop", (es("glop") or 0) + (es("dis_aplik") or 0), "banyo glopu + dış aplikler"),
                                    ("Ampul", isik, "ışık noktaları"), ("Tekli anahtar (takım)", es("anahtar_tekli"), ""), ("Çiftli anahtar (takım)", es("anahtar_cift"), ""),
                                    ("Tekli priz (takım)", es("priz_tekli"), ""), ("Çiftli priz (takım)", es("priz_cift"), ""), ("Uydu prizi (takım)", es("uydu_prizi"), ""),
                                    ("Zil", es("zil"), ""), ("Sigorta kutusu (12'li)", es("sigorta_kutusu"), "")):
            ekle("1007", kalem, "adet", adet, "Sayım (pafta)", formul or "elektrik planından", "göz sayımı; kurallar.json › elektrik")
        ekle("1007", "NYM kablo 3 × 2,5", "metre", 130, "Kural (PK-01)", "PK-01'de 130", aday=1 * 20 + priz * 2, aday_notu="şablon: sigorta × en uzun (≈ 20 m) + priz × 2")
        ekle("1007", "NYM kablo 2 × 1,5", "metre", 100, "Kural (PK-01)", "PK-01'de 100", aday=1 * 20 + anah * 2, aday_notu="şablon: sigorta × en uzun (≈ 20 m) + anahtar × 2")
        ekle("1007", "Uydu kablo", "metre", 25 * (es("uydu_prizi") or 0), "Şablon formülü", "uydu prizi × 25 m")
        ekle("1007", "Besleme kablosu", "metre", 5, "Şablon formülü", "kat × 5 m")
        ekle("1007", "Besleme kablo borusu", "metre", 5, "Şablon formülü", "kat × 5 m")
        ekle("1007", "İzole bant", "adet", TAVAN(bina_m2 * 6 / 100), "Şablon formülü", "m² × 6 ÷ 100")
        ekle("1007", "Kaçak akım rölesi (ikili)", "adet", 1, "Şablon formülü", "tek kat 1 ikili", "PK-01'de 2 (\"bozuk gelmiş\")")
    else:
        ekle("1007", "Elektrik grubu", "—", None, "Kural yok", "elektrik planı yok", "kurallar.json › elektrik")

    # ── 1008 Vida (PK-01 dersi 9) ───────────────────────────────────────────
    n_sandvic = TAVAN(2 * mahya_boy / kap_m)
    ekle("1008", "16 mm betopan ve kapı kolu vidası (3,9 × 32)", "adet", 250, "Kural (PK-01)", "PK-01'de 250")
    ekle("1008", "Trapez vida 5,5 × 110 (sandviç panel)", "adet", int(math.ceil(L_pan / 200 * n_sandvic / 100 - 1e-9) * 100), "Şablon formülü",
         f"panel boyu {L_pan} ÷ 200 × {n_sandvic} panel, 100'e yukarı", "PK-01'de 385 → 400 tuttu")
    ekle("1008", "8'lik trapez uç", "adet", TAVAN(bina_m2 / 15), "Şablon formülü", "m² ÷ 15", "PK-01'de tuttu")
    ekle("1008", "PH2 uç", "adet", TAVAN(bina_m2 / 15), "Şablon formülü", "m² ÷ 15", "PK-01'de tuttu")
    ekle("1008", "İnox taş", "adet", TAVAN(bina_m2 / 10), "Şablon formülü", "m² ÷ 10", "PK-01'de tuttu")
    ekle("1008", "Alçıpan vidası", "adet", 0, "Kural (PK-01)", "PK-01'de 0", aday=toplam * 40, aday_notu="şablon: alçıpan × 40")
    ekle("1008", "RYSB pul başlı vida", "adet", 0, "Kural (PK-01)", "PK-01'de 0", aday=TAVAN(bina_m2 * 7.5), aday_notu="şablon: m² × 7,5")

    # ── 1009 Depo ───────────────────────────────────────────────────────────
    ekle("1009", "Acil müdahale kapağı", "adet", 0 if any("acil" in x for x in alici) else 1, "Şablon formülü", "sabit 1" + (" (alıcıya ait)" if any("acil" in x for x in alici) else ""))
    ekle("1009", "Şase pul", "adet", dubelli, "Şablon formülü", f"dübelli H adedi kadar (dış H {ec[('dis', 'pano_eki')]} + dış 3'lü H {ec[('dis', 'uclu')]})", "PK-01'de 24 tuttu")
    ekle("1009", "Çelik dübel", "adet", 0, "Kural (PK-01)", "PK-01'de 0", aday=dubelli, aday_notu="şablon: dübelli H adedi kadar")

    # ── 1010 Sıhhi tesisat ──────────────────────────────────────────────────
    tes_alici = any("tesisat" in x for x in alici)
    ekle("1010", "Sıhhi tesisat grubu", "—", 0 if tes_alici else None, "İş Emri" if tes_alici else "Kural yok", "alıcıya ait" if tes_alici else "—",
         "" if tes_alici else "İş Emri'nde alıcıya ait yazmıyor; şablon: su tesisatı WC × 6, vitrifiye 1, batarya 1")

    # ── 1011 Dere ───────────────────────────────────────────────────────────
    dere_hat = [mahya_boy, mahya_boy]
    pd_, bd = _kural(k, "parca_boyu_m", "dere"), _kural(k, "bindirme_m", "dere")
    dere = sum(TAVAN(x / (pd_ - bd)) for x in dere_hat)
    ekle("1011", "Metal dere", "L 4000", dere, "Kural", f"iki saçak kenarı {mahya_boy:.2f} m ÷ 3,8, ayrı ayrı yukarı", "PK-01'de tuttu",
         aday=TAVAN(sum(dere_hat) / 3.8), aday_notu="şablon: toplam dere ÷ 3,8")
    ekle("1011", "Dere kelepçesi", "adet", dere * _kural(k, "dere_kelepcesi_dere_basina"), "Kural", "dere × 8", "PK-01'de tuttu")
    ins = _kural(k, "inis")
    inis = 2 * 2 * ins["kose_basina"] + sum(1 for x in dere_hat if x > ins["orta_inis_esigi_m"])
    ekle("1011", "Metal dere inişi aparatı", "adet", inis, "Kural (Lokman)", f"her dere hattının iki ucu + {ins['orta_inis_esigi_m']:g} m'yi geçen hattın ortası",
         "kurallar.json › inis", pafta=("inis",))
    ekle("1011", "70 mm PVC dere iniş borusu", "L 2500", inis, "Kural (PK-01)", "iniş başına bir L 2500 (PK-01 dersi 7)")
    ekle("1011", "70 mm PVC dere iniş borusu", "L 500", inis, "Kural (PK-01)", "iniş başına bir L 500 (PK-01 dersi 7)")
    ib = _kural(k, "inis_basina")
    for kalem, anahtar in (("Açık dirsek", "acik_dirsek"), ("Kapalı dirsek", "kapali_dirsek"), ("PVC iniş kelepçesi", "inis_kelepcesi")):
        ekle("1011", kalem, "adet", inis * ib[anahtar], "Kural", f"iniş × {ib[anahtar]}", "PK-01'de tuttu")
    ekle("1011", "Dere kapağı", "adet", 4, "Kural (PK-01)", "beşikte 4 (PK-01 dersi 7)")

    # ── 1012 Boya ───────────────────────────────────────────────────────────
    boya_alici = any("boya" in x for x in alici) or ("alıcı" in oz.get("dış cephe boya", "") and "alıcı" in oz.get("iç cephe boya", ""))
    if boya_alici:
        ekle("1012", "Boya grubu ve mastik", "—", 0, "İş Emri", "alıcıya ait")
    else:
        n_pen = sum(a.tur == "pencere" for a in acl)
        ekle("1012", "Boya grubu (17,5 kg kova)", "kova", TAVAN(bina_m2 * 2 / 100), "Şablon formülü", "m² × 2 ÷ 100", f"özellik: {oz.get('dış cephe boya', '...')}")
        ekle("1012", "Silikonize mastik", "adet", n_pen + TAVAN(bina_m2 * 2 / 3), "Şablon formülü", "mantolama yok: pencere + m² × 2/3")
    ekle("1012", "Dayson (çatı renginde)", "adet", int(math.floor(bina_m2 * 0.03 + 1e-9)), "Şablon formülü", "beşikte m² × 0,03, aşağı", "PK-01'de 1,8 → 1")
    ekle("1012", "Poliüretan köpük", "adet", 0, "Kural (PK-01)", "PK-01'de 0", aday=2, aday_notu="şablon: standart 2")

    say = {"pano_dis": sum(len(d.panolar) for d in m["dis"]), "pano_ic": sum(len(d.panolar) for d in m["ic"]), "brut_m2": bina_m2,
           "dis_olcu_cm": [round(m["W"], 2), round(m["D"], 2)], "egimli_boy_m": round(egik, 3), "mahya_boyu_m": round(mahya_boy, 3),
           "cati_m2": round(2 * egik * mahya_boy, 2), "tavan_net_m2": round(tavan_net, 2), "makas": n_makas, "asik_sira_yuz": sira,
           "asma_tavan_hat_m": round(L_hat, 2), "ic_duvar_m": round(L_duvar, 2)}
    return {"is_emri_no": ie.get("is_emri_no"), "kod": ie.get("yapi", {}).get("referans_model"), "uretici_surum": SURUM,
            "uretildi": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "kural_seti": k.get("surum") or k.get("sema"), "girdi_ozeti": say,
            "satirlar": satirlar,
            "ozet": {"satir": len(satirlar), "adetli": sum(s["adet"] is not None for s in satirlar), "kural_yok": sum(s["dayanak"] == "Kural yok" for s in satirlar),
                     "pafta_katmanli": sum(s["pafta"] is not None for s in satirlar), "aday_li": sum(s["aday"] is not None for s in satirlar)}}


def xlsx(L: dict, yol: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Liste"
    ws.append([f"{L['kod']} · kendi yükleme listemiz (kör test; gerçek liste açılmadan) · {L['is_emri_no']} · üretici {L['uretici_surum']} · {L['uretildi']}"])
    ws.append(["Grup", "Kalem", "Ölçü", "Adet", "Birim", "Dayanak", "Formül", "Kaynak / not", "Pafta", "Pafta notu", "Aday", "Aday notu"])
    for c_ in ws[2]:
        c_.font = Font(bold=True, color="FFFFFF"); c_.fill = PatternFill("solid", fgColor="2F3B4C")
    renk = {"Kural yok": "F2F2F2", "Liste kuralı": "FFF2CC", "Kural (uydurma)": "FCE4D6", "Şablon formülü": "E2EFDA", "Kural (PK-01)": "DDEBF7"}
    for s in L["satirlar"]:
        ws.append([f"{s['grup']} {s['grup_adi']}", s["kalem"], s["olcu"], s["adet"], s["birim"], s["dayanak"], s["formul"], s["kaynak"], s["pafta"],
                   s["pafta_notu"], s["aday"], s["aday_notu"]])
        if s["dayanak"] in renk:
            for c_ in ws[ws.max_row]:
                c_.fill = PatternFill("solid", fgColor=renk[s["dayanak"]])
    for i, w in enumerate([16, 46, 22, 7, 7, 16, 60, 50, 8, 50, 14, 50], 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=3):
        for c_ in row:
            c_.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "C3"
    wb.save(yol)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", type=Path); ap.add_argument("cikti", type=Path); ap.add_argument("--pafta", type=Path, default=None)
    a = ap.parse_args()
    ie = json.loads(a.is_emri.read_text(encoding="utf-8"))
    k = json.loads((KOK / "kurallar" / "liste" / "kurallar.json").read_text(encoding="utf-8"))
    pafta = json.loads(a.pafta.read_text(encoding="utf-8")) if a.pafta else None
    L = liste(ie, k, pafta)
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = (L["kod"] or "PK").replace("-", "")
    (a.cikti / f"{kod}_liste.json").write_text(json.dumps(L, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    xlsx(L, a.cikti / f"{kod}_liste.xlsx")
    print(json.dumps(L["ozet"], ensure_ascii=False), "→", a.cikti / f"{kod}_liste.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
