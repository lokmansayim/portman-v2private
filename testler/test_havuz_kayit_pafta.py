"""D-87 › Ek (15 Kasım 2026): 71 m² 2+1 (PA-26, PA-35) ve 45 m² 1+1 (PA-27) kayıtları paftadaki gibi. LLM'siz, Postgres'siz.

Lokman, 15 Kasım 2026 UTC: 08:53:28 (71 m², sağ dış duvar) ve 08:53:55 (45 m², salonun ön dış duvarı) notları; 09:42:35 kartı "Evet,
paftadaki gibi". Kayıtlar aynı numarayla yenilenir (D-103 › Açık kalan). Motor'un kodu değişmez: `dis_pano_dayanagi` ve
`karkasli_panolar` (D-46) İş Emri'ne yazılır. 71 m²'de yalnız sağ dış duvar değişir; iç bölmelere dokunulmaz (okuma, D-87 › Ek).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin.katalog import SABLON_DIR, havuz_kayitlari  # noqa: E402
from motor import geometry as G, prefabrik_liste as PL  # noqa: E402

D87 = (KOK / "KARARLAR" / "D-87.md").read_text(encoding="utf-8")
D103 = (KOK / "KARARLAR" / "D-103.md").read_text(encoding="utf-8")
SOZ_71 = ("bu doğru neden çektirme U'sunun koyulacağı ölçü net değil o yüzden panoyu bölmüş ama şunu söylemeliyim mühendis burada da iç "
          "bölmelerde hata yapmış istersen 71 m² de son güncellemeyi yap depoya al ve bırak çünkü bu projede hata çok fazla")
SOZ_45 = "71 m² deki durumun aynısı yeri net değil"
KART = ("09:42:35", "Evet, paftadaki gibi")
KART_SORU = "71 m2 ve 45 m2 kayıtları paftadaki gibi düzeltilsin mi?"
KART_METNI = ("71 m2'nin iki kaydı ve 45 m2 paftadaki pano bölünüşüne döner, birleşimde 3'lü H; kayıtlar aynı numarayla "
              "yenilenir.")
# 71 m²'nin iki kaydı: kaynak, karar, sağ dış duvarın ekseni (Motor çerçevesi), arka dış duvarın ekseni, pano, dış ölçü
EVLER_71 = {
    "PA26": ("testler/havuz/is_emirleri/AP08.json", "D-87", 780.0, 895.0, 57, (785.0, 900.0)),
    "PA35": ("testler/havuz/is_emirleri/PA26_UCLU_H.json", "D-92", 768.0, 883.5, 48, (773.0, 888.5)),
}
DAYANAK_71 = {"y": 215.25, "aralik_cm": [5, 256], "cephe": "sag"}                       # arka-sol çerçevesi (y arka dış yüzden)
KARKASLI_71 = {"yon": "y", "aralik_cm": [67.75, 215.25], "aciklik_ortasi_cm": [138.4]}  # eksen evden eve
DAYANAK_45 = {"x": 318.75, "aralik_cm": [295, 381.5], "cephe": "on"}
AP07, AP07_PAFTA = "testler/havuz/is_emirleri/AP07.json", "testler/havuz/is_emirleri/AP07_PAFTA.json"
# yükleme listesi farkı (grup, kalem, ölçü, önce, sonra); D-87 › Ek
LISTE = {
    "PA26": {
        ("1001", "100'lük yapıştırma dolu pano", "100 × 1250 × 2500", 16, 15),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 405 × 2500", 2, 3),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 625 × 2500", 9, 10),
        ("1001", "Karkaslı kaplama duvar panosu", "100 × 1475 × 2500", None, 1),
        ("1001", "Karkaslı özel pencere panosu (100/120)", "100 × 1250 × 2500", 1, None),
        ("1002", "3'lü H 100 × 100 × 100 (dış duvar T'si)", "L 2500", 3, 4),
        ("1002", "Çektirme U'su 100 (iç duvar)", "100 × 2440", 3, 2),      # D-105 madde 2 (BK-38; Lokman kartı 15 Kasım 09:14:41 "Evet, 1 adet 100'lük"): köşe direkli 100'lük dış köşede 1 çektirme U'su (iki hâlde de); fark aynı, 1 az
        ("1009", "Çelik dübel", "adet", 26, 27),
    },
    "PA35": {
        ("1001", "100'lük yapıştırma dolu pano", "100 × 1250 × 2500", 25, 24),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 405 × 2500", 1, 2),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 625 × 2500", 3, 4),
        ("1001", "Karkaslı kaplama duvar panosu", "100 × 1475 × 2500", None, 1),
        ("1001", "Karkaslı özel pencere panosu (100/120)", "100 × 1250 × 2500", 1, None),
        ("1002", "3'lü H 100 × 100 × 100 (dış duvar T'si)", "L 2500", 4, 5),
        ("1002", "Çektirme U'su 100 (iç duvar)", "100 × 2440", 2, 1),
        ("1009", "Çelik dübel", "adet", 22, 23),
    },
}
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}


def _ie(yol) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _sablon(kod: str) -> dict:
    return json.loads((SABLON_DIR / KAYIT[kod]["sablon"]).read_text(encoding="utf-8"))


def _once_71(ie: dict) -> dict:
    """Kartın önceki hâli: sağ dış duvarın dayanağı ve karkaslı pano yok."""
    ie = copy.deepcopy(ie)
    dz = ie["yapi"]["dizilim"]
    assert dz["dis_pano_dayanagi"][-1] == DAYANAK_71
    dz["dis_pano_dayanagi"] = dz["dis_pano_dayanagi"][:-1]
    dz.pop("karkasli_panolar")
    return ie


def _an(q) -> tuple:
    """Pano kimliği: duvar, yer, karkas ve açıklık (tür, ölçü, kayma). Öteki panolarda bunların hiçbiri değişmez."""
    ac = q.acilim
    acilim = None if ac is None else (ac.tur, ac.olcu, round(ac.kayma or 0, 3))
    return (q.duvar.id, round(q.a0, 3), round(q.a1, 3), bool(q.karkasli), acilim)


def _satirlar(ie: dict) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        L = PL.liste(PL.model_motor(copy.deepcopy(ie)))
    return {(r["grup"], r["kalem"], r["olcu"]): r["adet"] for r in L["satirlar"]}


@pytest.mark.parametrize("kod", sorted(EVLER_71))
def test_71m2_kaynak(kod):
    """Kaynakta sağ dış duvarın dayanağı ve karkaslı pano; talep metni sözü ve kartı, son varsayım satırı kartı yazar."""
    kaynak, _, eksen, _, _, _ = EVLER_71[kod]
    ie = _ie(kaynak)
    dz = ie["yapi"]["dizilim"]
    assert dz["dis_pano_dayanagi"][-1] == DAYANAK_71
    assert dz["karkasli_panolar"] == [{**KARKASLI_71, "eksen_cm": eksen}]
    assert f"08:53:28 UTC sözü \"{SOZ_71}\"" in ie["talep"]["metin"] and f'{KART[0]} "{KART[1]}"' in ie["talep"]["metin"]
    assert f"kart {KART[0]} '{KART[1]}'" in ie["varsayimlar"][-1] and "147,5 karkaslı pano" in ie["varsayimlar"][-1]


@pytest.mark.parametrize("kod", sorted(EVLER_71))
def test_71m2_sag_dis_duvar(kod):
    """Yalnız sağ dış duvarın mutfak bölümü değişir: iki 125,5 → 40,75 + 147,5 karkaslı (100/120 pencere) + 62,75. Pencerenin ortası arka
    köşeden 62,75 → 133,4 cm. Öteki panolar (iç bölmeler dahil) aynı; dış ölçü aynı, bir pano fazla."""
    _, _, eksen, arka, pano, dis = EVLER_71[kod]
    sab = _sablon(kod)
    p0, p1 = G.kur(_once_71(sab)), G.kur(copy.deepcopy(sab))
    assert (p0.W, p0.H) == (p1.W, p1.H) == dis and (len(p0.panolar), len(p1.panolar)) == (pano - 1, pano)
    k0, k1 = {_an(q): q for q in p0.panolar}, {_an(q): q for q in p1.panolar}
    eski, yeni = [k0[k] for k in k0 if k not in k1], [k1[k] for k in k1 if k not in k0]
    assert {(q.duvar.yon, q.duvar.tur, q.duvar.c) for q in eski + yeni} == {("y", "dis", eksen)}
    assert [round(q.boy, 2) for q in sorted(eski, key=lambda q: q.a0)] == [125.5, 125.5]
    assert [(round(q.boy, 2), q.karkasli) for q in sorted(yeni, key=lambda q: q.a0)] == [(40.75, False), (147.5, True), (62.75, False)]

    def pencere(plan):
        q = next(q for q in plan.panolar if q.duvar.c == eksen and q.duvar.tur == "dis" and q.acilim is not None
                 and q.acilim.olcu == "100x120")
        return round(arka - ((q.a0 + q.a1) / 2 + (q.acilim.kayma or 0)), 2), q.karkasli
    assert (pencere(p0), pencere(p1)) == ((62.75, False), (133.4, True))


@pytest.mark.parametrize("kod", sorted(EVLER_71))
def test_71m2_liste_farki(kod):
    """Liste farkı karar dosyasındaki gibi: T pano ekinde 3'lü H (çektirme U'su bir az), karkaslı pencere panosu 1475'lik karkaslı pano."""
    sab = _sablon(kod)
    a, b = _satirlar(_once_71(sab)), _satirlar(sab)
    assert {(*k, a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)} == LISTE[kod]


def test_45m2_kaynak_yeni_dosya():
    """45 m²'nin kaynağı yeni dosya: AP07.json'un kopyası, fark yalnız salonun ön dış duvarının dayanağı, talep metninin sonu ve bir
    varsayım satırı. AP07.json aynen kalır (PA-28 ve PA-29 ondan türer)."""
    eski, ie = _ie(AP07), _ie(AP07_PAFTA)
    assert ie["yapi"]["dizilim"]["dis_pano_dayanagi"][-1] == DAYANAK_45
    assert ie["talep"]["metin"].startswith(eski["talep"]["metin"]) and f'08:53:55 UTC sözü "{SOZ_45}"' in ie["talep"]["metin"]
    assert f'{KART[0]} "{KART[1]}"' in ie["talep"]["metin"]
    assert ie["varsayimlar"][:-1] == eski["varsayimlar"] and f"kart {KART[0]} '{KART[1]}'" in ie["varsayimlar"][-1]
    ie["yapi"]["dizilim"]["dis_pano_dayanagi"].pop()
    for d in (ie, eski):
        d["talep"].pop("metin")
        d["varsayimlar"] = d["varsayimlar"][:len(eski["varsayimlar"])]
    assert ie == eski
    for kod in ("PA28", "PA29"):
        assert KAYIT[kod]["kaynak"]["kart_kiyasi"]["kaynak_is_emri"] == AP07


def test_45m2_salonun_on_dis_duvari():
    """Yalnız salonun ön dış duvarı değişir: 86,5 cm'lik pano → köşeden 23,75 + 62,75. Öteki duvarlar (yan dış duvar ve yatak odası–salon
    duvarı dahil; karta girmedi) aynı. Liste iki cumbayı BK-45'ten beri sayar: cumbada 3, sundurmada 2 makas (paftadaki gibi)."""
    p0, p1 = G.kur(_ie(AP07)), G.kur(copy.deepcopy(_sablon("PA27")))
    assert (p0.W, p0.H) == (p1.W, p1.H) and (len(p0.panolar), len(p1.panolar)) == (36, 37)
    k0, k1 = {_an(q): q for q in p0.panolar}, {_an(q): q for q in p1.panolar}
    ozet = lambda qs: sorted((q.duvar.yon, q.duvar.tur, q.duvar.c, round(q.a0, 2), round(q.boy, 2)) for q in qs)  # noqa: E731
    assert ozet(q for k, q in k0.items() if k not in k1) == [("x", "dis", 155.0, 295.0, 86.5)]
    assert ozet(q for k, q in k1.items() if k not in k0) == [("x", "dis", 155.0, 295.0, 23.75), ("x", "dis", 155.0, 318.75, 62.75)]
    satir = _satirlar(_sablon("PA27"))
    assert satir[("1005", "Yavru makas · cumba", "L 3600")] == 3
    assert satir[("1005", "Yavru makas · sundurma çatısı", "L 1955")] == 2


def test_45m2_standart_halleri_bu_durumda_degil():
    """Okuma (D-87 › Ek): PA-28'de salonun ön dış duvarı T'nin yerinden başlar; PA-29'da T ilk 125,5'lik panonun tam ortasındadır
    (Lokman 08:51:58, 140 m²: tam panonun ortasına çektirme U'su). İkisinin kaydı değişmez."""
    def duvar(kod):
        p = G.kur(copy.deepcopy(_sablon(kod)))
        t = next(d.c for d in p.duvarlar if d.yon == "y" and d.tur != "dis" and abs(d.c - 318.75) < 1e-6)
        w = next(d for d in p.duvarlar if d.yon == "x" and d.tur == "dis" and d.a0 <= t <= d.a1 and d.c < p.H / 2)
        return t, w.a0, [(round(q.a0, 2), round(q.boy, 2)) for q in sorted((q for q in p.panolar if q.duvar is w), key=lambda q: q.a0)][0]
    assert duvar("PA28") == (318.75, 318.75, (318.75, 251.0))
    assert duvar("PA29") == (318.75, 256.0, (256.0, 125.5)) and 256.0 + 125.5 / 2 == 318.75
    d87 = " ".join(D87.split())
    assert "PA-28'de 23,75 cm'lik parça silinmiş" in d87 and "PA-29'da T, duvarın ilk 125,5'lik panosunun tam ortasındadır" in d87


@pytest.mark.parametrize("kod,proje,kaynak,karar,pano", [
    ("PA26", "AP-08", "testler/havuz/is_emirleri/AP08.json", "D-87", 57),
    ("PA35", "AP-08", "testler/havuz/is_emirleri/PA26_UCLU_H.json", "D-92", 48),
    ("PA27", "AP-07", AP07_PAFTA, "D-87", 37),
])
def test_kayit_ve_karar(kod, proje, kaynak, karar, pano):
    """Kayıt aynı numarayla, kaynağı ve kararıyla; kayıt metni D-87 › Ek'i anar; karar dosyası sözleri, kartı ve evi yazar."""
    a = KAYIT[kod]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"], a["kaynak"]["kart_kiyasi"]["kart"]) == (kaynak, karar, proje)
    assert a["kaynak"]["kart_kiyasi"]["sonuc"] == "geçti" and a["ozet"]["pano"] == pano
    assert "D-87 › Ek" in a["kaynak"]["metin"] and KART[0] in a["kaynak"]["metin"]
    if kod != "PA35":                                                                  # PA-35'i silme hâli kipi denetler
        assert HH.denetle(_sablon(kod), HH.kartlar()[proje])[0] == []
    assert f"| {kod[:2]}-{kod[2:]} | {proje} | `{kaynak}` |" in D87 and f'| {KART[0]} "{KART[1]}" |' in D87
    d87 = " ".join(D87.split())                                                      # satır kırılımı sözü bölmesin
    assert f'"{SOZ_71}"' in d87 and f'"{SOZ_45}"' in d87 and f'{KART[0]}, Lokman kartta seçti: **"{KART[1]}"**' in d87
    assert KART_SORU in d87 and KART_METNI in d87 and KART_SORU in D103 and KART_METNI in D103
