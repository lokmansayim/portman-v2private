"""Arşiv montaj paftasından İş Emri (`araclar/hdd_turev/plan_geometri.py`), pano dizilimi uydurma (`uydur.py`) ve kıyas (`pafta_kiyas.py`).

Gerçek pafta depoya girmez (kişisel veri; İE-43). 2019–2020 şablonundaki bir ev burada kodla çizilir: 10'luk dış duvar, 6'lık iç duvar,
duvar yüzleri pano pano (her pano bir dikdörtgen), pencere bloğu ve yazısı, kapı yayı, oda yazıları, başlık ve ölçüler. Beklenen:
okuyucu gövdeyi, odaları, açıklıkları ve pano eklerini paftadaki gibi okur; Motor'un kurduğu plan paftayla duvar duvar aynıdır (pembe 0);
pafta düzeltilmez (okuyucu çizilmeyen şeyi yazmaz), kutu profil kolonun iç karesi ikinci kolon sayılmaz.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "araclar" / "hdd_turev"))
ezdxf = pytest.importorskip("ezdxf")
pytest.importorskip("shapely")
import pafta_kiyas as kiyas  # noqa: E402  (testler/kimlik/hakem/kiyas.py ile ad çakışmasın)
import pafta_kart  # noqa: E402
import plan_geometri as PG  # noqa: E402
import uydur  # noqa: E402

MOD = 125.5
W, H = 4 * MOD + 10, 3 * MOD + 20            # 512 × 396,5: uzun duvarlar (yatay) aksın dışında, kısa duvarlar aksa ortalı (2020 düzeni)
XI = 5 + 2 * MOD                              # 6'lık iç duvarın aksı (256)


def _pano(m, x0, y0, x1, y1):
    m.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True)


def _duvar(m, yon, c, a0, a1, t, ekler):
    """Duvar: yüzden yüze pano dikdörtgenleri (ekler duvar boyunca)."""
    E = [a0] + [e for e in ekler if a0 < e < a1] + [a1]
    for a, b in zip(E, E[1:]):
        if yon == "y":                        # yatay duvar (y sabit)
            _pano(m, a, c - t / 2, b, c + t / 2)
        else:
            _pano(m, c - t / 2, a, c + t / 2, b)


def _cizim(yol: Path, kolon=False):
    d = ezdxf.new("R2018")
    pen = d.blocks.new("BFGNBFGN")            # 2019–2020 şablonunun pencere panosu bloğu
    pen.add_lwpolyline([(0, 0), (MOD, 0), (MOD, 10), (0, 10)], close=True)
    pen.add_line((2.75, 5), (MOD - 2.75, 5))
    m = d.modelspace()
    ek = [5 + MOD * k for k in range(1, 4)]
    # yatay (uzun) dış duvar düşey duvarın aksından aksına; köşede 5 × 10 cm boş (paftada köşe direği), düşey duvar yatayların arasında
    _duvar(m, "y", 5, 5, W - 5, 10, ek)       # ön duvar (y = 0 … 10)
    _duvar(m, "y", H - 5, 5, W - 5, 10, ek)   # arka duvar
    dik = [10 + MOD, 10 + 2 * MOD]
    _duvar(m, "x", 5, 10, H - 10, 10, dik)
    _duvar(m, "x", W - 5, 10, H - 10, 10, dik)
    _duvar(m, "x", XI, 10, H - 10, 6, dik)
    # pencere: salonun arka duvarında, ikinci panoda (blok panonun yerinde)
    m.add_blockref("BFGNBFGN", (5 + MOD, H - 10))
    m.add_text("120/120", dxfattribs={"height": 12, "insert": (5 + MOD + 20, H + 15)})
    # iç kapı: iç duvarda, ön duvardan ikinci panoda; yay merkezi duvarın yüzünde
    m.add_arc((XI + 3, 10 + MOD + 20), 82, 0, 90)
    m.add_line((XI + 3, 10 + MOD + 20), (XI + 3, 10 + MOD + 102))
    # dış kapı: ön duvarda, Y.ODASI'nın değil salonun ikinci panosunda
    m.add_arc((5 + MOD + 20, 10), 90, 0, 90)
    m.add_line((5 + MOD + 20, 10), (5 + MOD + 20, 100))
    m.add_mtext("SALON\\P30.00 m²", dxfattribs={"insert": (100, 250), "char_height": 12})
    m.add_mtext("Y.ODASI\\P15.00 m²", dxfattribs={"insert": (350, 250), "char_height": 12})
    m.add_text("Deneme Kişi 20 M2", dxfattribs={"height": 40, "insert": (0, H + 120)})
    m.add_text("MONTAJ VE ELEKTRİK PLANI", dxfattribs={"height": 40, "insert": (100, -140)})
    m.add_linear_dim(base=(0, H + 60), p1=(0, H), p2=(W, H), angle=0).render()
    m.add_linear_dim(base=(W + 60, 0), p1=(W, 0), p2=(W, H), angle=90).render()
    if kolon:                                  # kutu profil kolon: dış ve iç kare (iç kare ikinci kolon değildir)
        m.add_lwpolyline([(W + 100, 0), (W + 110, 0), (W + 110, 10), (W + 100, 10)], close=True)
        m.add_lwpolyline([(W + 102, 2), (W + 108, 2), (W + 108, 8), (W + 102, 8)], close=True)
    d.saveas(yol)
    return yol


@pytest.fixture()
def okunan(tmp_path):
    yol = _cizim(tmp_path / "pafta.dxf")
    P = pafta_kart.oku(str(yol))
    j = next(i for i, p in enumerate(P) if p["alt_yazi"] == "montaj" and not p["kopya"])
    doc = pafta_kart.yukle(str(yol))
    g = PG.geometri(doc, P[j]["kutu_dunya"], P[j])
    ie = PG.is_emri(g, P[j], "HD-000", P[j].get("teknik"))
    return g, ie


def test_govde_odalar_aciklik(okunan):
    g, ie = okunan
    assert (g["W"], g["H"]) == (W, H)
    assert ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 6.0}
    assert {m["ad"]: m["tur"] for m in ie["mahaller"]} == {"SALON": "salon", "Y.ODASI": "yatak_odasi"}
    tur = sorted(a["tur"] for a in ie["acikliklar"])
    assert tur == ["dis_kapi", "ic_kapi", "pencere"]
    pen = next(a for a in ie["acikliklar"] if a["tur"] == "pencere")
    assert pen["olcu"] == "120x120" and pen["mahal"] == "SALON"
    assert "Deneme" not in json.dumps(ie, ensure_ascii=False)          # ad İş Emri'ne yazılmaz


def test_motor_dizilimi_paftayla_ayni(okunan, tmp_path):
    g, ie = okunan
    satir, ac, plan = kiyas.karsilastir(g, ie)
    if any(not s["ayni"] for s in satir):                                # dayanakla uydur, sonra yeniden kıyasla
        (tmp_path / "g.json").write_text(json.dumps(g)); (tmp_path / "ie.json").write_text(json.dumps(ie))
        sys.argv = ["uydur.py", str(tmp_path / "g.json"), str(tmp_path / "ie.json"), str(tmp_path / "ieu.json")]
        uydur.main()
        ie = json.loads((tmp_path / "ieu.json").read_text())
        satir, ac, plan = kiyas.karsilastir(g, ie)
    assert len(satir) == 5                                               # dört dış, bir iç duvar
    assert all(s["ayni"] for s in satir), [s for s in satir if not s["ayni"]]
    assert all(uydur.pembe(s) == 0 for s in satir)
    assert all(a["motor"] is not None for a in ac)


def test_kutu_profil_kolon_tek_sayilir(tmp_path):
    yol = _cizim(tmp_path / "kolonlu.dxf", kolon=True)
    doc = pafta_kart.yukle(str(yol))
    S, bloklar, kesik, kare, yaylar, olcu_yazi, tefris = PG.topla(doc, (-200, -300, W + 300, H + 300))
    assert len(kare) == 2                                                # çizimde iki kare
    g = PG.geometri(doc, (-200, -300, W + 300, H + 300), {"mahaller": [], "acikliklar": [], "kutu_dunya": (-200, -300, W + 300, H + 300)})
    assert len(g["kolonlar"]) == 1                                       # okuyucu tek kolon yazar


def _kare(x, y, k=8.0):
    return [x, y, x + k, y + k]


def test_veranda_ara_kolonu_paftadan():
    """D-109 (kart 16 Kasım 2026 08:42:16 "Kolon arası en çok 565 cm"): kısa verandada paftanın ara kolonu İş Emri'ne `ara_kolon` olur."""
    v = {"cephe": "on", "bas_cm": 0.0, "bit_cm": 449.25, "derinlik_cm": 200.0,
         "kolonlar": [_kare(0, 400), _kare(220.6, 400), _kare(441.25, 400)]}          # ortada, eşit aralıkta (224,6)
    ara, not_ = PG.veranda_ara_kolonu(v, 396.5)
    assert ara == 1 and "ara_kolon: 1" in not_ and "eşit aralıkla" not in not_
    v["kolonlar"][1] = _kare(150, 400)                                                  # pafta düzeltilmez: yer farkı nota
    ara, not_ = PG.veranda_ara_kolonu(v, 396.5)
    assert ara == 1 and "154 cm'de" in not_ and "224.6 cm'ye" in not_
    s = {"cephe": "sag", "bas_cm": 0.0, "bit_cm": 453.2, "derinlik_cm": 200.0,       # sağ cephe: gerçek çerçeve y önden (H - y)
         "kolonlar": [_kare(700, 388.5), _kare(700, 165.9), _kare(700, -56.7)]}
    ara, not_ = PG.veranda_ara_kolonu(s, 396.5)
    assert ara == 1 and "eşit aralıkla" not in not_
    s["kolonlar"][1] = _kare(700, 250)                                                  # önden 142,5: fark nota
    assert "142.5 cm'de" in PG.veranda_ara_kolonu(s, 396.5)[1]


def test_veranda_ara_kolonu_kural():
    iki = lambda en: {"cephe": "on", "bas_cm": 0.0, "bit_cm": en, "derinlik_cm": 200.0, "kolonlar": [_kare(0, 400), _kare(en - 8, 400)]}
    assert PG.veranda_ara_kolonu(iki(453.2), 396.5) == (None, None)                    # 92 m²: iki köşe kolonu, not yok
    ara, not_ = PG.veranda_ara_kolonu(iki(710.25), 396.5)                               # 565'i geçen: Motor koyar, İş Emri yazmaz
    assert ara is None and "1 ara kolon koyar" in not_
    uc = iki(1200.0); uc["kolonlar"].insert(1, _kare(596, 400))                         # pafta kuraldan az gösteriyor: sayı yazılmaz
    ara, not_ = PG.veranda_ara_kolonu(uc, 396.5)
    assert ara is None and "2 ara kolon koyar" in not_
