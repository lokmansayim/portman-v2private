"""İE-09 · Model atölyesi (D-20): `araclar/atolye.py` adımları geçici bir bankada (deneme modeli Ç8801Z, Ç8801'in çatı varyantı; metraj
kapısı için KT99, çelik hakeminin açık projesi ÇP-14'ün tanımı), bankanın Katalog / aday kabulüne birleşmesi (İE-14 uyarlamasına girmez,
İE-09 PR-1), kod çakışması, kör test engeli, çelik hakeminden okunan metraj kapısı ve pim, gün sonu sayımı.

Gerçek banka (`modeller/banka/`) ve kusur defteri değişmez: araç `--banka` ile geçici köke, defter geçici dosyaya yönlendirilir. Kabul
kapısı (harness + pytest) burada koşmaz (`--kapisiz`, iç içe pytest olmasın); tam izler de koşmaz (`--izsiz`; `test_banka.py` sınar)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import atolye as A  # noqa: E402
from beyin import banka as B  # noqa: E402

CATI_D = json.loads((KOK / "modeller" / "banka" / "C8801D" / "tanim.json").read_text(encoding="utf-8"))["cati"]
CATI_K = json.loads((KOK / "modeller" / "C8801K.json").read_text(encoding="utf-8"))["cati"]
CEKIRDEK = {a["kod"]: a for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8"))}


def kos(banka: Path, *argv) -> int:
    return A.main(["--banka", str(banka), *[str(x) for x in argv]])


@pytest.fixture(scope="module")
def atolye(tmp_path_factory):
    """Geçici depo kökü: <kök>/modeller/banka (banka), <kök>/is_emri (aday görselinin göreli yolu için), çizim çıktısı ayrı."""
    kok = tmp_path_factory.mktemp("atolye")
    (kok / "is_emri").mkdir()
    banka = kok / "modeller" / "banka"
    banka.mkdir(parents=True)
    cati = kok / "cati.json"
    cati.write_text(json.dumps(CATI_D, ensure_ascii=False), encoding="utf-8")
    defter = kok / "kusurlar.md"
    eski = A.KUSUR_DEFTERI
    A.KUSUR_DEFTERI = defter
    try:
        assert kos(banka, "varyant", "Ç8801Z", "--taban", "Ç8801", "--cati", cati, "--ad", "Deneme (Ç8801 çatı varyantı Z)",
                   "--kaynak-metni", "atölye testi") == 0
        assert kos(banka, "ciz", "Ç8801Z", "--cikti", kok / "cikti") == 0
        yield {"kok": kok, "banka": banka, "cati": cati, "defter": defter, "cikti": kok / "cikti"}
    finally:
        A.KUSUR_DEFTERI = eski


def kart(ctx) -> dict:
    return json.loads((ctx["banka"] / "C8801Z" / "kart.json").read_text(encoding="utf-8"))


def test_kor_test_seti_acilmaz(tmp_path):
    assert "kör test" in A.kor_test_engeli(Path("/Users/x/Desktop/AIPrefabrik/AP-06 proje/yukleme listesi.xlsx"))
    assert "kör test" in A.kor_test_engeli(Path("liste.xlsx"), proje="AP-28")
    assert A.kor_test_engeli(Path("/Users/x/Desktop/AIPrefabrik/proje/liste.xlsx")) is not None          # kod okunamazsa da açılmaz
    assert A.kor_test_engeli(Path("/Users/x/Desktop/AIPrefabrik/AP-07/yukleme.xlsx")) is None             # açılmış liste (TS-01)
    assert A.kor_test_engeli(Path("/Users/x/Desktop/AIPrefabrik/AP-06/montaj paftasi.pdf")) is None       # pafta liste değil
    assert A.kor_test_engeli(Path("/Users/x/muhendis/C9001 liste.xlsx")) is None                           # AIPrefabrik dışı
    banka = tmp_path / "modeller" / "banka"
    excel = tmp_path / "AP-12 yukleme listesi.xlsx"
    excel.write_bytes(b"okunmaz")
    assert kos(banka, "ac", "Ç9901", "--ad", "deneme", "--kaynak-dosya", excel) == 2 and not (banka / "C9901").exists()
    # çelik hattının proje kodu kartın kaynağına yazılır ama kör test engeline girmez (engel yalnız AIPrefabrik'in AP kodları)
    assert A.kaynak_proje_kodu("ÇP-14") == A.kaynak_proje_kodu("cp14") == "ÇP-14" and A.kaynak_proje_kodu("AP-7") == "AP-07"
    assert A.proje_kodu("ÇP-14") is None and A.kaynak_proje_kodu("KT04") is None
    assert A.kor_test_engeli(Path("liste.xlsx"), proje="ÇP-14") is None


def test_kod_cakismasi_ve_ayni_cati(atolye, tmp_path):
    assert kos(atolye["banka"], "ac", "Ç8801K", "--ad", "çekirdekte var") == 2
    assert kos(atolye["banka"], "ac", "Ç8801Z", "--ad", "atölyede var") == 2
    cati_k = tmp_path / "k.json"
    cati_k.write_text(json.dumps(CATI_K, ensure_ascii=False), encoding="utf-8")
    assert kos(atolye["banka"], "varyant", "Ç8801Y", "--taban", "Ç8801", "--cati", cati_k, "--ad", "K'nın aynısı") == 2   # bu çatı bankada var
    assert kos(atolye["banka"], "varyant", "Ç8801Y", "--taban", "Ç8801K", "--cati", atolye["cati"], "--ad", "varyantın varyantı") == 2


def test_varyant_taban_tanimi_degistirmez_ve_kart_dolu(atolye):
    t = json.loads((atolye["banka"] / "C8801Z" / "tanim.json").read_text(encoding="utf-8"))
    taban = json.loads((KOK / "modeller" / "C8801.json").read_text(encoding="utf-8"))
    assert {k for k in taban if t.get(k) != taban.get(k)} == {"kod", "ad", "kaynak", "cati"}
    k = kart(atolye)
    assert k["sema"] == B.KART_SEMASI and k["durum"] == "kontrolde" and k["taban_model"] == "Ç8801" and k["gosterim"] == "Ç8801-Z"
    assert k["kaynak"]["taban_sha256"] == A.sha256(KOK / "modeller" / "C8801.json")
    assert k["metraj_testi"]["durum"] == "yok" and "koşulmadı" in k["metraj_testi"]["not"]
    dn = {d["ad"]: d for d in k["son_cizim"]["denetimler"]}
    assert dn["Motor doğrulaması"]["durum"] == "geçti" and dn["IFC şema denetimi"]["durum"] == "geçti"
    assert dn["Kartla çizimin tutarlılığı (m², oda programı, açıklık, çatı)"]["durum"] == "geçti"      # taban kaydıyla aynı plan
    assert dn["Bankada aynı model"]["durum"] == "geçti" and "Ç8801K" in dn["Bankada aynı model"]["ayrinti"]
    assert (Path(k["son_cizim"]["kontrol_pdf"]) if Path(k["son_cizim"]["kontrol_pdf"]).is_absolute() else KOK / k["son_cizim"]["kontrol_pdf"]).is_file()


def test_kontrol_sayfasi(atolye):
    import pymupdf
    k = kart(atolye)
    pdf = Path(k["son_cizim"]["kontrol_pdf"])
    with pymupdf.open(pdf if pdf.is_absolute() else KOK / pdf) as d:
        assert d.page_count == 5                                            # özet, çizim seti, bayi paftası (2), bayi görseli
        metin = d[0].get_text()
    # sayfa teknik kalır (Lokman, 30 Ekim 12:56: "teknik hali kalsın ... bayiye gitmeyecek"; 08:12'deki sade sayfa denendi, geri alındı)
    for s in ("Ç8801-Z", "Oda tablosu", "Yaşam Alanı", "21,34", "bankada Ç8801 kaydı", "Metraj kapısı: referans yok, koşulmadı", "kabul"):
        assert s in metin, s


def test_pimsiz_kart_kontrolun_setiyle_cizilir(atolye):
    # pimsiz kart kontrol dosyasının donacağı setle (dondurulmuş setlerin en yenisi) çizilir: Lokman'ın onayladığı çizim ile dondurulan
    # kontrol aynı kural setinden (D-28 madde 2; geometri hakemi, 30 Ekim)
    sc = kart(atolye)["son_cizim"]
    assert sc["kural_seti"] == A.pim_seti().name == "0.19.json" and sc["kural_seti_sha256"] == A.sha256(A.pim_seti())
    assert sc["karkas_sha256"] is None and sc["metraj_izi"] == A.metraj_izi(kart(atolye)["metraj_testi"])   # Ç8801 karkas kuralı istemez
    t = {"karkas": "kural"}                                                                             # isteyen pimsiz tanım bugünkü kuralla pimlenir
    from motor.genel import karkas
    assert A.cizim_kurallari({"pim": None}, t) == (A.pim_seti(), karkas.KURAL) and A.cizim_kurallari({}, {})[1] is None


def test_liste_ozeti_celik_kg_motorun_saglama_satirindan():
    # çelik kg'ı motor üretir, atölye okur (D-28 madde 1); sağlama satırı grubun kg toplamına girmez
    satirlar = [{"grup": A.CELIK_GRUBU, "kalem": "Duvar paneli", "kg": 100.0}, {"grup": A.CELIK_GRUBU, "kalem": "Makas", "kg": 50.0},
                {"grup": A.CELIK_GRUBU, "kalem": A.TOPLAM_SATIRI, "kg": 149.5}, {"grup": "Dış cephe", "kalem": "Taş yünü", "kg": 10.0}]
    o = A.liste_ozeti({"satirlar": satirlar})
    assert o["celik_kg"] == 149.5 and o["gruplar"][A.CELIK_GRUBU] == {"satir": 3, "kg": 149.5} and o["gruplar"]["Dış cephe"]["kg"] == 10.0
    assert A.liste_ozeti({"satirlar": satirlar[3:]})["celik_kg"] == 0


def test_metraj_kapisi_hakem_olcumu_olmayan_modelde_kosulmaz(atolye):
    # Ç8801Z'nin çelik hakemi ölçümü yok: başka projenin ölçümü ona yazılamaz (tanım hakemin ölçtüğü tanım değil); kart değişmez
    once = kart(atolye)
    assert kos(atolye["banka"], "metraj", "Ç8801Z", "--celik", "ÇP-14") == 2
    assert kos(atolye["banka"], "metraj", "Ç8801Z", "--celik", "ÇP-99") == 2                              # hakemde böyle proje yok
    assert kart(atolye) == once and once["metraj_testi"]["durum"] == "yok" and once["durum"] == "kontrolde"


def test_kabul_banka_kaydi_ve_kontrol(atolye):
    banka = atolye["banka"]
    t_yol = banka / "C8801Z" / "tanim.json"
    asil = t_yol.read_text(encoding="utf-8")
    t_yol.write_text(asil.replace('"Deneme (Ç8801 çatı varyantı Z)"', '"Deneme Z (değişti)"'), encoding="utf-8")
    assert kos(banka, "kabul", "Ç8801Z", "--kapisiz", "--izsiz") == 2                                    # tanım son çizimden sonra değişti
    t_yol.write_text(asil, encoding="utf-8")
    assert kos(banka, "kabul", "Ç8801Z", "--kapisiz", "--izsiz", "--tarih", "2026-10-17") == 0
    k = kart(atolye)
    assert k["durum"] == "kabul" and k["kabul"]["karar"] == "D-11" and k["kabul"]["metraj_kapisi"] == "yok"
    assert B.denetle(banka) == []
    kayit = B.kayitlar(banka)
    assert [x["kod"] for x in kayit] == ["Ç8801Z"] and kayit[0]["banka"] is True and kayit[0]["taban_model"] == "Ç8801"
    a = kayit[0]
    assert a["tanim"] == "modeller/banka/C8801Z/tanim.json" and a["gorsel"] == "../modeller/banka/C8801Z/kart.png"
    assert (banka / "C8801Z" / "kart.png").is_file() and (banka / "C8801Z" / "kontrol.json").is_file()
    # aday kaydı aday_kaydet.genel ile aynı alanları taşır; aynı plan olduğu için alanlar ve oda tablosu Ç8801 kaydıyla aynı
    c = CEKIRDEK["Ç8801"]
    assert set(k["aday"]) == set(c)
    for alan in ("katalog_m2", "kapali_m2", "veranda_m2", "oda_programi", "kat", "yapi_turu", "motor", "durum"):
        assert a[alan] == c[alan], alan
    for alan in ("odalar", "pencere", "kapi", "dis_olcu_cm", "oturum_m2"):
        assert a["ozet"][alan] == c["ozet"][alan], alan
    assert a["referans_model"] == "Ç8801" and a["varyantlar"] == [] and a["sunum"]["cati_adi"] == "Tam kırma"
    # kabul donar: kontrol hızlı yoldan aynı; tanım değişirse kontrol düşer; düzeltme ve yeniden çizim reddedilir
    assert kos(banka, "kontrol") == 0
    t_yol.write_text(asil.replace('"Deneme (Ç8801 çatı varyantı Z)"', '"Deneme Z (değişti)"'), encoding="utf-8")
    try:
        assert kos(banka, "kontrol") == 1 and B.kayitlar(banka) == [] and len(B.denetle(banka)) == 1
    finally:
        t_yol.write_text(asil, encoding="utf-8")
    assert kos(banka, "duzelt", "Ç8801Z", "--tur", "tercih", "--metin", "x") == 2 and kos(banka, "ciz", "Ç8801Z") == 2
    assert kos(banka, "ret", "Ç8801Z", "--neden", "x") == 2


def test_dondur_ve_tam_kontrol(atolye):
    # yeniden dondurma gerekçe ve var olan bir kararla (D-02); tam izler (sabit zaman, perspektifsiz, pim 0.19) iki koşuda aynı
    banka = atolye["banka"]
    assert kos(banka, "dondur", "Ç8801Z", "--gerekce", "", "--karar", "D-02") == 2
    assert kos(banka, "dondur", "Ç8801Z", "--gerekce", "deneme", "--karar", "D-99") == 2
    assert kos(banka, "dondur", "Ç8801Z", "--gerekce", "deneme", "--karar", "D-02") == 0
    k = json.loads((banka / "C8801Z" / "kontrol.json").read_text(encoding="utf-8"))
    assert k["kural_seti"] == "kurallar/liste/setler/0.19.json" and k["dondurma"]["karar"] == "D-02"
    assert {"C8801Z_pafta.pdf", "C8801Z_plan.png", "C8801Z.ifc", "C8801Z_yukleme.json", "C8801Z_cizim.dxf"} <= set(k["tam"])
    assert kos(banka, "kontrol", "--tam") == 0


def test_duzeltme_turu_ve_kusur_defteri(atolye):
    banka = atolye["banka"]
    cati = atolye["cati"]
    assert kos(banka, "varyant", "Ç8801X", "--taban", "Ç8801", "--cati", cati, "--ad", "x") == 2               # aynı çatı: Ç8801Z bankada
    t = dict(CATI_D, tip_adi="tam kırma: deneme")
    p = atolye["kok"] / "cati_x.json"
    p.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    assert kos(banka, "varyant", "Ç8801X", "--taban", "Ç8801", "--cati", p, "--ad", "x") == 0
    assert kos(banka, "duzelt", "Ç8801X", "--tur", "motor", "--metin", "eğim yazısı mahyaya biniyor") == 0
    assert "eğim yazısı mahyaya biniyor" in atolye["defter"].read_text(encoding="utf-8")
    assert kos(banka, "ret", "Ç8801X", "--neden", "deneme") == 0
    assert json.loads((banka / "C8801X" / "kart.json").read_text(encoding="utf-8"))["durum"] == "ret"


def test_gunluk_sayim(atolye, capsys):
    kos(atolye["banka"], "gunluk", "--tarih", A.bugun())
    out = capsys.readouterr().out
    assert "Açılan: " in out and "Ç8801-Z" in out and "motor 1" in out and "Kabul: " in out


# ── bankanın okuyanları (Katalog, İE-14, aday kabulü); gerçek banka yerine sahte kayıt ─────────────────────────────────────
def _sahte(kod: str, taban: str | None = None) -> dict:
    a = dict(CEKIRDEK["Ç8201"], kod=kod, gosterim=kod, varyantlar=[], referans_model=taban or kod)
    return {**a, "banka": True, "taban_model": taban}


def test_katalog_atolye_modelini_yalniz_acik_kabulle_gosterir(monkeypatch):
    from beyin.katalog import Katalog
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902"), _sahte("Ç8201V", taban="Ç8201"), _sahte("Ç8801")])
    hepsi = Katalog()
    assert "Ç9902" in hepsi.adaylar and hepsi.aday("Ç9902") is None                         # kabul kümesi yok: görünmez (harness, yerel)
    assert hepsi.adaylar["Ç8801"].get("banka") is None                                        # çekirdekle çakışan kod alınmaz
    k = Katalog(kabul_edilmis={"Ç9902", "Ç8201V", "Ç8801"})
    assert k.aday("Ç9902")["kod"] == "Ç9902" and k.aday("Ç8201V") is None                     # çatı varyantı ayrı sunulmaz
    assert {a["kod"] for a in k.gorunur_adaylar()} == {"Ç9902", "Ç8801"}


def test_plan_uretici_bankasi_atolye_modelini_almaz(monkeypatch):
    # İE-09 PR-1 (CIO, 29 Ekim): İE-14 uyarlaması atölye bankasını okumaz; canlıda `plan_uretimi` açık, K-A10 kaydı olmadan sessiz değişiklik yok
    from beyin import plan_uretici as PU
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902"), _sahte("Ç8201V", taban="Ç8201")])
    PU._banka.cache_clear()
    try:
        assert [b["kod"] for b in PU._banka()] == ["Ç8801", "Ç8201", "KT01", "KT02", "KT03"]      # yalnız çekirdek bankanın varyantsız planları
    finally:
        PU._banka.cache_clear()


def test_aday_kabul_atolye_kodunu_tanir(monkeypatch, capsys):
    from araclar import aday_kabul
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902")])
    assert aday_kabul.main(["--kodlar", "Ç9902,Ç8801", "--tarih", "2026-10-17", "--kuru"]) == 0
    assert "2 kayıt yazılacak (Ç9902, Ç8801)" in capsys.readouterr().out
    # bankanın çatı varyantı Katalog'da ayrı sunulmaz; kabul kaydı da yazılmaz (kod incelemesi, 30 Ekim)
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902"), _sahte("Ç8201V", taban="Ç8201")])
    assert aday_kabul.main(["--kodlar", "Ç9902,Ç8201V", "--tarih", "2026-10-17", "--kuru"]) == 2
    assert "çatı varyantı" in capsys.readouterr().out


# ── metraj kapısı çelik hakeminden (İE-09 PR-1, D-28 madde 1): KT99 = ÇP-14'ün tanımı, kod ve ad dışında ────────────────────
CP14 = KOK / "testler" / "celik" / "projeler" / "CP14" / "CP14.json"


@pytest.fixture(scope="module")
def hakemli(tmp_path_factory):
    kok = tmp_path_factory.mktemp("hakemli")
    (kok / "is_emri").mkdir()
    banka = kok / "modeller" / "banka"
    banka.mkdir(parents=True)
    t = json.loads(CP14.read_text(encoding="utf-8"))
    t["kod"], t["ad"] = "KT99", "Deneme (ÇP-14'ün tanımı)"
    tp = kok / "KT99.json"
    tp.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    assert kos(banka, "ac", "KT99", "--ad", t["ad"], "--tanim", tp, "--musteri-projesi", "--kaynak-metni", "atölye testi") == 0
    assert kos(banka, "kaynak", "KT99", "--kaynagi", "test", "--proje", "KT04") == 2                     # proje kodu okunamaz
    assert kos(banka, "kaynak", "KT99", "--kaynagi", "test", "--proje", "ÇP-14", "--brut-m2", "120") == 0
    assert kos(banka, "metraj", "KT99", "--celik", "ÇP-14") == 0
    assert kos(banka, "ciz", "KT99", "--cikti", kok / "cikti") == 0
    return {"kok": kok, "banka": banka, "tanim": t}


def kart99(ctx) -> dict:
    return json.loads((ctx["banka"] / "KT99" / "kart.json").read_text(encoding="utf-8"))


def test_hakem_olcumu_kapi_tur_tablosu_ve_pim(hakemli):
    k = kart99(hakemli)
    mt = k["metraj_testi"]
    sonuc = json.loads((KOK / "testler" / "celik" / "projeler" / "CP14" / "sonuc.json").read_text(encoding="utf-8"))
    assert k["durum"] == "kontrolde" and k["gosterim"] == "KT-99" and mt["kaynak"] == "celik_hakemi" and mt["proje"] == "ÇP-14"
    assert mt["durum"] == "gecti" and mt["hakem_sonucu"] == "geçti" and mt["fark_yuzde"] == sonuc["celik_kg_kapisi"]["fark_yuzde"] == 0.93
    assert mt["kapi_disi"] == ["c_profil"] and mt["yontem"]["kod"] == "omega_asik"
    assert k["kaynak"]["tur"] == "proje" and k["kaynak"]["proje"] == "ÇP-14" and k["kaynak_degerleri"]["brut_m2"]["deger"] == 120
    turler = {r["tur"]: r for r in mt["turler"]}
    assert set(turler) >= {"duvar_paneli", "kolon_kiris", "makas", "cati_paneli"} and turler["makas"]["gercek_adet"] == 26
    bizim = json.loads((KOK / "testler" / "celik" / "projeler" / "CP14" / "bizim_liste.json").read_text(encoding="utf-8"))
    assert k["pim"]["kural_seti"]["yol"] == bizim["kural_seti"]["kopya"] and k["pim"]["karkas"]["yol"] == bizim["karkas_kurali"]["kopya"]
    assert k["son_cizim"]["pim"] == k["pim"]                                                            # çizim ölçümdeki kural setiyle


def test_hakem_olcumu_tanim_farkini_ve_gecmeyen_kapiyi_yakalar(hakemli):
    t = dict(hakemli["tanim"], lento=hakemli["tanim"]["lento"] + 5)
    assert A.celik_olcumu("ÇP-14", t)[0] is None and "farklı" in A.celik_olcumu("ÇP-14", t)[1]
    olculen = json.loads((KOK / "testler" / "celik" / "projeler" / "CP06" / "bizim_liste.json").read_text(encoding="utf-8"))["tanim"]["yol"]
    t06 = dict(json.loads((KOK / olculen).read_text(encoding="utf-8")), kod="KT98", ad="x")             # hedef örneğin karkas kurallı tanımı
    o, sorun = A.celik_olcumu("ÇP-06", t06)
    assert sorun is None and o["metraj_testi"]["durum"] == "beklemede" and o["metraj_testi"]["hakem_sonucu"] == "geçmedi"   # −%12,83


def test_hakem_olcumu_git_okunamazsa_gecmez(hakemli, monkeypatch):
    # liste sonuçtan sonra değişmedi mi denetimi git'ten; git okunamazsa iki boş dizge eşit sayılmaz (geometri hakemi, 30 Ekim)
    monkeypatch.setattr(A, "_git", lambda *a: "")
    o, sorun = A.celik_olcumu("ÇP-14", hakemli["tanim"])
    assert o is None and "bugünkü listenin sonucu değil" in sorun


def test_kabul_paketi_atolye_modelini_kendi_pimiyle_cizer(hakemli, monkeypatch, tmp_path):
    # kabul paketi atölye modelini kontrol dosyasının ve onaylı çizimin kural setiyle üretir, güncel kural setiyle değil (kod incelemesi, 30 Ekim)
    pytest.importorskip("openpyxl")                                                                   # paket Excel'siz durur
    from araclar import kabul_paketi
    from motor.genel import uret as U
    cagri = {}

    def sahte_uret(tanim, hedef, **kw):
        cagri.update(kw, tanim=tanim)
        raise RuntimeError("yalnız çağrı")
    monkeypatch.setattr(U, "uret", sahte_uret)
    monkeypatch.setattr(B, "BANKA_DIR", hakemli["banka"])
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [{**_sahte("KT99"), "tanim": str(hakemli["banka"] / "KT99" / "tanim.json")}])
    with pytest.raises(RuntimeError, match="yalnız çağrı"):
        kabul_paketi.main([str(tmp_path / "paket"), "--kodlar", "KT99", "--perspektifsiz"])
    k = kart99(hakemli)
    assert cagri["set_yolu"] == KOK / k["pim"]["kural_seti"]["yol"] and cagri["karkas_yolu"] == KOK / k["pim"]["karkas"]["yol"]


def test_hakemli_kontrol_sayfasi(hakemli):
    import pymupdf
    pdf = Path(kart99(hakemli)["son_cizim"]["kontrol_pdf"])
    with pymupdf.open(pdf if pdf.is_absolute() else KOK / pdf) as d:
        metin = " ".join(d[0].get_text().split())
    for s in ("KT-99", "gerçek proje ÇP-14", "çelik hakemi", "+%0,93", "Duvar paneli", "+%6,3", "Kolon-kiriş paneli", "−%14,9", "Makas",
              "birbirini götürüyor", "panel", "brut_m2: çizim 123.78, kaynak 120.0"):
        assert s in metin, s
    assert "%-" not in metin                                                                             # işaret yüzde imisinden önce


def test_duzeltmeden_sonra_eski_metraj_tasinmaz(hakemli, tmp_path):
    # tanım ölçümden sonra değişirse (Lokman'ın düzeltmesi) eski "geçti" taşınmaz: çizimde hakemin ölçümü bugünkü kuralla yeniden
    # denetlenir, tutmazsa kart beklemede, kabul edilemez; sayfa bunu sade dille söyler (gerçek bankanın kopyasında)
    import pymupdf
    import shutil
    kopya = tmp_path / "modeller" / "banka"
    shutil.copytree(hakemli["banka"], kopya)
    (tmp_path / "is_emri").mkdir()
    tp = kopya / "KT99" / "tanim.json"
    t = json.loads(tp.read_text(encoding="utf-8"))
    for a in t["acikliklar"]:
        if a["ad"] == "K2":
            a["mentese"] = "bas" if a.get("mentese", "bas") == "son" else "son"
    tp.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    assert kos(kopya, "duzelt", "KT99", "--tur", "tercih", "--metin", "yatak odası 1 kapısı ters açılsın") == 0
    assert kos(kopya, "ciz", "KT99", "--cikti", tmp_path / "cikti") == 0
    k = json.loads((kopya / "KT99" / "kart.json").read_text(encoding="utf-8"))
    mt = k["metraj_testi"]
    assert k["durum"] == "beklemede" and mt["durum"] == "beklemede" and mt["hakem_sonucu"] is None and "farklı" in mt["neden"]
    assert kos(kopya, "kabul", "KT99", "--kapisiz", "--izsiz") == 2
    pdf = Path(k["son_cizim"]["kontrol_pdf"])
    with pymupdf.open(pdf if pdf.is_absolute() else KOK / pdf) as d:
        metin = " ".join(d[0].get_text().split())
    assert "hakemin ölçümü bu tanım için geçerli değil" in metin and "kabul edilemez" in metin and "+%0,93" not in metin


def test_ciz_metraj_kapisinin_pimiyle_cizer(hakemli, tmp_path):
    # metraj kapısı çizimden önce: hakemin ölçümü pimi değiştirirse çizim yeni pimle yapılır, son çizime o pim yazılır; kabulün "son
    # çizim kartın pimiyle mi" denetimi gerçek pimi görür (geometri hakemi, 30 Ekim)
    import shutil
    kopya = tmp_path / "modeller" / "banka"
    shutil.copytree(hakemli["banka"], kopya)
    (tmp_path / "is_emri").mkdir()
    kp = kopya / "KT99" / "kart.json"
    k = json.loads(kp.read_text(encoding="utf-8"))
    k["pim"], k["metraj_testi"]["tanim_kanonik"] = None, "eski"                                       # pimsiz, ölçüm eski tanımdan
    kp.write_text(json.dumps(k, ensure_ascii=False), encoding="utf-8")
    assert kos(kopya, "ciz", "KT99", "--cikti", tmp_path / "cikti") == 0
    k = json.loads(kp.read_text(encoding="utf-8"))
    pim = k["pim"]["kural_seti"]
    assert k["metraj_testi"]["durum"] == "gecti" and k["son_cizim"]["pim"] == k["pim"]
    assert k["son_cizim"]["kural_seti"] == Path(pim["yol"]).name and k["son_cizim"]["kural_seti_sha256"] == pim["sha256"]


def test_hakemli_kabul_pim_ve_kontrol(hakemli, tmp_path, capsys):
    import shutil
    banka = hakemli["banka"]
    # kabulü durduran her denetim kendi nedeniyle: beklemede, başka pim ya da setle çizim, hakemin bugünkü sonucu, sayfadaki metraj kaydı
    # (gerçek bankanın kopyasında)
    kopya = tmp_path / "modeller" / "banka"
    shutil.copytree(banka, kopya)
    (tmp_path / "is_emri").mkdir()
    k = kart99(hakemli)
    eski_fark = {**k["metraj_testi"], "fark_yuzde": 0.5}                                                # hakemin bugünkü sonucu başka
    for degisik, neden in (({**k, "durum": "beklemede", "metraj_testi": {**k["metraj_testi"], "durum": "beklemede"}}, "metraj kabul testi geçmedi"),
                           ({**k, "son_cizim": {**k["son_cizim"], "pim": None}}, "kartın pimindeki kural setiyle çizilmedi"),
                           ({**k, "son_cizim": {**k["son_cizim"], "kural_seti_sha256": "0" * 64}}, "kontrol dosyasının donacağı kural setiyle"),
                           ({**k, "son_cizim": {**k["son_cizim"], "karkas_sha256": None}}, "kontrol dosyasının donacağı kural setiyle"),
                           ({**k, "metraj_testi": eski_fark, "son_cizim": {**k["son_cizim"], "metraj_izi": A.metraj_izi(eski_fark)}},
                            "hakemin bugünkü sonucu kartınkiyle aynı değil"),
                           ({**k, "son_cizim": {**k["son_cizim"], "metraj_izi": "0" * 64}}, "metraj kaydı son çizimden sonra değişti")):
        (kopya / "KT99" / "kart.json").write_text(json.dumps(degisik, ensure_ascii=False), encoding="utf-8")
        capsys.readouterr()
        assert kos(kopya, "kabul", "KT99", "--kapisiz", "--izsiz") == 2
        assert neden in capsys.readouterr().out, neden
    duzeltmeli = {**k, "duzeltmeler": [{"zaman": "2026-10-30T12:00+0300", "tur": "tercih", "metin": "pencere sürgülü olsun", "cizim": 1}]}
    (banka / "KT99" / "kart.json").write_text(json.dumps(duzeltmeli, ensure_ascii=False), encoding="utf-8")
    assert kos(banka, "kabul", "KT99", "--kapisiz", "--izsiz", "--tarih", "2026-10-29") == 0
    k = kart99(hakemli)
    assert k["durum"] == "kabul" and k["kabul"]["metraj_kapisi"] == "gecti" and k["kabul"]["metraj_proje"] == "ÇP-14"
    assert k["kabul"]["kapi"] == "atlandi" and k["kabul"]["izsiz"] is True                               # gerçek bankada test_banka reddeder
    assert k["aday"]["kaynak"]["metin"].endswith("; düzeltme (c01 sonrası): pencere sürgülü olsun")      # açılış metni düzeltmeleri de anar
    assert "çelik hakemi, ÇP-14" in k["aday"]["kaynak"]["dogrulama"] and k["aday"]["musteri_projesi"] is True and k["aday"]["sunum"]["ad"] == ""
    kontrol = json.loads((banka / "KT99" / "kontrol.json").read_text(encoding="utf-8"))
    assert kontrol["kural_seti"] == k["pim"]["kural_seti"]["yol"] and kontrol["karkas_kurali"] == k["pim"]["karkas"]["yol"]
    assert B.denetle(banka) == [] and kos(banka, "kontrol", "KT99") == 0
