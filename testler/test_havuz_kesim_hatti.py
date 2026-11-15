"""BK-34 · Havuz hakeminin silme hâli kaleminde kesim hattı, üçlü H ve yeniden dizilen duvarda açıklık kayması: 71 m² 2+1'in üçlü H'lı hâli
(773 × 888,5 cm), yalnız Lokman'ın o evin kartı ve sözüyle. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC (proje sohbeti ve standart pano sohbeti, 71 m² 2+1'in eskizi üstüne):
- 20:46:54: "salon ön tarafta ki 120,5 panoyuda kendi ölçüsüne getirir misin birde başka bir düzeltilmesi gereken yer 120,5 aksındaki 115,5
  pano ana giriş kapısını dik kesen pano orada köşe direği olmayacak üçlü H olacak yanlış çizmiş mühendis yani 120,5 panoyu 125,5 yaparsan
  115,5 pano 120,5 olur ama oradaki köşe direğini alırsan 115,5 panoda 125,5 olur"
- kart 20:57:28 "Doğru, yanına eklensin": "Bugünkü 71 m2 kalır; 773 × 888,5 cm üçlü H'lı hâl (kapı panosu 120,5) Motor eklemesinden sonra
  ayrı ev olarak girer." (eskiz `05c_71m2_2+1_on_5_uclu_h_once_sonra.png`: sağ 12 cm içeri, ön 17 cm içeri (770 hattında), ön 5,5 cm dışarı).
CIO, 15 Kasım 2026 05:59: kesim hattı kalemi, kapsam büyüme kalemi gibi yalnız ev kartının sözüyle. Silme ve büyüme kalemleri (BK-31) aynen.
Girdi: `testler/motor/veri/D96_71m2_uclu_h.json` (D-96'nın hedef örneğinin girdisi; Motor'un planı eskizle birebir, BK-32).
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402

SOZ_71 = ("Lokman 14 Kasım 2026 20:46:54 UTC: \"salon ön tarafta ki 120,5 panoyuda kendi ölçüsüne getirir misin birde başka bir "
          "düzeltilmesi gereken yer 120,5 aksındaki 115,5 pano ana giriş kapısını dik kesen pano orada köşe direği olmayacak üçlü H olacak "
          "yanlış çizmiş mühendis yani 120,5 panoyu 125,5 yaparsan 115,5 pano 120,5 olur ama oradaki köşe direğini alırsan 115,5 panoda 125,5 "
          "olur\"; kart 20:57:28 \"Doğru, yanına eklensin\"")
KART_71 = ("Lokman, 14 Kasım 2026 20:57:28 UTC kartı \"Doğru, yanına eklensin\": \"Bugünkü 71 m2 kalır; 773 × 888,5 cm üçlü H'lı hâl (kapı "
           "panosu 120,5) Motor eklemesinden sonra ayrı ev olarak girer.\" (eskiz 05c: sağ 12 cm içeri, ön 17 cm içeri, ön 5,5 cm dışarı)")
UCLU_H = "testler/motor/veri/D96_71m2_uclu_h.json"
KAYNAK = "is_emri/adaylar/PA26.json"
KART = "AP-08"
KESIM = "on:17:770"
SOZLER = {"veranda_sozu": KART_71, "buyume_sozu": SOZ_71, "kesim_hatti": KESIM, "kesim_sozu": KART_71, "uclu_h_sozu": SOZ_71,
          "aciklik_sozu": KART_71}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _denetle(ie: dict | None = None, **degis) -> tuple[list[str], dict]:
    return HH.denetle_silme(ie or _ie(UCLU_H), HH.kartlar()[KART], _ie(KAYNAK), **{**SOZLER, **degis})


def test_71m2_uclu_h_gecer():
    """Eskizin hâli bütün sözlerle geçer: ön 17 cm 770 hattında kesilir (kapı duvarı 775 → 758), sağ 12 cm ve ön 5,5 cm dış yüzde; üçlü H
    kaynak evde 775'teki köşeye eşlenir; kesilen kısa parçalar 17 cm (iç duvar ve sağ dış duvar), veranda yan duvarı 120 → 125,5; yatak
    odasının verandaya bakan penceresi yeniden dizilen kapı duvarında 8,5 cm kayar (oda ortasında kalır)."""
    bulgular, o = _denetle()
    assert bulgular == []
    assert (o["kaynak_dis_olcu_cm"], o["dis_olcu_cm"]) == ([785.0, 900.0], [773.0, 888.5])
    assert (o["silinen_cm"], o["buyuyen_cm"]) == ([12.0, 17.0], [0.0, 5.5])
    assert o["kesim_hatti"] == {"yazi": KESIM, "eksen": "y", "hat_cm": 770.0, "cm": 17.0}
    assert o["uclu_h"] == [{"nokta_cm": [386.5, 758.0], "kaynakta_cm": [386.5, 775.0]}]
    assert {(p["duvar"], p["boy"]) for p in o["silinen"]} >= {("ic y 386.5", 17.0), ("dis y 780", 17.0), ("dis x 5", 12.0)}
    assert o["tamamlanan"] == [{"duvar": "dis y 386.5", "once": 120.0, "sonra": 125.5}]
    assert o["veranda_kisalan"] == ["VERANDA"]
    assert o["kayan_aciklik"] == [{"aciklik": "pencere 120x120", "duvar": "dis x 758", "once_cm": [583.25, 708.75],
                                   "sonra_cm": [574.75, 700.25]}]
    assert {d["duvar"]: d["sonra"] for d in o["yeniden_dizilen"]}["dis x 775"] == [120.5, 62.75, 125.5, 62.75]   # kapı panosu 120,5


@pytest.mark.parametrize("eksik,beklenen", [
    ("kesim_sozu", "--kesim-sozu"),
    ("uclu_h_sozu", "--uclu-h-sozu"),
    ("aciklik_sozu", "--aciklik-sozu"),
    ("veranda_sozu", "--veranda-sozu"),
    ("buyume_sozu", "--buyume-sozu"),
])
def test_her_degisiklik_yalniz_sozuyle(eksik, beklenen):
    """Her değişiklik kendi sözüyle: biri eksikse hâl kalır ve bulgu eksik seçeneği adıyla söyler."""
    bulgular, _ = _denetle(**{eksik: None})
    assert bulgular and any(beklenen in b for b in bulgular), bulgular


def test_kesimsiz_kalir():
    """Kesim hattı yazılmazsa içerideki kesim duvar kayması sayılır: kapı duvarı, iç duvarlar ve veranda yerinde değil (BK-31 kalemi aynen)."""
    bulgular, _ = _denetle(kesim_hatti=None, kesim_sozu=None)
    assert any(b.startswith("duvar: kaynak evin dis x 775") for b in bulgular)
    assert any(b.startswith("oda köşesi: VERANDA") for b in bulgular)


@pytest.mark.parametrize("yazi,beklenen", [
    ("on:12:770", "duvar: kaynak evin"),                  # parça eskizdeki kesimden farklı: duvarlar yerinde değil
    ("on:17:890", "iki dış duvarın arasında değil"),      # dış yüzde kesim silme kalemidir
    ("arka:17:300", "dizilim sonunda değil"),             # arka-sol başlangıçta arka cephe dizilimin başı
    ("sol:17:300", "dizilim sonunda değil"),
    ("on:31:770", "kısa parça kesilir"),
    ("on:17:390", "kesilen bantta"),                      # 373–390 bandında oturma odası ile salonun duvarı (381,5)
    ("on-17-770", "okunmadı"),
])
def test_yanlis_kesim_hatti(yazi, beklenen):
    bulgular, _ = _denetle(kesim_hatti=yazi)
    assert bulgular and any(beklenen in b for b in bulgular), (yazi, bulgular)


def test_yalniz_uclu_h_eklenir(monkeypatch):
    """Silinmiş hâlde yeni birleşim yalnız üçlü H olabilir; çektirme U'su gibi öteki birleşimler kaynak evle aynı kalır. Motor'un planı
    aynı kalsın diye kurulumda çektirme U'su süzülür; hakem İş Emri'ndeki yazıyı denetler."""
    from motor import geometry as G
    asil = G.kur

    def kur(ie, *a, **k):
        ie = json.loads(json.dumps(ie))
        if (ie.get("yapi") or {}).get("birlesimler"):
            ie["yapi"]["birlesimler"] = [x for x in ie["yapi"]["birlesimler"] if x.get("t") != "cektirme_u"]
        return asil(ie, *a, **k)
    monkeypatch.setattr(G, "kur", kur)
    ie = _ie(UCLU_H)
    ie["yapi"]["birlesimler"].append({"nokta_cm": [512.0, 444.25], "t": "cektirme_u"})
    bulgular, _ = _denetle(ie)
    assert bulgular and all("yalnız üçlü H eklenebilir" in b for b in bulgular), bulgular


def test_komut_satiri():
    """Hakemin komut satırı: bütün sözlerle GEÇTİ ve sözler satırda; kesim hattı sözsüz DUR; seçenekler yalnız silme hâliyle."""
    komut = [sys.executable, "araclar/havuz_hakemi.py", UCLU_H, "--kart", KART, "--silme-hali", KAYNAK]
    sozlu = komut + sum(([f"--{k.replace('_', '-')}", v] for k, v in SOZLER.items()), [])
    r = subprocess.run(sozlu, cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    son = r.stdout.strip().splitlines()[-1]
    assert son.startswith("GEÇTİ: silme hâli") and f"kesim hattı {KESIM}: {KART_71}" in son and "üçlü H [386.5, 758.0]" in son
    r = subprocess.run(komut + ["--kesim-hatti", KESIM], cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 2 and "--kesim-sozu" in r.stdout
    r = subprocess.run([sys.executable, "araclar/havuz_hakemi.py", UCLU_H, "--kart", KART, "--uclu-h-sozu", SOZ_71], cwd=KOK,
                       capture_output=True, text=True)
    assert r.returncode == 2 and "yalnız --silme-hali ile" in r.stdout


def test_aday_kaydi_ayni_secenekler():
    """Aday kaydı hakemle aynı seçenekleri alır (sözler kayda yazılır); kesim hattı sözsüz DUR, kayıt yazılmaz."""
    r = subprocess.run([sys.executable, "araclar/aday_kaydet.py", "--help"], cwd=KOK, capture_output=True, text=True)
    assert all(ad in r.stdout for ad, _ in HH.KESIM_SECENEKLERI)
    komut = [sys.executable, "araclar/aday_kaydet.py", UCLU_H, "--kod", "PA-99", "--durum", "test", "--katalog-m2", "69", "--kart", KART,
             "--silme-hali", KAYNAK, "--kesim-hatti", KESIM]
    r = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 2 and "--kesim-sozu" in r.stdout, r.stdout + r.stderr
