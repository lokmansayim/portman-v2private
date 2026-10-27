"""İE-16 PR-2 · hedef örnek ÇP-06 (öneren tarafı): Yapı Tanımı bugünkü genel motor ve kural kitabıyla geçer, panel adedi tanıma paftadan
yazıldı (girdi), listemiz hakemin türleriyle okunur. PR-3a'dan beri listemiz panelli tanımın bölmesiz yazımından (`CP06_kural.json`). Listenin yeniden üretimi ve sözlüğün sayı kuralı `test_listeler.py`'de; hakemin
kendisi `testler/celik/test_celik_hakem.py`'dedir (değişmez)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas, oku  # noqa: E402
from testler.celik.projeler import liste_yap  # noqa: E402

BURADA = Path(__file__).resolve().parent
TANIM = BURADA / "CP06" / "CP06.json"
BIZIM = BURADA / "CP06" / "bizim_liste.json"
CEVAP = KOK / "testler" / "celik" / "veri" / "CP06_hakem_cevabi.json"
SONUC = BURADA / "CP06" / "sonuc.json"
KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")


@pytest.fixture(scope="module")
def uretim(tmp_path_factory):
    klasor = tmp_path_factory.mktemp("cp06")
    liste_yap.motor(TANIM, klasor, "omega_asik", liste_yap.VARSAYILAN_SET)
    return klasor


def test_tanim_motordan_gecer(uretim):
    klasor = uretim
    m = json.loads((klasor / "manifest.json").read_text(encoding="utf-8"))
    assert m["passed"], m.get("warnings")
    for ad in ("CP06_plan.png", "CP06_gorunusler.png", "CP06_pafta.png", "CP06.ifc", "CP06.ozet.json"):
        assert m["ciktilar"][ad], ad
    assert (klasor / "CP06_cizim.dxf").exists()


def test_panel_adetleri_paftadan_yazildi():
    """Duvar paneli (D), kolon-kiriş (K) ve makas (M) tanıma paftanın etiketlerinden yazıldı (girdi; kıyasta aynı çıkmaları sonuç değil);
    çatı paneli (C) tanımda yok (bilinen sınır)."""
    t = json.loads(TANIM.read_text(encoding="utf-8"))
    p = json.loads(CEVAP.read_text(encoding="utf-8"))["pafta"]
    sinif = [d["sinif"] for d in t["duvarlar"]]
    assert sinif.count("dis") + sinif.count("ic") == p["D"]["adet"] == 26
    assert sinif.count("kolon") + len(t["kirisler"]) == p["K"]["adet"] == 4
    assert sum(g.get("adet", 0) for g in t["cati"]["makaslar"].values()) == p["M"]["adet"] == 13
    assert p["C"]["adet"] == 2 and not any(dz.get("ust_yapi") == "cati_paneli" for dz in t["cati"]["duzlemler"])
    assert any("C01–C02" in s for s in t["bilinen_sinirlar"])


def test_bizim_liste_hakemin_turleriyle_okunur():
    """İE-16 PR-3a'dan beri listemiz bölmesiz tanımdan (`CP06_kural.json`, `karkas: kural`): duvar paneli adedi karkas kuralının bölmesidir
    (22; paftada 26: kıyasın sonucu, girdi değil). PR-2'de liste panelli tanımdandı (26, paftadan girdi); gerekçe İE-16 › PR-3a.
    PR-3b'den beri makas adedi de kuralın dizilimidir (15: 13 tam, 1 kısa, 1 kırma çaprazı; paftada 13 M ve cumbada 2 C: kıyasın sonucu);
    PR-3a'da tanımdaki `cati.makaslar`dı (13, paftadan girdi); gerekçe İE-16 › PR-3b. PR-3c'den beri panel oda bölmesinde biter (Lokman,
    27 Ekim 2026): 20 (PR-3a/3b'nin 366 cm kuralıyla 22)."""
    b = json.loads(BIZIM.read_text(encoding="utf-8"))
    assert b["tanim"]["yol"] == "testler/celik/projeler/CP06/CP06_kural.json" and b["karkas_kurali"]["yol"] == "kurallar/karkas/celik_karkas.json"
    bc = kiyas.bizim_celik(b["satirlar"])
    assert set(bc["turler"]) == {"duvar_paneli", "kolon_kiris", "makas", "c_profil"}
    assert (bc["turler"]["duvar_paneli"]["adet"], bc["turler"]["kolon_kiris"]["adet"], bc["turler"]["makas"]["adet"]) == (20, 4, 15)
    assert all(oku.celik_grubu_mu(s["grup"]) == ("tur" in s) for s in b["satirlar"])


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
def test_sonuc_hakemin_ciktisi():
    """`sonuc.json` elle düzenlenmez: hakem bugünkü listemizle yeniden koşunca tarih ve kıyas commit'i dışında aynı kayıt çıkar."""
    k = kiyas.kiyasla(BIZIM, Path(KAYNAK) / "1C8D2vCGZDTwqKA2eBnSyjtJ1iyKg3U9T.xlsx", Path(KAYNAK) / "13qR8PNSlt1eWtWpsqX8WwFmwoMJv89g8.pdf")
    yeni, kayitli = kiyas.sonuc_kaydi(k), json.loads(SONUC.read_text(encoding="utf-8"))
    for d in (yeni, kayitli):
        d.pop("tarih"), d.pop("kiyas_commit")
    assert yeni == kayitli
