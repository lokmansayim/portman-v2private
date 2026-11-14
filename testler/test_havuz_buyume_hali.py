"""BK-31 PR-2 · Havuz hakeminin silme hâli kaleminde büyüme: kalan özel pano dış duvar dışarı kayarak tam ya da yarım panoya tamamlanmış ev,
yalnız Lokman'ın o evdeki sözüyle (`--buyume-sozu`). LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC (standart pano sohbeti, proje sohbeti):
- 140 m² 3+1: 20:22:14 "sağ taraf doğru ön tarafta da salon kısmında 101,5'u 125,5 a tamamlayabilirsin"; kart 20:25:45 "Doğru, yanına
  eklensin" ("Bugünkü 140 m2 kalır; 1390,5 × 1024 cm hâli (142,4 m2, veranda 24,0 m2) yeni numarayla girer.").
- 77 m² 2+1: 20:35:43 "salon ve mutfaktaki 1000cm çizgisindeki 48,75'leride 62,75'e tamamla"; kart 20:38:43 "Doğru, yanına eklensin"
  ("Bugünkü 77 m2 kalır; 773 × 1014 cm hâli (78,4 m2) yeni numarayla girer.").
CIO, 20:27: büyüme ayrı kalem, yalnız Lokman'ın ev sözüyle, kapsam "kalan özel pano tam panoya tamamlanır"; tek ev sözü, genelleme
varsayımdır. Silme kalemi (BK-31) ve standart hâl kipi (D-91) aynen.
"""
from __future__ import annotations
import contextlib
import copy
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from motor import geometry as G  # noqa: E402

SOZ_140 = ("Lokman 14 Kasım 2026 20:22:14 UTC: \"sağ taraf doğru ön tarafta da salon kısmında 101,5'u 125,5 a tamamlayabilirsin\"; "
           "kart 20:25:45 \"Doğru, yanına eklensin\"")
VERANDA_140 = ("Lokman, 14 Kasım 2026 20:25:45 UTC kartı \"Doğru, yanına eklensin\": \"Bugünkü 140 m2 kalır; 1390,5 × 1024 cm hâli "
               "(142,4 m2, veranda 24,0 m2) yeni numarayla girer.\"")
SOZ_77 = ("Lokman 14 Kasım 2026 20:35:43 UTC: \"salon ve mutfaktaki 1000cm çizgisindeki 48,75'leride 62,75'e tamamla\"; kart 20:38:43 "
          "\"Doğru, yanına eklensin\"")
PA24 = "is_emri/adaylar/PA24.json"
# büyümüş hâl → (kaynak şablon, kart, büyüme sözü, veranda sözü, kaynak dış ölçü, yeni dış ölçü, silinen (x, y), büyüyen (x, y),
#                tamamlanan, kısa parçası düşen)
EVLER = {
    "PA08_BUYUME": ("is_emri/adaylar/PA08.json", "AP-01", SOZ_140, VERANDA_140, (1400.0, 1000.0), (1390.5, 1024.0), (9.5, 0.0), (0.0, 24.0),
                    [("dis y 5", 101.5, 125.5)], [("dis x 700.25", 9.5)]),
    "PA24_BUYUME": (PA24, "AP-27", SOZ_77, None, (773.0, 1000.0), (773.0, 1014.0), (0.0, 0.0), (0.0, 14.0),
                    [("dis y 5", 48.75, 62.75), ("dis y 768", 48.75, 62.75)], []),
}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _ev(kod: str) -> dict:
    return _ie(f"testler/havuz/is_emirleri/{kod}.json")


def _buyut(ie: dict, cm: float) -> dict:
    """Bozuk örnek için: dizilim sonundaki ön cepheyi (y) `cm` kadar dışarı al, anahtarla; bantta kalan değerler kayar. Motor'un kabul ettiği
    ızgarayı arar."""
    ie = json.loads(json.dumps(ie))
    diz = ie["yapi"].setdefault("dizilim", {})
    diz["tek_ozel_pano"] = "dizilim_sonu"
    L = float(ie["yapi"]["dis_olcu_cm"]["y"])
    kay = lambda v: v + cm if v >= L - 10.5 else v
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            r[1], r[3] = kay(r[1]), kay(r[3])
    for dy in diz.get("dis_pano_dayanagi") or []:
        if "y" in dy:
            dy["y"], dy["aralik_cm"] = kay(dy["y"]), [kay(v) for v in dy["aralik_cm"]]
    ie["yapi"]["dis_olcu_cm"]["y"] = L + cm
    for g in (x / 2 for x in range(4, 40)):
        ie["yapi"]["grid"]["y_pano"] = g
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                G.kur(copy.deepcopy(ie))
            return ie
        except G.IsEmriHatasi:
            continue
    raise AssertionError(f"y +{cm}: Motor'un kabul ettiği ızgara yok")


def test_sabitler():
    """Hedef boylar iki ev sözünden (125,5 ve 62,75); silme kaleminin 30 cm'si aynen."""
    assert HH.TAMAMLAMA_BOYLARI_CM == (125.5, 62.75) and HH.TOL_SILME_CM == 30.0


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_onayli_ev_gecer(kod):
    """Lokman'ın sözüyle ve kartıyla onaylanan iki ev hakemden geçer: büyüme yalnız kalan özel pano kadar, o pano tamamlanır."""
    kaynak, kart, soz, veranda, olcu_k, olcu_s, silinen_cm, buyuyen_cm, tamamlanan, silinen = EVLER[kod]
    bulgular, o = HH.denetle_silme(_ev(kod), HH.kartlar()[kart], _ie(kaynak), veranda, soz)
    assert bulgular == [], (kod, bulgular)
    assert tuple(o["kaynak_dis_olcu_cm"]) == olcu_k and tuple(o["dis_olcu_cm"]) == olcu_s
    assert tuple(o["silinen_cm"]) == silinen_cm and tuple(o["buyuyen_cm"]) == buyuyen_cm
    assert sorted((p["duvar"], p["once"], p["sonra"]) for p in o["tamamlanan"]) == sorted(tamamlanan)
    assert sorted((p["duvar"], p["boy"]) for p in o["silinen"]) == sorted(silinen)
    assert o["veranda_kisalan"] == (["VERANDA"] if veranda else [])


def test_yetmis_yedi_ic_duvar_yeniden_dizilir():
    """77 m²: salon ile mutfak arasındaki iç duvarı Motor anahtarla yeniden dizer (Lokman'ın kartta gördüğü; açıklıklı pano yok)."""
    _, o = HH.denetle_silme(_ev("PA24_BUYUME"), HH.kartlar()["AP-27"], _ie(PA24), None, SOZ_77)
    assert o["yeniden_dizilen"] == [{"duvar": "ic y 449.25", "once": [122.5, 125.5, 125.5, 43.75], "sonra": [59.75, 125.5, 125.5, 120.5]}]


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_sozsuz_gecmez(kod):
    """Büyüme Lokman'ın ev sözü olmadan kalemin kapsamına girmez (boş söz de söz değildir)."""
    kaynak, kart, _soz, veranda, *_ = EVLER[kod]
    for soz in (None, "   "):
        bulgular, _ = HH.denetle_silme(_ev(kod), HH.kartlar()[kart], _ie(kaynak), veranda, soz)
        assert len(bulgular) == 1 and bulgular[0].startswith("dış ölçü:") and "--buyume-sozu" in bulgular[0], bulgular


def test_yuz_kirk_veranda_sozsuz_gecmez():
    """140 m²'de veranda 24 cm derinleşir: büyüme sözü verandayı kapsamaz, ev kartı ayrıca gerekir."""
    bulgular, _ = HH.denetle_silme(_ev("PA08_BUYUME"), HH.kartlar()["AP-01"], _ie("is_emri/adaylar/PA08.json"), None, SOZ_140)
    assert bulgular and all(x.startswith("veranda:") for x in bulgular), bulgular


@pytest.mark.parametrize("cm, bas", [(10.0, "büyüme:"), (130.0, "dış ölçü:")])
def test_tamamlamayan_buyume_kalir(cm, bas):
    """Sözle de olsa büyüme yalnız kalan özel panoyu tam ya da yarım panoya tamamlar: 77 m²'de 10 cm (48,75 → 58,75) ve 130 cm kalır."""
    bulgular, _ = HH.denetle_silme(_buyut(_ie(PA24), cm), HH.kartlar()["AP-27"], _ie(PA24), None, SOZ_77)
    assert any(x.startswith(bas) for x in bulgular), bulgular


def test_silme_ve_standart_kipi_aynen():
    """Silme kaleminin onaylı üç evi sözsüz kipte aynen geçer; D-91 standart hâl kipi büyümüş evi kabul etmez."""
    for kod, kaynak, kart, veranda in (("PA12_SILME", "is_emri/adaylar/PA12.json", "AP-11", None),
                                       ("PA14_SILME", "is_emri/adaylar/PA14.json", "AP-13", "kart"),
                                       ("PA15_SILME", "is_emri/adaylar/PA15.json", "AP-16", "kart")):
        bulgular, o = HH.denetle_silme(_ev(kod), HH.kartlar()[kart], _ie(kaynak), veranda)
        assert bulgular == [] and o["tamamlanan"] == [] and o["buyuyen_cm"] == [0.0, 0.0], (kod, bulgular)
    bulgular, _ = HH.denetle_standart(_ev("PA24_BUYUME"), HH.kartlar()["AP-27"], _ie(PA24))
    assert bulgular


def test_komut_satiri(capsys):
    assert HH.main(["testler/havuz/is_emirleri/PA24_BUYUME.json", "--kart", "AP-27", "--silme-hali", PA24, "--buyume-sozu", SOZ_77]) == 0
    out = capsys.readouterr().out
    assert "büyüyen 0 / 14 cm (tamamlanan: dis y 5 48.75 → 62.75 + dis y 768 48.75 → 62.75)" in out and "büyüme sözü: Lokman" in out
    assert HH.main(["testler/havuz/is_emirleri/PA24_BUYUME.json", "--kart", "AP-27", "--silme-hali", PA24]) == 1
    assert "--buyume-sozu" in capsys.readouterr().out
    assert HH.main(["x.json", "--kart", "AP-27", "--buyume-sozu", SOZ_77]) == 2


def test_aday_kaydet_sozsuz_yazmaz(tmp_path):
    """Kayıt aracı büyüme sözünü hakeme verir: sözsüz 77 m² DUR, şablon ve kayıt yazılmaz; söz yalnız --silme-hali ile."""
    r = subprocess.run([sys.executable, str(KOK / "araclar/aday_kaydet.py"), str(KOK / "testler/havuz/is_emirleri/PA24_BUYUME.json"),
                        "--kod", "PA-97", "--durum", "test", "--kart", "AP-27", "--silme-hali", str(KOK / PA24), "--standart", "--havuz"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 1 and "proje kartı hakemi geçmedi (AP-27)" in r.stdout and "--buyume-sozu" in r.stdout, r.stdout + r.stderr
    assert not (KOK / "is_emri/adaylar/PA97.json").exists() and not (KOK / "beyin/veri/havuz/PA97.json").exists()
    r = subprocess.run([sys.executable, str(KOK / "araclar/aday_kaydet.py"), "x.json", "--kod", "PA-97", "--kart", "AP-27",
                        "--buyume-sozu", SOZ_77], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2 and "yalnız --silme-hali ile" in r.stdout


def test_is_emri_belgesi():
    """İş emri iki ev sözünü saatiyle, kartları ve "tek ev sözü, genelleme varsayımdır" işaretini yazar."""
    belge = (KOK / "docs/is_emirleri/BK-31.md").read_text(encoding="utf-8")
    for s in ("20:22:14", "20:25:45", "20:35:43", "20:38:43", "101,5'u 125,5 a tamamlayabilirsin", "48,75'leride 62,75'e tamamla",
              "Tek ev sözü, genelleme varsayımdır"):
        assert s in belge, s
