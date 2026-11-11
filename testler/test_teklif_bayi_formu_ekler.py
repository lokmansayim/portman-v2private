"""D-77 · Bayi formunun ekleri, yurt içi pazarı ve bu eve özel fiyat (`araclar/teklif.py --bayi … --proje-fiyat …`).

Lokman, 11 Kasım 2026 09:02 UTC (TK-06, Doğan Prefabrik): "Ürün Detayına bir satır daha ekle ve İç cephe alçıpan kaplama yaz fiyat
kısmını boş bırak … Ters tavanı bolt yap, çatı kaplaması kısmını bolt yap, ve - Antrasit Gri yaz (bolt olacak) Pencerelre satırını Kapsam
dışı işler kısmına (al ve komple satırı)"; 09:02:46 "2. sayfaya Kat planını ekle"; 09:05:45 kart "Kâr %20 + KDV %20: 550.535,63 TL";
09:09:02 "şimdilik bu işi münferit olarak tamamlayalım"; 09:17:35 "birim fiyatı 550.000 TL yap KDV yi 0 Yap Toplamı da 550.000 TL yap
Genel Toplamıda 550.000 TL yap 2. sayfaya png yi değil ön onay paftasını koy ürün detayı açıklama kısmına yazdığın KDV detayını sil";
09:18:28 "malzeme listesinden pencereleri kopmle sil" (adet 0, `--proje-fiyat`). Ek yoksa form eskisiyle aynıdır
(`test_teklif_bayi_formu.py`, mühür M-14).
"""
import json
import sys
import tempfile
from pathlib import Path

import pymupdf
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import teklif as TK  # noqa: E402
from araclar import teklif_pdf as TP  # noqa: E402
from motor import dxf_out  # noqa: E402

IE = KOK / "testler" / "teklif" / "TK01_is_emri_r05.json"
BAYRAK = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
DEFTER = ["--defter", str(KOK / "kurallar" / "fiyat" / "defter_2026-11.json")]
GIRDI = {"pazar": "yurt_ici",
         "bilgi": {"Bayi": "ÖRNEK BAYİ", "Adres": "Örnek İlçe"},
         "kosullar": {"Teslim süresi": "10 gün", "Teslim şekli": "Fabrika Teslim", "Ödeme şekli": "Nakit"},
         "urun_ek_satirlari": ["İç Cephe Alçıpan Kaplama"], "ek_yazi": {"Çatı Kaplaması": "Antrasit Gri"},
         "kalin": ["Tavan"], "kapsam_disina": ["Pencereler"], "on_onay_paftasi": True}


def _yaz(p: Path, d: dict) -> Path:
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


def _metin(sayfa) -> str:
    return " ".join(sayfa.get_text(flags=BAYRAK).split())


def _kalin(sayfa) -> set[str]:
    return {sp["text"].strip() for b in sayfa.get_text("dict")["blocks"] for s in b.get("lines", []) for sp in s["spans"]
            if sp["flags"] & 16}


@pytest.fixture(scope="module")
def cikti(tmp_path_factory):
    d = tmp_path_factory.mktemp("ekler")
    g = _yaz(d / "girdi.json", GIRDI)
    assert TK.main([str(IE), str(d / "c"), "--tavan", "ters", "--tarih", "11.11.2026", "--bayi", str(g), *DEFTER]) == 0
    return d / "c"


def test_yurt_ici_pazari():
    """Yurt içi: kâr %20 KDV hariç tabana; KDV %20 birimin üstüne; toplam KDV dahil (TK-06: 382.316,41 → 550.535,63)."""
    yi = TP.fiyatlandirma_oku()["pazarlar"]["yurt_ici"]
    assert TP.bayi_fiyati(382316.41, yi) == {"taban": 382316.41, "artis_orani": 0.2, "birim": 458779.69, "kdv_orani": 0.2,
                                             "kdv": 91755.94, "toplam": 550535.63}


def test_ekler_formda(cikti):
    """02'de fiyatsız ek ürün satırı; 04'te çatı kaplamasının sonunda kalın " - Antrasit Gri", tavan bütünüyle kalın; pencereler 04'te
    yok, 05'in başında bütün satırıyla; açıklamada pazarın KDV cümlesi; 2. sayfa Motor'un ön onay paftası; Ek-1 3. sayfadan; JSON'da
    ekler, iletişim yok."""
    T = json.loads((cikti / "TK01_teklif.json").read_text(encoding="utf-8"))
    with pymupdf.open(cikti / "TK01_teklif_formu.pdf") as d:
        s1, s2, s3 = _metin(d[0]), _metin(d[1]), _metin(d[2])
        kalin = _kalin(d[0])
        ciz2 = len(d[1].get_drawings())
    b = T["bayi_formu"]
    assert (b["kdv_orani"], b["birim"], b["toplam"]) == (0.2, round(b["taban"] * 1.2, 2), round(b["birim"] * 1.2, 2))
    assert "İç Cephe Alçıpan Kaplama Gen. Toplam" in s1 and s1.count(TP.tl(b["toplam"])) == 2
    assert TP.fiyatlandirma_oku()["pazarlar"]["yurt_ici"]["kdv_notu"] in s1
    assert "Tek Kat Panel - Antrasit Gri" in s1 and "Antrasit Gri" in kalin and "Ters Tavan" in kalin
    on4, on5 = s1.split("05 KAPSAM DIŞI İŞLER")
    assert "Pencereler" not in on4.split("04 PAKET İÇERİĞİ")[1] and on5.split("• ")[1].startswith("Pencereler: 70 mm profil")
    with tempfile.TemporaryDirectory() as t:                # Motor'un ön onay PDF'i; yazıları da çizgi, metin yok
        with pymupdf.open(Path(t) / dxf_out.uret(json.loads(IE.read_text(encoding="utf-8")), t)["pdf"]) as m:
            pafta = len(m[0].get_drawings())
    assert pafta > 1000 and ciz2 == pafta and s2.startswith("TK-01 · teklif ve satış onay formu · sayfa 2")
    assert s3.startswith("EK-1 · MALZEME LİSTESİ")
    assert b["ekler"]["on_onay_paftasi"] is True and "ÖRNEK" not in json.dumps(b, ensure_ascii=False)


def test_sabit_fiyat(tmp_path):
    """Lokman'ın verdiği fiyat (09:17:35): birim, tutar, toplam ve genel toplam 550.000,00 TL, Kdv %0; açıklamada KDV cümlesi yok;
    pazarın hesabı JSON'da `hesaplanan`; paftasız formda Ek-1 2. sayfadan."""
    g = _yaz(tmp_path / "g.json", dict(GIRDI, on_onay_paftasi=False, sabit_fiyat={"birim": 550000, "kdv_orani": 0}))
    assert TK.main([str(IE), str(tmp_path / "c"), "--tavan", "ters", "--tarih", "11.11.2026", "--bayi", str(g), *DEFTER]) == 0
    b = json.loads((tmp_path / "c" / "TK01_teklif.json").read_text(encoding="utf-8"))["bayi_formu"]
    assert (b["birim"], b["kdv_orani"], b["kdv"], b["toplam"], b["sabit"]) == (550000.0, 0, 0.0, 550000.0, True)
    assert b["hesaplanan"]["toplam"] == TP.bayi_fiyati(b["taban"], TP.fiyatlandirma_oku()["pazarlar"]["yurt_ici"])["toplam"]
    with pymupdf.open(tmp_path / "c" / "TK01_teklif_formu.pdf") as d:
        s1, s2 = _metin(d[0]), _metin(d[1])
    assert s1.count("550.000,00 TL") == 4 and "%0" in s1 and "KDV (%20)" not in s1 and s2.startswith("EK-1 · MALZEME LİSTESİ")


def test_ek_denetimi(tmp_path, capsys):
    """Biçimi bozuk ek durur; 04'te olmayan satır adı dosya yazılmadan durur."""
    ie = json.loads(IE.read_text(encoding="utf-8"))
    for bozuk in [dict(GIRDI, kalin="Tavan"), dict(GIRDI, urun_ek_satirlari=[""]), dict(GIRDI, ek_yazi={"Tavan": ""}),
                  dict(GIRDI, on_onay_paftasi="evet"), dict(GIRDI, kat_plani=True), dict(GIRDI, sabit_fiyat={"birim": 0, "kdv_orani": 0}),
                  dict(GIRDI, sabit_fiyat={"birim": 550000}), dict(GIRDI, sabit_fiyat={"birim": 550000, "kdv_orani": 20})]:
        with pytest.raises(ValueError, match="bayi formu"):
            TP.bayi_hazirla(bozuk, ie, 100)
    g = _yaz(tmp_path / "g.json", dict(GIRDI, kapsam_disina=["Garaj"]))
    assert TK.main([str(IE), str(tmp_path / "c"), "--tavan", "ters", "--bayi", str(g), *DEFTER]) == 1
    assert "'Garaj' satırı yok" in capsys.readouterr().err and not (tmp_path / "c").exists()


def test_proje_fiyati(tmp_path, capsys):
    """Bu eve özel fiyat ve adet (D-77): anahtarın fiyatı "PROJE" kaynağıyla (CRM defterinde dosyanın KDV oranıyla); adet düzeltilir; toplam ona göre;
    listede olmayan anahtar ve dayanaksız dosya durur. Dosya yoksa teklif eskisiyle aynı."""
    assert TK.main([str(IE), str(tmp_path / "a"), "--tavan", "ters", *DEFTER]) == 0
    A = json.loads((tmp_path / "a" / "TK01_teklif.json").read_text(encoding="utf-8"))
    sa = A["secenekler"][0]["fiyat"]["satirlar"]
    f = next(s for s in sa if s["tutar"] and s["adet"] and s["adet"] > 1)
    a = next(s for s in sa if s["tutar"] and s["adet"] and s is not f)
    anahtar = lambda s: f"{s['kalem']} | {s['olcu']}"                          # noqa: E731
    proje = {"dayanak": "deneme", "kaynak": {"kisa": "Deneme, 11.11.2026"},
             "fiyatlar": [{"anahtar": anahtar(f), "fiyat": 10.0, "kdv": 0.1, "kdv_grubu": "Trapez", "teklif_adi": "Yeni ad"}],
             "adetler": [{"anahtar": anahtar(a), "adet": 0}]}
    assert TK.main([str(IE), str(tmp_path / "b"), "--tavan", "ters", "--proje-fiyat", str(_yaz(tmp_path / "p.json", proje)), *DEFTER]) == 0
    B = json.loads((tmp_path / "b" / "TK01_teklif.json").read_text(encoding="utf-8"))
    sb = {anahtar(s): s for s in B["secenekler"][0]["fiyat"]["satirlar"]}
    yf, ya = sb[anahtar(f)], sb[anahtar(a)]
    assert (yf["birim_fiyat"], yf["tutar"], yf["kaynak"], yf["teklif_adi"]) == (10.0, round(10 * f["adet"], 2), "PROJE", "Yeni ad")
    assert ya["adet"] == 0 and ya["tutar"] == 0
    beklenen = A["secenekler"][0]["fiyat"]["ozet"]["toplam"] - f["tutar"] - a["tutar"] + yf["tutar"]
    assert B["secenekler"][0]["fiyat"]["ozet"]["toplam"] == pytest.approx(beklenen, abs=0.01)
    assert B["proje_fiyat"] == {"kaynak": {"kisa": "Deneme, 11.11.2026"}, "dayanak": "deneme", "fiyat": 1, "adet": 1}
    for bozuk, ileti in [(dict(proje, fiyatlar=[{"anahtar": "Yok | yok", "fiyat": 1, "kdv": 0.2}]), "tam bir satıra"),
                         (dict(proje, dayanak=""), "dayanağı")]:
        with pytest.raises(SystemExit, match=ileti):
            TK.main([str(IE), str(tmp_path / "x"), "--tavan", "ters", "--proje-fiyat", str(_yaz(tmp_path / "q.json", bozuk)), *DEFTER])
