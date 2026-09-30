"""İE-04 · Aday kaydı: İş Emri JSON → Motor koşumu → özet, şablon, bayi görseli ve kayıt satırı.

    python3 araclar/aday_kaydet.py <is_emri.json> --kod TEST01 --durum test --katalog-m2 94 [--referans P9401] [--kaynak "…"] [--not "…"]
                                   [--ayna x|y] [--test-dosyasi]

Yazdıkları: is_emri/adaylar/<kod>.json (şablon; is_emri_no PM-ADAY-<kod>, revizyon 1), is_emri/adaylar/<kod>.png (bayi görseli),
beyin/veri/adaylar.json (ya da --test-dosyasi ile adaylar_test.json) içinde <kod> satırı (varsa yenilenir).
Özet Motor doğrulamasından gelir (oda alanları, pano, pencere, kapı, dış ölçü); kapalı alan = dış kutu − veranda (kutu içi).
'gecerli' durum burada verilmez: K-A9 denetimi ve K-A10 kabulü Postgres'te kayıtlıyken ayrıca verilir (docs/is_emirleri/IE-04-aday-teslimi.md).
"""
from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("is_emri"); ap.add_argument("--kod", required=True); ap.add_argument("--durum", choices=["test", "kosullu"], default="test")
    ap.add_argument("--katalog-m2", type=float, required=True); ap.add_argument("--referans", default=None); ap.add_argument("--kaynak", default="")
    ap.add_argument("--not", dest="not_", default=""); ap.add_argument("--ayna", choices=["x", "y"], default=None)
    ap.add_argument("--test-dosyasi", action="store_true", help="kaydı beyin/veri/adaylar_test.json'a yaz (yalnız yerel testlerde yüklenir)")
    a = ap.parse_args()
    from motor import dxf_out, bayi_gorseli as BG
    from beyin import varyant
    ie = json.loads(Path(a.is_emri).read_text(encoding="utf-8"))
    if a.ayna:
        ie = varyant.ayna(ie, a.ayna)
    kod = a.kod.upper()
    ie["is_emri_no"] = f"PM-ADAY-{kod}"; ie["revizyon"] = 1
    ie.setdefault("yapi", {})["referans_model"] = a.referans or ie.get("yapi", {}).get("referans_model")
    ie["talep"] = {"bayi": {"kod": "ADAY", "ad": "Aday kaydı"}, "musteri_adi": f"ADAY {kod}", "metin": a.kaynak or ie.get("talep", {}).get("metin", "")}
    with tempfile.TemporaryDirectory() as t:
        m = dxf_out.uret(ie, Path(t))
        v = json.loads((Path(t) / "validation.json").read_text(encoding="utf-8"))
        if not v.get("passed"):
            print("DUR: Motor doğrulaması geçmedi:", v.get("errors")); return 1
        rooms = v.get("rooms_m2") or {}
        W, H = v.get("outer_cm") or [0, 0]
        veranda = round(sum(m2 for ad, m2 in rooms.items() if ad.upper().startswith(("VERANDA", "SUNDURMA", "BALKON", "TERAS"))), 2)
        kapali = round(W * H / 1e4 - veranda, 1)
        oda_prog = ie.get("oda_programi") or _oda_programi(ie)
        sablon_dir = KOK / "is_emri" / "adaylar"; sablon_dir.mkdir(parents=True, exist_ok=True)
        (sablon_dir / f"{kod}.json").write_text(json.dumps(ie, ensure_ascii=False, indent=1), encoding="utf-8")
        BG.plan_gorseli(ie, sablon_dir / f"{kod}.png", v)
        kayit = {"kod": kod, "durum": a.durum, "sablon": f"adaylar/{kod}.json", "gorsel": f"adaylar/{kod}.png", "referans_model": ie["yapi"].get("referans_model"),
                 "yapi_turu": "prefabrik", "oda_programi": oda_prog, "katalog_m2": a.katalog_m2, "kapali_m2": kapali, "veranda_m2": veranda,
                 "ozet": {"grid": ie["yapi"]["grid"], "dis_olcu_cm": [W, H], "pano": v.get("panel_count"), "pencere": v.get("windows"), "kapi": v.get("doors"),
                          "odalar": {k: round(x, 2) for k, x in rooms.items()}},
                 "kaynak": {"metin": a.kaynak, "dosya": str(Path(a.is_emri)), "ayna": a.ayna}, "not": a.not_}
    yol = KOK / "beyin" / "veri" / ("adaylar_test.json" if a.test_dosyasi else "adaylar.json")
    liste = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else []
    liste = [x for x in liste if str(x.get("kod")).upper() != kod] + [kayit]
    yol.write_text(json.dumps(liste, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: kayit[k] for k in ("kod", "durum", "oda_programi", "katalog_m2", "kapali_m2", "veranda_m2")}, ensure_ascii=False), "→", yol.name)
    return 0


def _oda_programi(ie: dict) -> str:
    yatak = sum(1 for m in ie.get("mahaller", []) if m.get("tur") == "yatak_odasi")
    salon = 1 if any(m.get("tur") in ("salon", "mutfak") for m in ie.get("mahaller", [])) else 0
    return f"{yatak}+{salon}"


if __name__ == "__main__":
    sys.exit(main())
