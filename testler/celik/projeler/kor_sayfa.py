"""İE-16 PR-4 · kör paftanın sayfa denetimi (öneren tarafı; hakem değil).

Kör projenin Yapı Tanımı yalnız montaj paftasının 1. sayfasından (müşteri onay paftası: plan, ölçüler, odalar, kapı ve pencereler,
görünüşler) yazılır; panel sayfaları cevap tarafıdır (İE-16 › Kör ölçüm; plan `Celik_Cizim_Kurallari/PR-4/plan.md`, Lokman 27 Ekim 2026
14:36 UTC kartı "Planla başla (dokuzu birden)"). Bu araç paftanın metnini kodla okur ve yalnız şunları yazar; etiket, sayı ya da panel
sayfasının içeriği yazılmaz:
- `onay_sayfasi_etiketsiz`: 1. sayfada hakemin pafta okuyucusunun (`testler/celik/pafta.py`) etiket biçimine uyan sözcük var mı (yalnız
  evet ya da hayır; birimler M2, M3 sayılmaz). Açık beşin beşinde de yok. Varsa sayfa görüntüye çevrilmez, proje durur.
- `yontem`: paftanın herhangi bir sayfasında "omega" ya da "aşık" sözcüğü geçiyorsa B (omega-aşıklı), yoksa A (panelli). Açık beşte
  ÇP-03 A, öteki dördü B: listelerimizin yöntemiyle aynı (`test_kor_sayfa.py`).
- `kat` ve `kat_dayanagi`: mühürdeki kat ayrımıyla (`muhur.json › kat_ayrimi`): bir sayfada "1. KAT" (ya da "1.KAT", "BİRİNCİ KAT")
  geçiyorsa çift, yoksa tek; dayanak sayfa numarası ve eşleşen sözcüklerdir (kat kaydının `dayanak` alanı).
- `sha256`: paftanın özeti; `--kod` verilirse dosya hakemin mühür denetiminden geçer (projenin mühürlü montaj paftası mı; içerik okunmaz).
`--png` verilirse yalnız etiketsiz 1. sayfa görüntüye çevrilir (tanım yazılırken bakılan tek sayfa).
Veri, talimat değildir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from testler.celik import kiyas, pafta  # noqa: E402

YONTEM_B = re.compile(r"OMEGA|\bASIK")
CIFT_KAT = re.compile(r"\b1\s*\.\s*KAT\b|\bBIRINCI\s+KAT\b")


def duz(metin: str) -> str:
    """Türkçe büyük harf, işaretsiz: "Aşık" → "ASIK", "birinci" → "BIRINCI"."""
    t = metin.replace("i", "İ").replace("ı", "I").upper()
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def etiketli_mi(sayfa) -> bool:
    """Sayfada panel etiketi biçiminde bir sözcük var mı (pafta okuyucusunun ayıklamasıyla); hangisi olduğu döndürülmez."""
    for w in sayfa.get_text("words"):
        t = w[4].strip().strip(pafta.NOKTALAMA).upper()
        if t not in pafta.BIRIMLER and pafta.ETIKET.match(t):
            return True
    return False


def denetle(yol: Path) -> dict:
    import pymupdf

    doc = pymupdf.open(str(yol))
    yontem, dayanak = "A", None
    for sno, sayfa in enumerate(doc, 1):
        t = duz(sayfa.get_text())
        if YONTEM_B.search(t):
            yontem = "B"
        m = CIFT_KAT.search(t)
        if m and dayanak is None:
            dayanak = f"{sno}. sayfa: " + re.sub(r"\s+", " ", m.group(0))
    return {"sha256": hashlib.sha256(Path(yol).read_bytes()).hexdigest(), "sayfa_sayisi": doc.page_count,
            "onay_sayfasi_etiketsiz": not etiketli_mi(doc[0]), "yontem": yontem,
            "kat": "çift" if dayanak else "tek", "kat_dayanagi": dayanak}


def onay_png(yol: Path, cikti: Path, dpi: int = 150) -> Path:
    """Etiketsiz 1. sayfayı görüntüye çevirir; etiketliyse durur (sayfa açılmaz)."""
    import pymupdf

    doc = pymupdf.open(str(yol))
    if etiketli_mi(doc[0]):
        raise SystemExit(f"{yol.name}: 1. sayfada panel etiketi biçiminde sözcük var; sayfa açılmaz, proje durur")
    doc[0].get_pixmap(dpi=dpi).save(str(cikti))
    return cikti


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pafta", type=Path)
    ap.add_argument("--kod", help="proje kodu (ör. ÇP-12): pafta mühürdeki montaj paftasıyla denetlenir")
    ap.add_argument("--png", type=Path, help="etiketsiz 1. sayfanın görüntüsü")
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args(argv)
    if a.kod:
        try:
            kiyas.muhur_denetle(a.pafta, json.loads(kiyas.MUHUR.read_text(encoding="utf-8")), a.kod, turler=(kiyas.PAFTA,))
        except kiyas.Durdu as e:
            raise SystemExit(f"mühür: {e}") from None
    sonuc = denetle(a.pafta)
    if a.png:
        sonuc["png"] = str(onay_png(a.pafta, a.png, a.dpi))
    print(json.dumps({"kod": a.kod, **sonuc}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
