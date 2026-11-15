"""İE-43 PR-3 · Arşivin 2019–2020 yükleme listesinden (Excel) malzeme satırları.

Şablon: sayfalar TEKLİF, SEVKİYAT, İMALAT, DEPO; başlık satırı "S | Malzeme | Malzeme Ölçüsü | Adet". Evin gerçek listesi TEKLİF
sayfasındadır; SEVKİYAT ve İMALAT her evde aynıdır (şablondan kalmış), okunmaz. Grup satırı ("KOD:" ölçü sütununda) atılır.
Okuma kör testin okuyucusuyla (`testler/kor/oku.py`). Excel'de TC kimlik no, telefon ve adres vardır: araç yalnız malzeme satırını yazar
(malzeme, boyut, adet); dosya Mac'te koşulur, çıktı Mac'ten yalnız malzeme satırlarıyla çıkar.

    python3 araclar/hdd_turev/liste_oku.py <kök klasör> '{"HD-252": "<göreli yol>.xlsx", ...}' <çıktı.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.kor import oku  # noqa: E402

SAYFA = ("TEKLİF", "TEKLIF")
if "MALZEME ÖLÇÜSÜ" not in oku.SUTUN_BOYUT:
    oku.SUTUN_BOYUT = oku.SUTUN_BOYUT + ("MALZEME ÖLÇÜSÜ",)


def oku_liste(yol: Path) -> dict:
    """Excel → {"sayfa", "satirlar": [{grup, malzeme, boyut, adet}], "okunmayan"}; TEKLİF sayfası yoksa OkumaHatasi."""
    import openpyxl
    s: dict = {}
    wb = openpyxl.load_workbook(str(yol), data_only=True, read_only=True)
    adlar = [ws.title.strip().upper() for ws in wb.worksheets]
    i = next((k for k, a in enumerate(adlar) if a in SAYFA), None)
    if i is None:
        raise oku.OkumaHatasi(f"TEKLİF sayfası yok: {adlar}")
    satir = [x for x in oku.excel_sayfasi(wb.worksheets[i], s) if (x.get("boyut") or "").upper() != "KOD:"]
    return {"sayfa": wb.worksheets[i].title, "satirlar": satir, "okunmayan": s}


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 3:
        print(__doc__); return 2
    kok, esle, cikti = Path(a[0]), json.loads(a[1]), Path(a[2])
    R = {}
    for kod, yol in esle.items():
        try:
            R[kod] = oku_liste(kok / yol)
        except Exception as e:                     # okunamayan liste kayda hata olarak girer, sessizce düşmez
            R[kod] = {"hata": f"{type(e).__name__}: {str(e)[:200]}"}
    cikti.write_text(json.dumps(R, ensure_ascii=False), encoding="utf-8")
    for k, v in R.items():
        dolu = sum(1 for x in v.get("satirlar", []) if isinstance(x.get("adet"), (int, float)) and x["adet"] > 0)
        print(k, v.get("sayfa"), len(v.get("satirlar", [])), dolu, v.get("hata", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
