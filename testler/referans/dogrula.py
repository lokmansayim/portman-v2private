"""Dondurulmuş referansa karşı doğrulama: v1.1.1 çekirdeği (Beyin kuralları, Motor, çıkarıcı) bugün de aynı sonucu
veriyor mu?

Referans, testler/referans/ altında tarihli bir klasördür (ilki 2026-09-28). Betik en yeni klasörle karşılaştırır:
  referans_girdiler.json   girdi dosyalarının özeti ve Beyin test vakalarının vaka vaka özeti
  denetim_kosum.json       kos.py adım durumları, sayılar, BOM sayımları, 16 plan sonucu
  dxf_parmak_izleri.txt    DXF çıktılarının içerik parmak izi (parmak_izi.py; zaman damgası ve kimlikler hariç)
  pdf_parmak_izleri.txt    PDF çıktılarının sayfa sayısı ve ölçüsü
  GEREKCE.md               neden ve hangi kodla donduruldu

Depo koduna dokunmaz: v1.1.1 ağacını geçici bir klasöre kopyalar (deneme/, testler/, KARARLAR/ hariç) ve
`denetim/kos.py`'yi orada, PORTMAN_* ve LLM anahtarı ortam değişkenleri olmadan koşar. Ağ, LLM, WhatsApp ya da
canlı sunucu kullanmaz.

Kurallar:
  - Referans girdiler değişmemeli: İş Emri şablonları (is_emri/), referans çizim ve kayıtlar (ref_katalog/, ref_yan/,
    kanal/ref_*), katalog verisi ve test bayi kaydı (beyin/veri/). Dondurulan dosya silinemez; yeni dosya bilgi olarak
    raporlanır.
  - Beyin test vakaları vaka vaka izlenir. Vaka özeti harness'in okuduğu her şeyi kapsar: mesaj kaydı (beklenen eylem
    ve içerik kontrolü dahil) ve kayıtlı LLM çıkarımı; ayrıca çıkarımın kaynağı olan grup kaydını (harness bunu okumaz).
    Kimlikler tamsayı olmalı; çıkarım, harness'teki gibi kimliğin kendisiyle eşlenir. Dondurulan vakalar aynı sırayla ve
    değişmeden durmalı; yeni vaka yalnız sona eklenebilir (aynı göndericinin vakaları konuşma durumunu paylaşır).
  - v1.1.1 ağacındaki değişiklikler (SHA256SUMS'a göre değişen, eksik ve yeni dosyalar) yalnız bilgi olarak raporlanır;
    kod değişikliği tek başına fark sayılmaz.
  - Beyin harness'inde tüm vakalar uyumlu olmalı; vaka sayısı referanstan az olamaz.
  - Motor sayıları, BOM sayımları, çıkarıcı sonuçları ve içerik parmak izleri referansla aynı olmalı.
  - Bilerek yapılan bir değişiklik referansı değiştirirse --dondur ile gerekçeli ve tarihli yeni klasör açılır; eskisi
    silinmez. Bir adım geçmiyorsa ya da test verisi okunamıyorsa dondurulmaz.

Kullanım (depo kökünde):
  python3 testler/referans/dogrula.py                       en yeni referansla tam karşılaştırma (~4,5 dk)
  python3 testler/referans/dogrula.py --hizli               16 katalog planı hariç (~45 sn)
  python3 testler/referans/dogrula.py --referans 2026-09-28 belirli bir referansla
  python3 testler/referans/dogrula.py --dondur --gerekce "…" [--ad 2026-10-02]   yeni referans (tam koşu, ~5 dk)
  python3 testler/referans/dogrula.py --girdi-dokumu        bugünkü girdi özetini yazar; koşu yapmaz
Çıkış kodu 0 = referansla aynı (ya da dondurma tamam). Fark varsa listelenir; düzeltilmez.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF))
from parmak_izi import ozet  # noqa: E402

HIZLI = {"altin_6x8", "altin_yan", "p6001"}  # --hizli koşuda üretilen çıktılar (+ çıkarıcı P6001)
GIRDI_KALIPLARI = ["is_emri/*.json", "ref_katalog/*", "ref_yan/*", "kanal/ref_*", "beyin/veri/*.json"]
REF_AD = re.compile(r"\d{4}-\d{2}-\d{2}[a-z]?")  # referans klasörü: tarih, aynı gün ikincisi için sonda bir harf
KOK_DISI = {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}  # kökte v1.1.1 dışı
SAYILAR = {
    "motor_altin_6x8": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_altin_yan_6x8p5_bom": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_p6001": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "dis_olcu", "dis_olcu_ok"],
}
LISTE_SINIRI = 12


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _kanonik_ozet(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _kisa(ad: str, liste: list) -> str:
    fazla = len(liste) - LISTE_SINIRI
    return f"{ad}: " + ", ".join(liste[:LISTE_SINIRI]) + (f" … (+{fazla})" if fazla > 0 else "")


def girdi_durumu(kok: Path, kaliplar: list[str]) -> dict:
    """Girdilerin bugünkü özeti: dosyalar tek tek; Beyin vakaları vaka vaka, harness'in eşlediği gibi."""
    dosyalar = {}
    for k in kaliplar:
        for p in sorted(kok.glob(k)):
            if p.is_file():
                dosyalar[p.relative_to(kok).as_posix()] = _sha(p)
    T = kok / "beyin" / "testler"

    def kimlik(i, yer: str) -> int:
        if type(i) is not int:  # harness kimliği olduğu gibi eşler: "2" ya da 2.0 başka bir kayda gidebilir
            raise ValueError(f"{yer}: kimlik tamsayı değil: {i!r}")
        return i

    def kayitlar(desen: str, alan: str | None = None) -> dict:
        out = {}  # harness gibi: dosyalar ada göre sıralı, aynı kimlikte sonraki kazanır
        for f in sorted(T.glob(desen)):
            for r in json.loads(f.read_text(encoding="utf-8")):
                out[kimlik(r["id"], f.name)] = r[alan] if alan else r
        return out

    try:
        mesajlar = json.loads((T / "mesajlar.json").read_text(encoding="utf-8"))
        cikarim, grup = kayitlar("cikarim_*.json", "talep"), kayitlar("grup_*.json")
        sira = [str(kimlik(m["id"], "mesajlar.json")) for m in mesajlar]
        vakalar = {str(m["id"]): _kanonik_ozet({"mesaj": m, "llm_girdisi": grup.get(m["id"]), "cikarim": cikarim.get(m["id"])})
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
    ad = "Beyin test vakaları (mesaj, kayıtlı çıkarım, grup kaydı)"
    if "hata" in bugun:
        sonuc.append((ad, False, f"okunamadı: {bugun['hata']}"))
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
    sonuc.append((ad, not degisen and not eksik and sira_ok, ek))
    return sonuc


def agac_durumu(W: Path) -> str:
    """Kopyalanan ağacın SHA256SUMS'a (v1.1.1) göre durumu; bilgi içindir, koşudan önce çağrılır."""
    toplamlar = KOK / "SHA256SUMS"
    if not toplamlar.exists():
        return "SHA256SUMS yok"
    beklenen = {yol: oz for oz, yol in (l.split("  ", 1) for l in toplamlar.read_text(encoding="utf-8").splitlines() if l.strip())}
    mevcut = {p.relative_to(W).as_posix() for p in W.rglob("*") if p.is_file()}
    degisen = sorted(k for k in beklenen if k in mevcut and _sha(W / k) != beklenen[k])
    eksik = sorted(k for k in beklenen if k not in mevcut)
    yeni = sorted(mevcut - set(beklenen))
    parcalar = [_kisa(a, L) for a, L in (("değişti", degisen), ("eksik", eksik), ("yeni", yeni)) if L]
    return "; ".join(parcalar) if parcalar else f"{len(beklenen)} dosya SHA256SUMS ile aynı"


def _yoksay(dizin, adlar):
    """Kökte yalnız v1.1.1 dışındaki klasörler atlanır; beyin/testler gibi alt klasörler kopyalanır."""
    if Path(dizin).resolve() == KOK:
        return [a for a in adlar if a in KOK_DISI]
    return [a for a in adlar if a in {"__pycache__", ".git"}]


def _ozet_guvenli(yol: Path) -> str:
    try:
        return ozet(yol)
    except Exception as e:  # bozuk çıktı fark sayılır, betik çökmez
        return f"okunamadı: {type(e).__name__}"


def _kos(W: Path, hizli: bool) -> Path | None:
    """kos.py'yi kopyada koşar. PORTMAN_* (başka referans klasörü, bayi kaydı, durum dizini) ve LLM anahtarları
    alt sürece geçmez; test canlı ayarlardan etkilenmez ve ücretli bir çağrı yapamaz."""
    ortam = {k: v for k, v in os.environ.items() if not k.startswith("PORTMAN_") and k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    komut = [sys.executable, "denetim/kos.py"] + ([] if hizli else ["--planlar"])
    r = subprocess.run(komut, cwd=W, capture_output=True, text=True, env=ortam)
    yol = W / "cikti/denetim/sonuc.json"
    if not yol.exists():
        print(r.stdout[-2000:], r.stderr[-2000:])
        return None
    return yol


def referans_klasorleri() -> list[Path]:
    return sorted(p for p in REF.iterdir() if p.is_dir() and REF_AD.fullmatch(p.name))


def karsilastir(ref_klasor: Path, hizli: bool) -> int:
    ref = json.loads((ref_klasor / "denetim_kosum.json").read_text(encoding="utf-8"))
    ref_g = json.loads((ref_klasor / "referans_girdiler.json").read_text(encoding="utf-8"))
    oku = lambda f: dict(reversed(l.split("  ", 1)) for l in (ref_klasor / f).read_text(encoding="utf-8").splitlines() if l.strip())
    ref_pi, ref_pdf = oku("dxf_parmak_izleri.txt"), oku("pdf_parmak_izleri.txt")
    gp = ref_klasor / "GEREKCE.md"
    satirlar_g = gp.read_text(encoding="utf-8").splitlines() if gp.exists() else []
    gerekce = next((l for l in satirlar_g if l.startswith("Gerekçe:")), "GEREKCE.md'de gerekçe yok")
    satir, kotu = [], 0

    def yaz(ad, ok, ek=""):
        nonlocal kotu
        kotu += not ok
        satir.append((ad, ("AYNI" if ok else "FARKLI") + (f" · {ek}" if ek else "")))

    with tempfile.TemporaryDirectory() as t:
        W = Path(t) / "is"
        shutil.copytree(KOK, W, ignore=_yoksay)
        # koşudan önce: kos.py'nin yazdığı dosyalar karışmasın
        try:
            girdi_satirlari = girdileri_karsilastir(ref_g, girdi_durumu(W, ref_g["kaliplar"]))
        except Exception as e:
            girdi_satirlari = [("referans girdiler ve Beyin test vakaları", False, f"okunamadı: {type(e).__name__}: {e}")]
        agac = agac_durumu(W)
        yol = _kos(W, hizli)
        if yol is None:
            return 2
        yeni = json.loads(yol.read_text(encoding="utf-8"))
        ra, ya = ref["adimlar"], yeni["adimlar"]
        # hata veren ya da eksik adım burada FARKLI görünür; aşağıdaki karşılaştırmalar boş sayılarla sürer, çökmez
        adimlar = [x for x in ra if not (hizli and x == "cikarici_16_plan")] + [x for x in ya if x not in ra]
        for adim in adimlar:
            v = ya.get(adim) or {}
            yaz(f"{adim}: durum", v.get("durum") == "passed", (v.get("durum") or "adım yok") + (f" · {v['hata'][:160]}" if v.get("hata") else ""))
        say = lambda adim: (ya.get(adim) or {}).get("sayilar") or {}
        for ad, ok, ek in girdi_satirlari:
            yaz(ad, ok, ek)
        satir.append(("v1.1.1 ağacı (bilgi)", agac))
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
        if not hizli:
            ys, rs = ya.get("cikarici_16_plan") or {}, ra["cikarici_16_plan"]
            yaz("cikarici_16_plan: özet", ys.get("sayilar") == rs["sayilar"],
                f"{(ys.get('sayilar') or {}).get('motor_passed')}/{(ys.get('sayilar') or {}).get('toplam')}")
            plan = lambda d: {k: (v.get("cikis_kodu"), v.get("motor_passed")) for k, v in (d.get("planlar") or {}).items()}
            yaz("cikarici_16_plan: plan plan", plan(ys) == plan(rs))
        for tur, ref_d in (("DXF", ref_pi), ("PDF", ref_pdf)):
            beklenen = [k for k in ref_d if not hizli or k.split("/")[2] in HIZLI or k.startswith("cikti/denetim/cikarici/P6001/")]
            eksik = [k for k in beklenen if not (W / k).exists()]
            fark = [k for k in beklenen if (W / k).exists() and _ozet_guvenli(W / k) != ref_d[k]]
            ek = f"{len(beklenen) - len(eksik)}/{len(beklenen)} dosya"
            if eksik: ek += f", eksik: {eksik}"
            if fark: ek += f", fark: {fark}"
            yaz(f"{tur} içerik parmak izleri" if tur == "DXF" else "PDF sayfa sayısı ve ölçüsü", not eksik and not fark, ek)

    print(f"Referans: {ref_klasor.relative_to(KOK)} · {gerekce}")
    g = max(len(x) for x, _ in satir)
    for x, s in satir:
        print(f"{x:<{g}}  {s}")
    print("SONUÇ:", "referansla aynı" if not kotu else f"{kotu} kontrolde fark var")
    return 0 if not kotu else 1


def dondur(gerekce: str, ad: str | None) -> int:
    """Yeni referans: tam koşu, tüm adımlar geçmeli. Yeni tarihli klasöre yazar; var olan klasöre dokunmaz."""
    ad = ad or datetime.date.today().isoformat()
    if not REF_AD.fullmatch(ad):
        print(f"geçersiz ad: {ad} (YYYY-AA-GG, aynı gün ikincisi için sonda bir harf)"); return 1
    hedef = REF / ad
    if hedef.exists():
        print(f"{hedef.relative_to(KOK)} zaten var; eskisi silinmez, başka bir ad verin (örneğin --ad {ad}b)"); return 1
    if not gerekce.strip():
        print("--gerekce gerekli: neyin neden değiştiği"); return 1
    onceki = referans_klasorleri()
    with tempfile.TemporaryDirectory() as t:
        W = Path(t) / "is"
        shutil.copytree(KOK, W, ignore=_yoksay)
        girdi = girdi_durumu(W, GIRDI_KALIPLARI)
        if "hata" in girdi:
            print(f"dondurulmadı: Beyin test vakaları okunamadı: {girdi['hata']}"); return 1
        yol = _kos(W, hizli=False)
        if yol is None:
            return 2
        sonuc = json.loads(yol.read_text(encoding="utf-8"))
        gecmeyen = [a for a, v in sonuc["adimlar"].items() if v.get("durum") != "passed"]
        if gecmeyen:
            print(f"dondurulmadı: geçmeyen adımlar: {gecmeyen}"); return 1
        ciktilar = sorted(p for p in (W / "cikti/denetim").rglob("*") if p.is_file() and p.suffix.lower() in (".dxf", ".pdf"))
        try:
            izler = {p: ozet(p) for p in ciktilar}
        except Exception as e:
            print(f"dondurulmadı: parmak izi alınamadı: {type(e).__name__}: {e}"); return 1
        satirlar = lambda uz: "".join(f"{iz}  {p.relative_to(W).as_posix()}\n" for p, iz in izler.items() if p.suffix.lower() == uz)
        dxf, pdf = satirlar(".dxf"), satirlar(".pdf")
        git = lambda *a: subprocess.run(["git", "-C", str(KOK), *a], capture_output=True, text=True).stdout.strip()
        head, kirli = git("rev-parse", "--short", "HEAD") or "bilinmiyor", bool(git("status", "--porcelain"))
        o = sonuc["adimlar"].get("ortam", {})
        hedef.mkdir(parents=True)
        (hedef / "denetim_kosum.json").write_bytes(yol.read_bytes())
        (hedef / "dxf_parmak_izleri.txt").write_text(dxf, encoding="utf-8")
        (hedef / "pdf_parmak_izleri.txt").write_text(pdf, encoding="utf-8")
        (hedef / "referans_girdiler.json").write_text(
            json.dumps({"tarih": ad, "kaliplar": GIRDI_KALIPLARI, **girdi}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (hedef / "GEREKCE.md").write_text(
            f"# Referans · {ad}\n\nGerekçe: {' '.join(gerekce.split())}\n\n"
            f"- Dondurulduğu kod: `{head}`" + (" üzerine kaydedilmemiş değişiklikler" if kirli else "") + "\n"
            f"- Ortam: Python {o.get('python')}, ezdxf {o.get('ezdxf')}, shapely {o.get('shapely')}, pydantic {o.get('pydantic')}, "
            f"numpy {o.get('numpy')}\n"
            f"- Önceki referans: {onceki[-1].name if onceki else 'yok'}\n"
            f"- İçerik: {len(girdi['dosyalar'])} girdi dosyası, {len(girdi['vakalar'])} Beyin vakası, {dxf.count(chr(10))} DXF, "
            f"{pdf.count(chr(10))} PDF\n", encoding="utf-8")
    print(f"donduruldu: {hedef.relative_to(KOK)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Dondurulmuş referansa karşı doğrulama (ayrıntı: dosyanın başı)")
    ap.add_argument("--hizli", action="store_true", help="16 katalog planını atla")
    ap.add_argument("--referans", metavar="AD", help="karşılaştırılacak referans klasörü (varsayılan: en yenisi)")
    ap.add_argument("--dondur", action="store_true", help="yeni tarihli referans klasörü aç (tam koşu)")
    ap.add_argument("--gerekce", default="", help="--dondur için: neyin neden değiştiği")
    ap.add_argument("--ad", help="--dondur için klasör adı (varsayılan: bugünün tarihi)")
    ap.add_argument("--girdi-dokumu", action="store_true", help="bugünkü girdi özetini JSON olarak yaz; koşu yapma")
    a = ap.parse_args()
    if a.girdi_dokumu:
        d = girdi_durumu(KOK, GIRDI_KALIPLARI)
        if "hata" in d:
            print(f"Beyin test vakaları okunamadı: {d['hata']}", file=sys.stderr); return 1
        print(json.dumps({"tarih": datetime.date.today().isoformat(), "kaliplar": GIRDI_KALIPLARI, **d}, ensure_ascii=False, indent=1))
        return 0
    if a.dondur:
        if a.hizli or a.referans:
            print("--dondur tam koşu ister; --hizli ve --referans ile kullanılmaz"); return 1
        return dondur(a.gerekce, a.ad)
    if a.referans:
        klasor = REF / a.referans
        if not (REF_AD.fullmatch(a.referans) and klasor.is_dir()):
            print(f"referans klasörü yok: {a.referans}; olanlar: {[p.name for p in referans_klasorleri()]}"); return 1
    else:
        klasorler = referans_klasorleri()
        if not klasorler:
            print("testler/referans altında tarihli referans klasörü yok"); return 1
        klasor = klasorler[-1]
    return karsilastir(klasor, a.hizli)


if __name__ == "__main__":
    raise SystemExit(main())
