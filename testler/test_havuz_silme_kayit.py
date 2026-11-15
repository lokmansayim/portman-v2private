"""D-92 › Kısa parça silinmiş hâllerin havuz kaydı (İE-40 PR-3): 85, 60 ve 70 m² evlerin silinmiş hâli yeni numarayla. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC (standart pano sohbeti): kart 19:39:46 "Kısa parça silinsin"; ev kartları "Doğru, yanına eklensin": 85 m² 20:05:33,
60 m² 20:09:12, 70 m² 20:14:50. Bugünkü evler (PA-12, PA-14, PA-15) aynen kalır; silinmiş hâl yanına girer (PA-30, PA-31, PA-32). Kayıt
hakemin silme hâli kipinden (BK-31, `havuz_hakemi.denetle_silme`): oda, açıklık ve kapı kaynakla aynı; dış ölçü yalnız kısa parça kadar;
veranda Lokman'ın ev kartıyla kısalır.
Büyümüş hâller (BK-31 PR-2 büyüme kalemi, yalnız Lokman'ın ev sözüyle): 140 m² 20:22:14 sözü ve 20:25:45 kartı (PA-33), 77 m² 20:35:43
sözü ve 20:38:43 kartı (PA-34); bugünkü 140 m² (PA-08) ve 77 m² (PA-24) aynen.
Kesim hattı, üçlü H ve kayan pencere (BK-34, D-96): 71 m² 20:46:54 sözü ve 20:57:28 kartı (PA-35); bugünkü 71 m² (PA-26) aynen.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin.katalog import ADAYLAR_PREFABRIK_JSON, SABLON_DIR, havuz_kayitlari  # noqa: E402
from motor import geometry as G  # noqa: E402

D92 = (KOK / "KARARLAR" / "D-92.md").read_text(encoding="utf-8")
# kod → (kaynak ev, kart, silinmiş İş Emri, dış ölçü (önce, sonra), brüt m², veranda m², kartın saati ve seçenek metninin başı)
HALLER = {
    "PA30": ("PA12", "AP-11", "testler/havuz/is_emirleri/PA12_SILME.json", ((1166.0, 726.0), (1139.5, 726.0)), 82.73, 12.8,
             "20:05:33", "Bugünkü 85 m² kalır; 1139,5 cm hâli (82,7 m²) yeni"),
    "PA31": ("PA14", "AP-13", "testler/havuz/is_emirleri/PA14_SILME.json", ((763.0, 788.0), (763.0, 773.0)), 58.98, 9.64,
             "20:09:12", "Bugünkü 60 m2 kalır; 773 cm hâli (59,0 m2, veranda"),
    "PA32": ("PA15", "AP-16", "testler/havuz/is_emirleri/PA15_SILME.json", ((763.0, 918.5), (763.0, 898.5)), 68.56, 7.28,
             "20:14:50", "Bugünkü 70 m2 kalır; 898,5 cm hâli (68,6 m2,"),
    "PA33": ("PA08", "AP-01", "testler/havuz/is_emirleri/PA08_BUYUME.json", ((1400.0, 1000.0), (1390.5, 1024.0)), 142.39, 24.0,
             "20:25:45", "Bugünkü 140 m2 kalır; 1390,5 × 1024 cm hâli (142,4 m2, veranda 24,0 m2)"),
    "PA34": ("PA24", "AP-27", "testler/havuz/is_emirleri/PA24_BUYUME.json", ((773.0, 1000.0), (773.0, 1014.0)), 78.38, 0,
             "20:38:43", "Bugünkü 77 m2 kalır; 773 × 1014 cm hâli (78,4 m2)"),
    "PA35": ("PA26", "AP-08", "testler/havuz/is_emirleri/PA26_UCLU_H.json", ((785.0, 900.0), (773.0, 888.5)), 68.68, 4.79,
             "20:57:28", "Bugünkü 71 m2 kalır; 773 × 888,5 cm üçlü H'lı hâl (kapı panosu 120,5)"),
}
# büyüyen hâl → (Lokman'ın ev sözünün saati, sözden parça, tamamlanan duvar sayısı)
BUYUYEN = {"PA33": ("20:22:14", "101,5'u 125,5 a tamamlayabilirsin", 1), "PA34": ("20:35:43", "48,75'leride 62,75'e tamamla", 2),
           "PA35": ("20:46:54", "120,5 panoyuda kendi ölçüsüne getirir misin", 1)}
# kesim hattı, üçlü H ve açıklık kayması (BK-34): yalnız 71 m² üçlü H'lı hâlde, Lokman'ın o evdeki sözüyle
KESIMLI = {"PA35": ("on:17:770", [{"nokta_cm": [386.5, 758.0], "kaynakta_cm": [386.5, 775.0]}], ["pencere 120x120"])}
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}
# kaynak evler: havuz kaydı (D-87) ya da ilk sekiz aday (D-80; 140 m² PA-08)
KAYNAK = {**{a["kod"]: a for a in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8"))}, **KAYIT}


def _ie(yol) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def _sablon(kod: str) -> dict:
    return _ie(SABLON_DIR / KAYIT[kod]["sablon"])


def _sozler(kk: dict) -> dict:
    """Kayıttaki sözler `denetle_silme`'nin seçenekleri olarak (kesim hattının yazısı ölçümden)."""
    kesim = (kk["olcum"].get("kesim_hatti") or {}).get("yazi")
    return {"veranda_sozu": kk.get("veranda_sozu"), "buyume_sozu": kk.get("buyume_sozu"), "kesim_hatti": kesim,
            "kesim_sozu": kk.get("kesim_sozu"), "uclu_h_sozu": kk.get("uclu_h_sozu"), "aciklik_sozu": kk.get("aciklik_sozu")}


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kayit_silme_kipinden(kod):
    """Kayıt silme hâli kipinden geçti; hakem şablonla yeniden koşunca ölçüm aynı; kaynak ev değişirse kayıt yeniden yazılır."""
    kaynak, kart, silme, (once, sonra), brut, veranda, *_ = HALLER[kod]
    a = KAYIT[kod]
    kk = a["kaynak"]["kart_kiyasi"]
    kaynak_ie = f"is_emri/adaylar/{kaynak}.json"
    assert (a["kaynak"]["karar"], a["kaynak"]["dosya"], a["kaynak"]["standart"]) == ("D-92", silme, True)
    assert (kk["kart"], kk["sonuc"], kk["kip"], kk["kaynak_is_emri"]) == (kart, "geçti", "silme_hali", kaynak_ie)
    assert kk["kart_sha256"] == HH.kartlar()[kart]["kart_sha256"]
    assert kk["kaynak_sha256"] == hashlib.sha256((KOK / kaynak_ie).read_bytes()).hexdigest()
    bulgular, olc = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / kaynak_ie), **_sozler(kk))
    assert bulgular == [] and olc == kk["olcum"], (kod, bulgular)
    assert tuple(olc["kaynak_dis_olcu_cm"]) == once and tuple(olc["dis_olcu_cm"]) == sonra
    assert (a["ozet"]["brut_m2"], a["veranda_m2"]) == (brut, veranda) and a["katalog_m2"] == round(brut)
    assert a["oda_programi"] == KAYNAK[kaynak]["oda_programi"]


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_veranda_kartla_degisir(kod):
    """Veranda yalnız Lokman'ın ev kartıyla değişir (60 ve 70 m² kısalır, 140 m² derinleşir); 85 ve 77 m²'de söz yok, veranda aynı.
    Sözsüz koşu kalır."""
    kaynak, kart, *_ = HALLER[kod]
    kk = KAYIT[kod]["kaynak"]["kart_kiyasi"]
    soz = kk.get("veranda_sozu")
    if soz is None:
        assert kk["olcum"]["veranda_kisalan"] == [] and KAYIT[kod]["veranda_m2"] == KAYNAK[kaynak]["veranda_m2"], kod
        return
    saat, secenek = HALLER[kod][6:]
    assert saat in soz and '"Doğru, yanına eklensin"' in soz and secenek in soz and kk["olcum"]["veranda_kisalan"] == ["VERANDA"]
    bulgular, _ = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / f"is_emri/adaylar/{kaynak}.json"),
                                   **{**_sozler(kk), "veranda_sozu": None})
    assert bulgular, kod


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_buyume_yalniz_ev_soziyle(kod):
    """Dış duvar yalnız Lokman'ın o evdeki sözüyle dışarı kayar (kalan özel pano tam ya da yarım panoya); öteki hâllerde büyüme yok.
    Sözsüz koşu kalır."""
    kaynak, kart, *_ = HALLER[kod]
    kk = KAYIT[kod]["kaynak"]["kart_kiyasi"]
    soz = kk.get("buyume_sozu")
    if kod not in BUYUYEN:
        assert soz is None and kk["olcum"]["tamamlanan"] == [] and kk["olcum"]["buyuyen_cm"] == [0.0, 0.0], kod
        return
    saat, parca, n = BUYUYEN[kod]
    assert saat in soz and parca in soz and len(kk["olcum"]["tamamlanan"]) == n
    bulgular, _ = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / f"is_emri/adaylar/{kaynak}.json"),
                                   **{**_sozler(kk), "buyume_sozu": None})
    assert bulgular, kod


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kaynak_ev_aynen(kod):
    """Bugünkü ev yerinde kalır ("yanına eklensin"): kaynak evin kaydı D-87 ile (140 m² D-80 ile), anahtarsız; silinmiş hâlin şablonu
    kaynak İş Emri'nin standart hâli (yalnız kimlik, talep ve referans kodu farklı)."""
    kaynak = HALLER[kod][0]
    assert KAYNAK[kaynak]["kaynak"]["karar"] == ("D-80" if kaynak == "PA08" else "D-87")
    assert not _ie(SABLON_DIR / KAYNAK[kaynak]["sablon"])["yapi"].get("dizilim", {}).get("tek_ozel_pano")
    sab, src = _sablon(kod), _ie(KOK / HALLER[kod][2])
    for d in (sab, src):
        for anahtar in ("is_emri_no", "revizyon", "talep", "ozellikler", "alici_ait"):
            d.pop(anahtar, None)
        d["yapi"].pop("referans_model", None)
    assert sab == src


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kisa_parca_kalmadi(kod):
    """Motor'un planında 9,5–27 cm'lik kısa pano yok; dış ölçü kayıttaki gibi."""
    p = G.kur(_sablon(kod))
    assert not [x.boy for x in p.panolar if 9.0 <= x.boy <= 27.5], kod
    assert [p.W, p.H] == KAYIT[kod]["ozet"]["dis_olcu_cm"]


def test_karar_dosyasi():
    """D-92 kartları saatiyle ve üç kaydı kaynağıyla yazar (projeler kodla; CLAUDE.md › soru 15)."""
    assert "19:39:46 UTC, Lokman kartta seçti: **\"Kısa parça silinsin\"**" in D92
    for kod, (_, kart, silme, _, _, _, saat, _) in HALLER.items():
        assert f"{saat} UTC, Lokman kartta seçti: **\"Doğru, yanına eklensin\"**" in D92, kod
        assert f"| PA-{kod[2:]} | {kart} | `{silme}` |" in D92, kod


def test_silinmis_hal_anahtarli_kaynak_ev_anahtarsiz():
    """Silinmiş hâlin şablonu D-92 anahtarlı; kaynak ev (bugünkü hâl) anahtarsız. Anahtarlı şablonların tam kümesi
    `test_havuz_tek_pano.py::test_anahtar_yalniz_95m2_evde`'de."""
    anahtarli = {f.stem for f in (SABLON_DIR / "adaylar").glob("*.json")
                 if ((_ie(f).get("yapi") or {}).get("dizilim") or {}).get("tek_ozel_pano")}
    assert set(HALLER) <= anahtarli and not {h[0] for h in HALLER.values()} & anahtarli


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kesim_hatti_yalniz_ev_soziyle(kod):
    """Kesim hattı, üçlü H ve kayan pencere (BK-34) yalnız 71 m² üçlü H'lı hâlde, Lokman'ın 20:46:54 sözü ve 20:57:28 kartıyla; öteki
    hâllerde yok. Sözlerden biri düşerse hakem kalır."""
    kaynak, kart, *_ = HALLER[kod]
    kk = KAYIT[kod]["kaynak"]["kart_kiyasi"]
    olc = kk["olcum"]
    if kod not in KESIMLI:
        assert not ({"kesim_sozu", "uclu_h_sozu", "aciklik_sozu"} & set(kk)) and not (
            {"kesim_hatti", "uclu_h", "kayan_aciklik"} & set(olc)), kod
        return
    yazi, uclu_h, kayan = KESIMLI[kod]
    assert olc["kesim_hatti"]["yazi"] == yazi and olc["uclu_h"] == uclu_h
    assert [a["aciklik"] for a in olc["kayan_aciklik"]] == kayan
    assert "20:57:28" in kk["kesim_sozu"] and "20:57:28" in kk["aciklik_sozu"] and "üçlü H olacak" in kk["uclu_h_sozu"]
    assert _sablon(kod)["yapi"]["birlesimler"] == [{"nokta_cm": [386.5, 758.0], "t": "uclu_h"}]
    for dusen in ("kesim_sozu", "uclu_h_sozu", "aciklik_sozu"):
        sozler = {**_sozler(kk), dusen: None}
        if dusen == "kesim_sozu":
            sozler["kesim_hatti"] = None
        bulgular, _ = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / f"is_emri/adaylar/{kaynak}.json"), **sozler)
        assert bulgular, (kod, dusen)
