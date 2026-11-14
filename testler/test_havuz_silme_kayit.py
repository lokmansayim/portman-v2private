"""D-92 › Kısa parça silinmiş hâllerin havuz kaydı (İE-40 PR-3): 85, 60 ve 70 m² evlerin silinmiş hâli yeni numarayla. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC (standart pano sohbeti): kart 19:39:46 "Kısa parça silinsin"; ev kartları "Doğru, yanına eklensin": 85 m² 20:05:33,
60 m² 20:09:12, 70 m² 20:14:50. Bugünkü evler (PA-12, PA-14, PA-15) aynen kalır; silinmiş hâl yanına girer (PA-30, PA-31, PA-32). Kayıt
hakemin silme hâli kipinden (BK-31, `havuz_hakemi.denetle_silme`): oda, açıklık ve kapı kaynakla aynı; dış ölçü yalnız kısa parça kadar;
veranda Lokman'ın ev kartıyla kısalır.
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
from beyin.katalog import SABLON_DIR, havuz_kayitlari  # noqa: E402
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
}
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}


def _ie(yol) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def _sablon(kod: str) -> dict:
    return _ie(SABLON_DIR / KAYIT[kod]["sablon"])


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
    bulgular, olc = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / kaynak_ie), kk.get("veranda_sozu"))
    assert bulgular == [] and olc == kk["olcum"], (kod, bulgular)
    assert tuple(olc["kaynak_dis_olcu_cm"]) == once and tuple(olc["dis_olcu_cm"]) == sonra
    assert (a["ozet"]["brut_m2"], a["veranda_m2"]) == (brut, veranda) and a["katalog_m2"] == round(brut)
    assert a["oda_programi"] == KAYIT[kaynak]["oda_programi"]


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_veranda_kartla_kisalir(kod):
    """Veranda yalnız Lokman'ın ev kartıyla kısalır (60 ve 70 m²); 85 m²'de veranda aynı, söz yok. Sözsüz koşu kalır."""
    kaynak, kart, *_ = HALLER[kod]
    kk = KAYIT[kod]["kaynak"]["kart_kiyasi"]
    soz = kk.get("veranda_sozu")
    if kod == "PA30":
        assert soz is None and kk["olcum"]["veranda_kisalan"] == [] and KAYIT[kod]["veranda_m2"] == KAYIT[kaynak]["veranda_m2"]
        return
    saat, secenek = HALLER[kod][6:]
    assert saat in soz and '"Doğru, yanına eklensin"' in soz and secenek in soz and kk["olcum"]["veranda_kisalan"] == ["VERANDA"]
    bulgular, _ = HH.denetle_silme(_sablon(kod), HH.kartlar()[kart], _ie(KOK / f"is_emri/adaylar/{kaynak}.json"))
    assert bulgular, kod


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kaynak_ev_aynen(kod):
    """Bugünkü ev yerinde kalır ("yanına eklensin"): kaynak evin kaydı D-87 ile, anahtarsız; silinmiş hâlin şablonu kaynak İş Emri'nin
    standart hâli (yalnız kimlik, talep ve referans kodu farklı)."""
    kaynak = HALLER[kod][0]
    assert KAYIT[kaynak]["kaynak"]["karar"] == "D-87"
    assert not _ie(SABLON_DIR / KAYIT[kaynak]["sablon"])["yapi"].get("dizilim", {}).get("tek_ozel_pano")
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


def test_anahtar_yalniz_silinmis_hallerde():
    """D-92 anahtarı havuz şablonlarında yalnız kısa parçası silinmiş hâllerde; kaynak evler ve öteki şablonlar anahtarsız. 95 m²'nin
    anahtarı (PA-10, kart 20:32:51) korunan dosyaya dokunduğu için ayrı PR'da girer; girince bu küme bilinçli olarak genişler."""
    anahtarli = {f.stem for f in (SABLON_DIR / "adaylar").glob("*.json")
                 if ((_ie(f).get("yapi") or {}).get("dizilim") or {}).get("tek_ozel_pano")}
    assert anahtarli == set(HALLER)
