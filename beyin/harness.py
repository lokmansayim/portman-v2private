"""Test koşumu: mesajlar.json + cikarim_*.json (LLM çıktıları) → kural katmanı → beklenen eylemle karşılaştır.

python3 -m beyin.harness            # rapor: beyin/testler/rapor.json ve stdout
Kanal öz-testi aynı koşumu `main(durum_dir=..., sessiz=True)` ile çağırır; canlı konuşma durumuna dokunmaz.
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path

from .sema import Talep
from .katalog import Katalog
from .konusma import Konusma, DURUM_DIR
from .karar import karar_ver, bayileri_yukle

T = Path(__file__).resolve().parent / "testler"


def main(durum_dir: Path | None = None, sessiz: bool = False, rapor_yaz: bool = True) -> tuple[int, int]:
    durum_dir = Path(durum_dir) if durum_dir else DURUM_DIR
    mesajlar = json.loads((T / "mesajlar.json").read_text(encoding="utf-8"))
    cikarim = {}
    for f in sorted(T.glob("cikarim_*.json")):
        for kayit in json.loads(f.read_text(encoding="utf-8")):
            cikarim[kayit["id"]] = kayit["talep"]
    if durum_dir.exists():
        shutil.rmtree(durum_dir)
    katalog = Katalog(); bayiler = bayileri_yukle()
    rapor, ok = [], 0
    for m in mesajlar:
        ham = cikarim.get(m["id"])
        satir = {"id": m["id"], "mesaj": m["mesaj"], "beklenen": m["beklenen"], "not": m["not"]}
        if ham is None:
            satir.update(eylem="(çıkarım yok)", uyum=False); rapor.append(satir); continue
        try:
            talep = Talep.model_validate(ham)
        except Exception as e:
            satir.update(eylem="(şema hatası)", hata=str(e)[:300], uyum=False); rapor.append(satir); continue
        k = Konusma(m["gonderen"], durum_dir)
        karar = karar_ver(talep, k, bayiler.get(m["gonderen"]), katalog, metin=m["mesaj"])
        uyum = karar.eylem in m["beklenen"].split("|")
        ok += uyum
        if karar.is_emri and rapor_yaz:
            (T / f"is_emri_{m['id']}.json").write_text(json.dumps(karar.is_emri, ensure_ascii=False, indent=1), encoding="utf-8")
        satir.update(niyet=talep.niyet, guven=talep.guven, kod=talep.katalog_kodu, varyant=[v.tur for v in talep.varyantlar],
                     eylem=karar.eylem, gerekce=karar.gerekce, cevap=karar.mesaj, uyum=uyum,
                     is_emri_no=(karar.is_emri or {}).get("is_emri_no"), asama=k.d["asama"])
        rapor.append(satir)
    if rapor_yaz:
        (T / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    if not sessiz:
        for s in rapor:
            isaret = "✓" if s["uyum"] else "✗"
            print(f"{isaret} #{s['id']:>2} [{s.get('niyet','-'):>10}/{s.get('guven','-'):>6}] → {s['eylem']:<9} ({s.get('gerekce','')[:48]})")
            print(f"      «{s['mesaj'][:70]}»")
            print(f"      → {s.get('cevap','')[:160]}")
        print(f"\n{ok}/{len(rapor)} beklenen eylemle uyumlu")
    return ok, len(rapor)


if __name__ == "__main__":
    main()
