"""İE-13 PR-11 · Bayi teklif formu (D-64; `araclar/teklif.py --bayi`, `araclar/teklif_pdf.py`): bayiye giden teklif ve satış onay formu.

Lokman, 6 Kasım 2026 08:38 (TK-05, yurt dışı bayi): TASLAK ve kırmızı uyarı yok; 01 bayinin bilgileri; 02'de "Tek Kat Prefabrik Yapı",
tavan yazmaz, birim fiyat taban + %30 (kâr %20 + KDV'nin yarısı), KDV 0; açıklama bayinin anlayacağı dille; 03 teslim süresi, teslim
şekli, ödeme şekli; 04'te standart dışı değer kalın (2500 mm, 100 mm, 60 mm, trapez sac dışındakiler; iç teklifte de); Ek-1'de malzeme
listesi, birim fiyat ve tutar boş, "Motor" ve "fiyatsız satır" yazmaz. Oranlar kural kitabında (`kurallar/teklif/fiyatlandirma.json`).
Girdi TK-01 r05 İş Emri'yle ve sahte bayi bilgisiyle; bayinin telefonu açık (Lokman 6 Kasım 09:01 kartı), kural "maskeli" derse son dört
hane. Formun kendisi henüz hedef örnek değildir (D-28
madde 2: Lokman'ın önizleme onayı bekleniyor); bu test sayıları teklifin JSON'una ve kurala karşı sınar.
"""
import json
import sys
from pathlib import Path

import pymupdf
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import teklif as TK  # noqa: E402
from araclar import teklif_pdf as TP  # noqa: E402

IE = KOK / "testler" / "teklif" / "TK01_is_emri_r05.json"
BAYRAK = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
SAHTE_NUMARA = "+00 000 000 1234"                          # sahte numara
DEFTER = ["--defter", str(KOK / "kurallar" / "fiyat" / "defter_2026-11.json")]   # D-72'den beri kaynak açıkça; form kuralı kaynaktan bağımsız
GIRDI = {"pazar": "yurt_disi",
         "bilgi": {"Bayi": "ÖRNEK BAYİ - Deneme Bey", "İletişim (GSM)": SAHTE_NUMARA, "Adres": "Örnek Ülke"},
         "kosullar": {"Teslim süresi": "1 Hafta", "Teslim şekli": "Fabrika Teslim", "Ödeme şekli": "Peşin"}}


def _oku(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _metin(yol):
    with pymupdf.open(yol) as d:
        return [" ".join(s.get_text(flags=BAYRAK).split()) for s in d]


@pytest.fixture(scope="module")
def girdi(tmp_path_factory):
    p = tmp_path_factory.mktemp("bayi_girdi") / "girdi.json"
    p.write_text(json.dumps(GIRDI, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture(scope="module")
def cikti(tmp_path_factory, girdi):
    d = tmp_path_factory.mktemp("bayi_formu")
    assert TK.main([str(IE), str(d), "--tavan", "asma", "--tarih", "06.11.2026", "--bayi", str(girdi), *DEFTER]) == 0
    return d


@pytest.fixture(scope="module")
def T(cikti):
    return _oku(cikti / "TK01_teklif.json")


def test_fiyat_kuralı_pazardan():
    """Birim = taban × (1 + kâr + KDV × fiyata katılan pay); formdaki KDV = birim × fatura oranı. Yurt dışı: kâr %20 + KDV'nin (%20)
    yarısı = %30, faturada KDV 0 (Lokman: "+%30 ekle ... KDV'ye 0"). Oranlar kuralda; başka pazar kendi oranlarıyla."""
    yd = TP.fiyatlandirma_oku()["pazarlar"]["yurt_disi"]
    assert TP.bayi_fiyati(186585.66, yd) == {"taban": 186585.66, "artis_orani": 0.3, "birim": 242561.36, "kdv_orani": 0.0, "kdv": 0.0,
                                             "toplam": 242561.36}
    baska = {"kar_orani": 0.2, "kdv_orani": 0.2, "fiyata_katilan_kdv_payi": 0, "faturada_kdv_orani": 0.2}
    assert TP.bayi_fiyati(100, baska) == {"taban": 100, "artis_orani": 0.2, "birim": 120.0, "kdv_orani": 0.2, "kdv": 24.0, "toplam": 144.0}


def test_bayi_formu_ve_json(cikti, T):
    """Tek seçenekte iç teklifin PDF'i ve bayi formu; JSON'da formun fiyatı (iletişim bilgisi yok)."""
    assert sorted(p.name for p in cikti.glob("*.pdf")) == ["TK01_teklif.pdf", "TK01_teklif_formu.pdf"]
    b = T["bayi_formu"]
    toplam = T["secenekler"][0]["fiyat"]["ozet"]["toplam"]
    assert b["pazar"] == "yurt_disi" and b["taban"] == round(toplam, 2) and b["birim"] == round(toplam * 1.3, 2)
    assert (b["kdv"], b["toplam"]) == (0.0, b["birim"])
    assert "Deneme" not in json.dumps(T, ensure_ascii=False) and "1234" not in json.dumps(b)


def test_ilk_sayfa(cikti, T):
    """TASLAK, uyarı, Motor, defter ve fiyatsız satır yazmaz; ürün tavansız; birim fiyat dört yerde; KDV %0; 01 ve 03 girdiden; bayinin
    telefonu açık (D-64 madde 6); açıklama KDV'nin neden yok olduğunu söyler."""
    s1 = _metin(cikti / "TK01_teklif_formu.pdf")[0]
    b = T["bayi_formu"]
    for x in ["TEKLİF VE SATIŞ ONAY FORMU", "Tarih: 06.11.2026", "1 Tek Kat Prefabrik Yapı", "ÖRNEK BAYİ - Deneme Bey", SAHTE_NUMARA,
              "Örnek Ülke", "Teslim süresi 1 Hafta", "Teslim şekli Fabrika Teslim", "Ödeme şekli Peşin", "%0",
              "Yurt dışı satış olduğu için KDV uygulanmaz.", "Müşteri / proje"]:
        assert x in s1, x
    assert s1.count(TP.tl(b["birim"])) == 4
    for x in ["TASLAK", "fiyatsız", "Fiyatı olmayan", "Motor", "defter", "öneri", "Asma tavan", "…1234",
              TP.tl(T["secenekler"][0]["fiyat"]["ozet"]["toplam"])]:
        assert x not in s1, x


def test_ek1_fiyatsiz(cikti, T):
    """Ek-1: başlık "EK-1 · MALZEME LİSTESİ"; her satırda birim fiyat ve tutar boş; ara ve genel toplam yok; adedi 0 olan satır yok;
    öteki satırlar teklifin satırlarıyla aynı sayıda."""
    yol = cikti / "TK01_teklif_formu.pdf"
    metin = " ".join(_metin(yol)[1:])
    assert metin.startswith("EK-1 · MALZEME LİSTESİ Kalem")
    for x in ["toplamı", "GENEL TOPLAM", "Fiyatı olmayan", "Motor", " TL"]:
        assert x not in metin, x
    satir = []
    with pymupdf.open(yol) as d:
        for s in list(d)[1:]:
            for t in s.find_tables().tables:
                for r in t.extract():
                    if len(r) == 6 and r[0] not in (None, "", "Kalem") and r[2] not in (None, ""):
                        satir.append(r)
    beklenen = [s for s in T["secenekler"][0]["fiyat"]["satirlar"] if s.get("adet") != 0]
    assert len(satir) == len(beklenen) > 50
    assert all((r[4] or "").strip() == "" and (r[5] or "").strip() == "" for r in satir)
    assert all((r[3] or "").strip() != "0" for r in satir)


def test_standart_disi_kalin():
    """Standart: kat 2500 mm, dış 100 mm, iç 60 mm, çatı trapez sac. Ayrılan kısım kalın (yalnız "160 mm", bütün satır değil); standart
    değerde kalın yok."""
    form, ie = TP.form_oku(), _oku(IE)
    std = dict(ie, yapi=dict(ie["yapi"], duvar_yuksekligi_cm=250, duvar_kalinligi_cm={"dis": 10, "ic": 6}),
               ozellikler=dict(ie.get("ozellikler") or {}, **{"Çatı Kaplaması": "Trapez Saç"}))
    assert TP.standart_disi(form, std, TP.teknik_ve_kapsam(form, std)[0]) == {}
    tk05 = dict(ie, yapi=dict(ie["yapi"], duvar_yuksekligi_cm=280, duvar_kalinligi_cm={"dis": 16, "ic": 10}),
                ozellikler=dict(ie.get("ozellikler") or {}, **{"Çatı Kaplaması": "Sandviç Panel"}))
    assert TP.standart_disi(form, tk05, TP.teknik_ve_kapsam(form, tk05)[0]) == {
        "Kat Yüksekliği": "2800 mm", "Dış Cephe Panelleri": "160 mm", "İç Cephe Panelleri": "100 mm", "Çatı Kaplaması": "Sandviç Panel"}
    assert TP.satir("Dış Cephe Panelleri", "Kalınlık 160 mm; 8 mm", "160 mm").count("<b>160 mm</b>") == 1


def test_kalin_pdfte(cikti):
    """TK-01 r05'in çatı kaplaması "Tek Kat Panel": standart (trapez) dışı, PDF'te kalın; standart kat yüksekliği kalın değil. İç teklifte
    de aynı (genel kural)."""
    for ad in ("TK01_teklif_formu.pdf", "TK01_teklif.pdf"):
        kalin, ince = set(), set()
        with pymupdf.open(cikti / ad) as d:
            for blok in d[0].get_text("dict")["blocks"]:
                for sat in blok.get("lines", []):
                    for sp in sat["spans"]:
                        (kalin if sp["flags"] & 16 else ince).add(sp["text"].strip())
        assert "Tek Kat Panel" in kalin and "2500 mm" in ince, ad


def test_girdi_denetimi(girdi, tmp_path, capsys):
    """Tanımsız pazar, bilinmeyen satır, boş ödeme satırı ve birden çok seçenek durur; hiçbir dosya yazılmaz."""
    ie = _oku(IE)
    for bozuk, ileti in [(dict(GIRDI, pazar="tanimsiz_pazar"), "tanımlı değil"),            # D-77'den beri yurt_ici tanımlı
                         (dict(GIRDI, kosullar={**GIRDI["kosullar"], "Teslim şekli": ""}), "boş satır"),
                         (dict(GIRDI, bilgi={**GIRDI["bilgi"], "Vergi no": "1"}), "bilinmeyen satır"),
                         (dict(GIRDI, fiyat=1), "bilinmeyen alan")]:
        with pytest.raises(ValueError, match=ileti):
            TP.bayi_hazirla(bozuk, ie, 100)
    assert TK.main([str(IE), str(tmp_path / "iki"), "--tavan", "asma,ters", "--bayi", str(girdi), *DEFTER]) == 1
    assert "tek seçenekle" in capsys.readouterr().err and not (tmp_path / "iki").exists()
    p = tmp_path / "bos.json"
    p.write_text(json.dumps(dict(GIRDI, kosullar={})), encoding="utf-8")
    assert TK.main([str(IE), str(tmp_path / "bos"), "--tavan", "asma", "--bayi", str(p), *DEFTER]) == 1
    assert not (tmp_path / "bos").exists()


def test_telefon_kurali():
    """Kural "acik": numara girdideki gibi (D-64 madde 6); "maskeli": son dört hane (D-33 madde 3). Kural kitabında bugün "acik"."""
    form, ie = TP.form_oku(), _oku(IE)
    assert form["bayi_formu"]["telefon"] == "acik"
    acik = dict(TP.bayi_hazirla(GIRDI, ie, 100, form)["bilgi"])
    assert acik["İletişim (GSM)"] == SAHTE_NUMARA
    maskeli = dict(form, bayi_formu=dict(form["bayi_formu"], telefon="maskeli"))
    assert dict(TP.bayi_hazirla(GIRDI, ie, 100, maskeli)["bilgi"])["İletişim (GSM)"] == "…1234"


def test_ayni_girdi_ayni_form(cikti, girdi, tmp_path):
    assert TK.main([str(IE), str(tmp_path), "--tavan", "asma", "--tarih", "06.11.2026", "--bayi", str(girdi), *DEFTER]) == 0
    assert (tmp_path / "TK01_teklif_formu.pdf").read_bytes() == (cikti / "TK01_teklif_formu.pdf").read_bytes()
