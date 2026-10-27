"""Çelik projesinin kendi listemiz (öneren, İE-16 PR-2): Yapı Tanımı → genel motor → `bizim_liste.json`.

Hakemin (`testler/celik/kiyas.py`) okuduğu tek listemizi kurar. Liste elle yazılmaz: tanım genel motordan geçer (LLM yok), motorun yükleme
listesinin satırları yazılış sözlüğüyle (`sozluk.json`) listenin yazılışına çevrilir; adet ve kg motorundur. Çelik panel satırlarına hakemin
türü (`tur`) yazılır; bilinmeyen çelik satırı aracı durdurur. Kıyas, projenin paftasındaki yöntemle yapılır: ÇP-06, ÇP-07, ÇP-13 ve
ÇP-14'te tavan omegası ve aşık (B, varsayılan), ÇP-03'te makas, tavan paneli ve çatı paneli (A, `--yontem panel`; İE-16 PR-3a: PR-2'de beşi
de B sanılmıştı); bayiye giden liste kitabın yöntemiyle (A) ayrıca üretilir, kıyasa girmez.

Liste girdileriyle yeniden üretilebilir (`test_listeler.py`): tanım ve sözlük öneren ağacındadır, değişince liste yeniden üretilir; kural seti
kitaptadır (başkası değiştirebilir), bu yüzden listeyle birlikte içerik adresli kopyası `setler/<sha256 ilk 16>.json` donar
(`motor/genel/kural.py`: liste, hazırlandığı günkü setle yeniden üretilebilmelidir). Sözlüğün sayı kuralı `sayi_denetimi`'nde, iki satırımızın
hakemin bir anahtarında toplanmaması `anahtar_denetimi`'ndedir; çelik grubuna yalnız motorun çelik panel satırları girer (`grup_denetimi`); renk
yalnız motorun satırından gelir (kitabın `renkli_kalemler` kuralı), adı motorun renginin baştan kısaltmasıdır (`renk_adi`) ve sözlüğün adı
bizim kalemimizde olmayan bir renk sözcüğü yazamaz (`ad_renk_denetimi`, `RENKLER`).

    python3 -m testler.celik.projeler.liste_yap testler/celik/projeler/CP06/CP06.json [--yontem omega_asik] [--set kurallar/liste/kurallar.json]
        [--karkas kurallar/karkas/celik_karkas.json]

Tanım karkas kuralını isterse (`karkas: kural`; İE-16 PR-3a) kuralın dosyası da kural seti gibi içerik adresli kopyasıyla donar (`setler/`).
Mühürde kör ya da kapalı olan projenin listesinde yazılış sözlüğü de içerik adresli kopyasıyla donar ve liste o kopyayla yeniden üretilir
(İE-16 PR-4; plan `Celik_Cizim_Kurallari/PR-4/plan.md`, PR-2'nin açık sorusu): ölçüm, listenin yazıldığı günkü kuralın ve sözlüğün ölçümüdür;
sözlük sonra değişse de kör liste değişmez. Açık beşin ve hedef örneğin listesi bugünkü sözlükle üretilir (değişmedi).

Çıktı tanımın yanındaki `bizim_liste.json`; `--motor-cikti <klasör>` motorun bütün çıktısını (plan, çizim seti, IFC, liste) o klasörde bırakır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from testler.celik import kiyas, oku  # noqa: E402  (yalnız hakemin anahtarı ve çelik grubu okuması çağrılır)

BURADA = Path(__file__).resolve().parent
KOK = BURADA.parents[2]
SOZLUK = BURADA / "sozluk.json"
VARSAYILAN_SET = KOK / "kurallar" / "liste" / "kurallar.json"
VARSAYILAN_KARKAS = KOK / "kurallar" / "karkas" / "celik_karkas.json"   # karkas kuralı (İE-16 PR-3a); yalnız tanım `karkas: kural` isterse
SETLER = BURADA / "setler"
DONAN_SOZLUK = ("kor", "kapali")   # mühürdeki proje durumu: bu projelerin listesinde sözlük listeyle donar (İE-16 PR-4)
SAYI = re.compile(r"\d+(?:[.,]\d+)?")  # hakemin anahtarındaki sayı (testler/celik/kiyas.py)
# adda denetlenen renk sözcükleri (katlanmış); kapalı liste, dışındaki renk yazımı incelemede bakılır (sozluk.json › açıklama)
RENKLER = {"ANTRASIT", "GRI", "FUME", "KIRMIZI", "BORDO", "BEYAZ", "SIYAH", "YESIL", "MAVI", "LACIVERT", "KAHVE", "KAHVERENGI", "SARI",
           "KREM", "BEJ", "TURUNCU", "MOR", "PEMBE", "GUMUS", "ALTIN", "BAKIR", "BRONZ", "RAL"}

# motorun çelik panel satırları → hakemin türleri (testler/celik/oku.py › HARF)
CELIK_TURLERI = [
    (r"^(Dış|İç) cephe duvar panelleri$", "duvar_paneli"),
    (r"^Müştemilat duvar panelleri$", "duvar_paneli"),                       # ÇP-13 (= KT-01; İE-16 PR-3a): müştemilat ve veranda duvarları
    (r"^Veranda (korkuluğu|duvarı \(giriş çerçevesi\))", "duvar_paneli"),   # hakemde D (DUVAR, KORKULUK)
    (r"^Veranda dikmeleri \(kolon paneli\)$", "kolon_kiris"),
    (r"^Kirişler \(kiriş paneli", "kolon_kiris"),
    (r"^Çatı makas panelleri( \(\d+,\d+ mm\))?$", "makas"),              # İE-16 PR-3c: tek açıklığı 8 m'yi aşan makaslar ayrı satır
    (r"^Tavan paneli \(makas arası\)$", "tavan_paneli"),
    (r"^Çatı paneli \(", "cati_paneli"),
    (r"^Baca karkası$", "baca_paneli"),
    (r"^Boy C profil$", "c_profil"),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def celik_turu(kalem: str) -> str:
    uyan = {t for d, t in CELIK_TURLERI if re.search(d, kalem)}
    if len(uyan) != 1:
        raise SystemExit(f"çelik panel satırının türü {'bilinmiyor' if not uyan else 'belirsiz'}: {kalem!r} (CELIK_TURLERI)")
    return uyan.pop()


def olcu_yaz(sablon: str, boyut: str, kalem: str) -> str:
    """{0}, {1}… bizim ölçümüzün sayıları; {a0}, {a1}… adımızın sayıları; yazıldığı gibi."""
    adda = {f"a{i}": x for i, x in enumerate(SAYI.findall(kalem))}
    try:
        return sablon.format(*SAYI.findall(boyut or ""), **adda)
    except (IndexError, KeyError):
        raise SystemExit(f"sözlükteki ölçü yazılışı {sablon!r} bizim satırımıza ({kalem!r}, {boyut!r}) uymuyor") from None


def sayilar(metin: str) -> Counter:
    return Counter(float(x.replace(",", ".")) for x in SAYI.findall(metin or ""))


def sayi_denetimi(kalem: str, boyut: str, liste_adi: str, liste_boyutu: str) -> None:
    """Sözlük yalnız yazılışı çevirir: listemizin ad ve ölçüsündeki sayılar bizim ad ve ölçümüzdeki sayılarla aynıdır (sayı eklenmez, düşmez,
    değişmez; ad ile ölçü arasında taşınabilir ve sırası değişebilir). Bozulursa araç durur."""
    kaynak, yazilan = sayilar(boyut) + sayilar(kalem), sayilar(liste_adi) + sayilar(liste_boyutu)
    if kaynak != yazilan:
        raise SystemExit(f"sözlük {kalem!r} ({boyut!r}) satırının sayılarını değiştiriyor → {liste_adi!r} ({liste_boyutu!r}): "
                         f"düşen {sorted((kaynak - yazilan).elements())}, eklenen {sorted((yazilan - kaynak).elements())} (sozluk.json › sayı kuralı)")


def grup_denetimi(satir: dict) -> None:
    """Hakem çelik grubundaki satırın türünü okur (`kiyas.bizim_celik`): çelik grubunda yalnız motorun çelik panel satırları (`tur`lu) durur;
    grup adında sayı olmaz (hakemin anahtarı grubu sayısız okur)."""
    if oku.celik_grubu_mu(satir["grup"]) != ("tur" in satir):
        raise SystemExit(f"sözlük {satir['kalem']!r} satırını {'çelik grubuna' if 'tur' not in satir else 'çelik grubunun dışına'} "
                         f"taşıyor ({satir['grup']!r})")
    if re.search(r"\d", satir["grup"]):
        raise SystemExit(f"grup adında sayı: {satir['grup']!r} ({satir['kalem']!r})")


def renk_adi(renk: str, sozluk: dict) -> str:
    """Şablonun renk adı motorun renginin baştan kısaltmasıdır (ör. antrasit gri → ANTRASİT; GRİ olmaz); sözlük rengi değiştiremez."""
    ad = sozluk["renk_adlari"].get(renk, renk.upper())
    sozcukler, motorun = oku.katla(ad).split(), oku.katla(renk).split()
    if not sozcukler or sozcukler != motorun[:len(sozcukler)]:
        raise SystemExit(f"sözlükteki renk adı {ad!r} motorun rengi {renk!r} değil")
    return ad


def renk_sozcukleri(metin: str) -> set[str]:
    return set(re.findall(r"[A-Z]+", oku.katla(metin))) & RENKLER


def ad_renk_denetimi(kalem: str, ad: str) -> None:
    """Sözlüğün adı, bizim kalemimizde olmayan bir renk sözcüğü yazamaz (renk yalnız motorun satırından gelir; liste `RENKLER`'le sınırlı)."""
    eklenen = renk_sozcukleri(ad) - renk_sozcukleri(kalem)
    if eklenen:
        raise SystemExit(f"sözlük {kalem!r} satırının adına renk yazıyor: {sorted(eklenen)} → {ad!r} (renk yalnız motordan)")


def anahtar_denetimi(satirlar: list[dict]) -> None:
    """Hakem aynı anahtardaki adetleri toplar (`kiyas.satir_satir`): sözlük, motorun ayrı tuttuğu iki satırı bir anahtara toplayamaz."""
    goren: dict = {}
    for s in satirlar:
        if "tur" in s:
            continue
        bizim = kiyas.anahtar(s.get("bizim_grup") or s["grup"], s["kalem"], s.get("bizim_boyut", s["boyut"]))
        liste_ = kiyas.anahtar(s["grup"], s.get("liste_adi") or s["kalem"], s["boyut"])
        if goren.setdefault(liste_, bizim) != bizim:
            raise SystemExit(f"sözlük iki satırımızı hakemin bir anahtarına topluyor: {goren[liste_]} ve {bizim} → {liste_}")


def cevir(s: dict, sozluk: dict) -> dict:
    """Motorun bir satırı → listemizin satırı. Bizim grup, ad ve ölçü `bizim_*` alanlarında kalır. Renk yalnız motorun satırındadır
    (`renk`; kitabın `renkli_kalemler` kuralı); sözlüğün `renkli`si yalnız şablonun o rengi adda yazıp yazmadığını söyler."""
    out = {"grup": s["grup"], "kalem": s["kalem"], "boyut": s.get("boyut") or "", "adet": s.get("adet"), "kg": s.get("kg"),
           "durum": s.get("durum")}
    if s["grup"] == "Çelik panel":
        out["tur"] = celik_turu(s["kalem"])
        grup_denetimi(out)
        return out
    uyan = [k for k in sozluk["kalemler"] if re.search(k["bizim"], s["kalem"])]
    if len(uyan) > 1:
        raise SystemExit(f"sözlükte {s['kalem']!r} için birden çok kalem var")
    grup = sozluk["gruplar"].get(s["grup"])
    if not uyan:
        out.update({"grup": grup, "bizim_grup": s["grup"]} if grup else {})
        grup_denetimi(out)
        return out
    k = uyan[0]
    ad = k["ad"]
    ad_renk_denetimi(s["kalem"], ad)
    if k.get("renkli") and s.get("renk"):
        ad += f" ({renk_adi(s['renk'], sozluk)})"
    out.update(grup=k.get("grup") or grup or s["grup"], bizim_grup=s["grup"], liste_adi=ad)
    if "olcu" in k:
        out.update(boyut=olcu_yaz(k["olcu"], out["boyut"], s["kalem"]), bizim_boyut=out["boyut"])
    sayi_denetimi(s["kalem"], out.get("bizim_boyut", out["boyut"]), ad, out["boyut"])
    grup_denetimi(out)
    return out


def motor(tanim: Path, cikti: Path, yontem: str, kural_seti: Path, karkas: Path | None = None) -> Path:
    komut = [sys.executable, "-m", "motor.genel.uret", str(tanim), str(cikti), "--set", str(kural_seti), "--yontem", yontem,
             "--perspektifsiz", "--bayisiz"] + (["--karkas", str(karkas)] if karkas else [])
    r = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"genel motor başarısız ({r.returncode}): {(r.stdout + r.stderr)[-2000:]}")
    yollar = sorted(Path(cikti).glob("*_yukleme.json"))
    if len(yollar) != 1:
        raise SystemExit(f"motor çıktısında tek yükleme listesi yok: {[p.name for p in yollar]}")
    return yollar[0]


def _icerik_kopyasi(yol: Path, yaz: bool) -> tuple[str, Path]:
    """Dosyanın SHA-256'sı ve listeyle donan içerik adresli kopyası (`setler/`; yalnız liste depoya yazılırken); kopya varsa baytları aynı olmalı."""
    h = sha256(yol)
    kopya = SETLER / f"{h[:16]}.json"
    if not kopya.exists() and yaz:
        SETLER.mkdir(exist_ok=True)
        shutil.copyfile(yol, kopya)
    elif kopya.exists() and sha256(kopya) != h:
        raise SystemExit(f"{kopya} başka bir dosyanın kopyası")
    return h, kopya


def set_kaydi(kural_seti: Path, yaz: bool = True) -> dict:
    """Kural setinin kaydı ve listeyle donan içerik adresli kopyası."""
    h, kopya = _icerik_kopyasi(kural_seti, yaz)
    ks = json.loads(Path(kural_seti).read_text(encoding="utf-8"))
    return {"yol": Path(kural_seti).resolve().relative_to(KOK).as_posix(), "sema": ks.get("sema"), "sha256": h,
            "kopya": kopya.relative_to(KOK).as_posix()}


def sozluk_donar_mi(kod: str) -> bool:
    """Projenin mühürdeki durumu kör ya da kapalıysa listesinin sözlüğü listeyle donar."""
    m = json.loads(kiyas.MUHUR.read_text(encoding="utf-8"))
    return (m["projeler"].get(kod) or {}).get("durum") in DONAN_SOZLUK


def sozluk_kaydi(sozluk_yolu: Path = SOZLUK, yaz: bool = True) -> dict:
    """Sözlüğün kaydı ve listeyle donan içerik adresli kopyası."""
    h, kopya = _icerik_kopyasi(sozluk_yolu, yaz)
    return {"surum": json.loads(Path(sozluk_yolu).read_text(encoding="utf-8"))["surum"], "sha256": h, "kopya": kopya.relative_to(KOK).as_posix()}


def liste(tanim: Path, yukleme: Path, yontem: str, kural_kaydi: dict, sozluk_yolu: Path = SOZLUK, karkas_kaydi: dict | None = None,
          sozluk_donmus: dict | None = None) -> dict:
    """`sozluk_donmus` (kör ve kapalı proje): sözlüğün donan kopyasının kaydı; sözlük o kopyadan okunur (kopyanın baytları kaydın
    SHA-256'sıyla aynı olmalı; ayrıca başka bir sözlük verilemez)."""
    t = json.loads(Path(tanim).read_text(encoding="utf-8"))
    y = json.loads(Path(yukleme).read_text(encoding="utf-8"))
    if sozluk_donmus:
        if Path(sozluk_yolu) != SOZLUK:
            raise SystemExit("sözlük ya donmuş kopyadan ya verilen dosyadan okunur, ikisi birden değil")
        sozluk_yolu = KOK / sozluk_donmus["kopya"]
        if sha256(sozluk_yolu) != sozluk_donmus["sha256"]:
            raise SystemExit(f"{sozluk_donmus['kopya']} donmuş sözlüğün kaydıyla aynı değil")
    sozluk = json.loads(Path(sozluk_yolu).read_text(encoding="utf-8"))
    if y["yontem"] != yontem:
        raise SystemExit(f"motorun listesi {y['yontem']} yöntemiyle; istenen {yontem}")
    satirlar = [cevir(s, sozluk) for s in y["satirlar"] if not s["kalem"].startswith("Toplam")]
    anahtar_denetimi(satirlar)
    return {
        "aciklama": ("Kendi listemiz (öneren, İE-16): Yapı Tanımı genel motordan geçti, satırlar yazılış sözlüğüyle listenin yazılışına çevrildi "
                     "(`testler/celik/projeler/liste_yap.py`); adet ve kg motorundur. Hakem bu dosyayı yalnız bu yoldan ve commit'li okur."),
        "kod": t["kod"],
        "tanim": {"yol": Path(tanim).resolve().relative_to(KOK).as_posix(), "sha256": sha256(tanim)},
        "kural_seti": kural_kaydi,
        **({"karkas_kurali": karkas_kaydi} if karkas_kaydi else {}),
        "yontem": {"kod": y["yontem"], "ad": y.get("yontem_adi")},
        "sozluk": sozluk_donmus or {"surum": sozluk["surum"], "sha256": sha256(sozluk_yolu)},
        "satirlar": satirlar,
    }


def yaz(veri: dict, yol: Path) -> None:
    ust = {k: v for k, v in veri.items() if k != "satirlar"}
    metin = json.dumps(ust, ensure_ascii=False, indent=1)[:-2]
    satirlar = ",\n".join("  " + json.dumps(s, ensure_ascii=False) for s in veri["satirlar"])
    Path(yol).write_text(metin + ',\n "satirlar": [\n' + satirlar + "\n ]\n}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--yontem", choices=("omega_asik", "panel"), default="omega_asik")
    ap.add_argument("--set", type=Path, default=VARSAYILAN_SET)
    ap.add_argument("--karkas", type=Path, default=VARSAYILAN_KARKAS, help="karkas kuralı (yalnız tanım `karkas: kural` isterse)")
    ap.add_argument("--motor-cikti", type=Path, help="motorun çıktısını bu klasörde bırak (yoksa geçici klasör)")
    ap.add_argument("--cikti", type=Path, help="liste dosyası (varsayılan: tanımın yanındaki bizim_liste.json)")
    a = ap.parse_args(argv)
    tanim = a.tanim.resolve()
    hedef = (a.cikti or tanim.parent / "bizim_liste.json").resolve()
    kayit = set_kaydi(a.set.resolve(), yaz=hedef.is_relative_to(BURADA))
    calisan = KOK / kayit["kopya"] if (KOK / kayit["kopya"]).exists() else a.set.resolve()
    # karkas kuralı (yalnız tanım isterse): kural seti gibi içerik adresli kopyası listeyle donar, motor o kopyayla koşar
    kk = (set_kaydi(a.karkas.resolve(), yaz=hedef.is_relative_to(BURADA))
          if json.loads(tanim.read_text(encoding="utf-8")).get("karkas") == "kural" else None)
    kk_calisan = (KOK / kk["kopya"] if (KOK / kk["kopya"]).exists() else a.karkas.resolve()) if kk else None
    kod = json.loads(tanim.read_text(encoding="utf-8"))["kod"]
    # kör ve kapalı proje: sözlük de listeyle donar; depo dışına yazılan denemede kopya yazılmaz, sözlük bugünkü dosyadan okunur
    sd = sozluk_kaydi(yaz=hedef.is_relative_to(BURADA)) if sozluk_donar_mi(kod) else None
    if sd and not (KOK / sd["kopya"]).exists():
        sd = None
    with tempfile.TemporaryDirectory() as gecici:
        klasor = a.motor_cikti.resolve() if a.motor_cikti else Path(gecici)
        veri = liste(tanim, motor(tanim, klasor, a.yontem, calisan, kk_calisan), a.yontem, kayit, karkas_kaydi=kk, sozluk_donmus=sd)
    yaz(veri, hedef)
    celik = [s for s in veri["satirlar"] if "tur" in s]
    print(f"{veri['kod']}: {len(veri['satirlar'])} satır ({len(celik)} çelik, {round(sum(s['kg'] or 0 for s in celik), 2)} kg; "
          f"yöntem {veri['yontem']['kod']}) → {hedef}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
