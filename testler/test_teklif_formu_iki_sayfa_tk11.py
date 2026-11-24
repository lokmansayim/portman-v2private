"""D-152 · İki sayfalık bayi teklif formu: hedef örnek Mehmet Kapaklı Tek 63 m² (TK-11), mühürlü form (D-28 madde 2 ve 3).

Lokman 23 Kasım 2026 09:09:56 UTC (TK-10): "Kar marjını %25 yap teklif formundan malzeme listesini kaldık 1. sayfa teklif sayfası
2. sayfa kat planı kalsın sadece"; 09:10:50 UTC (TK-11): "aynısını 63 içinde yap"; kart 09:12:35 "Onaylıyorum". Ana koda alma:
Lokman 24 Kasım 2026 06:51:52 UTC "1-5 evet" (3. madde: 2 sayfalık teklif formunun yaması ana koda alınsın mı?).
Girdi depoda: İş Emri, 23 Kasım 06:19 CRM anlık görüntüsü, Kasım istisnası (D-120), bu eve özel fiyatlar (D-77), form girdisi.
Kod, eşleme ya da Motor bu formu değiştirirse test kırmızıdır; hedef yalnız Lokman'ın onayıyla yeniden dondurulur (D-02)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pymupdf
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import teklif as TK  # noqa: E402
from motor import dxf_out  # noqa: E402

HEDEF = KOK / "testler" / "teklif_formu" / "TK11" / "TK11_beklenen.json"
BAYRAK = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES


@pytest.fixture(scope="module")
def H():
    return json.loads(HEDEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def C(H, tmp_path_factory):
    g = H["girdi"]
    d = tmp_path_factory.mktemp("tk11") / "c"
    arg = [str(KOK / g["is_emri"]), str(d), "--tavan", g["tavan"], "--crm", str(KOK / g["crm"]), "--istisna", str(KOK / g["istisna"]),
           "--proje-fiyat", str(KOK / g["proje_fiyat"]), "--bayi", str(KOK / g["bayi"]), "--tarih", g["tarih"]]
    assert TK.main(arg + (["--oneri"] if g["oneri"] else [])) == 0
    return d


def test_sayilar(H, C):
    """Taban 361.841,51 TL, 136/136 satır fiyatlı; formda 452.301,89 TL (sabit fiyat, KDV %0)."""
    T = json.loads(next(C.glob("*_teklif.json")).read_text(encoding="utf-8"))
    o, b, B = T["secenekler"][0]["fiyat"]["ozet"], T["bayi_formu"], H["beklenen"]
    assert (o["toplam"], o["fiyatli"], o["satir"]) == (B["taban"], B["fiyatli_satir"], B["satir"])
    assert (b["birim"], b["toplam"], b["kdv_orani"], b["ekler"]["malzeme_listesi"]) == (B["birim"], B["toplam"], 0, False)


def test_iki_sayfa_muhurlu_formla_ayni(H, C):
    """Form 2 sayfa; her sayfanın metni mühürlü PDF'inkiyle aynı; 2. sayfa Motor'un ön onay paftası; Ek-1 yok."""
    B = H["beklenen"]
    with pymupdf.open(next(C.glob("*_teklif_formu.pdf"))) as d:
        assert d.page_count == B["sayfa"]
        metin = [" ".join(p.get_text(flags=BAYRAK).split()) for p in d]
        ciz2 = len(d[1].get_drawings())
    assert metin == B["sayfa_metni"]
    with tempfile.TemporaryDirectory() as t:
        ie = json.loads((KOK / H["girdi"]["is_emri"]).read_text(encoding="utf-8"))
        with pymupdf.open(Path(t) / dxf_out.uret(ie, t)["pdf"]) as m:
            pafta = len(m[0].get_drawings())
    assert pafta > 1000 and ciz2 == pafta
