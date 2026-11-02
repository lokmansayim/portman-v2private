"""İE-04 / İE-08 · Aday kaydı: (prefabrik) İş Emri JSON → Motor koşumu → özet, şablon, bayi görseli ve kayıt satırı;
(çelik, `--motor genel`) Yapı Tanımı → genel motor koşumu → bayi görseli (aday kartı) ve kayıt satırı.

    python3 araclar/aday_kaydet.py <is_emri.json> --kod TEST01 --durum test --katalog-m2 94 [--referans P9401] [--kaynak "…"] [--not "…"]
                                   [--ayna x|y] [--test-dosyasi]
    python3 araclar/aday_kaydet.py --motor genel --tanim modeller/C8801.json [--kod Ç8801] [--durum gecerli] [--referans Ç8801]
                                   [--varyantlar Ç8801K,Ç8801L] [--kat 1] [--musteri-projesi] [--kaynak "…"] [--not "…"] [--perspektifsiz]

Yazdıkları (prefabrik): is_emri/adaylar/<kod>.json (şablon; is_emri_no PM-ADAY-<kod>, revizyon 1), is_emri/adaylar/<kod>.png (bayi görseli),
beyin/veri/adaylar.json (ya da --test-dosyasi ile adaylar_test.json) içinde <kod> satırı (varsa yenilenir).
Özet Motor doğrulamasından gelir (oda alanları, pano, pencere, kapı, dış ölçü); kapalı alan = dış kutu − veranda (kutu içi).
Prefabrikte 'gecerli' durum burada verilmez: K-A9 denetimi ve K-A10 kabulü Postgres'te kayıtlıyken ayrıca verilir (IE-04-aday-teslimi.md).

Çelik (İE-08 Adım 8; D-08 madde 4, D-10): tanım `modeller/` altında durur (gömülmez; sha256 kayda yazılır), çizim `motor.genel.uret` ile
geçici klasörde koşar (perspektifli: aday kartında ön-sağ ve arka-sağ perspektif, VTK yoksa görünüşler), bayi görseli
`is_emri/adaylar/<kod>.png` (= `<kod>_bayi_gorsel.png`). Kayıt `durum: gecerli` yazılabilir (Lokman, 12 Ekim 2026: yedi aday gecerli);
bayiye sunulma yine K-A10 kabul kaydına bağlıdır (`araclar/aday_kabul.py`, mühendis yedi modeli kabul paketiyle görür). Alan
(`katalog_m2`) brüt oturumdur: yükleme listesindeki `bina_m2` (K-A1, D-08 madde 5). KT'ler müşteri projesidir, bayiye adsız.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))


def kod_normalize(s: str) -> str:
    """Aday kodu (Ç8801-K → Ç8801K, KT-01 → KT01): tek kaynak `beyin.katalog.Katalog.kod_normalize`."""
    from beyin.katalog import Katalog
    return Katalog.kod_normalize(s) or s.strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("is_emri", nargs="?"); ap.add_argument("--motor", choices=["pano", "genel"], default="pano")
    ap.add_argument("--tanim", default=None, help="çelik: Yapı Tanımı (modeller/<kod>.json)")
    ap.add_argument("--kod", default=None); ap.add_argument("--durum", choices=["test", "kosullu", "gecerli"], default="test")
    ap.add_argument("--katalog-m2", type=float, default=None); ap.add_argument("--referans", default=None); ap.add_argument("--kaynak", default="")
    ap.add_argument("--not", dest="not_", default=""); ap.add_argument("--ayna", choices=["x", "y"], default=None)
    ap.add_argument("--varyantlar", default="", help="çelik: aynı planın çatı varyantları (virgülle; yalnız katalog modelinde)")
    ap.add_argument("--kat", type=int, default=None); ap.add_argument("--musteri-projesi", action="store_true")
    ap.add_argument("--perspektifsiz", action="store_true", help="çelik: aday kartında perspektif yerine görünüşler")
    ap.add_argument("--test-dosyasi", action="store_true", help="kaydı beyin/veri/adaylar_test.json'a yaz (yalnız yerel testlerde yüklenir)")
    a = ap.parse_args()
    if a.motor == "genel":
        return genel(a)
    if not a.is_emri or not a.kod or a.katalog_m2 is None:
        print("DUR: prefabrik aday için <is_emri.json>, --kod ve --katalog-m2 gerekir"); return 2
    if a.durum == "gecerli":
        print("DUR: prefabrik adayda 'gecerli' burada verilmez (K-A9/K-A10, IE-04-aday-teslimi.md)"); return 2
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
    _yaz(kayit, a.test_dosyasi)
    return 0


def genel(a) -> int:
    """Çelik aday: Yapı Tanımı genel motorla çizilir, bayi görseli aday kartı olur, kayıt satırı yazılır (D-08 madde 4, D-10)."""
    if not a.tanim:
        print("DUR: --motor genel için --tanim gerekir"); return 2
    from motor.genel import uret as U, yapi, cati_genel, kural, girdi_genel
    from motor.genel.bayi_gorseli import oda_programi, musteri_projesi, sahip_adi
    tanim_yolu = Path(a.tanim)
    if not tanim_yolu.is_absolute():
        tanim_yolu = KOK / tanim_yolu
    try:
        gorece = tanim_yolu.resolve().relative_to(KOK).as_posix()        # kayıt depo köküne göre yol taşır (zarf da öyle)
    except ValueError:
        print("DUR: tanım depo kökünün altında olmalı (modeller/<kod>.json):", tanim_yolu); return 2
    t = json.loads(tanim_yolu.read_text(encoding="utf-8"))
    kod = kod_normalize(a.kod or t["kod"])
    with tempfile.TemporaryDirectory() as tmp:
        m = U.uret(tanim_yolu, Path(tmp), is_emri_no=None, revizyon=None, set_yolu=None, yontem="panel", perspektif=not a.perspektifsiz, bayi=True,
                   kaynak=f"Yapı Tanımı 0.5 ({tanim_yolu.name})")          # revizyon None: aday kartında "TASLAK", r01 yok (Lokman 12.10)
        v = json.loads((Path(tmp) / "validation.json").read_text(encoding="utf-8"))
        if not m.get("passed"):
            print("DUR: genel motor doğrulaması geçmedi:", v.get("errors")); return 1
        if not m.get("bayi_gorsel"):
            print("DUR: bayi görseli üretilmedi:", v.get("warnings")); return 1
        gk = U.kod_govde(t)
        girdi = json.loads((Path(tmp) / f"{gk}_girdi.json").read_text(encoding="utf-8"))
        with kural.secili(None):
            kur = kural.oku()
        y = yapi.kur(t); c = cati_genel.cati_kur(t["cati"], kur)
        odalar = {ad: round(b["alan_m2"], 2) for ad, b in y["bolgeler"].items() if b.get("sinif") != "dis"}
        acl = y["acikliklar"]
        bina = round(float(girdi["bina_m2"]), 2)                               # listedeki bina_m2 (brüt oturum, tam sayıya yuvarlı; K-A1, D-08 madde 5) → katalog_m2
        oturum = round(float(girdi.get("oturum_m2") or girdi["bina_m2"]), 2)   # yuvarlanmamış brüt oturum (K16: sessiz yuvarlama yok; geometri hakemi 12.10) → özet ve kapalı alan
        vm = girdi.get("veranda_m2") or 0                                       # girdi: {"brut", "net", ...} ya da sayı
        veranda = round(float(vm.get("net") or vm.get("brut") or 0) if isinstance(vm, dict) else float(vm), 2)
        sablon_dir = KOK / "is_emri" / "adaylar"; sablon_dir.mkdir(parents=True, exist_ok=True)
        dosya = kod.replace("Ç", "C")                                           # dosya adı ASCII (Mac/Linux/git uyumu); kayıt kodu Ç ile
        shutil.copyfile(Path(tmp) / m["bayi_gorsel"], sablon_dir / f"{dosya}.png")
        varyantlar = [kod_normalize(x) for x in a.varyantlar.split(",") if x.strip()]
        try:                                                                   # çatı tipinin okunur adı (kural anahtarı; iç anahtar bayiye basılmaz)
            cati_adlari = (json.loads((KOK / "kurallar" / "cizim" / "pafta_sablonu.json").read_text(encoding="utf-8")).get("cati_tipi_adi") or {}).get("deger") or {}
        except Exception:
            cati_adlari = {}
        ct = t.get("cati") or {}
        cati_adi = (ct.get("tip_adi") or "").split(":")[0].strip() or cati_adlari.get(ct.get("tip"), ct.get("tip") or "")
        cati_adi = cati_adi[:1].upper() + cati_adi[1:]                         # "beşik + cumba" → "Beşik + cumba" (kural anahtarındaki adlarla aynı biçim)
        kayit = {"kod": kod, "gosterim": t["kod"], "durum": a.durum, "motor": "genel", "tanim": gorece,
                 "tanim_sha256": hashlib.sha256(tanim_yolu.read_bytes()).hexdigest(), "gorsel": f"adaylar/{dosya}.png",
                 "referans_model": kod_normalize(a.referans) if a.referans else kod,
                 "yapi_turu": "celik", "kat": int(a.kat if a.kat is not None else (1 if str(t.get("kat", "zemin")) in ("zemin", "1") else 2)),
                 "oda_programi": oda_programi(t), "katalog_m2": bina, "kapali_m2": round(oturum - veranda, 2), "veranda_m2": veranda,
                 "varyantlar": varyantlar, "musteri_projesi": bool(a.musteri_projesi or musteri_projesi(t)),
                 "sunum": {"cati_adi": cati_adi, "ad": sahip_adi(t) if (a.musteri_projesi or musteri_projesi(t)) else t.get("ad", "")},   # D-33
                 "ozet": {"dis_olcu_cm": [round(x, 1) for x in girdi_genel.metraj(y, c, kur)["dis_olcu_cm"]], "oturum_m2": oturum, "odalar": odalar,
                          "pencere": sum(1 for x in acl if x["tur"] == "pencere"), "kapi": sum(1 for x in acl if x["tur"] in ("dis_kapi", "ic_kapi")),
                          "cati": t.get("cati", {}).get("tip"), "liste_satir": v.get("liste_satir"), "kural_seti": Path(v.get("set", "")).name,
                          "perspektif": v.get("perspektif", {}).get("durum")},
                 "kaynak": {"metin": a.kaynak, "dosya": gorece, "dogrulama": "çizim seti (İE-08, 12 Ekim 2026)", "karar": "D-08 madde 4; D-10"},
                 "not": a.not_}
    _yaz(kayit, a.test_dosyasi)
    return 0


def _yaz(kayit: dict, test_dosyasi: bool) -> None:
    kod = kayit["kod"]
    yol = KOK / "beyin" / "veri" / ("adaylar_test.json" if test_dosyasi else "adaylar.json")
    liste = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else []
    liste = [x for x in liste if str(x.get("kod")).upper() != kod] + [kayit]
    yol.write_text(json.dumps(liste, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: kayit.get(k) for k in ("kod", "durum", "oda_programi", "katalog_m2", "kapali_m2", "veranda_m2", "motor")}, ensure_ascii=False), "→", yol.name)


def _oda_programi(ie: dict) -> str:
    yatak = sum(1 for m in ie.get("mahaller", []) if m.get("tur") == "yatak_odasi")
    salon = 1 if any(m.get("tur") in ("salon", "mutfak") for m in ie.get("mahaller", [])) else 0
    return f"{yatak}+{salon}"


if __name__ == "__main__":
    sys.exit(main())
