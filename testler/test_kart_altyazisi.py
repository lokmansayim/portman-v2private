"""İE-08 PR-2a (Lokman'ın göz denetimi, 12 Ekim 2026): seçenek görselinde çelik kartının alt yazısı kesilmez ve sayılar Türkçe biçimde;
prefabrik kartının alt yazısı bugünkü tek satır olarak değişmez."""
from __future__ import annotations
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from motor import bayi_gorseli as BG  # noqa: E402

CELIK_K = {"kod": "Ç8801K", "gosterim": "Ç8801-K", "motor": "genel", "katalog_m2": 88.0, "kapali_m2": 74.33, "veranda_m2": 13.73,
           "sunum": {"cati_adi": "Beşik + cumba, doğu ucu kırma", "ad": "x"}, "sira": 2, "puan": None}
PREFAB = {"kod": "P6001", "katalog_m2": 60, "kapali_m2": 58.37, "sira": 1, "puan": 100}


def test_celik_altyazi_iki_satir_turkce_sayi():
    assert BG.kart_altyazisi(CELIK_K) == ["88 m² katalog · kapalı 74,3 m²", "Çatı: Beşik + cumba, doğu ucu kırma"]
    assert BG._tr(74.33) == "74,3" and BG._tr(88.0) == "88" and BG._tr(92.27) == "92,3" and BG._tr("?") == "?"
    assert BG.kart_altyazisi({**CELIK_K, "sunum": {}}) == ["88 m² katalog · kapalı 74,3 m²"]


def test_prefabrik_altyazi_degismez():
    # bugünkü biçim aynen (prefabrik seçenek görseli değişmez — Lokman 12.10)
    assert BG.kart_altyazisi(PREFAB) == ["60 m² katalog · kapalı 58.37"]
    assert BG.kart_altyazisi({**PREFAB, "sunum": {"cati_adi": "Kırma"}}) == ["Kırma · 60 m² katalog · kapalı 58.37"]


def test_sigdir_kesmez_once_kucultur(tmp_path):
    from PIL import Image, ImageDraw
    import matplotlib.font_manager as fm
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    font_yol = fm.findfont("DejaVu Sans")
    metin = "Çatı: Beşik + cumba, doğu ucu kırma"
    f, s = BG._sigdir(d, metin, font_yol, 16, 584)                 # çelik paneli 600 px: sığar, kesilmez
    assert s == metin and f.size == 16
    f2, s2 = BG._sigdir(d, metin, font_yol, 16, 240)               # dar yer: önce küçülür
    assert s2 == metin and 12 <= f2.size < 16
    f3, s3 = BG._sigdir(d, metin, font_yol, 16, 60)                # çok dar: en küçük boyda "…" ile kısalır
    assert f3.size == 12 and s3.endswith("…") and len(s3) < len(metin)


def test_bilesik_gorsel_celik_karti_cizer(tmp_path):
    from PIL import Image
    kart = tmp_path / "kart.png"; Image.new("RGB", (900, 700), "white").save(kart)
    adaylar = [{**CELIK_K, "gorsel_yolu": kart, "sira": i, "puan": p} for i, p in ((1, 100), (2, 98), (3, None))]
    yol = BG.bilesik_gorsel(adaylar, tmp_path / "secenekler.png", baslik="Ç8801", panel_px=600)
    assert yol and yol.is_file() and Image.open(yol).size == (16 + 3 * 616, 64 + 600 + 96)
