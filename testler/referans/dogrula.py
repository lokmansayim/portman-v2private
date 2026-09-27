"""Dondurulmuş referansa karşı doğrulama: v1.1.1 çekirdeği (Beyin kuralları, Motor, çıkarıcı) bugün de aynı sonucu
veriyor mu?

Depo koduna dokunmaz: v1.1.1 ağacını geçici bir klasöre kopyalar (deneme/, testler/, KARARLAR/ hariç),
`denetim/kos.py --planlar` koşar ve sonucu dondurulmuş kayıtlarla karşılaştırır (28 Eylül 2026, üç ayrı temiz koşuda aynı):
  referans_girdiler.json         girdi dosyalarının özeti ve Beyin test vakalarının vaka vaka özeti
  denetim_kosum_2026-09-28.json  adım durumları, sayılar, BOM sayımları, 16 plan sonucu
  dxf_parmak_izleri.txt          18 DXF çıktısının içerik parmak izi (parmak_izi.py; zaman damgası ve kimlikler hariç)
  pdf_parmak_izleri.txt          18 PDF çıktısının sayfa sayısı ve ölçüsü

Kurallar:
  - Referans girdiler değişmemeli: İş Emri şablonları (is_emri/), referans çizim ve kayıtlar (ref_katalog/, ref_yan/,
    kanal/ref_*), katalog verisi ve test bayi kaydı (beyin/veri/). Dondurulan dosya silinemez; yeni dosya bilgi olarak
    raporlanır.
  - Beyin test vakaları vaka vaka izlenir; harness'in okuduğu her şey özetin içindedir: mesaj kaydı (beklenen eylem ve
    içerik kontrolü dahil), LLM'e giden grup kaydı ve kayıtlı LLM çıkarımı. Dondurulan vakalar aynı sırayla ve değişmeden
    durmalı; yeni vaka yalnız sona eklenebilir (aynı göndericinin vakaları konuşma durumunu paylaşır, sıra sonucu etkiler).
  - Kod dosyalarının özeti yalnız bilgi olarak raporlanır; kod değişikliği tek başına fark sayılmaz.
  - Beyin harness'inde tüm vakalar uyumlu olmalı; vaka sayısı referanstan az olamaz.
  - Motor sayıları, BOM sayımları, çıkarıcı sonuçları ve içerik parmak izleri referansla aynı olmalı. Bilerek yapılan
    bir değişiklik bunları değiştirirse referans gerekçesiyle ve yeni tarihle yeniden dondurulur; eskisi silinmez.

Kullanım (depo kökünde):  python3 testler/referans/dogrula.py [--hizli | --girdi-dokumu]
    --hizli: 16 katalog planını atlar (~45 sn yerine ~4,5 dk)
    --girdi-dokumu: bugünkü girdi özetini JSON olarak yazar (yeniden dondurmak için); koşu yapmaz
Çıkış kodu 0 = referansla aynı. Fark varsa listelenir; düzeltilmez.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF))
from parmak_izi import ozet  # noqa: E402

HIZLI = {"altin_6x8", "altin_yan", "p6001"}  # --hizli koşuda üretilen çıktılar (+ çıkarıcı P6001)
GIRDI_KALIPLARI = ["is_emri/*.json", "ref_katalog/*", "ref_yan/*", "kanal/ref_*", "beyin/veri/*.json"]
SAYILAR = {
    "motor_altin_6x8": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_altin_yan_6x8p5_bom": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_p6001": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "dis_olcu", "dis_olcu_ok"],
}


def _kanonik_ozet(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def girdi_durumu(kok: Path, kaliplar: list[str]) -> dict:
    """Girdilerin bugünkü özeti. Dosyalar tek tek. Beyin vakaları, harness'in okuduğu biçimde vaka vaka: mesaj kaydı,
    grup_*.json'daki LLM girdisi ve cikarim_*.json'daki kayıtlı çıkarım (dosyalar ada göre sıralı, aynı kimlikte sonraki kazanır)."""
    dosyalar = {}
    for k in kaliplar:
        for p in sorted(kok.glob(k)):
            if p.is_file():
                dosyalar[p.relative_to(kok).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    T = kok / "beyin" / "testler"

    def kayitlar(desen: str, alan: str | None = None) -> dict:
        out = {}
        for f in sorted(T.glob(desen)):
            for r in json.loads(f.read_text(encoding="utf-8")):
                out[str(r["id"])] = r[alan] if alan else r
        return out

    try:
        mesajlar = json.loads((T / "mesajlar.json").read_text(encoding="utf-8"))
        cikarim, grup = kayitlar("cikarim_*.json", "talep"), kayitlar("grup_*.json")
        sira = [str(m["id"]) for m in mesajlar]
        vakalar = {str(m["id"]): _kanonik_ozet({"mesaj": m, "llm_girdisi": grup.get(str(m["id"])), "cikarim": cikarim.get(str(m["id"]))})
                   for m in mesajlar}
    except Exception as e:  # bozuk test verisi: dosya denetimi yine yapılır, vakalar okunamadı diye raporlanır
        return {"dosyalar": dosyalar, "hata": f"{type(e).__name__}: {e}"}
    return {"dosyalar": dosyalar, "vaka_sirasi": sira, "vakalar": vakalar}


def girdileri_karsilastir(ref_g: dict, bugun: dict) -> list[tuple[str, bool, str]]:
    sonuc = []
    rd, bd = ref_g["dosyalar"], bugun["dosyalar"]
    degisen = sorted(k for k in rd if k in bd and bd[k] != rd[k])
    eksik = sorted(k for k in rd if k not in bd)
    yeni = sorted(k for k in bd if k not in rd)
    ek = f"{len(rd) - len(degisen) - len(eksik)}/{len(rd)} dosya aynı"
    if degisen: ek += f", değişti: {degisen}"
    if eksik: ek += f", eksik: {eksik}"
    if yeni: ek += f", yeni (bilgi): {yeni}"
    sonuc.append(("referans girdiler (şablon, çizim, katalog verisi)", not degisen and not eksik, ek))
    if "hata" in bugun:
        sonuc.append(("Beyin test vakaları (mesaj, LLM girdisi, kayıtlı çıkarım)", False, f"okunamadı: {bugun['hata']}"))
        return sonuc
    rs, bs, rv, bv = ref_g["vaka_sirasi"], bugun["vaka_sirasi"], ref_g["vakalar"], bugun["vakalar"]
    degisen = [k for k in rs if k in bv and bv[k] != rv[k]]
    eksik = [k for k in rs if k not in bv]
    sira_ok = bs[:len(rs)] == rs and len(set(bs)) == len(bs)
    yeni = [k for k in bs if k not in rv]
    ek = f"{len(rs) - len(degisen) - len(eksik)}/{len(rs)} vaka aynı"
    if degisen: ek += f", değişti: {degisen}"
    if eksik: ek += f", eksik: {eksik}"
    if not sira_ok: ek += ", sıra bozuldu ya da kimlik tekrar ediyor (dondurulan vakalar başta ve aynı sırada olmalı)"
    if yeni: ek += f", yeni vaka (bilgi): {yeni}"
    sonuc.append(("Beyin test vakaları (mesaj, LLM girdisi, kayıtlı çıkarım)", not degisen and not eksik and sira_ok, ek))
    return sonuc


def _yoksay(dizin, adlar):
    """Kökte yalnız v1.1.1 dışındaki klasörler atlanır; beyin/testler gibi alt klasörler kopyalanır."""
    if Path(dizin).resolve() == KOK:
        return [a for a in adlar if a in {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}]
    return [a for a in adlar if a in {"__pycache__", ".git"}]


def _ozet_guvenli(yol: Path) -> str:
    try:
        return ozet(yol)
    except Exception as e:  # bozuk çıktı fark sayılır, betik çökmez
        return f"okunamadı: {type(e).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--hizli", action="store_true"); ap.add_argument("--girdi-dokumu", action="store_true")
    a = ap.parse_args()
    if a.girdi_dokumu:
        d = girdi_durumu(KOK, GIRDI_KALIPLARI)
        if "hata" in d:  # bozuk veriden referans dondurulmaz
            print(f"Beyin test vakaları okunamadı: {d['hata']}", file=sys.stderr); return 1
        print(json.dumps({"tarih": datetime.date.today().isoformat(), "kaliplar": GIRDI_KALIPLARI, **d}, ensure_ascii=False, indent=1))
        return 0
    ref = json.loads((REF / "denetim_kosum_2026-09-28.json").read_text(encoding="utf-8"))
    ref_g = json.loads((REF / "referans_girdiler.json").read_text(encoding="utf-8"))
    oku = lambda f: dict(reversed(l.split("  ", 1)) for l in (REF / f).read_text().splitlines() if l.strip())
    ref_pi, ref_pdf = oku("dxf_parmak_izleri.txt"), oku("pdf_parmak_izleri.txt")
    satir, kotu = [], 0

    def yaz(ad, ok, ek=""):
        nonlocal kotu
        kotu += not ok
        satir.append((ad, ("AYNI" if ok else "FARKLI") + (f" · {ek}" if ek else "")))

    with tempfile.TemporaryDirectory() as t:
        W = Path(t) / "is"
        shutil.copytree(KOK, W, ignore=_yoksay)
        try:  # koşudan önce: kos.py'nin yazdığı dosyalar karışmasın
            girdi_satirlari = girdileri_karsilastir(ref_g, girdi_durumu(W, ref_g["kaliplar"]))
        except Exception as e:  # bozuk ya da eksik test verisi
            girdi_satirlari = [("referans girdiler ve Beyin test vakaları", False, f"okunamadı: {type(e).__name__}: {e}")]
        komut = [sys.executable, "denetim/kos.py"] + ([] if a.hizli else ["--planlar"])
        r = subprocess.run(komut, cwd=W, capture_output=True, text=True)
        yol = W / "cikti/denetim/sonuc.json"
        if not yol.exists():
            print(r.stdout[-2000:], r.stderr[-2000:]); return 2
        yeni = json.loads(yol.read_text(encoding="utf-8"))
        ra, ya = ref["adimlar"], yeni["adimlar"]
        # hata veren ya da eksik adım burada FARKLI görünür; aşağıdaki karşılaştırmalar boş sayılarla sürer, çökmez
        adimlar = [x for x in ra if not (a.hizli and x == "cikarici_16_plan")] + [x for x in ya if x not in ra]
        for adim in adimlar:
            v = ya.get(adim) or {}
            yaz(f"{adim}: durum", v.get("durum") == "passed", (v.get("durum") or "adım yok") + (f" · {v['hata'][:160]}" if v.get("hata") else ""))
        say = lambda adim: (ya.get(adim) or {}).get("sayilar") or {}
        def duz(d, on=""):
            out = {}
            for k, v in d.items():
                out.update(duz(v, on + k + "/") if isinstance(v, dict) else {on + k: v})
            return out
        for ad, ok, ek in girdi_satirlari:
            yaz(ad, ok, ek)
        # kos.py'nin kendi girdi özetlerinden yalnız kod dosyaları kullanılır (bilgi); veri dosyaları yukarıda denetlendi
        yh, rh = duz((ya.get("girdi_hashleri") or {}).get("hashler") or {}), duz(ra["girdi_hashleri"]["hashler"])
        kod = lambda y: y.endswith((".py", ".php"))
        kod_fark = sorted(k for k in set(yh) | set(rh) if kod(k) and yh.get(k) != rh.get(k))
        satir.append(("kod dosyaları (bilgi)", ("değişti: " + ", ".join(kod_fark)) if kod_fark else "değişmedi"))
        yb, rb = say("beyin_harness"), ra["beyin_harness"]["sayilar"]
        yaz("beyin_harness", bool(yb) and yb.get("uyumlu") == yb.get("toplam") and (yb.get("toplam") or 0) >= rb["toplam"],
            f"{yb.get('uyumlu')}/{yb.get('toplam')} (referans {rb['toplam']} vaka)")
        for adim, alanlar in SAYILAR.items():
            ys, rs = say(adim), ra[adim]["sayilar"]
            yaz(f"{adim}: sayılar", bool(ys) and all(ys.get(k) == rs.get(k) for k in alanlar), f"pano {ys.get('pano')}, dış ölçü {ys.get('dis_olcu')}")
            yaz(f"{adim}: BOM sayımı", (ya.get(adim) or {}).get("bom_sayim") == ra[adim].get("bom_sayim"))
        ys, rs = say("cikarici_p6001_altin"), ra["cikarici_p6001_altin"]["sayilar"]
        alan3 = ("grid_esit", "mahal_esit", "aciklik_esit")
        yaz("cikarici_p6001_altin: sayılar", bool(ys) and {k: ys.get(k) for k in alan3} == {k: rs.get(k) for k in alan3},
            f"mahal {ys.get('mahal_esit')}, açıklık {ys.get('aciklik_esit')}")
        yaz("sir_taramasi", say("sir_taramasi") == ra["sir_taramasi"]["sayilar"])
        if not a.hizli:
            ys, rs = ya.get("cikarici_16_plan") or {}, ra["cikarici_16_plan"]
            yaz("cikarici_16_plan: özet", ys.get("sayilar") == rs["sayilar"],
                f"{(ys.get('sayilar') or {}).get('motor_passed')}/{(ys.get('sayilar') or {}).get('toplam')}")
            plan = lambda d: {k: (v.get("cikis_kodu"), v.get("motor_passed")) for k, v in (d.get("planlar") or {}).items()}
            yaz("cikarici_16_plan: plan plan", plan(ys) == plan(rs))
        for tur, ref_d in (("DXF", ref_pi), ("PDF", ref_pdf)):
            beklenen = [k for k in ref_d if a.hizli is False or k.split("/")[2] in HIZLI or k.startswith("cikti/denetim/cikarici/P6001/")]
            eksik = [k for k in beklenen if not (W / k).exists()]
            fark = [k for k in beklenen if (W / k).exists() and _ozet_guvenli(W / k) != ref_d[k]]
            ek = f"{len(beklenen) - len(eksik)}/{len(beklenen)} dosya"
            if eksik: ek += f", eksik: {eksik}"
            if fark: ek += f", fark: {fark}"
            yaz(f"{tur} içerik parmak izleri" if tur == "DXF" else "PDF sayfa sayısı ve ölçüsü", not eksik and not fark, ek)

    g = max(len(x) for x, _ in satir)
    for x, s in satir:
        print(f"{x:<{g}}  {s}")
    print("SONUÇ:", "referansla aynı" if not kotu else f"{kotu} kontrolde fark var")
    return 0 if not kotu else 1


if __name__ == "__main__":
    raise SystemExit(main())
