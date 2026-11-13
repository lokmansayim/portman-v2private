"""BK-29 PR-2 (pano 201, 210) · birden çok pencereli odada "Hangi pencere?", oda sorusu düğmeli, botun örnekleri yalnız yapılabilen iş.

13 Kasım 2026 WhatsApp denetimi (canlı v2026.11.13; kabul seti B2–B6, C3): iki pencereli odada bot soru sormadan yönlendiriyordu
(PA-06 "mutfak penceresi 120x120 olsun"); "salonun sol penceresi" sözündeki "sol" okunmuyordu; "Hangi odanın penceresi?" sorusuna
"Oda 1" cevabı anlaşılmıyor, soru her mesajda yineleniyordu; bot "veranda arkada olsun" örneğini gösteriyordu. LLM yok, Postgres yok,
çizim yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür, düğmeler `kanal/etkilesim.coz` ile çözülür. Katalog canlının kabul kümesiyle.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from beyin.konusma import _tekillestir  # noqa: E402
from kanal import etkilesim as ET  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen, var  # noqa: E402
from test_bk29_revizyon_reddi import KABUL, _gecerli  # noqa: E402


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


def _plan(s: Sohbet, kod: str):
    """Prefabrik plan r01: talep → öncelik → set (PA-06'da çatı seti: evin çatısı) ya da doğrudan kod."""
    k = s.yaz("Tek kat prefabrik, 2+1, 85 m²", yapi_turu="prefabrik", kat_sayisi=1, oda_programi="2+1", alan_m2=85)
    k = s.dugme("q:oncelik:butce")
    if kod in [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]]:
        k = s.dugme("s:{set}:" + kod)
        if k.eylem == "secenek":                                           # PA-06: çatı seti, evin çatısı
            k = s.dugme(k.butonlar[0]["id"])
    else:
        k = s.yaz(kod, katalog_kodu=kod)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    return k


def _pencereler(k, mahal: str) -> list[tuple[str, str]]:
    return [(a["olcu"], a.get("duvar")) for a in k.is_emri["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == mahal]


def _pv(olcu: str, aciklama: str, mahal: str | None = None) -> dict:
    prm = {"yeni": olcu}
    if mahal:
        prm["mahal"] = mahal
    return {"tur": "pencere_degistir", "aciklama": aciklama, "parametreler": prm}


def test_b2_iki_pencereli_mutfakta_hangi_pencere(s):
    """B2: PA-06 mutfakta iki pencere (120x100 sol, 160x180 ön). Bot yönlendirmez, iki düğmeyle sorar; düğme o pencereyi değiştirir."""
    _plan(s, "PA06")
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim")
    assert k.mesaj == "MUTFAK odasında 2 pencere var. Hangisini 120x120 yapalım? 1) 120x100, sol duvar; 2) 160x180, ön duvar."
    assert k.butonlar == [{"id": "q:pencere_secim:1", "baslik": "120x100 sol"}, {"id": "q:pencere_secim:2", "baslik": "160x180 ön"}]
    k = s.dugme("q:pencere_secim:1")
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x180", "on")]
    assert "kısa cevap" not in k.mesaj


def test_c3_sozdeki_duvar_ve_eski_olcu_pencereyi_secer(s):
    """C3: "Mutfağın sol duvarındaki 120x100 pencere 120x120 olsun" sorusuz r02 olur (duvar ve eski ölçü bayinin sözünden; K18)."""
    _plan(s, "PA06")
    k = s.yaz("Mutfağın sol duvarındaki 120x100 pencere 120x120 olsun", pencereler=[pen("mutfak", "120x120", duvar="sol")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x180", "on")]


def test_b3_salonun_sol_penceresi(s):
    """B3: PA-04 "salonun sol penceresi 120x180 olsun": "sol" okunur, yalnız sol pencere değişir."""
    _plan(s, "PA04")
    k = s.yaz("salonun sol penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sol")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "SALON") == [("120x180", "sol"), ("120x180", "on")]


@pytest.mark.parametrize("cevap, beklenen", [("2", [("120x100", "sol"), ("120x120", "on")]),
                                             ("öndeki", [("120x100", "sol"), ("120x120", "on")]),
                                             ("160x180 olan", [("120x100", "sol"), ("120x120", "on")]),
                                             ("ikisi de", [("120x120", "sol"), ("120x120", "on")])])
def test_hangi_pencere_yazili_cevap(s, cevap, beklenen):
    """Yazılı cevap: numara, duvar, eski ölçü, "ikisi de"; LLM'in bu kısa cevaba verdiği içerik yok sayılır."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    k = s.yaz(cevap, niyet="diger", pencereler=[pen("salon", "60x40")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "MUTFAK") == beklenen and ("60x40", "sag") not in _pencereler(k, "SALON")


def test_hangi_pencere_anlasilmayan_cevap_yinelenir_hicbiri_plani_acik_tutar(s):
    """Kısa ama anlaşılmayan cevap soruyu yineler; "hiçbiri" planı değiştirmez, revizyon hakkı harcanmaz, plan onaylanabilir kalır."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    k = s.yaz("hangisi daha iyi", niyet="soru")
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and k.mesaj.startswith("Anlayamadım. MUTFAK odasında 2 pencere var.")
    k = s.yaz("hiçbiri", niyet="red")
    no = s.plan["is_emri_no"]
    assert k.eylem == "cevapla" and k.gerekce == K.PLAN_DEGISMEDI
    assert k.mesaj == (f"Tamam, o pencereyi değiştirmedim. Planınız ({no} r01) değişmedi. "
                       "Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")
    assert s.plan["revizyon"] == 1 and s.k.d["asama"] == "onay_bekliyor" and not s.k.d["taslak"].get("pencereler") and _gecerli(s, "o")
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2


def test_ayni_odanin_oteki_penceresi_onceki_revizyonu_bozmaz(s):
    """r02'de mutfağın sol penceresi, r03'te ön penceresi değişir: r03'te ikisi de yeni ölçüde (aynı odanın eski satırı düşmez)."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert s.dugme("q:pencere_secim:1").revizyon == 2
    k = s.yaz("mutfak ön penceresi 160x120 olsun", pencereler=[pen("mutfak", "160x120", duvar="on")])
    assert k.eylem == "is_emri" and k.revizyon == 3, k.mesaj
    assert _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x120", "on")]
    k = s.yaz("mutfağın sol penceresi 120x180 olsun", pencereler=[pen("mutfak", "120x180", duvar="sol")])
    assert k.revizyon == 4 and _pencereler(k, "MUTFAK") == [("120x180", "sol"), ("160x120", "on")]
    assert len([p for p in s.k.d["taslak"]["pencereler"] if p["mahal"] == "mutfak"]) == 2     # sol pencerenin eski satırı düştü


def test_hangi_pencere_cevapsiz_yeni_istek(s):
    """Soru askıdayken başka bir istek gelirse askıdaki pencere düşer ve bayiye söylenir; aynı odanın penceresini yeniden yazmak söylenmez."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.mesaj.startswith("Önceki pencere sorumu cevaplamadığınız için")
    assert _pencereler(k, "MUTFAK") == [("120x100", "sol"), ("160x180", "on")]
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    k = s.yaz("mutfağın sol penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120", duvar="sol")])
    assert k.eylem == "is_emri" and k.revizyon == 3 and not k.mesaj.startswith("Önceki pencere sorumu")


def test_belirsiz_soz_once_degistir_mi_ekle_mi(s):
    """İki pencereli odada fiilsiz söz ("mutfak 120x120"): önce "değiştir mi, ekle mi?"; "değiştir" → "Hangi pencere?"."""
    _plan(s, "PA06")
    k = s.yaz("mutfak 120x120", pencereler=[pen("mutfak", "120x120", islem=None)])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_islem") and k.mesaj.startswith("MUTFAK odasında 2 pencere var (120x100, 160x180).")
    k = s.dugme("q:pencere_islem:degistir")
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim")
    assert s.dugme("q:pencere_secim:2").revizyon == 2


def test_b5_oda_sorusu_dugmeli_ve_yazili_cevap(s):
    """B5: PA-03 "pencere 120x120 olsun" → oda sorusu, her odaya bir düğme (4 oda: liste); "Oda 1" yazısı ve düğme kabul edilir."""
    _plan(s, "PA03")
    k = s.yaz("pencere 120x120 olsun", varyantlar=[_pv("120x120", "pencere 120x120 olsun")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_mahal")
    assert k.mesaj == "Hangi odanın penceresini 120x120 yapalım? Seçenekler: ODA 1, BANYO, ODA 2, SALON+MUTFAK."
    assert [b["baslik"] for b in k.butonlar] == ["ODA 1", "BANYO", "ODA 2", "SALON+MUTFAK"]
    assert [b["id"] for b in k.butonlar] == [f"q:pencere_mahal:{i}" for i in range(1, 5)]
    k = s.yaz("Oda 1", niyet="diger")
    # D-86 (BK-29 tur 5; Lokman 13 Kasım 21:36 kartı): ODA 1 penceresi PA-03'te zaten 120x120; aynı plan yeni numarayla gitmez.
    # Önceki beklenen: is_emri, r02, gerekçede "ODA 1 penceresi 120x120". Oda cevabının alındığı yine sınanır (soru yinelenmez).
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 1, k.mesaj
    assert "değişmedi; ODA 1 penceresi zaten 120x120." in k.mesaj


def test_oda_sorusu_dugmesi_ve_yalniz_numara(s):
    """Düğme "seçenek 3" → ODA 2; yalnız "2" yazmak oda adındaki numarayla karışır: soru yinelenir (K21)."""
    _plan(s, "PA03")
    s.yaz("pencere 120x180 olsun", varyantlar=[_pv("120x180", "pencere 120x180 olsun")])
    k = s.yaz("2", niyet="diger")
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_mahal") and k.mesaj.startswith("Anlayamadım. Hangi odanın")
    k = s.dugme("q:pencere_mahal:3")
    assert k.eylem == "is_emri" and _pencereler(k, "ODA 2") == [("120x180", "sag")] and _pencereler(k, "ODA 1") == [("120x120", "sol")]


def test_oda_sorusu_birden_cok_eslesen_oda(s):
    """"yatak odası penceresi" iki odaya uyar: yalnız o iki oda sorulur (iki düğme)."""
    _plan(s, "PA04")
    k = s.yaz("yatak odası penceresi 120x180 olsun", varyantlar=[_pv("120x180", "yatak odası penceresi 120x180 olsun", mahal="yatak odası")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_mahal")
    assert [b["baslik"] for b in k.butonlar] == ["YATAK ODASI 1", "YATAK ODASI 2"]
    k = s.dugme("q:pencere_mahal:2")
    assert k.eylem == "is_emri" and _pencereler(k, "YATAK ODASI 2") == [("120x180", "sag")]


def test_oda_sorusu_cevapsiz_kalinca_yinelenmez(s):
    """13 Kasım: oda sorusu cevaplanmadan gelen başka istekten sonra aynı soru her mesajda yineleniyordu; artık bekleyen pencere düşer.
    P6001'de denenir: prefabrik setteki evlerde aynalama yok (pano 198)."""
    s.yaz("P6001", katalog_kodu="P6001")
    s.yaz("pencere 120x120 olsun", varyantlar=[_pv("120x120", "pencere 120x120 olsun")])
    assert s.k.d["pencere_mahal_sorusu"]
    k = s.yaz("aynalı olsun", varyantlar=[var("ayna_x", "aynalı olsun")])
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and k.mesaj.startswith("Önceki pencere değişikliğini netleştirmediğiniz için")
    assert "pencere_mahal_sorusu" not in s.k.d
    assert not any(v.get("tur") == "pencere_degistir" for v in s.k.d["taslak"].get("varyantlar") or [])


def test_onceki_revizyonun_odasi_yeni_olcuyu_dusurmez(s):
    """r02 satırla "yatak odası 1 120x180", r03'te aynı oda varyantla "60x40" gelir: yeni ölçü uygulanır (sessizce düşmüyordu değil)."""
    s.yaz("P6001", katalog_kodu="P6001")
    assert s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")]).revizyon == 2
    k = s.yaz("yatak odası 1 penceresi 120x50 olsun", varyantlar=[_pv("120x50", "yatak odası 1 penceresi 120x50 olsun", mahal="yatak odası 1")])
    assert k.eylem == "is_emri" and k.revizyon == 3 and _pencereler(k, "YATAK ODASI 1") == [("120x50", "sag")], k.mesaj


def test_revize_et_yalniz_yapilabilen_ornek(s):
    """Pano 210: "Revize et" cevabı kapı, veranda, oda yerleşimi saymaz; prefabrikte pencere örneği, çelikte çelik örnekleri."""
    _plan(s, "PA04")
    k = s.dugme(f"r:{s.plan['is_emri_no']}:1")
    assert k.mesaj == "Anladım. Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120 olsun\")."
    c = Sohbet(s.k.path.parent / "celik", kabul=KABUL)
    c.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik")
    k = c.dugme(f"r:{c.plan['is_emri_no']}:1")
    assert k.mesaj == "Anladım. " + K._NEYI_DEGISTIRELIM and "veranda" not in k.mesaj


def test_pencere_kimligi_secilen_pencereyi_ayirir():
    """Taslakta aynı odanın iki seçilmiş penceresi ayrı satırdır; aynı pencere yeniden seçilince son söz geçerli."""
    a = {"mahal": "mutfak", "islem": "degistir", "duvar": None, "olcu": "120x120", "pencere_sira": [0]}
    b = {"mahal": "mutfak", "islem": "degistir", "duvar": None, "olcu": "160x120", "pencere_sira": [1]}
    c = {"mahal": "mutfak", "islem": "degistir", "duvar": None, "olcu": "120x180", "pencere_sira": [0]}
    assert _tekillestir([a, b], "pencereler") == [a, b]
    assert _tekillestir([a, b, c], "pencereler") == [c, b]
    eski = {"mahal": "mutfak", "islem": "degistir", "duvar": None, "olcu": "120x120"}
    assert _tekillestir([eski, {**eski, "olcu": "60x40"}], "pencereler") == [{**eski, "olcu": "60x40"}]       # seçimsiz satır: bugünkü gibi


def test_kisa_cevap_dugmeleri_cozulur():
    """q:pencere_mahal:<n> → "seçenek <n>", q:pencere_secim:<n> → "<n>"; soru askıda değilse düğme geçmez."""
    e = ET.coz({"reply_id": "q:pencere_mahal:4", "type": "interactive"}, {"son_soru_alani": "pencere_mahal"})
    assert e["gecerli"] and e["metin"] == "seçenek 4"
    e = ET.coz({"reply_id": "q:pencere_secim:2", "type": "interactive"}, {"son_soru_alani": "pencere_secim"})
    assert e["gecerli"] and e["metin"] == "2"
    assert ET.coz({"reply_id": "q:pencere_secim:0", "type": "interactive"}, {"son_soru_alani": "pencere_secim"})["metin"] == "hiçbiri"
    assert not ET.coz({"reply_id": "q:pencere_secim:2", "type": "interactive"}, {"son_soru_alani": None})["gecerli"]


# ─── geometri hakemi (13 Kasım 2026, kapanış incelemesi): bulgular 1–5 ───
def test_hakem1_llm_ekle_dedi_secilen_pencere_degistirmedir(s):
    """LLM "ekle" yazsa da soru değiştirme sözünden doğdu: düğme r02 verir, sonraki revizyon yönlendirilmez (önce ikisi de ret oluyordu)."""
    _plan(s, "PA06")
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120", islem="ekle")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim")
    k = s.dugme("q:pencere_secim:1")
    assert k.eylem == "is_emri" and k.revizyon == 2 and _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x180", "on")]
    k = s.yaz("Mutfağın sol duvarındaki 120x120 pencere 120x180 olsun", pencereler=[pen("mutfak", "120x180", islem="ekle", duvar="sol")])
    assert k.eylem == "is_emri" and k.revizyon == 3
    k = s.yaz("ikinci yatak odasının penceresi 120x180 olsun", pencereler=[pen("yatak odası 2", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 4 and _pencereler(k, "MUTFAK") == [("120x180", "sol"), ("160x180", "on")]


def test_hakem2_ortusen_secimde_son_soz_gecerli(s):
    """r03 "ikisi de" (iki pencere), r04 yalnız ön pencere: r05'te ön pencere r04'teki ölçüde kalır (r03'ün ölçüsüne dönüyordu)."""
    _plan(s, "PA06")
    assert s.yaz("mutfağın ön penceresi 120x100 olsun", pencereler=[pen("mutfak", "120x100", duvar="on")]).revizyon == 2
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert _pencereler(s.yaz("ikisi de", niyet="diger"), "MUTFAK") == [("120x120", "sol"), ("120x120", "on")]
    k = s.yaz("mutfağın ön penceresi 160x180 olsun", pencereler=[pen("mutfak", "160x180", duvar="on")])
    assert k.revizyon == 4 and _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x180", "on")]
    k = s.yaz("salonun sağ penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sag")])
    assert k.revizyon == 5 and _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("160x180", "on")]
    assert sorted(p["pencere_sira"] for p in s.k.d["taslak"]["pencereler"] if p["mahal"] == "mutfak") == [[0], [1]]


@pytest.mark.parametrize("metin, satirlar", [
    ("Salonun ön penceresi 120x180 olsun, mutfak penceresi de 120x180 olsun", [pen("salon", "120x180", duvar="on"), pen("mutfak", "120x180")]),
    ("Mutfak penceresi 120x120 olsun, salonun sağ penceresi de 120x120 olsun", [pen("mutfak", "120x120"), pen("salon", "120x120", duvar="sag")])])
def test_hakem3_baska_odanin_sozu_okunmaz(s, metin, satirlar):
    """Mutfağın cümlesinde duvar yok: salonun cümlesindeki "ön"/"sağ" mutfak penceresini seçmez, bot sorar."""
    _plan(s, "PA06")
    k = s.yaz(metin, pencereler=satirlar)
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and k.mesaj.startswith("MUTFAK odasında 2 pencere var.")


def test_hakem4_on_onay_on_duvar_degildir(s):
    """"Ön onay planında …": "ön" botun terimi, duvar değil; mutfağın ön penceresi sorusuz değişmez."""
    _plan(s, "PA06")
    k = s.yaz("Ön onay planında mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim")
    assert K._duvarlar_metin("Ön onay planında mutfak penceresi 120x120 olsun") == set()
    assert K._duvarlar_metin("mutfağın öndeki penceresi 120x120 olsun") == {"on"}


def test_hakem5_ayni_olcu_ayni_duvar_tekil_sozle_sorulur(s):
    """PA-02 SALON+MUTFAK: arkada 2 adet 120x120. "arka penceresi" (tekil) ikisini birden sorusuz değiştirmez; düğme ikisini, "Hiçbiri"
    hiçbirini; çoğul söz ("arka pencereleri") sormadan ikisini değiştirir."""
    _plan(s, "PA02")
    k = s.yaz("salonun arka penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="arka")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim")
    assert k.mesaj == "SALON+MUTFAK odasının arka duvarında 2 adet 120x120 pencere var. İkisini de 120x180 yapalım mı?"
    assert k.butonlar == [{"id": "q:pencere_secim:1", "baslik": "İkisi de"}, {"id": "q:pencere_secim:0", "baslik": "Hiçbiri"}]
    k = s.dugme("q:pencere_secim:0")
    assert k.eylem == "cevapla" and k.gerekce == K.PLAN_DEGISMEDI and s.plan["revizyon"] == 1
    s.yaz("salonun arka penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="arka")])
    k = s.yaz("evet", niyet="onay")
    assert k.eylem == "is_emri" and k.revizyon == 2
    assert sorted(o for o, d in _pencereler(k, "SALON+MUTFAK") if d == "arka") == ["120x180", "120x180"]
    k = s.yaz("salonun arka pencereleri 160x120 olsun", pencereler=[pen("salon", "160x120", duvar="arka")])
    assert k.eylem == "is_emri" and k.revizyon == 3
    assert sorted(o for o, d in _pencereler(k, "SALON+MUTFAK") if d == "arka") == ["160x120", "160x120"]


# ─── geometri hakemi ikinci tur (13 Kasım 2026): tekil kısıt, yalın onay, iki odalı cümle ───
@pytest.mark.parametrize("metin", ["Salonun arka pencerelerinden biri 120x180 olsun", "Salonun arkadaki ikisinden biri 120x180 olsun",
                                   "Salonun arka penceresi 120x180 olsun diğer pencereler kalsın"])
def test_hakem2_1_tekil_kisit_cogul_sayilmaz(s, metin):
    """"biri", "diğer pencereler kalsın": aynı duvardaki iki pencere sorusuz birlikte değişmez."""
    _plan(s, "PA02")
    k = s.yaz(metin, pencereler=[pen("salon", "120x180", duvar="arka")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and "İkisini de 120x180 yapalım mı?" in k.mesaj


@pytest.mark.parametrize("cevap", ["olur mu", "olur mu?", "tamam onaylıyorum", "tek kanat olsun", "Onaylıyorum, diğer her şey kalsın"])
def test_hakem2_2_onay_sorusuna_soru_bicimli_cevap_onay_degil(s, cevap):
    """"İkisini de … yapalım mı?" sorusuna soru biçimli ya da fazla sözlü cevap onay değildir: soru yinelenir, plan değişmez."""
    _plan(s, "PA02")
    s.yaz("salonun arka penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="arka")])
    k = s.yaz(cevap, niyet="diger")
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and k.mesaj.startswith("Anlayamadım.") and s.plan["revizyon"] == 1


@pytest.mark.parametrize("cevap", ["evet sadece biri", "tamam ama sadece birini", "biri yeter", "bir tane", "1 tane", "ilki"])
def test_hakem2_2_yalniz_biri_istenirse_yonlendirilir_plan_acik(s, cevap):
    """"Sadece biri": iki aynı pencereden birini kod seçemez; soru döngüye girmez, istek Lokman Bey'e gider, plan açık kalır (BK-29 PR-1)."""
    _plan(s, "PA02")
    s.yaz("salonun arka penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="arka")])
    k = s.yaz(cevap, niyet="diger")
    no = s.plan["is_emri_no"]
    assert k.eylem == "yonlendir" and k.mesaj.startswith("Aynı duvardaki aynı ölçülü pencerelerden yalnız birini otomatik seçemiyorum.")
    assert k.mesaj.endswith(f"Planınız ({no} r01) değişmedi. Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")
    assert s.plan["revizyon"] == 1 and s.k.d["asama"] == "onay_bekliyor" and _gecerli(s, "o")


@pytest.mark.parametrize("cevap", ["evet", "ikisi de", "olur", "1"])
def test_hakem2_2_yalin_onay_ikisini_degistirir(s, cevap):
    _plan(s, "PA02")
    s.yaz("salonun arka penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="arka")])
    k = s.yaz(cevap, niyet="diger")
    assert k.eylem == "is_emri" and sorted(o for o, d in _pencereler(k, "SALON+MUTFAK") if d == "arka") == ["120x180", "120x180"]


def test_hakem2_3_tek_cumlede_iki_oda(s):
    """"Salonun ön penceresi ile mutfak penceresi 120x180 olsun": "ön" salonun; mutfakta soru gelir (mutfağın ön penceresi değişmiyordu)."""
    _plan(s, "PA06")
    k = s.yaz("Salonun ön penceresi ile mutfak penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="on"), pen("mutfak", "120x180")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and k.mesaj.startswith("MUTFAK odasında 2 pencere var.")
    assert K._oda_parcasi("Salonun ön penceresi ile mutfak penceresi 120x180 olsun", "SALON", ["MUTFAK"]) == "Salonun ön penceresi"


# ─── geometri hakemi üçüncü tur (13 Kasım 2026) ───
@pytest.mark.parametrize("metin", ["Mutfak penceresi ile öndeki salon penceresi 120x180 olsun",
                                   "Mutfak ve ön cephedeki salon penceresi 120x180 olsun"])
def test_hakem3_2_oteki_odanin_sifati_bu_odaya_okunmaz(s, metin):
    """Öteki odanın adından önceki sıfat ("öndeki salon") mutfağın ön penceresini seçmez: önce mutfak sorulur."""
    _plan(s, "PA06")
    k = s.yaz(metin, pencereler=[pen("mutfak", "120x180"), pen("salon", "120x180", duvar="on")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_secim") and k.mesaj.startswith("MUTFAK odasında 2 pencere var.")
    assert K._oda_parcasi(metin, "MUTFAK", ["SALON"]) in ("Mutfak penceresi", "Mutfak")
    assert K._oda_parcasi("Mutfak penceresi öndeki salon penceresi 120x180 olsun", "MUTFAK", ["SALON"]) == "Mutfak"   # bağlaçsız: ayrılamaz


# ─── geometri hakemi dördüncü tur (13 Kasım 2026) ───
def test_hakem4_oda_icindeki_ve_bolunmez(s):
    """"Mutfağın sol ve ön pencereleri ile salonun sağ penceresi 120x180 olsun": mutfağın iki penceresi de, salonun sağ penceresi de 120x180
    (önce yalnız "sol" okunuyor, ön pencere sessizce eski ölçüde kalıyordu)."""
    _plan(s, "PA06")
    metin = "Mutfağın sol ve ön pencereleri ile salonun sağ penceresi 120x180 olsun"
    assert K._oda_parcasi(metin, "MUTFAK", ["SALON"]) == "Mutfağın sol ve ön pencereleri"
    k = s.yaz(metin, pencereler=[pen("mutfak", "120x180"), pen("salon", "120x180", duvar="sag")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "MUTFAK") == [("120x180", "sol"), ("120x180", "on")]
    assert _pencereler(k, "SALON") == [("120x180", "sag"), ("120x160", "on")]


def test_hakem4_coğul_soz_odanin_butun_pencereleri(s):
    """"mutfak pencereleri 120x120 olsun" (çoğul, kısıtsız): mutfağın iki penceresi de değişir; tekil söz sorar (B2)."""
    _plan(s, "PA06")
    k = s.yaz("mutfak pencereleri 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and _pencereler(k, "MUTFAK") == [("120x120", "sol"), ("120x120", "on")]
