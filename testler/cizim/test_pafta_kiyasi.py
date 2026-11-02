"""İE-17 · Paftaya uygunluk: açılan evlerin (PR-1 üç, PR-2 dört) Motor planı, montaj paftasından ölçülen değerlerle (`pafta_olcu.json`).

Bu bir Motor kilidi değil, pafta sayılarıdır (test politikası; İE-11'deki PK-01 testleri gibi): paftanın vektör çiziminden okunan duvar
parçaları, pencere ve kapı boşlukları, köşe parçaları (ad ve antet okunmadı). Pafta kendi ölçeğiyle çizilmiş (dış kutusu 762 × 917 gibi,
binde 1–2 fark); değerler paftanın dış kutusundan Motor'un dış ölçüsüne ölçeklenir. Kalan farklar tek tek aşağıda (`BILINEN_*`), gerekçesi
İş Emri'nin `varsayimlar`ında ve İE-17 › Kanıt'ta; yeni bir fark çıkarsa da biri kapanırsa da test düşer.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
PAFTA = json.loads((KOK / "testler" / "cizim" / "pafta_olcu.json").read_text(encoding="utf-8"))
EV = ("AP01", "AP13", "AP16", "AP15", "AP09", "AP03", "AP22")
DERZ_PAYI = 2.0          # cm: paftanın okunuşu ve ölçeği (eşdeğer derz)

# Paftada olup Motor'un çizmediği duvar parçaları: (yön, eksen)
BILINEN_FAZLA_DUVAR = {"AP01": {("x", 476.5), ("y", 176.3)}}          # genel banyodaki tesisat kutusu
# Ek farkları: (yön, eksen) → (yalnız Motor'da, yalnız paftada; cm)
BILINEN_DERZ = {
    "AP01": {
        ("x", 299.75): ([1009.0], [946.2, 1071.8]),   # veranda duvarı: paftada mutfak duvarının T'sinden tam pano, Motor'da tam aksta
        ("x", 613.5): ([1009.0], [1071.8]),           # koridor duvarı: aynı
        ("x", 739.0): ([883.5, 1009.0], [946.2]),     # banyoların önü: paftada iki banyonun arasındaki T'de ek
        ("y", 318.75): ([488.0], [485.0]),            # genel banyo kapılı panosunun başı: paftada tam pano kavşağın yüzünden (2,5–3)
        ("y", 946.25): ([362.5, 488.0], [359.5, 485.0]),   # mutfak duvarı: aynı
    },
    "AP13": {
        ("y", 256.0): ([338.75], [341.9]),            # banyo–salon duvarı: paftada yarım pano bölmenin yüzünden (3)
    },
    "AP16": {
        ("x", 218.25): ([569.75, 695.25], []),        # mutfağın veranda penceresi paftada 251'lik tek pencereli panoda (D-29: Motor'da iki yanı
                                                      # 62,75, ekler 1 cm kaydı; önceden 568,75 / 694,25)
    },
    # PR-2 (1 Kasım 2026)
    "AP15": {
        ("y", 381.5): ([], [348.53]),                 # salon–yatak odası 2 bölmesi: paftada 57,75 + 59,75 + 62,75, Motor'da 57,75 + 125,5
        ("y", 758.0): ([602.5, 728.0], []),           # yatak odası 2'nin sağ penceresi paftada 251'lik tek pencereli panoda (D-29: iki yanı 62,75)
    },
    "AP09": {
        ("x", 249.25): ([261.0], []),                 # veranda–salon duvarı paftada eksiz tek parça (150'lik sürgülü + kapı); Motor'da 251 + kapılı pano
        ("y", 5.0): ([437.5], []),                    # salonun sol penceresi (120/70) paftada 251'lik panoda, ortada değil; Motor'da iki tam pano
        ("y", 735.0): ([], [248.9]),                  # sağ duvar: paftada veranda hizasında iki yarım pano, Motor'da tam pano
    },
    "AP03": {
        ("y", 632.5): ([512.0], [516.97]),            # veranda–salon duvarı: dış kapılı pano paftada köşenin yüzünden 125,5, Motor'da aksından
                                                      # (duvar_ucu: 120,5 + 62,75; paftada 125,5 + 57,75)
    },
    "AP22": {},
}
# Köşe parçası farkları (Motor, pafta; yuvarlak cm): iç L köşelerde 1–5 cm; paftadaki tesisat kutusunun köşesi
BILINEN_KOSE = {
    "AP01": ([(628, 295, 632, 305)], [(173, 476, 179, 479), (627, 300, 637, 305)]),    # veranda iç köşesi: paftada parça 10 × 5 (Motor 5 × 10)
    "AP13": ([], []),
    "AP16": ([(253, 658, 259, 660), (378, 466, 384, 469)], [(256, 655, 259, 660), (382, 466, 385, 472)]),   # iki iç L köşe, 3 cm
    "AP15": ([(378, 414, 384, 417), (504, 348, 510, 352)], [(378, 411, 382, 417), (504, 349, 507, 354)]),   # iki iç L köşe, 3 cm
    "AP09": ([(384, 560, 390, 563), (386, 244, 392, 254)], [(381, 249, 392, 254), (384, 560, 392, 566)]),   # iç L köşe 3 cm; veranda iç
                                                                                                          # köşesi: paftada 10 × 5
    "AP03": ([(758, 382, 763, 392)], [(753, 387, 763, 391)]),         # veranda arka köşesi: paftada parça 10 × 5 (Motor 5 × 10)
    "AP22": ([(378, 572, 384, 575)], [(379, 572, 382, 578)]),         # iç L köşe, 3 cm
}
# Paftadaki yerinden PAY'dan uzak açıklıklar: (tür, yön, Motor duvar ekseni) → [(Motor orta, pafta orta)]; cm. Motor pencereyi pano ortasına,
# kapıyı kapı kuralıyla koyar; paftada pano ortasında olmayanlar burada
BILINEN_ACIKLIK = {
    "AP09": {
        ("pencere", "x", 939.5): [(323.75, 319.97)],     # banyo 60/40: paftada pano ortasından 3,8
        ("pencere", "x", 249.25): [(135.5, 155.04)],     # 150/180 sürgülü: paftada eksiz duvarda, Motor'da 251'lik panonun ortasında (BK-13)
        ("pencere", "y", 5.0): [(500.25, 466.2)],        # 120/70 sürgülü: paftada 251'lik panoda ortadan 29 cm kaçık, Motor'da pano ortasında
        ("kapi", "y", 261.0): [(625.75, 632.3)],         # oda 1 kapısı: paftada pano ortasından 6,55 (PAY 6,5)
        ("kapi", "y", 386.5): [(625.75, 632.3)],         # oda 2 kapısı: aynı
    },
    "AP22": {
        ("pencere", "x", 830.75): [(569.75, 577.42)],    # banyo 50/50: paftada pano ortasından 7,7
    },
}
PAY = {"pencere": 3.0, "kapi": 6.5}   # paftadaki yerine en çok (cm); paftada kapı panonun ortasından ±6 (AP-01 yatak odası 3: 6,0)


def _plan(ad: str) -> G.Plan:
    return G.kur(copy.deepcopy(json.loads((EVLER / f"{ad}.json").read_text(encoding="utf-8"))))


def _olcekli(ad: str, plan: G.Plan) -> dict:
    """Paftanın değerleri Motor'un dış ölçüsüne ölçekli: x yönündeki uzunluklar W / kutu x, y yönündekiler H / kutu y."""
    p = PAFTA[ad]
    sx, sy = plan.W / p["kutu"][0], plan.H / p["kutu"][1]
    eksen = lambda yon, c: c * (sy if yon == "x" else sx)           # x boyunca uzanan duvarın ekseni y'dedir
    boy = lambda yon, a: a * (sx if yon == "x" else sy)
    return {
        "duvarlar": [(w["yon"], eksen(w["yon"], w["c"]), w["t"], [(boy(w["yon"], a), boy(w["yon"], b)) for a, b in w["parcalar"]])
                     for w in p["duvarlar"]],
        "acikliklar": [(tur, y, eksen(y, c), boy(y, m)) for tur, k in (("pencere", "pencereler"), ("kapi", "kapilar"))
                       for y, c, m, w in p[k]],
        "koseler": [(x0 * sx, y0 * sy, x1 * sx, y1 * sy) for x0, y0, x1, y1 in p["koseler"]],
    }


@pytest.fixture(scope="module", params=EV)
def ev(request):
    plan = _plan(request.param)
    return request.param, plan, _olcekli(request.param, plan)


def _esi(d: G.Duvar, pafta: dict) -> list:
    return [w for w in pafta["duvarlar"] if w[0] == d.yon and abs(w[2] - 2 * d.h) < 1 and abs(w[1] - d.c) <= 1.0
            and min(w[3][-1][1], d.p1) - max(w[3][0][0], d.p0) > 20]


def test_duvarlar_paftadaki_yerde(ev):
    # her Motor duvarının paftada aynı yönde, aynı kalınlıkta, ekseni en çok 1 cm ötede eşi var; paftanın her duvar parçası bir Motor
    # duvarının üstünde (bilinen fazlalar dışında)
    ad, plan, pafta = ev
    assert [d.id for d in plan.duvarlar if not _esi(d, pafta)] == [], ad
    fazla = set()
    for yon, c, t, parcalar in pafta["duvarlar"]:
        for a, b in parcalar:
            m = (a + b) / 2
            if not any(d.yon == yon and abs(d.c - c) <= 1.0 and d.p0 - 3 <= m <= d.p1 + 3 for d in plan.duvarlar):
                fazla.add((yon, round(c, 1)))
    assert fazla == BILINEN_FAZLA_DUVAR.get(ad, set()), ad


def test_derzler_paftayla(ev):
    # pano ekleri: duvarın kendi aralığında paftanın ekleriyle aynı (DERZ_PAYI); kalan farklar bilinen listede, tam olarak
    ad, plan, pafta = ev
    fark = {}
    for d in plan.duvarlar:
        w = min(_esi(d, pafta), key=lambda w: abs(w[1] - d.c))
        motor = [p.a1 for p in d.panolar[:-1]]
        pd = [b for a, b in w[3][:-1] if d.p0 + 2 < b < d.p1 - 2]
        ym = [x for x in motor if not any(abs(x - y) <= DERZ_PAYI for y in pd)]
        yp = [y for y in pd if not any(abs(x - y) <= DERZ_PAYI for x in motor)]
        if ym or yp:
            fark[(d.yon, round(d.c, 2))] = (ym, yp)
    beklenen = BILINEN_DERZ[ad]
    assert sorted(fark) == sorted(beklenen), (ad, fark)
    for k, (ym, yp) in fark.items():
        bm, bp = beklenen[k]
        assert ym == pytest.approx(bm) and yp == pytest.approx(bp, abs=0.6), (ad, k, ym, yp)


def test_acikliklar_paftadaki_yerde(ev):
    # her pencere ve kapı paftadaki eşinin yerinde (pencere en çok 3, kapı 6,5 cm; kalanlar bilinen listede, tam olarak); paftada eşsiz
    # açıklık yok
    ad, plan, pafta = ev
    kalan = list(pafta["acikliklar"])
    fark = {}
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if not a or a.tur == "gecis":
                continue
            tur = "pencere" if a.tur == "pencere" else "kapi"
            m = (p.a0 + p.a1) / 2 + a.kayma
            aday = [x for x in kalan if x[0] == tur and x[1] == d.yon and abs(x[2] - d.c) <= 6]
            assert aday, (ad, tur, d.id, m)
            x = min(aday, key=lambda x: abs(x[3] - m))
            if abs(x[3] - m) > PAY[tur]:
                fark.setdefault((tur, d.yon, round(d.c, 2)), []).append((round(m, 2), round(x[3], 2)))
            kalan.remove(x)
    assert kalan == [], ad
    beklenen = BILINEN_ACIKLIK.get(ad, {})
    assert sorted(fark) == sorted(beklenen), (ad, fark)
    for k, v in fark.items():
        assert len(v) == len(beklenen[k]), (ad, k, v)
        for (m, p), (bm, bp) in zip(sorted(v), sorted(beklenen[k])):
            assert m == pytest.approx(bm) and p == pytest.approx(bp, abs=0.6), (ad, k, v)


def test_koseler_paftayla(ev):
    # köşe parçaları paftadakiyle en çok 1,5 cm; iç L köşelerdeki küçük farklar bilinen listede
    ad, plan, pafta = ev
    motor = [tuple(k.rect) for k in plan.koseler]
    pk = list(pafta["koseler"])
    ym = []
    for r in motor:
        e = next((q for q in pk if all(abs(u - v) <= 1.5 for u, v in zip(r, q))), None)
        if e is None:
            ym.append(tuple(round(v) for v in r))
        else:
            pk.remove(e)
    assert (sorted(ym), sorted(tuple(round(v) for v in q) for q in pk)) == BILINEN_KOSE[ad], ad
