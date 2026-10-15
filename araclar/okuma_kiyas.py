#!/usr/bin/env python3
"""İE-14 r3 · P4: LLM-önce okuma ile `celik_okuma`nın çevrimdışı kıyası (Lokman 14.10.2026, 4. madde; eski kod silinmez).

Her cümle, seçili modelin açık planına (tanım, pencere tablosu, çatı seçenekleri) karşı iki yoldan okunur:
- kural: `celik_okuma.oku` (bugün canlıda karar veren yol; ücretsiz)
- LLM: `degisiklik_okuyucu.oku` + kodla ayıklama (`denetle`). Üç kip:
    --kayit-dizini D   : D/<id>.json kayıtlı cevaplarını oynatır (LLM çağrısı yok, ücretsiz)
    --ucretli --tavan N: gerçek çağrı (anahtar ve Lokman'ın onayı gerekir; en çok N çağrı; cevaplar --kayit-dizini'ne yazılır)
    (ikisi de yoksa)   : LLM sütunu "llm_yok"; kural okuması baz çizgisi olarak yazılır
Çıktı: Markdown rapor + JSON (cümle, iki okuma, sınıf, insan etiketi). Sınıflar `beyin/okuma_kiyas.py`'de. Metinler numara maskeli.

Kullanım:
  python araclar/okuma_kiyas.py --cumleler testler/okuma/cumleler.json --rapor docs/raporlar/2026-10-15_Okuma_Kiyasi.md
  python araclar/okuma_kiyas.py ... --kayit-dizini testler/okuma/kayitlar
  python araclar/okuma_kiyas.py ... --ucretli --tavan 40 --kayit-dizini testler/okuma/kayitlar   # ücretli; onayla
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO, degisiklik_okuyucu as DO, numara, okuma_kiyas as OK, varyant  # noqa: E402


def _baglam(kod: str) -> dict:
    """Modelin tanımı, yapısı, pencere tablosu, çatı seçenekleri (katalog aday kaydıyla)."""
    adaylar = {a["kod"]: a for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8"))}
    a = adaylar[kod]
    t = json.loads((KOK / a["tanim"]).read_text(encoding="utf-8"))
    y = varyant._kur(t)
    catilar = [{"kod": x["kod"], "ad": (x.get("sunum") or {}).get("cati_adi") or ""} for x in [a] + [adaylar[v] for v in a.get("varyantlar") or []]] \
        if a.get("varyantlar") else []
    dis140 = "140" in str((t.get("duvar_siniflari") or {}).get("dis", {}).get("profil", ""))
    return {"t": t, "y": y, "katalog": a, "pencereler": CO.pencere_adaylari(t, y), "catilar": catilar, "dis140": dis140}


def kos(cumleler: list[dict], kayit_dizini: Path | None = None, ucretli: bool = False, tavan: int = 0) -> list[dict]:
    baglamlar: dict[str, dict] = {}
    cagri = 0
    out = []
    for c in cumleler:
        b = baglamlar.setdefault(c["model"], _baglam(c["model"]))
        metin = numara.maskele(c["metin"])
        llm = None
        kayit = (kayit_dizini / f"{c['id']}.json") if kayit_dizini else None
        if kayit and kayit.exists() and not ucretli:
            llm = DO.oku(metin, b["pencereler"], b["catilar"], b["dis140"], hazir=json.loads(kayit.read_text(encoding="utf-8")))
        elif ucretli and cagri < tavan:
            llm = DO.oku(metin, b["pencereler"], b["catilar"], b["dis140"], ayar={"backend": "anthropic"})
            cagri += llm.get("cagri") or 0
            if kayit and llm.get("durum") == "tamam":
                kayit.parent.mkdir(parents=True, exist_ok=True)
                kayit.write_text(json.dumps({"islemler": llm["islemler"], "bilgi": llm.get("bilgi") or []}, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
        k = OK.kiyas(metin, b["t"], b["katalog"], llm, b["pencereler"], {x["kod"] for x in b["catilar"]}, b["y"])
        out.append({"id": c["id"], "model": c["model"], "kaynak": c.get("kaynak"), "metin": metin, "etiket": c.get("etiket"), **k})
    return out


def rapor(sonuc: list[dict]) -> str:
    say = Counter(s["sinif"] for s in sonuc)
    satir = ["# LLM-önce okuma ↔ celik_okuma kıyası (İE-14 r3, P4)", "",
             "Kural okuması bugün karar veren yoldur; LLM okuması gölgededir. Sınıf yalnız farkı gösterir; doğru olanı insan etiketi söyler. "
             "Hedef yok: önce ölçülür (Lokman 14.10, 6. madde).", "",
             "| Sınıf | Cümle |", "|---|---|"] + [f"| {s} | {say.get(s, 0)} |" for s in OK.SINIFLAR + ("llm_yok",) if say.get(s)] + ["",
             "| # | Kaynak | Cümle | Kural | LLM | Sınıf | Etiket |", "|---|---|---|---|---|---|---|"]

    def oz(o):
        if o is None:
            return "—"
        p = "; ".join(" ".join(str(x) for x in g) for g in o["ogeler"]) or "değişiklik yok"
        if o.get("okunamayan"):
            p += f" · okunamayan {len(o['okunamayan'])}"
        if o.get("hata"):
            p = f"hata: {o['hata']}"
        return p.replace("|", "/")
    for s in sonuc:
        satir.append(f"| {s['id']} | {s.get('kaynak') or ''} | {s['metin'].replace('|', '/')} | {oz(s['kural'])} | {oz(s['llm'])} | {s['sinif']} | "
                     f"{s.get('etiket') or ''} |")
    return "\n".join(satir) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LLM-önce okuma ↔ celik_okuma kıyası")
    ap.add_argument("--cumleler", type=Path, default=KOK / "testler" / "okuma" / "cumleler.json")
    ap.add_argument("--rapor", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--kayit-dizini", type=Path)
    ap.add_argument("--ucretli", action="store_true", help="gerçek LLM çağrısı (ücretli; Lokman'ın onayıyla)")
    ap.add_argument("--tavan", type=int, default=0)
    a = ap.parse_args(argv)
    if a.ucretli and a.tavan <= 0:
        ap.error("--ucretli için --tavan gerekli")
    doc = json.loads(a.cumleler.read_text(encoding="utf-8"))
    sonuc = kos(doc["cumleler"], a.kayit_dizini, a.ucretli, a.tavan)
    if a.rapor:
        a.rapor.write_text(rapor(sonuc), encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=list) + "\n", encoding="utf-8")
    say = Counter(s["sinif"] for s in sonuc)
    print(f"{len(sonuc)} cümle · " + " · ".join(f"{k} {v}" for k, v in sorted(say.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
