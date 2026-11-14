"""BK-31 · Havuz hakeminin silme hâli kalemi: tek özel pano kuralının (D-92) dizilim sonunda bıraktığı kısa parça silinmiş ev. LLM'siz,
Postgres'siz.

Lokman, 14 Kasım 2026 UTC (standart pano sohbeti): kart 19:39:46 "Kısa parça silinsin" (soru "7 evde kural 9,5–27 cm'lik parça bırakıyor;
bu parça ne olsun?"); ev kartları "Doğru, yanına eklensin": 85 m² 20:05:33 (seçenek metni "… Kayıt denetimine silme kalemi eklenir."),
60 m² 20:09:12 ("… 773 cm hâli (59,0 m2, veranda 9,64 m2) …"), 70 m² 20:14:50 ("… 898,5 cm hâli (68,6 m2, veranda 7,28 m2) …").
Kabul (CIO): oda, açıklık, kapı kaynakla aynı; dış ölçü yalnız silinen kısa parça kadar sapar; başka sapma reddedilir; D-91 standart hâl
kipi gevşemez.
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

VERANDA_60 = "Lokman, 14 Kasım 2026 20:09:12 UTC kartı \"Doğru, yanına eklensin\" (… veranda 9,64 m2 …)"
VERANDA_70 = "Lokman, 14 Kasım 2026 20:14:50 UTC kartı \"Doğru, yanına eklensin\" (… veranda 7,28 m2 …)"
# silinmiş hâl → (kaynak şablon, kart, veranda sözü, kaynak dış ölçü, silinmiş dış ölçü, silinen cm (x, y), kısa parçası düşen duvarlar)
EVLER = {
    "PA12_SILME": ("is_emri/adaylar/PA12.json", "AP-11", None, (1166.0, 726.0), (1139.5, 726.0), (26.5, 0.0),
                   [("dis x 5", 26.5), ("ic x 452.25", 21.5), ("dis x 721", 26.5)]),
    "PA14_SILME": ("is_emri/adaylar/PA14.json", "AP-13", VERANDA_60, (763.0, 788.0), (763.0, 773.0), (0.0, 15.0),
                   [("dis y 5", 15.0), ("dis y 381.5", 15.0)]),
    "PA15_SILME": ("is_emri/adaylar/PA15.json", "AP-16", VERANDA_70, (763.0, 918.5), (763.0, 898.5), (0.0, 20.0),
                   [("dis y 5", 20.0)]),
}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _sil(kod: str) -> dict:
    return _ie(f"testler/havuz/is_emirleri/{kod}.json")


def _kes(ie: dict, eksen: str, cm: float) -> dict:
    """Bozuk örnek için: dizilim sonundaki cepheyi `cm` kadar içeri al (anahtarla); Motor'un kabul ettiği ızgarayı ara."""
    ie = json.loads(json.dumps(ie))
    ie["yapi"].setdefault("dizilim", {})["tek_ozel_pano"] = "dizilim_sonu"
    L = float(ie["yapi"]["dis_olcu_cm"][eksen])
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            for i in ((0, 2) if eksen == "x" else (1, 3)):
                if r[i] >= L - 10.5:
                    r[i] -= cm
    ie["yapi"]["dis_olcu_cm"][eksen] = L - cm
    for g in (x / 2 for x in range(4, 40)):
        ie["yapi"]["grid"][f"{eksen}_pano"] = g
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                G.kur(copy.deepcopy(ie))
            return ie
        except G.IsEmriHatasi:
            continue
    raise AssertionError(f"{eksen} {cm}: Motor'un kabul ettiği ızgara yok")


def test_sabitler():
    """Kısa parça 30 cm altı (varsayım, BK-31); kısa parça tek özel pano kuralının kalanı; D-91'in sınırları aynen."""
    assert HH.TOL_SILME_CM == 30.0 and HH.TEK_OZEL_PANO == "dizilim_sonu" and HH.TEK_OZEL_PANO in G.TEK_OZEL_PANO_YERLERI
    assert HH.TOL_STANDART_CM == 62.75 and HH.DIZILIM_SERBEST == ("son_pano",)


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_onayli_ev_gecer(kod):
    """Lokman'ın kartla onayladığı üç silinmiş hâl hakemden geçer: dış ölçü yalnız kısa parça kadar küçülür, kısa parçalar düşer."""
    kaynak, kart, soz, olcu_k, olcu_s, silinen_cm, silinen = EVLER[kod]
    bulgular, o = HH.denetle_silme(_sil(kod), HH.kartlar()[kart], _ie(kaynak), soz)
    assert bulgular == [], (kod, bulgular)
    assert tuple(o["kaynak_dis_olcu_cm"]) == olcu_k and tuple(o["dis_olcu_cm"]) == olcu_s and tuple(o["silinen_cm"]) == silinen_cm
    assert sorted((p["duvar"], p["boy"]) for p in o["silinen"]) == sorted(silinen)
    assert o["veranda_kisalan"] == (["VERANDA"] if soz else [])


def test_seksen_bes_metrekare_hedef():
    """85 m² (PA-30'un girdisi): 1166 → 1139,5 cm; iki yatak odası küçülür, veranda aynı; kartın öteki kalemleri aynı."""
    _, o = HH.denetle_silme(_sil("PA12_SILME"), HH.kartlar()["AP-11"], _ie("is_emri/adaylar/PA12.json"))
    assert o["brut_m2"] == 82.73 and o["yatak_odasi"] == 3 and o["veranda"] == 1
    assert o["pencereler"] == {"120x180": 5, "180x200": 1, "60x40": 1} and (o["dis_kapi"], o["ic_kapi"]) == (1, 5)
    assert o["yeniden_dizilen"] == []


def test_yetmis_metrekare_veranda_kenari():
    """70 m²: kısa parçası olmayan veranda kenarını Motor yeniden dizer (82,75 + 120,5 → 57,75 + 125,5); açıklıklı pano yok."""
    _, o = HH.denetle_silme(_sil("PA15_SILME"), HH.kartlar()["AP-16"], _ie("is_emri/adaylar/PA15.json"), VERANDA_70)
    assert o["yeniden_dizilen"] == [{"duvar": "dis y 381.5", "once": [120.5, 82.75], "sonra": [57.75, 125.5]}]


@pytest.mark.parametrize("kod", ["PA14_SILME", "PA15_SILME"])
def test_veranda_sozsuz_gecmez(kod):
    """Veranda kısalması Lokman'ın o evin kartı olmadan kalemin kapsamına girmez: tek bulgu verandadır."""
    kaynak, kart, *_ = EVLER[kod]
    bulgular, _ = HH.denetle_silme(_sil(kod), HH.kartlar()[kart], _ie(kaynak))
    assert len(bulgular) == 1 and bulgular[0].startswith("veranda:") and "--veranda-sozu" in bulgular[0], bulgular
    bulgular, _ = HH.denetle_silme(_sil(kod), HH.kartlar()[kart], _ie(kaynak), "   ")
    assert len(bulgular) == 1 and bulgular[0].startswith("veranda:")


def _anahtarsiz(ie):
    ie["yapi"]["dizilim"].pop("tek_ozel_pano")
    return ie


def _oda_adi(ie):
    return json.loads(json.dumps(ie, ensure_ascii=False).replace("SALON+MUTFAK", "SALON"))


def _pencere(ie):
    a = next(a for a in ie["acikliklar"] if a.get("mahal") == "YATAK ODASI 2")
    a["olcu"] = "100x140"
    return ie


def _dikme(ie):
    ie["dikmeler"][0][0] = float(ie["dikmeler"][0][0]) + 10
    return ie


def _cati(ie):
    ie["cati"]["egim_yuzde"] = 99
    return ie


# (ad, silinmiş hâl, kart, kaynak, beklenen bulgunun başı)
PA12 = "is_emri/adaylar/PA12.json"
BOZUK = [
    ("anahtarsiz", lambda: _anahtarsiz(_sil("PA12_SILME")), "AP-11", PA12, "dizilim:"),
    ("152_cm", lambda: _kes(_ie(PA12), "x", 152), "AP-11", PA12, "dış ölçü:"),
    ("20_cm_kisa_parca_degil", lambda: _kes(_ie(PA12), "x", 20), "AP-11", PA12, "silinen:"),
    ("27_cm_oda_fazla_kaydi", lambda: _kes(_ie(PA12), "x", 27), "AP-11", PA12, "oda köşesi:"),
    ("95_m2_kisa_parca_yok", lambda: _kes(_ie("is_emri/adaylar/PA10.json"), "x", 20), "AP-04", "is_emri/adaylar/PA10.json", "silinen:"),
    ("buyume", lambda: _ie(PA12), "AP-11", "testler/havuz/is_emirleri/PA12_SILME.json", "dış ölçü:"),
    ("oda_adi", lambda: _oda_adi(_sil("PA12_SILME")), "AP-11", PA12, "odalar:"),
    ("pencere_olcusu", lambda: _pencere(_sil("PA12_SILME")), "AP-11", PA12, "açıklıklar:"),
    ("dikme", lambda: _dikme(_sil("PA12_SILME")), "AP-11", PA12, "dikmeler:"),
    ("cati", lambda: _cati(_sil("PA12_SILME")), "AP-11", PA12, "cati:"),
    ("yanlis_kart", lambda: _sil("PA12_SILME"), "AP-13", PA12, "kaynak ev:"),
]


@pytest.mark.parametrize("ad, kur, kart, kaynak, bas", BOZUK, ids=[b[0] for b in BOZUK])
def test_bozuk_ornek_kalir(ad, kur, kart, kaynak, bas):
    """Başka her sapma reddedilir: anahtarsız, 30 cm ve üstü, kısa parça olmayan kesim, fazla kayan oda, kısa parçası olmayan ev, büyüme,
    oda, pencere, dikme, çatı ve kaynağın kartı."""
    bulgular, _ = HH.denetle_silme(kur(), HH.kartlar()[kart], _ie(kaynak))
    assert any(x.startswith(bas) for x in bulgular), (ad, bulgular)


def test_standart_hal_kipi_gevsemedi():
    """D-91 standart hâl kipi silinmiş hâli kabul etmez (ayrı kalem; standart hâl kipi aynen)."""
    bulgular, _ = HH.denetle_standart(_sil("PA12_SILME"), HH.kartlar()["AP-11"], _ie(PA12))
    assert any(x.startswith("dış duvarda özel pano:") for x in bulgular) and any(x.startswith("dizilim:") for x in bulgular)


def test_komut_satiri(capsys):
    """`--silme-hali` GEÇTİ yazar; standart hâlle birlikte, sözsüz veranda kipi ve çelikte DUR."""
    assert HH.main(["testler/havuz/is_emirleri/PA12_SILME.json", "--kart", "AP-11", "--silme-hali", PA12]) == 0
    assert "GEÇTİ: silme hâli (BK-31)" in capsys.readouterr().out
    assert HH.main(["testler/havuz/is_emirleri/PA14_SILME.json", "--kart", "AP-13", "--silme-hali", "is_emri/adaylar/PA14.json"]) == 1
    assert "KALDI:\n- veranda:" in capsys.readouterr().out
    assert HH.main(["testler/havuz/is_emirleri/PA14_SILME.json", "--kart", "AP-13", "--silme-hali", "is_emri/adaylar/PA14.json",
                    "--veranda-sozu", VERANDA_60]) == 0
    assert "veranda kısaldı (VERANDA)" in capsys.readouterr().out
    assert HH.main(["x.json", "--kart", "AP-11", "--silme-hali", PA12, "--standart-hal", PA12]) == 2
    assert HH.main(["x.json", "--kart", "AP-11", "--veranda-sozu", VERANDA_60]) == 2
    assert HH.main(["x.json", "--kart", "ÇP-18", "--silme-hali", PA12]) == 2


def _aday_kaydet(tmp_path, *arg):
    return subprocess.run([sys.executable, str(KOK / "araclar/aday_kaydet.py"), *arg], capture_output=True, text=True, cwd=tmp_path)


def test_aday_kaydet_hakemsiz_yazmaz(tmp_path):
    """Kayıt aracı silme hâli kipini çağırır: veranda sözü olmadan 60 m² DUR, şablon ve kayıt yazılmaz; bayraklar ayrı kalem."""
    r = _aday_kaydet(tmp_path, str(KOK / "testler/havuz/is_emirleri/PA14_SILME.json"), "--kod", "PA-97", "--durum", "test", "--kart", "AP-13",
                     "--silme-hali", str(KOK / "is_emri/adaylar/PA14.json"), "--standart", "--havuz")
    assert r.returncode == 1 and "proje kartı hakemi geçmedi (AP-13)" in r.stdout and "veranda:" in r.stdout, r.stdout + r.stderr
    assert not (KOK / "is_emri/adaylar/PA97.json").exists() and not (KOK / "beyin/veri/havuz/PA97.json").exists()
    r = _aday_kaydet(tmp_path, "x.json", "--kod", "PA-97", "--kart", "AP-11", "--silme-hali", PA12, "--standart-hal", PA12)
    assert r.returncode == 2 and "ayrı kalemlerdir" in r.stdout
    r = _aday_kaydet(tmp_path, "x.json", "--kod", "PA-97", "--kart", "AP-11", "--veranda-sozu", VERANDA_60)
    assert r.returncode == 2 and "yalnız --silme-hali ile" in r.stdout
    r = _aday_kaydet(tmp_path, str(KOK / "testler/havuz/is_emirleri/PA12_SILME.json"), "--kod", "PA-97", "--silme-hali", str(KOK / PA12))
    assert r.returncode == 2 and "yalnız --kart ile" in r.stdout


def test_is_emri_belgesi():
    """İş emri Lokman'ın kartlarını saatiyle ve 30 cm sınırını varsayım diye yazar."""
    belge = (KOK / "docs/is_emirleri/BK-31.md").read_text(encoding="utf-8")
    for s in ('"Kısa parça silinsin"', '"Doğru, yanına eklensin"', "19:39:46", "20:05:33", "20:09:12", "20:14:50", "Varsayım"):
        assert s in belge, s
