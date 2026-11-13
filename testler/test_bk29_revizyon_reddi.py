"""BK-29 PR-1 (pano 200) · geri çevrilen istek açık planı kapatmaz; soru hakkı her planda yenilenir.

13 Kasım 2026 WhatsApp denetimi (canlı v2026.11.13; kabul seti C1–C4): bot bir revizyon isteğini geri çevirince (yönlendirme) konuşma
taslağı boşaltıp "yonlendirildi" oluyordu. Bayi aynı planı onaylayamıyordu ("Bu plan için onay beklenmiyor", "Onaylanacak açık bir plan
görünmüyor"), sonraki revizyonu "Kaç oda istiyorsunuz?" sorusuna düşüyordu. Prefabrikte soru hakkı (MAX_SORU) talepten plana kadar
harcanıp revizyonda ilk soruda "Talebi netleştiremedim" oluyordu. LLM yok, Postgres yok, çizim yok: `karar_ver` elle kurulmuş `Talep`lerle
sürülür, düğmeler `kanal/etkilesim.coz` ile çözülür (worker'daki gibi). Katalog canlının kabul kümesiyle (12 Kasım K-A10: 18 kod) kurulur.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kanal import etkilesim as ET  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen, var  # noqa: E402

KABUL = {"PA01", "PA02", "PA03", "PA04", "PA05", "PA06", "PA07", "PA08", "PA06K", "PA06C",
         "KT01", "KT02", "KT03", "KT04", "Ç8201", "Ç8801", "Ç8801K", "Ç8801L"}
VERANDA = var("veranda_degistir", "veranda arkada olsun")


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


def _pa04(s: Sohbet):
    k = s.yaz("Tek kat prefabrik, 2+1, 78 m²", yapi_turu="prefabrik", kat_sayisi=1, oda_programi="2+1", alan_m2=78)
    assert k.soru_alani == "oncelik", k.mesaj
    k = s.dugme("q:oncelik:butce")
    assert k.eylem == "secenek", k.mesaj
    k = s.dugme("s:{set}:PA04")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    return k


def _gecerli(s: Sohbet, tur: str) -> bool:
    no, rev = s.plan["is_emri_no"], s.plan["revizyon"]
    return bool(ET.coz({"reply_id": f"{tur}:{no}:{rev}", "type": "interactive"}, s.k.d).get("gecerli"))


def test_c1_ret_sonrasi_onayla_dugmesi(s):
    """C1: P6001 "veranda arkada olsun" geri çevrilir; plan açık kalır, mesaj bunu söyler, Onayla düğmesi onaylar."""
    s.yaz("P6001", katalog_kodu="P6001")
    k = s.yaz("veranda arkada olsun", varyantlar=[VERANDA])
    assert k.eylem == "yonlendir"                                         # Patron'a bildirim bugünkü gibi
    etiket = f"{s.plan['is_emri_no']} r01"
    assert k.mesaj.endswith(f"Planınız ({etiket}) değişmedi. Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")
    assert [b["id"] for b in k.butonlar] == [f"o:{s.plan['is_emri_no']}:1", f"r:{s.plan['is_emri_no']}:1"]
    assert s.k.d["asama"] == "onay_bekliyor" and s.k.d["taslak"].get("katalog_kodu") == "P6001"
    assert not any(v.get("tur") == "veranda_degistir" for v in s.k.d["taslak"].get("varyantlar") or [])   # geri çevrilen istek taslağa yazılmaz
    assert _gecerli(s, "o") and _gecerli(s, "r")
    k = s.dugme(f"o:{s.plan['is_emri_no']}:1")
    assert k.mesaj.startswith(f"Onayınız kaydedildi ({s.plan['is_emri_no']}, revizyon 1)")


def test_c2_ret_sonrasi_onaylıyorum_yazisi(s):
    """C2: geri çevrilen pencere ekleme isteğinden sonra "Onaylıyorum" yazısı planı onaylar."""
    _pa04(s)
    k = s.yaz("yatak odası 1'e ikinci bir pencere ekleyin", pencereler=[pen("yatak odası 1", "120x120", islem="ekle")])
    assert k.eylem == "yonlendir" and "Pencere ekleme/kaldırma otomatik yapılamıyor" in k.mesaj and "değişmedi" in k.mesaj
    k = s.yaz("Onaylıyorum", niyet="onay")
    assert k.mesaj.startswith("Onayınız kaydedildi") and s.k.d["asama"] == "onaylandi"


def test_c3_ret_sonrasi_revizyon_ayni_planda(s):
    """C3: ret sonrası revizyon aynı planın r02'sidir; geri çevrilen istek r02'ye taşınmaz ("Kaç oda istiyorsunuz?" yok)."""
    _pa04(s)
    no = s.plan["is_emri_no"]
    k = s.yaz("veranda arkada olsun", varyantlar=[VERANDA])
    assert k.eylem == "yonlendir" and s.plan["is_emri_no"] == no
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "MUTFAK" and a["tur"] == "pencere"] == ["120x120"]
    assert "veranda" not in k.mesaj.lower()


def test_c4_celik_r03_ret_sonrasi_cati(s):
    """C4: çelik Ç8801 r03'te "veranda arkada olsun" geri çevrilir; "çatı K olsun" r04 olur."""
    s.yaz("Tek kat çelik, 2+1, 88 m²", yapi_turu="celik", kat_sayisi=1, oda_programi="2+1", alan_m2=88)
    s.yaz("Ç8801 olsun", katalog_kodu="Ç8801")
    assert s.yaz("çatı K olsun").eylem == "is_emri"
    assert s.yaz("çatı L olsun").revizyon == 2
    assert s.yaz("dışlar 140'lık olsun").revizyon == 3
    k = s.yaz("veranda arkada olsun", varyantlar=[VERANDA])
    assert k.eylem == "yonlendir" and "r03) değişmedi" in k.mesaj and _gecerli(s, "o")
    k = s.yaz("çatı K olsun")
    assert k.eylem == "is_emri" and k.revizyon == 4 and "çatı Ç8801-K" in k.mesaj


def test_onayli_plan_onayli_kalir(s):
    """Onaydan sonraki istek geri çevrilirse plan onaylı kalır (onay bekleyen plana dönmez); bayiye onaylı planın değişmediği yazılır."""
    s.yaz("P6001", katalog_kodu="P6001")
    s.yaz("onaylıyorum", niyet="onay")
    k = s.yaz("veranda arkada olsun", varyantlar=[VERANDA])
    assert k.eylem == "yonlendir" and k.mesaj.endswith(f"Onaylı planınız ({s.plan['is_emri_no']} r01) değişmedi.") and not k.butonlar
    assert s.k.d["asama"] == "onaylandi"


def test_revizyon_hakki_dolunca_onaylanabilir(s):
    """4 revizyon hakkı dolunca beşinci istek geri çevrilir; son plan onaylanabilir kalır, düğme yalnız Onayla."""
    s.yaz("P6001", katalog_kodu="P6001")
    for i, olcu in enumerate(("120x180", "120x120", "120x180", "120x120"), start=2):
        assert s.yaz(f"yatak odası 1 penceresi {olcu} olsun", pencereler=[pen("yatak odası 1", olcu)]).revizyon == i
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "yonlendir" and "revizyon hakkı doldu" in k.mesaj and k.mesaj.endswith("r05) değişmedi; onaylayabilirsiniz.")
    assert [b["baslik"] for b in k.butonlar] == ["Onayla"] and s.k.d["asama"] == "onay_bekliyor" and s.plan["revizyon"] == 5


def test_yeni_talep_reddi_eski_plani_kapatir(s):
    """Konuşma bu mesajda sıfırlandıysa (açık yeni talep) bugünkü yol: eski plan kapanır, plan cümlesi yazılmaz."""
    s.yaz("P6001", katalog_kodu="P6001")
    k = s.yaz("yeni talep: 7x4 m 2+1", oda_programi="2+1", dis_olcu={"en_m": 4, "boy_m": 7})
    assert k.eylem == "yonlendir" and "değişmedi" not in k.mesaj and not k.butonlar
    assert s.k.d["asama"] == "yonlendirildi" and not s.plan


def test_soru_hakki_her_planda_yenilenir(s):
    """Prefabrikte talepten plana 4 soru (oda, ölçü, öncelik, set) soruldu; revizyondaki ilk soru "Talebi netleştiremedim" olmaz."""
    assert s.yaz("prefabrik ev istiyorum", yapi_turu="prefabrik").soru_alani == "oda_programi"
    assert s.yaz("2+1", oda_programi="2+1").soru_alani == "dis_olcu"
    assert s.yaz("78 m²", alan_m2=78).soru_alani == "oncelik"
    assert s.yaz("fark etmez").eylem == "secenek"
    assert s.dugme("s:{set}:PA04").eylem == "is_emri"
    k = s.yaz("pencere 120x120 olsun", varyantlar=[{"tur": "pencere_degistir", "aciklama": "pencere 120x120 olsun", "parametreler": {"yeni": "120x120"}}])
    assert k.eylem == "sor" and k.soru_alani == "pencere_mahal", k.mesaj


def test_soru_siniri_reddinde_plan_acik(s):
    """Revizyonda soru hakkı dolunca ("Talebi netleştiremedim") da plan açık kalır."""
    _pa04(s)
    pv = [{"tur": "pencere_degistir", "aciklama": "pencere 120x120 olsun", "parametreler": {"yeni": "120x120"}}]
    for _ in range(4):
        assert s.yaz("pencere 120x120 olsun", varyantlar=pv).soru_alani == "pencere_mahal"
    k = s.yaz("pencere 120x120 olsun", varyantlar=pv)
    assert k.eylem == "yonlendir" and k.mesaj.startswith("Talebi netleştiremedim") and "r01) değişmedi" in k.mesaj
    assert s.k.d["asama"] == "onay_bekliyor" and s.k.d["son_soru_alani"] is None and _gecerli(s, "o")


def test_askidaki_sorunun_istegi_retten_sonra_kalmaz(s):
    """Soru askıdayken gelen istek geri çevrilirse plan, onu üreten taslağa döner: askıdaki pencere satırı sonraki revizyonda soru doğurmaz."""
    s.yaz("P6001", katalog_kodu="P6001")
    k = s.yaz("yatak odası 1'e 120x180 pencere", pencereler=[pen("yatak odası 1", "120x180", islem=None)])
    assert k.eylem == "sor" and k.soru_alani == "pencere_islem", k.mesaj
    k = s.yaz("veranda arkada olsun", varyantlar=[VERANDA])
    assert k.eylem == "yonlendir" and "r01) değişmedi" in k.mesaj
    assert not s.k.d["taslak"].get("pencereler") and s.k.d["son_soru_alani"] is None
    k = s.yaz("yatak odası 2 penceresi 120x120 olsun", pencereler=[pen("yatak odası 2", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    olcu = {a["mahal"]: a["olcu"] for a in k.is_emri["acikliklar"] if a["tur"] == "pencere" and a["mahal"].startswith("YATAK")}
    assert olcu == {"YATAK ODASI 1": "120x120", "YATAK ODASI 2": "120x120"}
