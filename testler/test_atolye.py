"""İE-09 · Model atölyesi (D-20): `araclar/atolye.py` adımları geçici bir bankada (deneme modeli Ç8801Z, Ç8801'in çatı varyantı),
bankanın Katalog / İE-14 / aday kabulüne birleşmesi, kod çakışması, kör test engeli, metraj kapısı ve gün sonu sayımı.

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
    for s in ("Ç8801-Z", "Oda tablosu", "Yaşam Alanı", "21,34", "bankada Ç8801 kaydı", "Metraj kapısı: referans yok, koşulmadı", "kabul"):
        assert s in metin, s


def test_metraj_kapisi_ve_kabul_sirasi(atolye, tmp_path):
    banka = atolye["banka"]
    excel = tmp_path / "gercek liste.xlsx"
    import openpyxl
    wb = openpyxl.Workbook(); wb.active["B2"] = 5300.0; wb.save(excel)          # bizimki ≈ 4990 kg: fark ≈ -%5,8
    assert kos(banka, "metraj", "Ç8801Z", "--excel", excel, "--hucre", "Sheet!B2") == 1
    k = kart(atolye)
    assert k["durum"] == "beklemede" and k["metraj_testi"]["durum"] == "beklemede" and "openpyxl" in k["metraj_testi"]["gercek_kaynak"]
    assert kos(banka, "kabul", "Ç8801Z", "--kapisiz", "--izsiz") == 2                                    # beklemede: kabul edilemez
    bizim = k["metraj_testi"]["bizim_kg"]
    assert kos(banka, "metraj", "Ç8801Z", "--excel", excel, "--kg", round(bizim * 1.02, 1)) == 0       # %2: geçer
    assert kart(atolye)["durum"] == "kontrolde" and kart(atolye)["metraj_testi"]["durum"] == "gecti"


def test_kabul_banka_kaydi_ve_kontrol(atolye):
    banka = atolye["banka"]
    t_yol = banka / "C8801Z" / "tanim.json"
    asil = t_yol.read_text(encoding="utf-8")
    t_yol.write_text(asil.replace('"Deneme (Ç8801 çatı varyantı Z)"', '"Deneme Z (değişti)"'), encoding="utf-8")
    assert kos(banka, "kabul", "Ç8801Z", "--kapisiz", "--izsiz") == 2                                    # tanım son çizimden sonra değişti
    t_yol.write_text(asil, encoding="utf-8")
    assert kos(banka, "kabul", "Ç8801Z", "--kapisiz", "--izsiz", "--tarih", "2026-10-17") == 0
    k = kart(atolye)
    assert k["durum"] == "kabul" and k["kabul"]["karar"] == "D-11" and k["kabul"]["metraj_kapisi"] == "gecti"
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


def test_plan_uretici_bankasi_atolye_modelini_alir_varyanti_almaz(monkeypatch):
    from beyin import plan_uretici as PU
    PU._banka.cache_clear()
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [])
    cekirdek = [b["kod"] for b in PU._banka()]
    assert cekirdek == ["Ç8801", "Ç8201", "KT01", "KT02", "KT03"]                              # çekirdek bankanın varyantsız planları
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902"), _sahte("Ç8201V", taban="Ç8201")])
    PU._banka.cache_clear()
    try:
        assert [b["kod"] for b in PU._banka()] == cekirdek + ["Ç9902"]                        # atölye modeli sonda; çatı varyantı yok
    finally:
        PU._banka.cache_clear()


def test_aday_kabul_atolye_kodunu_tanir(monkeypatch, capsys):
    from araclar import aday_kabul
    monkeypatch.setattr(B, "kayitlar", lambda *x, **k: [_sahte("Ç9902")])
    assert aday_kabul.main(["--kodlar", "Ç9902,Ç8801", "--tarih", "2026-10-17", "--kuru"]) == 0
    assert "2 kayıt yazılacak (Ç9902, Ç8801)" in capsys.readouterr().out
