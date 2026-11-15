"""BK-33 · D-98 (Lokman, 15 Kasım 2026 05:22:05 UTC, karar kartı "Evet, nem bariyeriyle"): çelik planda kiremit desen sac + OSB + nem bariyeri.

Genel motor (çelik) kural kitabının `genel_osbli_kaplama` anahtarındaki kaplamaları hesaplar; anahtar yoksa (eski setler) eski davranış: yalnız
sandviç ve tek kat panel, öteki kaplamada `SystemExit`. Çizimler kaplamadan bağımsızdır: paftada yalnız "Çatı Kaplaması" satırı değişir.

Hedef örnek: 140 m² çelik ev (KT-12, `modeller/havuz/KT12.json`) tanımın kaplaması `osb_kiremit` yapılarak; beklenen
`testler/genel/beklenen/KT12_osb_kiremit.json` (Lokman'ın onayıyla donduruldu; onayın tarihi ve sözü dosyada). Kıyaslanan: paftanın
"Çatı Kaplaması" yazısı ve yükleme listesinin kaplamaya bağlı satırları (çatı OSB, nem bariyeri, kiremit desen sac, mahyalar, mahya bandı,
5,5 × 60 vida). Üretim komutu: tanımın `cati.kaplama`'sı `osb_kiremit` iken `python -m motor.genel.uret <tanım> <çıktı>`."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, girdi_genel, kural, uret, yapi, yazi_cakisma as YC  # noqa: E402

TANIM = KOK / "modeller" / "havuz" / "KT12.json"
HEDEF = KOK / "testler" / "genel" / "beklenen" / "KT12_osb_kiremit.json"
ESKI_SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
KAPLAMA_SATIRLARI = ("Çatı OSB", "Nem bariyeri", "Kiremit desen sac", "Metal kiremit mahyası", "OSB mahyası", "Ters mahya", "Mahya bandı",
                     "Trapez vida (5,5 × 60)")
CIZIM_AYNI = ("plan.png", "plan_bayi.png", "gorunusler.png", "makaslar.png", "duvar_panelleri.png", "bayi_gorsel.png")
_URETIM: dict[str, tuple[Path, dict]] = {}
_GECICI = tempfile.TemporaryDirectory()


def _tanim(kaplama: str | None) -> dict:
    t = json.loads(TANIM.read_text(encoding="utf-8"))
    if kaplama:
        t = copy.deepcopy(t)
        t["cati"]["kaplama"] = kaplama
    return t


def uretim(kaplama: str) -> tuple[Path, dict]:
    """Ev bir kez üretilir (güncel kural kitabıyla); kaydedilen her figürün yazı raporu ile birlikte önbellekte."""
    if kaplama in _URETIM:
        return _URETIM[kaplama]
    import matplotlib.figure
    from matplotlib.backends.backend_pdf import PdfPages
    rapor: dict[str, dict] = {}
    asil_fig, asil_pdf = matplotlib.figure.Figure.savefig, PdfPages.savefig

    def fig_savefig(self, fname, *a, **k):
        ad = Path(str(fname)).name if not hasattr(fname, "write") else "akis"
        rapor[ad] = YC.denetle(self, ad)
        return asil_fig(self, fname, *a, **k)

    def pdf_savefig(self, figure=None, **k):
        dosya = Path(str(getattr(self, "_filename", "") or "")).name
        on = "pafta_sayfa_" if not dosya or dosya.endswith("_pafta.pdf") else f"{dosya}#"
        n = sum(1 for x in rapor if x.startswith(on)) + 1
        rapor[f"{on}{n}"] = YC.denetle(figure, f"{on}{n}")
        return asil_pdf(self, figure, **k)

    kok = Path(_GECICI.name) / kaplama
    kok.mkdir()
    tanim = kok / "KT12.json"
    tanim.write_text(json.dumps(_tanim(kaplama), ensure_ascii=False, indent=1), encoding="utf-8")
    matplotlib.figure.Figure.savefig, PdfPages.savefig = fig_savefig, pdf_savefig
    try:
        m = uret.uret(tanim, kok / "cikti", is_emri_no="PM-TEST-20261115-1", revizyon=1, perspektif=False, bayi=True)
        assert m["passed"], m.get("warnings")
    finally:
        matplotlib.figure.Figure.savefig, PdfPages.savefig = asil_fig, asil_pdf
    _URETIM[kaplama] = (kok / "cikti", rapor)
    return _URETIM[kaplama]


def ozet(cikti: Path) -> dict:
    """Hedef örnekle kıyaslanan özet: paftanın "Çatı Kaplaması" yazısı ve kaplamaya bağlı liste satırları (adı, ölçüsü, adedi)."""
    pafta = json.loads((cikti / "KT12_pafta_ozet.json").read_text(encoding="utf-8"))
    liste = json.loads((cikti / "KT12_yukleme.json").read_text(encoding="utf-8"))
    yazi = next(v for k, v in _duz(pafta) if k == "Çatı Kaplaması")
    return {"pafta_cati_kaplamasi": yazi,
            "satirlar": [{"kalem": s["kalem"], "liste_adi": s.get("liste_adi") or s["kalem"], "boyut": s["boyut"], "adet": s["adet"]}
                         for s in liste["satirlar"] if s["kalem"] in KAPLAMA_SATIRLARI],
            "cikan": sorted({s["kalem"] for s in liste["satirlar"] if s["kalem"] in ("Tek kat panel", "Sandviç panel")
                             or s["kalem"].startswith(("Trapez vida (5,5 × 76", "Trapez vida (5,5 × 110"))})}


def _duz(o, yol=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                yield from _duz(v, k)
            else:
                yield k, v
    elif isinstance(o, list):
        for v in o:
            yield from _duz(v, yol)


def test_eski_sette_kiremit_hesaplanmaz():
    """Anahtar yoksa eski davranış: genel motor kiremit desen saca `SystemExit` verir (eski set eski çıktıyı verir)."""
    t = _tanim("osb_kiremit")
    with kural.secili(ESKI_SET):
        kur = kural.oku()
        assert "genel_osbli_kaplama" not in kur
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        with pytest.raises(SystemExit, match="kaplamasını hesaplar"):
            girdi_genel.metraj(y, c, kur)


def test_kodu_yazilmamis_kaplama_kitaba_eklenince_durur(tmp_path):
    """Kitaba kodu yazılmamış bir kaplama (ör. trapez sac + OSB) eklenirse plan geçmez; liste sessizce eksik çıkmaz (hakem bulgusu 2)."""
    kur_kopya = json.loads(kural.yol().read_text(encoding="utf-8"))
    kur_kopya["genel_osbli_kaplama"]["deger"]["osb_trapez"] = {"osb_zayiat": 0.2, "ust_ortu": "nem_bariyeri"}
    set_yolu = tmp_path / "kitap.json"
    set_yolu.write_text(json.dumps(kur_kopya, ensure_ascii=False), encoding="utf-8")
    t = _tanim("osb_trapez")
    with kural.secili(set_yolu):
        kur = kural.oku()
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        with pytest.raises(SystemExit, match="kaplamasını hesaplar"):
            girdi_genel.metraj(y, c, kur)


def test_genel_girdide_kaplama_degisimi():
    """Genel girdide kaplama sonradan yalnız iki panel arasında değişir; kiremit desen sac ↔ panel değişimi dizilimi yeniden ister (bulgu 3)."""
    from motor.genel import yukleme
    for eski, yeni, durur in (("osb_kiremit", "tek_kat_panel", True), ("osb_kiremit", "sandvic_panel", True), ("tek_kat_panel", "osb_kiremit", True),
                              ("tek_kat_panel", "sandvic_panel", False), ("sandvic_panel", "tek_kat_panel", False), ("osb_kiremit", "osb_kiremit", False)):
        c = {"kaplama": eski, "dizilim": {"satirlar": []}}
        if durur:
            with pytest.raises(SystemExit, match="yeniden üretilmeli"):
                yukleme.genel_kaplama_degisimi(c, yeni)
        else:
            yukleme.genel_kaplama_degisimi(c, yeni)
    yukleme.genel_kaplama_degisimi({"kaplama": "osb_kiremit"}, "tek_kat_panel")       # 0.4 hattı girdisi (dizilimsiz): serbest, eski davranış


def test_kural_kitabi():
    """D-98'in değerleri kural kitabında; yalnız Lokman'ın seçtiği kaplama (kiremit desen sac + OSB) açık."""
    kur = kural.oku()
    k = kur["genel_osbli_kaplama"]
    assert k["durum"] == "lokman" and "D-98" in k["kaynak"] and "05:22:05" in k["kaynak"]
    assert k["deger"] == {"osb_kiremit": {"osb_zayiat": 0.2, "ust_ortu": "nem_bariyeri"}}
    assert kur["cati_kaplama"]["deger"]["osb_kiremit"] == "OSB + Nem Bariyeri + Kiremit Desen Sac"
    assert set(kur["cati_kaplama"]["deger"]) == {"sandvic_panel", "tek_kat_panel", "osb_kiremit", "osb_trapez", "trapez_sac", "osb_shingle"}
    # gerçek iki listenin OSB'si (140 m²: 64, ustanın planında 62; 166 m²: 77) yüzeyle (151,5 ve 193 m²) ± 2 levha
    import math
    for yuzey, gercek in ((151.5, 62), (193.0, 77)):
        assert abs(math.ceil(yuzey * 1.2 / kur["levha_m2"]["osb"]["deger"]) - gercek) <= 2


def test_hedef_ornekle_ayni():
    """140 m² çelik ev, kiremit desen sac + OSB: pafta yazısı ve kaplama satırları onaylı hedef örnekle aynı (D-28)."""
    if not HEDEF.is_file():
        pytest.fail(f"Hedef örnek yok: {HEDEF.relative_to(KOK)} (Lokman'ın onayıyla dondurulur)")
    h = json.loads(HEDEF.read_text(encoding="utf-8"))
    assert h["onay"]["karar"] == "D-98" and h["onay"]["soz"]
    cikti, _ = uretim("osb_kiremit")
    assert ozet(cikti) == h["ozet"]


def test_kaplama_satirlari():
    """Kiremit desen sac açılımın diziliminden; OSB yüzey × 1,20 ÷ 2,98; nem bariyeri yüzey; mahya ve OSB mahyası aynı adet; panel satırı yok."""
    cikti, _ = uretim("osb_kiremit")
    g = json.loads((cikti / "KT12_girdi.json").read_text(encoding="utf-8"))
    liste = json.loads((cikti / "KT12_yukleme.json").read_text(encoding="utf-8"))
    S = {}
    for s in liste["satirlar"]:
        S.setdefault(s["kalem"], []).append(s)
    c = g["cati"]
    assert c["kaplama"] == "osb_kiremit" and c["dizilim"]["kapatma_m"] == 1.0
    import math
    assert [(x["boyut"], x["adet"]) for x in S["Kiremit desen sac"]] == [
        (f"L {round(sat['boy_m'] * 1000)} · 100 cm kapatır", sat["adet"]) for sat in c["dizilim"]["satirlar"]]
    assert S["Çatı OSB"][0]["adet"] == math.ceil(c["yuzey_m2"] * 1.2 / 2.9768 - 1e-9)
    assert S["Nem bariyeri"][0]["adet"] == math.ceil(c["yuzey_m2"] - 1e-9) and S["Nem bariyeri"][0]["boyut"] == "m²"
    assert S["Metal kiremit mahyası"][0]["adet"] == S["OSB mahyası"][0]["adet"] > 0
    assert S["Mahya bandı"][0]["adet"] > 0                      # Lokman: mahya bandı kalır
    assert all(s["renk"] for s in S["Kiremit desen sac"])          # çatının rengiyle (gerçek listede ÇG10 ANTRAST)
    sac = sum(sat["boy_m"] * 1000 / 200 * sat["adet"] for sat in c["dizilim"]["satirlar"])
    assert S["Trapez vida (5,5 × 60)"][0]["olcu"] == pytest.approx(g["bina_m2"] * 2.5 + sac, abs=0.01)
    for yok in ("Tek kat panel", "Sandviç panel", "Trapez vida (5,5 × 76; tek kat panel)", "Metal kiremit (kiremit desen sac)", "Metal kiremit"):
        assert yok not in S


def test_cizimler_ayni_yalniz_pafta_satiri_degisir():
    """Çizimler kaplamadan bağımsız: plan, görünüşler, makaslar, duvar panelleri ve bayi görseli tek kat paneldekiyle bayt bayt aynı;
    liste yalnız kaplamaya bağlı satırlarda farklı; paftada yeni yazı çakışması yok."""
    k_cikti, k_rapor = uretim("osb_kiremit")
    t_cikti, t_rapor = uretim("tek_kat_panel")
    for ad in CIZIM_AYNI:
        assert (k_cikti / f"KT12_{ad}").read_bytes() == (t_cikti / f"KT12_{ad}").read_bytes(), ad
    satir = lambda d: {(s["grup"], s["kalem"], s["boyut"], s["adet"]) for s in json.loads((d / "KT12_yukleme.json").read_text(encoding="utf-8"))["satirlar"]}
    fark = {x[1] for x in satir(k_cikti) ^ satir(t_cikti)}
    assert fark == {"Çatı OSB", "Nem bariyeri", "Kiremit desen sac", "OSB mahyası", "Tek kat panel", "OSB ve yalıpan vidası (3,9 × 32)",
                    "Trapez vida (5,5 × 60)", "Trapez vida (5,5 × 76; tek kat panel)"}, fark
    # Örnek Şablon paftasının özetinde yalnız "Çatı Kaplaması" değişir; mühendis paftasında (pafta.png) bilgi satırı kaplamanın adını ve
    # levha sayısını yazar (bulgu 5)
    oz = [json.loads((d / "KT12_pafta_ozet.json").read_text(encoding="utf-8")) for d in (k_cikti, t_cikti)]
    farkli = sorted({a for a, v in _duz(oz[0])} ^ {a for a, v in _duz(oz[1])} | {a for (a, v), (b, w) in zip(_duz(oz[0]), _duz(oz[1])) if a != b or v != w})
    assert farkli == ["Çatı Kaplaması"], farkli
    for sayfa in ("pafta_sayfa_1", "pafta_sayfa_2", "KT12_plan_bayi.png"):
        for tur in ("cakisan", "cizgi_kapatan", "yay_kapatan", "sayfa_disi"):
            assert len(k_rapor[sayfa][tur]) <= len(t_rapor[sayfa][tur]), (sayfa, tur, k_rapor[sayfa][tur])
