"""Dondurulmuş referansa karşı doğrulama: v1.1.1 çekirdeği (Beyin kuralları, Motor, çıkarıcı) bugün de aynı sonucu
veriyor mu?

Referans, testler/referans/ altında tarihli bir klasördür (ilki 2026-09-28). Betik en yeni klasörle karşılaştırır:
  referans_girdiler.json   girdi dosyalarının özeti ve Beyin test vakalarının vaka vaka özeti
  denetim_kosum.json       kos.py adım durumları, sayılar, BOM sayımları, 16 plan sonucu
  dxf_parmak_izleri.txt    DXF çıktılarının içerik parmak izi (parmak_izi.py; zaman damgası ve kimlikler hariç)
  pdf_parmak_izleri.txt    PDF çıktılarının sayfa ölçüsü ve bütün çizimleri (2026-09-28b'den beri; D-02)
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
  - Betik ilk satırda koşulan kodu (commit ve kaydedilmemiş değişiklikler) yazar; her zaman çalışma ağacını koşar.
    Referans koşularında üretim zamanı sabitlenir (sabit_zaman/), böylece PDF çizimleri koşudan koşuya aynı kalır.
  - Bilerek yapılan bir değişiklik referansı değiştirirse --dondur ile gerekçeli ve tarihli yeni klasör açılır; eskisi
    silinmez. Önceki referanstan farklıysa dayandığı karar --karar ile verilmelidir (KARARLAR/<AD>.md). Bir adım geçmiyorsa ya da test verisi okunamıyorsa dondurulmaz. Önceki referansa göre kaldırma ya da
    azalma (girdi dosyası, vaka, çıktı, vaka sayısı, Motor'dan geçen plan) varsa --kaldirmaya-izin gerekir; izin ve
    fark listesi GEREKCE.md'ye yazılır.
  - Referans dosyaları elle değiştirilmez. Her koşuda GEREKCE.md'deki dosya özetleri sınanır ve her referans bir
    öncekine göre denetlenir (izinsiz kaldırma, tekrarlanan gerekçe, ileri tarih). Sorun varsa "REFERANS BOZUK", çıkış 2.

Kullanım (depo kökünde):
  python3 testler/referans/dogrula.py                       en yeni referansla tam karşılaştırma (~4,5 dk)
  python3 testler/referans/dogrula.py --hizli               16 katalog planı hariç (~45 sn)
  python3 testler/referans/dogrula.py --referans 2026-09-28 belirli bir referansla
  python3 testler/referans/dogrula.py --dondur --gerekce "…" --karar D-02 [--ad 2026-10-02] [--kaldirmaya-izin]
                                                            yeni referans (tam koşu, ~5 dk)
  python3 testler/referans/dogrula.py --girdi-dokumu        bugünkü girdi özetini yazar; koşu yapmaz
Çıkış kodu 0 = referansla aynı (ya da dondurma tamam), 1 = fark var, 2 = referans bozuk ya da koşu sonuç vermedi.
Fark varsa listelenir; düzeltilmez.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF))
from parmak_izi import genel_ozet, ozet  # noqa: E402

HIZLI = {"altin_6x8", "altin_yan", "p6001"}  # --hizli koşuda üretilen çıktılar (+ çıkarıcı P6001; genel motor: yalnız genel_c8801)
GIRDI_KALIPLARI = ["is_emri/*.json", "ref_katalog/*", "ref_yan/*", "kanal/ref_*", "beyin/veri/*.json",
                   # İE-08: genel motorun girdileri (model tanımları, dondurulmuş kural setleri, çizim seti, seçenekler, bayi örneği);
                   # güncel set kurallar/liste/kurallar.json girdi sayılmaz: altın adımlar setler/0.19.json pimiyle koşar
                   "modeller/*.json", "kurallar/liste/setler/*.json", "kurallar/cizim/*.json", "kurallar/model/secenekler/*.json", "kurallar/bayi/*.json",
                   # BK-12 PR-R (D-12): prefabrik hattının dondurulmuş kaynakları (26 dosya; alt klasörler dahil)
                   "ref_prefabrik/**/*"]
REF_AD = re.compile(r"\d{4}-\d{2}-\d{2}[a-z]?")  # referans klasörü: tarih, aynı gün ikincisi için sonda bir harf
KOK_DISI = {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}  # kökte v1.1.1 dışı
SAYILAR = {
    "motor_altin_6x8": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_altin_yan_6x8p5_bom": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_p6001": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "dis_olcu", "dis_olcu_ok"],
}
LISTE_SINIRI = 12
SABIT_ZAMAN = 1767225600          # 2026-01-01 00:00:00 UTC; referans koşularında üretim zamanı
KARARLAR = KOK / "KARARLAR"


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


def _surum(paket: str) -> str:
    """PDF parmak izi PyMuPDF'in çizim çıktısına dayanır (D-02); sürümü GEREKCE.md'ye yazılır. kos.py'nin ortam adımı bu sürümü
    okuyamıyor ("(64-bit)."), v1.1.1 kodu olduğu için ona dokunulmadı."""
    try:
        from importlib.metadata import version
        return version(paket)
    except Exception:
        return "?"


def _ozet_guvenli(yol: Path) -> str:
    try:
        return ozet(yol)
    except Exception as e:  # bozuk çıktı fark sayılır, betik çökmez
        return f"okunamadı: {type(e).__name__}"


def _genel_ozet_guvenli(yol: Path) -> str:
    try:
        return genel_ozet(yol)
    except Exception as e:
        return f"okunamadı: {type(e).__name__}"


def _kos(W: Path, hizli: bool) -> Path | None:
    """kos.py'yi kopyada koşar. PORTMAN_* (başka referans klasörü, bayi kaydı, durum dizini) ve LLM anahtarları
    alt sürece geçmez; test canlı ayarlardan etkilenmez ve ücretli bir çağrı yapamaz."""
    ortam = {k: v for k, v in os.environ.items() if not k.startswith("PORTMAN_") and k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    # Üretim zamanı sabit: PDF'teki "Üretim: … UTC" çizimi koşudan koşuya aynı olur (sabit_zaman/sitecustomize.py)
    ortam["TEST_SABIT_ZAMAN"] = str(SABIT_ZAMAN)
    ortam["PYTHONPATH"] = os.pathsep.join([str(REF / "sabit_zaman")] + ([ortam["PYTHONPATH"]] if ortam.get("PYTHONPATH") else []))
    komut = [sys.executable, "denetim/kos.py"] + ([] if hizli else ["--planlar"])
    r = subprocess.run(komut, cwd=W, capture_output=True, text=True, env=ortam)
    yol = W / "cikti/denetim/sonuc.json"
    if not yol.exists():
        print(r.stdout[-2000:], r.stderr[-2000:])
        return None
    return yol


REF_DOSYALAR = ("denetim_kosum.json", "dxf_parmak_izleri.txt", "pdf_parmak_izleri.txt", "referans_girdiler.json")
GENEL_DOSYA = "genel_parmak_izleri.txt"   # İE-08: genel motor izleri (PNG/PDF bayt, JSON kanonik, IFC içerik); eski klasörlerde yok, isteğe bağlı
IZIN_SATIRI = "Kaldırmaya izin: evet"


class ReferansHatasi(Exception):
    pass


def _ad_tarihi(ad: str) -> datetime.date | None:
    if not REF_AD.fullmatch(ad):
        return None
    try:
        return datetime.date.fromisoformat(ad[:10])
    except ValueError:
        return None


def referans_klasorleri() -> list[Path]:
    """Adı geçerli bir tarih olan klasörler, eskiden yeniye. İleri tarihli klasör hata sayılır."""
    L = sorted(p for p in REF.iterdir() if p.is_dir() and _ad_tarihi(p.name))
    ileri = [p.name for p in L if _ad_tarihi(p.name) > datetime.date.today()]
    if ileri:
        raise ReferansHatasi(f"tarihi ileride olan referans klasörü: {ileri}")
    return L


def _izler(yol: Path) -> dict:
    return {y: oz for oz, y in (l.split("  ", 1) for l in yol.read_text(encoding="utf-8").splitlines() if l.strip())}


def referans_yukle(klasor: Path) -> dict:
    """Klasörü okur ve bütünlüğünü sınar: dosyalar tam, gerekçe dolu, özetler GEREKCE.md'dekilerle aynı."""
    eksik = [f for f in REF_DOSYALAR + ("GEREKCE.md",) if not (klasor / f).is_file()]
    if eksik:
        raise ReferansHatasi(f"{klasor.name}: eksik dosya {eksik}")
    g = (klasor / "GEREKCE.md").read_text(encoding="utf-8")
    gerekce = next((l for l in g.splitlines() if l.startswith("Gerekçe:") and l[len("Gerekçe:"):].strip()), None)
    if not gerekce:
        raise ReferansHatasi(f"{klasor.name}: GEREKCE.md'de gerekçe yok")
    ozetler = dict(re.findall(r"^- `([^`]+)`: ([0-9a-f]{64})$", g, re.M))
    if GENEL_DOSYA in ozetler and not (klasor / GENEL_DOSYA).is_file():
        raise ReferansHatasi(f"{klasor.name}: GEREKCE.md {GENEL_DOSYA} özetini taşıyor ama dosya yok; referans dosyaları elle değiştirilmemeli")
    dosyalar = REF_DOSYALAR + ((GENEL_DOSYA,) if (klasor / GENEL_DOSYA).is_file() else ())
    bozuk = [f for f in dosyalar if ozetler.get(f) != _sha(klasor / f)]
    if bozuk:
        raise ReferansHatasi(f"{klasor.name}: {bozuk} GEREKCE.md'deki özetle uyuşmuyor; referans dosyaları elle değiştirilmemeli (--dondur kullanın)")
    try:
        karar = next((l.split(":", 1)[1].strip() for l in g.splitlines() if l.startswith("Karar:")), None)
        return {"ad": klasor.name, "gerekce": gerekce, "izin": IZIN_SATIRI in g, "karar": karar,
                "kosum": json.loads((klasor / "denetim_kosum.json").read_text(encoding="utf-8")),
                "girdi": json.loads((klasor / "referans_girdiler.json").read_text(encoding="utf-8")),
                "dxf": _izler(klasor / "dxf_parmak_izleri.txt"), "pdf": _izler(klasor / "pdf_parmak_izleri.txt"),
                "genel": _izler(klasor / GENEL_DOSYA) if (klasor / GENEL_DOSYA).is_file() else {}}
    except Exception as e:
        raise ReferansHatasi(f"{klasor.name}: okunamadı: {type(e).__name__}: {e}")


def referans_farki(eski: dict, yeni: dict) -> tuple[list[str], list[str]]:
    """Önceki referansa göre (kaldırılan ya da azalan, değişen ya da eklenen). İlki açık izin ister."""
    kaldir, degis = [], []
    ed, yd = eski["girdi"]["dosyalar"], yeni["girdi"]["dosyalar"]
    kaldir += [f"girdi dosyası kaldırıldı: {k}" for k in sorted(set(ed) - set(yd))]
    degis += [f"girdi dosyası değişti: {k}" for k in sorted(k for k in ed if k in yd and ed[k] != yd[k])]
    degis += [f"girdi dosyası eklendi: {k}" for k in sorted(set(yd) - set(ed))]
    es, ys, ev, yv = eski["girdi"]["vaka_sirasi"], yeni["girdi"]["vaka_sirasi"], eski["girdi"]["vakalar"], yeni["girdi"]["vakalar"]
    kaldir += [f"Beyin vakası kaldırıldı: {k}" for k in es if k not in yv]
    degis += [f"Beyin vakası değişti: {k}" for k in es if k in yv and ev[k] != yv[k]]
    degis += [f"Beyin vakası eklendi: {k}" for k in ys if k not in ev]
    if [k for k in ys if k in ev] != [k for k in es if k in yv]:
        kaldir.append("Beyin vakalarının sırası değişti")
    for tur in ("dxf", "pdf", "genel"):
        e, y = eski.get(tur) or {}, yeni.get(tur) or {}
        kaldir += [f"{tur.upper()} çıktısı kaldırıldı: {k}" for k in sorted(set(e) - set(y))]
        degis += [f"{tur.upper()} parmak izi değişti: {k}" for k in sorted(k for k in e if k in y and e[k] != y[k])]
        degis += [f"{tur.upper()} çıktısı eklendi: {k}" for k in sorted(set(y) - set(e))]
    ea, ya = eski["kosum"]["adimlar"], yeni["kosum"]["adimlar"]
    kaldir += [f"denetim adımı kaldırıldı: {a}" for a in ea if a not in ya]
    say = lambda d, a: (d.get(a) or {}).get("sayilar") or {}
    if (say(ya, "beyin_harness").get("toplam") or 0) < (say(ea, "beyin_harness").get("toplam") or 0):
        kaldir.append(f"harness vaka sayısı azaldı: {say(ea, 'beyin_harness').get('toplam')} → {say(ya, 'beyin_harness').get('toplam')}")
    e16, y16 = (ea.get("cikarici_16_plan") or {}).get("planlar") or {}, (ya.get("cikarici_16_plan") or {}).get("planlar") or {}
    kaldir += [f"katalog planı Motor doğrulamasında geriledi: {k}" for k in sorted(e16)
               if e16[k].get("motor_passed") and not (y16.get(k) or {}).get("motor_passed")]
    for a in [*SAYILAR, "cikarici_p6001_altin", "cikarici_16_plan", "sir_taramasi", "beyin_harness", "genel_c8801", "genel_matris"]:
        if a in ea and a in ya and (say(ea, a) != say(ya, a) or (ea[a].get("bom_sayim") != ya[a].get("bom_sayim"))):
            degis.append(f"{a}: sayılar değişti")
    return kaldir, degis


def _karar_var(karar: str | None) -> bool:
    """GEREKCE.md'deki "Karar:" satırı KARARLAR/ altında var olan bir karar dosyasını gösteriyor mu (ör. D-02, K21)?"""
    return bool(karar) and bool(re.fullmatch(r"[A-Z]{1,2}-?\d{1,3}", karar)) and (KARARLAR / f"{karar}.md").is_file()


def referans_zinciri(son: Path) -> tuple[dict, list[str]]:
    """Seçilen referansı ve ondan önceki her referansı sınar. Önceki referansa göre kaldırma ya da azalma varsa
    klasörün GEREKCE.md'sinde açık izin olmalı. Dönen: (seçilen referans, bilgi satırları)."""
    zincir = [p for p in referans_klasorleri() if p.name <= son.name]
    yuklu = [referans_yukle(p) for p in zincir]
    bilgi = []
    for eski, yeni in zip(yuklu, yuklu[1:]):
        if yeni["gerekce"] == eski["gerekce"]:
            raise ReferansHatasi(f"{yeni['ad']}: gerekçe önceki referansla ({eski['ad']}) aynı; her dondurma kendi gerekçesini yazar")
        kaldir, degis = referans_farki(eski, yeni)
        if (kaldir or degis) and not _karar_var(yeni.get("karar")):
            raise ReferansHatasi(f"{yeni['ad']}: önceki referansa ({eski['ad']}) göre değişiklik var ama dayandığı karar yazılı değil "
                                 f"ya da KARARLAR/'da yok (Karar: {yeni.get('karar')})")
        if kaldir and not yeni["izin"]:
            raise ReferansHatasi(f"{yeni['ad']}: önceki referansa ({eski['ad']}) göre kaldırma ya da azalma var ve izin kaydı yok: {kaldir[:5]}")
        if yeni is yuklu[-1] and (kaldir or degis):
            bilgi.append(f"önceki referans {eski['ad']}; değişen {len(degis)}, izinli kaldırma {len(kaldir)}")
            bilgi += [f"  izinli: {x}" for x in kaldir[:LISTE_SINIRI]] + [f"  değişen: {x}" for x in degis[:LISTE_SINIRI]]
            if len(kaldir) > LISTE_SINIRI or len(degis) > LISTE_SINIRI:
                bilgi.append(f"  … tam liste: testler/referans/{yeni['ad']}/GEREKCE.md")
    return yuklu[-1], bilgi


def kosulan_kod() -> str:
    """Karşılaştırılan kod: dalın son commit'i ve kaydedilmemiş değişiklikler (dogrula her zaman bu ağacı koşar)."""
    git = lambda *a: subprocess.run(["git", "-C", str(KOK), *a], capture_output=True, text=True).stdout.strip()
    head, dal = git("rev-parse", "--short", "HEAD") or "git yok", git("rev-parse", "--abbrev-ref", "HEAD")
    kirli = [l[3:] for l in git("status", "--porcelain").splitlines() if l.strip()]
    return f"{head} ({dal})" + (f" + {len(kirli)} kaydedilmemiş değişiklik: {', '.join(kirli[:6])}" + (" …" if len(kirli) > 6 else "") if kirli else "")


def karsilastir(R: dict, bilgi: list[str], hizli: bool) -> int:
    ref, ref_g, ref_pi, ref_pdf, ref_gen = R["kosum"], R["girdi"], R["dxf"], R["pdf"], R.get("genel") or {}
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
        adimlar = [x for x in ra if not (hizli and x in ("cikarici_16_plan", "genel_matris"))] + [x for x in ya if x not in ra]
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
        # Sır taraması: beklenmeyen bulgu sayısı (bulgu − bilinen sahte test sabitleri) referanstaki gibi 0 olmalı. Ham sayı
        # karşılaştırılmaz: kanal/tests'e sahte sabitli yeni bir test dosyası eklemek ham sayıyı artırır ama sır değildir.
        bek = lambda s: (s.get("bulgu") or 0) - (s.get("beklenen_sahte") or 0)
        ys, rs = say("sir_taramasi"), ra["sir_taramasi"]["sayilar"]
        yaz("sir_taramasi", bool(ys) and bek(ys) == bek(rs) == 0, f"beklenmeyen {bek(ys)} · sahte test sabiti {ys.get('beklenen_sahte')}")
        # İE-08: genel motor (serbest aks) adımları; eski referansta yoksa yalnız durum satırı (yukarıda) karşılaştırılır
        if "genel_c8801" in ra:
            ys, rs = say("genel_c8801"), ra["genel_c8801"]["sayilar"]
            yaz("genel_c8801: sayılar", bool(ys) and ys == rs, f"liste {ys.get('liste_satir')} satır, IFC şema hatası {ys.get('sema_hatasi')}, altın {ys.get('altin')}")
        if "genel_matris" in ra and not hizli:
            ys, rs = say("genel_matris"), ra["genel_matris"]["sayilar"]
            yaz("genel_matris: sayılar", bool(ys) and ys == rs, f"{ys.get('gecen')}/{ys.get('toplam')} birleşim")
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
            yaz(f"{tur} içerik parmak izleri", not eksik and not fark, ek)
        if ref_gen:   # İE-08: genel motor izleri; --hizli yalnız genel_c8801 klasörü
            beklenen = [k for k in ref_gen if not hizli or k.startswith("cikti/denetim/genel_c8801/")]
            eksik = [k for k in beklenen if not (W / k).exists()]
            fark = [k for k in beklenen if (W / k).exists() and _genel_ozet_guvenli(W / k) != ref_gen[k]]
            ek = f"{len(beklenen) - len(eksik)}/{len(beklenen)} dosya"
            if eksik: ek += f", eksik: {eksik[:LISTE_SINIRI]}"
            if fark: ek += f", fark: {fark[:LISTE_SINIRI]}"
            yaz("Genel motor izleri (PNG, PDF, JSON, IFC)", not eksik and not fark, ek)

    print(f"Koşulan kod: {kosulan_kod()}")
    print(f"Referans: testler/referans/{R['ad']} · {R['gerekce']}" + (f" · {bilgi[0]}" if bilgi else ""))
    for b in bilgi[1:]:
        print(b)
    g = max(len(x) for x, _ in satir)
    for x, s in satir:
        print(f"{x:<{g}}  {s}")
    print("SONUÇ:", "referansla aynı" if not kotu else f"{kotu} kontrolde fark var")
    return 0 if not kotu else 1


def dondur(gerekce: str, ad: str | None, kaldirmaya_izin: bool, karar: str | None = None) -> int:
    """Yeni referans: tam koşu, tüm adımlar geçmeli. Yeni tarihli klasöre yazar; var olan klasöre dokunmaz. Önceki
    referansa göre kaldırma ya da azalma (dosya, vaka, çıktı, vaka sayısı, geçen plan) varsa açık izin ister."""
    ad = ad or datetime.date.today().isoformat()
    tarih = _ad_tarihi(ad)
    if tarih is None or tarih > datetime.date.today():
        print(f"geçersiz ad: {ad} (bugün ya da geçmiş bir tarih, YYYY-AA-GG; aynı gün ikincisi için sonda bir harf)"); return 1
    hedef = REF / ad
    if hedef.exists():
        print(f"{hedef.relative_to(KOK)} zaten var; eskisi silinmez, başka bir ad verin (örneğin --ad {ad}b)"); return 1
    if not gerekce.strip():
        print("--gerekce gerekli: neyin neden değiştiği"); return 1
    onceki_klasorler = [p for p in referans_klasorleri() if p.name < ad]
    if [p for p in referans_klasorleri() if p.name > ad]:
        print(f"{ad} en yeni referans olmaz: daha yeni bir klasör var"); return 1
    onceki, _ = referans_zinciri(onceki_klasorler[-1]) if onceki_klasorler else (None, [])
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
        genel_mi = lambda p: p.relative_to(W).as_posix().startswith("cikti/denetim/genel")
        ciktilar = sorted(p for p in (W / "cikti/denetim").rglob("*") if p.is_file() and p.suffix.lower() in (".dxf", ".pdf") and not genel_mi(p))
        # İE-08: genel motor çıktıları ayrı kovada (PNG/PDF bayt, JSON kanonik, IFC içerik); süre ve yol taşıyan kayıtlar dışarıda.
        # D-11 (13.10.2026): düzenlenebilir DXF de bu kovada, içerik iziyle (parmak_izi.dxf_ozet); önceki referanslarda yoktu → "eklendi"
        genel_ciktilar = sorted(p for p in (W / "cikti/denetim").rglob("*") if p.is_file() and genel_mi(p)
                                and p.suffix.lower() in (".png", ".pdf", ".json", ".ifc", ".dxf") and p.name not in ("validation.json", "manifest.json"))
        try:
            izler = {p.relative_to(W).as_posix(): ozet(p) for p in ciktilar}
            genel_izler = {p.relative_to(W).as_posix(): genel_ozet(p) for p in genel_ciktilar}
        except Exception as e:
            print(f"dondurulmadı: parmak izi alınamadı: {type(e).__name__}: {e}"); return 1
        yeni = {"girdi": girdi, "kosum": sonuc,
                "dxf": {k: v for k, v in izler.items() if k.lower().endswith(".dxf")},
                "pdf": {k: v for k, v in izler.items() if k.lower().endswith(".pdf")}, "genel": genel_izler}
        kaldir, degis = referans_farki(onceki, yeni) if onceki else ([], [])
        if (kaldir or degis) and not _karar_var(karar):
            print("dondurulmadı: önceki referansa göre değişiklik var; beklenen davranışın hangi karara dayandığını --karar ile verin "
                  "(KARARLAR/ altında var olan bir dosya, ör. --karar D-02). Yalnız testi geçirmek için referans güncellenmez.")
            for x in (kaldir + degis)[:20]:
                print("  -", x)
            return 1
        if kaldir and not kaldirmaya_izin:
            print("dondurulmadı: önceki referansa göre kaldırma ya da azalma var. Bilerek yapıldıysa --kaldirmaya-izin ile tekrarlayın:")
            for x in kaldir:
                print("  -", x)
            return 1
        metin = lambda d: "".join(f"{v}  {k}\n" for k, v in d.items())
        git = lambda *a: subprocess.run(["git", "-C", str(KOK), *a], capture_output=True, text=True).stdout.strip()
        head, kirli = git("rev-parse", "--short", "HEAD") or "bilinmiyor", bool(git("status", "--porcelain"))
        o = sonuc["adimlar"].get("ortam", {})
        hedef.mkdir(parents=True)
        (hedef / "denetim_kosum.json").write_bytes(yol.read_bytes())
        (hedef / "dxf_parmak_izleri.txt").write_text(metin(yeni["dxf"]), encoding="utf-8")
        (hedef / "pdf_parmak_izleri.txt").write_text(metin(yeni["pdf"]), encoding="utf-8")
        if genel_izler:
            (hedef / GENEL_DOSYA).write_text(metin(genel_izler), encoding="utf-8")
        (hedef / "referans_girdiler.json").write_text(
            json.dumps({"tarih": ad, "kaliplar": GIRDI_KALIPLARI, **girdi}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        liste = lambda L: "".join(f"- {x}\n" for x in L[:60]) + (f"- … ve {len(L) - 60} satır daha\n" if len(L) > 60 else "")
        (hedef / "GEREKCE.md").write_text(
            f"# Referans · {ad}\n\nGerekçe: {' '.join(gerekce.split())}\n\n"
            f"- Dondurulduğu kod: `{head}`" + (" üzerine kaydedilmemiş değişiklikler" if kirli else "") + "\n"
            f"- Ortam: Python {o.get('python')}, ezdxf {o.get('ezdxf')}, shapely {o.get('shapely')}, pydantic {o.get('pydantic')}, "
            f"numpy {o.get('numpy')}, PyMuPDF {_surum('pymupdf')}\n"
            f"- Önceki referans: {onceki['ad'] if onceki else 'yok'}\n"
            f"- İçerik: {len(girdi['dosyalar'])} girdi dosyası, {len(girdi['vakalar'])} Beyin vakası, {len(yeni['dxf'])} DXF, "
            f"{len(yeni['pdf'])} PDF, {len(genel_izler)} genel motor izi\n"
            + (f"\nKarar: {karar}\n" if karar else "")
            + (f"\n{IZIN_SATIRI}\n" if kaldir else "")
            + (f"\n## Önceki referansa göre kaldırılan ya da azalan\n\n{liste(kaldir)}" if kaldir else "")
            + (f"\n## Önceki referansa göre değişen ya da eklenen\n\n{liste(degis)}" if degis else "")
            + "\n## Dosya özetleri\n\n" + "".join(f"- `{f}`: {_sha(hedef / f)}\n" for f in REF_DOSYALAR + ((GENEL_DOSYA,) if genel_izler else ())), encoding="utf-8")
    print(f"donduruldu: {hedef.relative_to(KOK)} (değişen {len(degis)}, izinli kaldırma {len(kaldir)})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Dondurulmuş referansa karşı doğrulama (ayrıntı: dosyanın başı)")
    ap.add_argument("--hizli", action="store_true", help="16 katalog planını atla")
    ap.add_argument("--referans", metavar="AD", help="karşılaştırılacak referans klasörü (varsayılan: en yenisi)")
    ap.add_argument("--dondur", action="store_true", help="yeni tarihli referans klasörü aç (tam koşu)")
    ap.add_argument("--gerekce", default="", help="--dondur için: neyin neden değiştiği")
    ap.add_argument("--ad", help="--dondur için klasör adı (varsayılan: bugünün tarihi)")
    ap.add_argument("--kaldirmaya-izin", action="store_true", help="--dondur için: kaldırma ya da azalmaya bilerek izin ver")
    ap.add_argument("--karar", help="--dondur için: değişikliğin dayandığı karar (KARARLAR/<AD>.md, ör. D-02)")
    ap.add_argument("--girdi-dokumu", action="store_true", help="bugünkü girdi özetini JSON olarak yaz; koşu yapma")
    a = ap.parse_args()
    try:
        if a.girdi_dokumu:
            d = girdi_durumu(KOK, GIRDI_KALIPLARI)
            if "hata" in d:
                print(f"Beyin test vakaları okunamadı: {d['hata']}", file=sys.stderr); return 1
            print(json.dumps({"tarih": datetime.date.today().isoformat(), "kaliplar": GIRDI_KALIPLARI, **d}, ensure_ascii=False, indent=1))
            return 0
        if a.dondur:
            if a.hizli or a.referans:
                print("--dondur tam koşu ister; --hizli ve --referans ile kullanılmaz"); return 1
            return dondur(a.gerekce, a.ad, a.kaldirmaya_izin, a.karar)
        klasorler = referans_klasorleri()
        if a.referans:
            secilen = [p for p in klasorler if p.name == a.referans]
            if not secilen:
                print(f"referans klasörü yok: {a.referans}; olanlar: {[p.name for p in klasorler]}"); return 1
        elif not klasorler:
            print("testler/referans altında tarihli referans klasörü yok"); return 1
        R, bilgi = referans_zinciri(secilen[0] if a.referans else klasorler[-1])
        return karsilastir(R, bilgi, a.hizli)
    except ReferansHatasi as e:
        print(f"REFERANS BOZUK: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
