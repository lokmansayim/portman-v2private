"""D-33 · Projenin sahibinin adı herkeste görünür (Lokman 30 Ekim 2026 13:24; 1 Kasım karar kartı "Projenin sahibinin adı").

Ad zarftan (`bilgi.musteri_adi`, bayinin mesajındaki müşteri) ya da tanımdan (`musteri_adi`, banka modelinin sahibi) gelir; tek işlev
`motor.genel.bayi_gorseli.sahip_adi`. Müşteri projesinde (KT-xx) modelin tarifi yazılmaz, sahibinin adı yazılıysa o yazılır; adı yazılı
olmayan modelin çıktısı değişmez (altın testler ve referans zinciri bunu bayt bayt korur). Telefon numarası her yerde maskelenir.
Testlerdeki adlar uydurmadır."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import celik  # noqa: E402
from motor.genel import uret, yazi_cakisma as YC  # noqa: E402
from motor.genel.bayi_gorseli import sahip_adi  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
SAHIP = "Deneme Sahibi Uzunsoyadlı"
BILGI = {"bayi_adi": "Deneme Bayi", "bayi_telefonu": "900000000555", "sevk_adresi": "Deneme Mah. Deneme Sok. No 1 Deneme İlçesi / Deneme İli",
         "ozel_istekler": ["çatı antrasit"], "ozellikler": {"Dış Boya Rengi": "krem"}}


def test_sahip_adi_sirasi_ve_numara():
    t = {"kod": "KT-09", "musteri_adi": "Tanım Sahibi"}
    assert sahip_adi(t) == "Tanım Sahibi"
    assert sahip_adi(t, {"musteri_adi": "Zarf Müşterisi"}) == "Zarf Müşterisi"           # bayinin mesajındaki müşteri önce
    assert sahip_adi({"kod": "KT-09"}) == "" and sahip_adi({"kod": "KT-09"}, {"musteri_adi": ""}) == ""
    assert sahip_adi({"musteri_adi": "Ali Deneme 0532 000 00 00"}) == "Ali Deneme …"      # numara ada karışmaz (D-09)
    assert sahip_adi({"musteri_adi": "Ali Deneme +905320000000"}) == "Ali Deneme …"


def test_celik_zarfi_musteri_adini_maskeli_tasir():
    aday = {"kod": "Ç8801", "tanim": "modeller/C8801.json"}
    ts = {"musteri": {"ad": "Veli Deneme 0532 000 00 00"}, "ozet": "deneme"}
    ie = celik.zarf(aday, {"kod": "BAYI", "ad": "Deneme Bayi"}, None, ts, None)
    assert ie["bilgi"]["musteri_adi"] == "Veli Deneme …"
    assert ie["talep"]["musteri_adi"] == "Veli Deneme 0532 000 00 00"                    # talep Postgres'te kalır, paftaya bilgi gider
    assert celik.zarf(aday, {"kod": "BAYI"}, None, {"ozet": "x"}, None)["bilgi"]["musteri_adi"] == ""


def _uret(model: str, ek: dict, bilgi: dict) -> dict:
    """Modeli (tanıma `ek` alanları eklenerek) üretir; kaydedilen her figürün yazıları ve yazı denetimi {ad: (yazılar, rapor)}."""
    import matplotlib.figure
    import matplotlib.text
    from matplotlib.backends.backend_pdf import PdfPages
    r: dict[str, tuple[list[str], dict]] = {}
    asil_fig, asil_pdf = matplotlib.figure.Figure.savefig, PdfPages.savefig

    def yazilar(fig):
        return [x.get_text() for x in fig.findobj(matplotlib.text.Text) if x.get_text()]

    def fig_savefig(self, fname, *a, **k):
        ad = Path(str(fname)).name if not hasattr(fname, "write") else "akis"
        r[ad] = (yazilar(self), YC.denetle(self, ad))
        return asil_fig(self, fname, *a, **k)

    def pdf_savefig(self, figure=None, **k):
        dosya = Path(str(getattr(self, "_filename", "") or "")).name
        on = "pafta_sayfa_" if not dosya or dosya.endswith("_pafta.pdf") else f"{dosya}#"
        n = sum(1 for x in r if x.startswith(on)) + 1
        r[f"{on}{n}"] = (yazilar(figure), YC.denetle(figure, f"{on}{n}"))
        return asil_pdf(self, figure, **k)

    t = json.loads((KOK / "modeller" / f"{model}.json").read_text(encoding="utf-8")) | ek
    matplotlib.figure.Figure.savefig, PdfPages.savefig = fig_savefig, pdf_savefig
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp) / f"{model}.json"
            tp.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
            m = uret.uret(tp, Path(tmp) / "c", is_emri_no="PM-TEST-20261101-1", revizyon=1, set_yolu=SET, yontem="panel", perspektif=False,
                          bayi=True, bilgi=bilgi)
            assert m["passed"], m.get("warnings")
            kod = uret.kod_govde(t)
            c = Path(tmp, "c")
            r["yukleme"] = (json.loads((c / f"{kod}_yukleme.json").read_text(encoding="utf-8")).get("ad"), {})
            r["kaynak"] = (json.loads((c / f"{kod}_girdi.json").read_text(encoding="utf-8")).get("kaynak"), {})
            r["dosyalar"] = (sorted(p.name for p in c.iterdir()), {})
            import ifcopenshell
            f = ifcopenshell.open(str(c / f"{kod}.ifc"))
            r["ifc"] = ([f.by_type("IfcProject")[0].Name, f.by_type("IfcBuilding")[0].Name], {})
            r["dxf"] = (Path(tmp, "c", f"{kod}.dxf").read_text(encoding="utf-8", errors="replace") if Path(tmp, "c", f"{kod}.dxf").exists()
                        else "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in Path(tmp, "c").glob("*.dxf")), {})
    finally:
        matplotlib.figure.Figure.savefig, PdfPages.savefig = asil_fig, asil_pdf
    r["_kod"] = (kod, {})
    return r


def _cakisma(rap: dict) -> list:
    return [(k, v) for k in ("cakisan", "cizgi_kapatan", "yay_kapatan", "sayfa_disi") if (v := rap.get(k))]


@pytest.fixture(scope="module")
def kt01_adli():
    return _uret("KT01", {"musteri_adi": SAHIP}, BILGI)


def test_kt_sahibinin_adi_cizimlerde_tarif_yok(kt01_adli):
    r = kt01_adli
    kod = r["_kod"][0]
    plan, s1, s2 = r[f"{kod}_plan_bayi.png"][0], r["pafta_sayfa_1"][0], r["pafta_sayfa_2"][0]
    assert any(SAHIP in x for x in plan)                                                 # bayi görseli
    assert any(x.startswith(f"KT-01 · {SAHIP} · ") and "m²" in x for x in s2)            # paftanın 2. sayfasının başlığı
    assert any(x.startswith(f"{SAHIP} · KT-01 · ") and "M² ÇELİK KONUT" in x for x in s1)  # antet: PROJE ADI & M²
    tarif = json.loads((KOK / "modeller" / "KT01.json").read_text(encoding="utf-8"))["ad"]
    assert not any("kör test" in x or tarif in x for d in (plan, s1, s2) for x in d)    # modelin tarifi bayiye gitmez
    assert SAHIP in r["dxf"][0]                                                          # düzenlenebilir DXF antedi
    # mühendis çizim seti (plan, pafta, görünüşler), yükleme listesi ve IFC: tarif yerine "kod · sahibinin adı · m²" (D-33 tamamlama)
    for d in (f"{kod}_plan.png", f"{kod}_pafta.png", f"{kod}_gorunusler.png"):
        assert any(x.startswith(f"KT-01 · {SAHIP} · ") and "m²" in x for x in r[d][0]), d
        assert not any("kör test" in x or tarif in x for x in r[d][0]), d
    assert r["yukleme"][0].startswith(f"KT-01 · {SAHIP} · ") and r["yukleme"][0].endswith(" m²")
    assert r["ifc"][0] == [f"Portman — KT-01 · {SAHIP}", SAHIP]
    for d in (f"{kod}_plan_bayi.png", "pafta_sayfa_1", "pafta_sayfa_2"):                 # uzun ad yazı çakışması doğurmaz (D-16)
        assert _cakisma(r[d][1]) == [], (d, _cakisma(r[d][1]))


def test_katalog_modelinde_antette_zarfin_adi():
    r = _uret("C8801", {}, BILGI | {"musteri_adi": "Zarf Müşterisi Deneme"})
    s1, s2 = r["pafta_sayfa_1"][0], r["pafta_sayfa_2"][0]
    assert any(x.startswith("Zarf Müşterisi Deneme · Ç8801 · ") and "M² ÇELİK KONUT" in x for x in s1)
    assert any(x.startswith("Ç8801 · Tek kat çelik") for x in s2)                        # katalogda tarif yine yazılır
    assert _cakisma(r["pafta_sayfa_1"][1]) == []


def test_adi_yazili_olmayan_kt_bugunku_gibi():
    r = _uret("KT01", {}, BILGI)
    s1, s2 = r["pafta_sayfa_1"][0], r["pafta_sayfa_2"][0]
    assert any(x.startswith("KT-01 · ") and x.split("   —   ")[0].count("·") == 1 for x in s2)   # "KT-01 · 99 m²"
    assert any(x.startswith("KT-01 · ") and "M² ÇELİK KONUT" in x for x in s1)
    tarif = json.loads((KOK / "modeller" / "KT01.json").read_text(encoding="utf-8"))["ad"]
    assert r["yukleme"][0].startswith("KT-01 · Tek kat çelik") and r["ifc"][0][1] == tarif   # çizim seti, liste ve IFC tarifle (BK-09 M7)


def test_kt04_sahibinin_adi_tanimda():
    # Lokman, 1 Kasım 2026 05:26 UTC: KT-04'ün sahibinin adı (D-33 › Sonraki); başlıkta m² kodun brüt oturumundan (K-A1)
    t = json.loads((KOK / "modeller" / "banka" / "KT04" / "tanim.json").read_text(encoding="utf-8"))
    assert t.get("musteri_adi") and sahip_adi(t) == t["musteri_adi"] and not any(c.isdigit() for c in t["musteri_adi"])


def test_kontrol_sayfasinda_sahibinin_adi():
    # atölyenin kontrol sayfası (Lokman'a): müşteri projesinin satırında sahibinin adı görünür, adı yoksa bugünkü satır
    from araclar import atolye_sayfa
    kart = {"gosterim": "KT-09", "kod": "KT09", "musteri_projesi": True}
    assert "sahibi Tanım Sahibi" in atolye_sayfa._sol(kart, "Tanım Sahibi")
    assert "evet (tarif yazılmaz;" in atolye_sayfa._sol(kart) and "evet · sahibi" not in atolye_sayfa._sol(kart)
    assert ">hayır<" in atolye_sayfa._sol({"gosterim": "Ç8801", "kod": "Ç8801"})
    # satır sayfaya verilen ada uyar (`atolye.ciz` adı motorun `musteri_projesi` koşuluyla verir): sayfa çizimle çelişmez
    assert "evet · sahibi Tanım Sahibi" in atolye_sayfa._sol({"gosterim": "Ç8801", "kod": "Ç8801"}, "Tanım Sahibi")


ZARF = "Zarf Müşterisi Deneme"


def test_zarfin_adi_tanima_yazilir():
    # İE-09 PR-6c: müşteri projesinde zarfın adı tanımdakinin önüne geçer; katalogda, zarfsızda ve ad aynıyken tanım aynen döner
    kt, kt_adli = {"kod": "KT-09", "ad": "tarif"}, {"kod": "KT-09", "ad": "tarif", "musteri_adi": "Tanım Sahibi"}
    assert uret.zarfin_adiyla(kt, {"musteri_adi": ZARF}) == kt | {"musteri_adi": ZARF}
    assert uret.zarfin_adiyla(kt_adli, {"musteri_adi": ZARF})["musteri_adi"] == ZARF                 # zarf önce
    assert uret.zarfin_adiyla(kt, {"musteri_adi": "Veli Deneme 0532 000 00 00"})["musteri_adi"] == "Veli Deneme …"   # numara yazılmaz
    for t, b in ((kt, None), (kt, {}), (kt, {"musteri_adi": "  "}), (kt_adli, {"musteri_adi": "Tanım Sahibi"}),
                 ({"kod": "Ç8801", "ad": "Tek kat çelik"}, {"musteri_adi": ZARF})):
        assert uret.zarfin_adiyla(t, b) is t, (t, b)                                                      # dosya kopyası yok, çıktı aynı
    assert uret.zarfin_adiyla({"kod": "X1", "musteri_projesi": True}, {"musteri_adi": ZARF})["musteri_adi"] == ZARF


def test_zarfin_adi_butun_ciktilarda():
    # bayi siparişi: tanımda başka ad yazılı (KT-04 gibi), zarfta bayinin müşterisi; her çıktı zarfın adını yazar, tanımdakini yazmaz
    r = _uret("KT01", {"musteri_adi": SAHIP}, BILGI | {"musteri_adi": ZARF})
    kod = r["_kod"][0]
    tarif = json.loads((KOK / "modeller" / "KT01.json").read_text(encoding="utf-8"))["ad"]
    figurler = {d: r[d][0] for d in (f"{kod}_plan_bayi.png", "pafta_sayfa_1", "pafta_sayfa_2", f"{kod}_plan.png", f"{kod}_pafta.png",
                                     f"{kod}_gorunusler.png")}
    for d, yazi in figurler.items():
        assert any(ZARF in x for x in yazi), d
        assert not any(SAHIP in x or "kör test" in x or tarif in x for x in yazi), d
    assert any(x.startswith(f"KT-01 · {ZARF} · ") for x in figurler["pafta_sayfa_2"])                 # paftanın başlığı
    assert any(x.startswith(f"{ZARF} · KT-01 · ") for x in figurler["pafta_sayfa_1"])                  # antet
    assert ZARF in r["dxf"][0] and SAHIP not in r["dxf"][0]                                            # düzenlenebilir DXF
    assert r["yukleme"][0].startswith(f"KT-01 · {ZARF} · ")                                             # yükleme listesi
    assert r["ifc"][0] == [f"Portman — KT-01 · {ZARF}", ZARF]                                           # IFC proje ve bina adı
    assert r["kaynak"][0] == "Yapı Tanımı 0.5 (KT01.json)"                                              # listenin kaynağı asıl dosyanın adı
    assert "KT01.json" not in r["dosyalar"][0] and not any("tanim" in d for d in r["dosyalar"][0])    # tanımın kopyası çıktıya girmez
    for d in (f"{kod}_plan_bayi.png", "pafta_sayfa_1", "pafta_sayfa_2"):
        assert _cakisma(r[d][1]) == [], (d, _cakisma(r[d][1]))
