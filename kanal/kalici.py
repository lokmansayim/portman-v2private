"""İE-02 · kalıcı işleyici: Postgres üzerinde mesaj → iş → Beyin/Motor → giden satırları → gönderim.

Kural ve Motor kodu değişmez: işleme kanal/worker.py::isle ile yapılır; konuşma dosyadan değil Postgres'ten okunur ve işin
bütün sonuçlarıyla birlikte tek işlemde yazılır (kanal/depo.py). Ayrıntı: docs/is_emirleri/IE-02.md.

Bu dosya WhatsApp'a bağlanmaz. Gönderim, çağıranın verdiği gönderici işleviyle yapılır (canlıda hosting; testte sahte).

Komut satırı (yalnız yerel/izole ortam; PORTMAN_PG_DSN ve PORTMAN_KANAL_DIR ortam değişkenleri):
  python kanal/kalici.py goc                        göçleri uygula
  python kanal/kalici.py isle --ayar AYAR.json [--tek] [--bos-bekle SN]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import sys
import time
import traceback
import uuid
from pathlib import Path

KOD = Path(__file__).resolve().parent
for _yol in (KOD, KOD.parent):                       # paket düzeninde beyin/ kökte (KOD), depoda bir üstte
    if (_yol / "beyin").is_dir() and str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))
if str(KOD) not in sys.path:
    sys.path.insert(0, str(KOD))

import worker as W                                   # noqa: E402  (kanal/worker.py; paket düzeninde kökte)
import etkilesim as ET                               # noqa: E402  (İE-04: buton ve liste cevaplarının çözümü)
from depo import HATA_BAYIYE, Cakisma, Depo, KiraKaybi, maske     # noqa: E402
from beyin.konusma import BellekKonusma              # noqa: E402


class Gonderilmedi(Exception):
    """Gönderici dış çağrı yapmadan vazgeçti (ör. dosya doğrulaması): satır kesin olarak gönderilmedi."""


class YenidenDene(Exception):
    """İE-06: dış çağrı (messages POST) yapılmadan vazgeçildi ve satır bir kez daha denenecek (ör. medya yüklenemedi):
    satır 'bekliyor'a döner, deneme sayısı artmış kalır; gönderici bir sonraki turda yeniden alır (feature.php upload_failed)."""


def isleyici_adi() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _kopya(d):
    return json.loads(json.dumps(d)) if d is not None else None


# ───────────────────────── revizyon onayı ─────────────────────────
def onay_denetimi(depo: Depo, gelen: dict, d: dict | None) -> dict:
    """Kural katmanı bir onay kaydettiyse çağrılır (d: işten önceki konuşma). Onay, bayinin mesajı yazdığı anda telefonuna
    ulaşmış son revizyona bağlanır. Ulaşma anı için ilk bulunan alt sınır kullanılır: Meta'nın ilk 'delivered'/'read'
    bildirimi (teslim); yoksa Meta'nın ilk 'sent' bildirimi (gonderildi); o da yoksa hosting'in WhatsApp API kabulünü
    kaydettiği an (kabul). İlk ikisi, bayinin mesaj zamanı gibi Meta saatidir; kabul hosting saatidir. Kabul teslim
    değildir; yalnız Meta bildirimi gelmediğinde alt sınırdır. Onay sınırdan SONRA (aynı saniye değil) yazılmış olmalı.
    Dönen: {"kabul": bool, "is_emri_no", "rev", "pdf_wamid", "alinti_id", "sinir", "neden", "mesaj"?, "patrona"?}."""
    bilgi = {"kabul": True, "alinti_id": gelen.get("context_id"), "is_emri_no": None, "rev": None, "pdf_wamid": None,
             "sinir": None, "neden": None}
    if not d or d.get("asama") != "onay_bekliyor" or not d.get("son_is_emri"):
        bilgi["neden"] = "onay bekleyen plan yok"
        return bilgi
    ie = d["son_is_emri"]; no = ie.get("is_emri_no"); rev = int(ie.get("revizyon") or 1)
    bilgi.update(is_emri_no=no, rev=rev)
    r = depo.revizyon_iletimi(gelen["sender"], no, rev)
    if r is None:
        bilgi["neden"] = "geçişten önceki plan: revizyon kaydı yok"      # bugünkü davranış
        return bilgi
    bilgi["pdf_wamid"] = r["pdf_wamid"]
    etiket = f"{no} r{rev:02d}"
    tekrar = f"{etiket} planını onaylıyorsanız lütfen yeniden \"onaylıyorum\" yazın."

    def red(neden: str, mesaj: str, patrona: bool = False) -> dict:
        bilgi.update(kabul=False, neden=neden, mesaj=mesaj, patrona=patrona)
        return bilgi
    if gelen.get("context_id"):
        ar = depo.alintinin_revizyonu(gelen["sender"], gelen["context_id"])
        if ar and (ar["is_emri_no"], ar["rev"]) != (no, rev):
            return red("alıntı başka revizyona ait",
                       f"Alıntıladığınız mesaj {ar['is_emri_no']} r{ar['rev']:02d} planına ait; güncel plan {etiket}. {tekrar}")
    if r["pdf_durum"] in ("belirsiz", "gonderilmedi") or r["teslim_durumu"] == "failed":
        neden = f"PDF gönderimi teyitsiz ({r['teslim_durumu'] if r['teslim_durumu'] == 'failed' else r['pdf_durum']})"
        return red(neden, f"{etiket} planının size ulaştığını teyit edemedim; onayınızı kaydetmedim. Lokman Bey'e iletiyorum.", True)
    sinir, an = next(((s, r[s]) for s in ("teslim", "gonderildi", "kabul") if r[s] is not None), (None, None))
    bilgi["sinir"] = sinir
    yazildi = float(gelen.get("timestamp") or 0)
    if an is None or yazildi <= float(an):
        return red("onay, plan ulaşmadan yazılmış",
                   f"Onay mesajınız {etiket} planı size ulaşmadan yazılmış görünüyor; onayınızı kaydetmedim. "
                   f"Planı inceledikten sonra {tekrar[0].lower()}{tekrar[1:]}")
    bilgi["neden"] = {"teslim": "plan teslim edildikten sonra yazılmış",
                      "gonderildi": "Meta planı gönderdikten sonra yazılmış (teslim bildirimi henüz yok)",
                      "kabul": "plan gönderimi kabul edildikten sonra yazılmış (Meta bildirimi henüz yok)"}[sinir]
    return bilgi


def _red_ciktisi(gelen: dict, k: BellekKonusma, talep: dict, red: dict) -> dict:
    satirlar = [W.giden_metin(gelen, red["mesaj"], 1)]
    if red["patrona"] and (gelen.get("role") or "bayi") != "patron":
        satirlar.append(W.giden_metin(gelen, f"Portman: {maske(gelen['sender'])} onay yazdı ama kaydedilmedi: {red['neden']}.", 2, "PATRON", "bildirim"))
    k.not_dus("gelen", talep.get("ozet") or "", {"niyet": talep.get("niyet"), "guven": talep.get("guven")})
    k.not_dus("kural", f"onay revizyona bağlanmadı: {red['neden']}")
    k.not_dus("giden", red["mesaj"], {"eylem": "cevapla", "gerekce": "onay bağlanmadı"})
    k.kaydet()
    return {"satirlar": satirlar, "sonuc": {"eylem": "cevapla", "gerekce": f"onay bağlanmadı: {red['neden']}", "niyet": "onay",
                                             "asama": k.d.get("asama")}}


def _karar_ozeti(d_eski: dict | None, k: BellekKonusma, cikti: dict) -> dict:
    """Soru ve revizyon kayıtları için bu işte ne olduğu: kural katmanının bu işte düştüğü notlardan ve konuşmanın
    sıfırlanıp sıfırlanmadığından okunur (kural koduna dokunmadan)."""
    kural = [str(g.get("metin") or "") for g in k.yeni_notlar if g.get("yon") == "kural"]
    onay = (cikti.get("sonuc") or {}).get("gerekce") == "plan onaylandı"
    ie = (d_eski or {}).get("son_is_emri") or {}
    return {"sifirlandi": k.sifirlandi,
            "d01_cevap": any(n.startswith("eski taslak sorusunun cevabı") for n in kural),
            "pencere_cevap": any(n.startswith("pencere_islem cevabı") for n in kural),
            "oncelik_cevap": any(n.startswith("öncelik cevabı") for n in kural),
            "okuma_cevap": any(n.startswith("okuma cevabı") for n in kural),          # İE-08 PR-2b
            "onaylanan_is_emri_no": ie.get("is_emri_no") if onay else None,
            "onaylanan_rev": int(ie.get("revizyon") or 1) if onay else None}


# ───────────────────────── işleme ─────────────────────────
def bir_is(depo: Depo, settings: dict, sahip: str | None = None) -> dict | None:
    """Bir işi alır ve bitirir. None: sırada iş yok. Dönen sözlükte 'durum': bitti | basarisiz | cakisma | atildi."""
    sahip = sahip or isleyici_adi()
    alinan = depo.is_al(sahip, kira_sn=int(settings.get("kira_sn") or 600), en_cok=int(settings.get("en_cok_deneme") or 3))
    if not alinan:
        return None
    j, gelen = alinan["is"], alinan["gelen"]
    t0 = time.time()
    d, surum = depo.konusma_oku(gelen["sender"])
    k = BellekKonusma(gelen["sender"], d)
    d_eski = _kopya(d)
    yazili = gelen.get("type") in W.GELEN_YAZILI and (bool((gelen.get("text") or "").strip()) or bool(gelen.get("reply_id")))
    cikarim = j.get("cikarim")
    muhendis_mu = (gelen.get("role") or "bayi") == "muhendis"      # İE-08 8b: mühendis kartının mesajı LLM'siz (kanal/muhendis.py)
    gorsel = gelen.get("type") in W.GORSEL_TURLERI and W.gorsel_acik(settings) and not muhendis_mu
    if gorsel and "gorsel" not in (cikarim or {}):
        # İE-20: plan resmi ya da PDF; dosyayı gönderici indirir (ajanın WhatsApp anahtarı yok): inene kadar beklenir, sonra okunur
        # (LLM, 1 çağrı). Okuma iş satırına yazılır: yeniden denenen iş dosyayı yeniden okutmaz.
        cikarim = {**(cikarim or {}), "gorsel": W.gorsel_oku(gelen, settings, medya_bekle(depo, gelen, settings))
                   if gelen.get("bayi") else {"durum": "atlandi", "neden": "kayıtsız gönderen"}}
        if not depo.cikarim_kaydet(j["id"], sahip, cikarim):
            return {"durum": "atildi", "is_id": j["id"], "neden": "kira kaybedildi (okuma kaydı)"}
    if yazili and cikarim is None and not muhendis_mu:
        if gelen.get("reply_id"):                    # İE-04: buton/liste cevabı; LLM çağrılmaz, kimlik kayıtla doğrulanır
            etk = ET.coz(gelen, d, depo.giden_satiri)
            cikarim = {"etkilesim": etk, "talep": etk.get("talep"), "meta": {"backend": "etkilesim", "kimlik": etk.get("kimlik"), "gecerli": etk.get("gecerli")}}
        else:
            try:
                talep, meta = W.cikar(gelen, settings, k)
                cikarim = {"talep": talep.model_dump(mode="json"), "meta": meta}
            except Exception as e:                       # hata da kaydedilir: yeniden alınan iş LLM'i yeniden çağırmaz
                cikarim = {"hata": f"{type(e).__name__}: {str(e)[:300]}"}
        if not depo.cikarim_kaydet(j["id"], sahip, cikarim):
            return {"durum": "atildi", "is_id": j["id"], "neden": "kira kaybedildi (çıkarım kaydı)"}
    hazirlik = W.KANAL / "projects" / ".hazirlik" / f"is{j['id']}-{uuid.uuid4().hex[:8]}"      # her deneme kendi klasöründe
    import muhendis as MH                              # İE-08 8b; burada: `kalici.py goc` ve eski paket düzenleri (Kapı M) muhendis.py'siz çalışır
    try:
        if muhendis_mu:
            cikti = MH.isle(depo, gelen)                 # İE-08 8b: mühendisin düğmesi, Excel'i ya da notu (LLM'siz)
        else:
            katalog = W.katalog_nesnesi(settings, kabul_edilmis=depo.kabul_edilmis_adaylar())      # K-A10: kabul kaydı olmayan 'gecerli' aday sunulmaz
            ekli = dict(cikarim or {})

            def ek_kaydet(anahtar: str, deger: dict) -> None:  # İE-14: LLM-önce sonuçları çıkarımın yanına; yeniden denenen iş LLM'i yeniden çağırmaz
                ekli[anahtar] = deger
                depo.cikarim_kaydet(j["id"], sahip, ekli)
            def ara_gonder(metin: str) -> dict | None:    # İE-14 (inceleme C7): "hazırlıyorum" uzun üretimden önce, ayrılmış sırayla gider
                s = W.giden_metin(gelen, metin, depo.ERKEN_SIRA)
                return s if depo.ara_satir_yaz(j["id"], sahip, gelen["id"], s) else None
            cikti = W.isle(gelen, settings, k=k, cikarim=cikarim if (yazili or gorsel) else None, proje_koku=hazirlik, giden_bul=depo.giden_satiri, katalog=katalog,
                           ek_kaydet=ek_kaydet, ara_gonder=ara_gonder)
            # Onay denetimi kuralın sonucuna bakar: hangi yoldan olursa olsun (ör. süresi dolan D-01 sorusundan sonra) bir onay
            # kaydedildiyse, onay bayinin gördüğü revizyona bağlanabiliyor mu diye sınanır; bağlanamıyorsa onay yazılmaz.
            if (cikti.get("sonuc") or {}).get("gerekce") == "plan onaylandı":
                denetim = onay_denetimi(depo, gelen, d)
                if not denetim["kabul"]:
                    k = BellekKonusma(gelen["sender"], d)
                    cikti = _red_ciktisi(gelen, k, cikarim["talep"], denetim)
                cikti["sonuc"]["onay"] = {a: denetim.get(a) for a in ("kabul", "is_emri_no", "rev", "pdf_wamid", "alinti_id", "sinir", "neden")}
                MH.onay_kancasi(depo, gelen, d, cikti)          # İE-08 8b: çelik onayı → mühendis kontrol kaydı ve bildirimi (aynı işlemde)
    except Exception:
        hata = traceback.format_exc()[-2500:]
        k = BellekKonusma(gelen["sender"], d)       # yarım kalan durum değişikliği yazılmaz
        import sablonlar as S
        cikti = {"satirlar": [W.giden_metin(gelen, HATA_BAYIYE, 1)]
                 + ([] if gelen.get("role") == "patron" else
                    [W.giden_metin(gelen, f"Portman: {maske(gelen['sender'])} mesajı işlenirken hata oluştu; günlüğe bakın.", 2, "PATRON", "bildirim"),
                     # İE-07 P4: Patron'un penceresi kapalıysa şablonla ulaşır (talep kimliği boş gitmez: T-<iz>)
                     S.patron_bildirim_satiri(gelen, 3, gelen.get("bayi"), None, ((d or {}).get("son_is_emri") or {}).get("is_emri_no"))]),
                 "sonuc": {"eylem": "hata", "gerekce": "beklenmeyen hata"}, "hata": hata}
    cikti["sonuc"]["worker"] = "kalici"; cikti["sonuc"]["sure_s"] = round(time.time() - t0, 1)
    yer = None
    try:
        yer = _yerlestir(cikti, hazirlik)
        kayit = depo.isi_bitir(j, sahip, gelen, surum, d_eski, k.d, cikti, _karar_ozeti(d_eski, k, cikti))
    except Cakisma as e:                            # kayıt kesin yazılmadı: bu işin dosyaları silinir, numara boşalır
        _dosyalari_sil(yer, hazirlik)
        depo.is_geri_birak(j["id"], sahip, str(e))
        return {"durum": "cakisma", "is_id": j["id"], "neden": str(e)}
    except KiraKaybi as e:
        _dosyalari_sil(yer, hazirlik)
        return {"durum": "atildi", "is_id": j["id"], "neden": str(e)}
    # Başka bir hata (ör. COMMIT sırasında bağlantı koptu) yukarı çıkar ve dosyalara dokunulmaz: kayıt yazılmış olabilir,
    # dosyayı geri almak yazılmış bir revizyonun PDF'ini yok ederdi. Kaydı olmayan bir klasör kalırsa gönderilmez.
    shutil.rmtree(hazirlik, ignore_errors=True)
    return {"durum": "basarisiz" if cikti.get("hata") else "bitti", "is_id": j["id"], "mesaj_id": gelen["id"],
            "eylem": cikti["sonuc"].get("eylem"), "gerekce": cikti["sonuc"].get("gerekce"), "giden": len(cikti["satirlar"]), **kayit}


MEDYA_BEKLE_SN = 60                 # İE-20: gelen dosyanın indirilmesi beklenir (gönderici her turda indirir; çoğu birkaç saniye)


def medya_bekle(depo: Depo, gelen: dict, settings: dict, uyu=time.sleep) -> dict | None:
    """İE-20: gelen mesajın dosyası indirilene kadar bekler ve kaydını döner ({yol, mime, boyut, sha256, …}). Kayıt yoksa (medya sınırı)
    ya da gönderici üç denemede indiremediyse ya da süre dolduysa None. Ajan WhatsApp'a bağlanmaz: indirme göndericinin işidir."""
    bekle = float((settings.get("gorsel_okuma") or {}).get("bekle_sn", MEDYA_BEKLE_SN))
    bitis = time.time() + bekle
    while True:
        d = depo.mesajin_dosyasi(gelen["id"])
        if d is None:
            return None
        if d.get("yol") and Path(d["yol"]).is_file():
            return d
        if int(d.get("deneme") or 0) >= 3 or time.time() >= bitis:
            return None
        uyu(1.0)


def _yol_degistir(x, eski: str, yeni: str):
    """cikti içindeki (satırlar, cizim, ekler) hazırlık yollarını yerine taşınan yollarla değiştirir (yerinde)."""
    if isinstance(x, dict):
        for k, v in list(x.items()):
            x[k] = _yol_degistir(v, eski, yeni)
        return x
    if isinstance(x, list):
        return [_yol_degistir(v, eski, yeni) for v in x]
    if isinstance(x, str) and x.startswith(eski):
        return yeni + x[len(eski):]
    return x


def _yerlestir(cikti: dict, hazirlik: Path):
    """Hazırlık klasöründeki her <ad>/rNN çıktısını (Motor: İş Emri numarası; İE-04: SECENEK-<set> görseli) projects/<ad>/rNN'e
    taşır. Hedef klasör yalnız yoksa açılır (os.mkdir, süreçler arası da tek); varsa başka bir iş aynı adı üretmiştir: üzerine
    yazılmaz, Cakisma. Satırlardaki ve çizim kaydındaki yollar güncellenir. Dönen: [(kaynak, hedef), …] ya da None."""
    if not hazirlik.is_dir():
        return None
    ciftler = []
    for ad_dir in sorted(p for p in hazirlik.iterdir() if p.is_dir()):
        for kaynak in sorted(p for p in ad_dir.iterdir() if p.is_dir() and p.name.startswith("r")):
            hedef = W.KANAL / "projects" / ad_dir.name / kaynak.name
            hedef.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.mkdir(hedef)
            except FileExistsError:
                for k_, h_ in ciftler:                       # bu işte daha önce açılanlar geri alınır
                    shutil.rmtree(h_, ignore_errors=True)
                raise Cakisma(f"projects/{ad_dir.name}/{kaynak.name} başka bir işe ait; üzerine yazılmaz") from None
            for f in kaynak.iterdir():
                os.replace(f, hedef / f.name)
            ciftler.append((kaynak, hedef))
            _yol_degistir(cikti, str(kaynak), str(hedef))
    return ciftler or None


def _dosyalari_sil(yer, hazirlik: Path) -> None:
    """Kaydı kesin yazılmayan işin dosyaları: bu işin açtığı projects/<ad>/rNN klasörleri (os.mkdir ile yalnız bu iş açtı) ve
    hazırlık klasörü. Numara başka bir işi engellemez; eski dosya hazırlıkta birikmez."""
    for _k, h in (yer or []):
        shutil.rmtree(h, ignore_errors=True)
    shutil.rmtree(hazirlik, ignore_errors=True)


# ───────────────────────── gönderim ─────────────────────────
def gonder(depo: Depo, gonderici, en_fazla: int = 100) -> dict:
    """Bekleyen giden satırlarını sırayla doğrudan gönderir (canlıda kanal/gonderici.py'nin Meta göndericisi; testlerde sahte).
    gonderici(satir) WhatsApp API kabul ederse giden mesaj kimliğini döner; Gonderilmedi → kesin gönderilmedi; YenidenDene →
    satır bekliyor'a döner ve tur biter (sonraki turda yeniden); başka her hata → belirsiz (otomatik yeniden gönderilmez)."""
    say = {"kabul_edildi": 0, "belirsiz": 0, "gonderilmedi": 0, "yeniden": 0, "yarim_belirsiz": depo.yarim_gonderimleri_belirsiz_say()}
    for _ in range(en_fazla):
        r = depo.gonderime_al()
        if r is None:
            break
        if r["dosya"]:                      # feature.php gibi: dosya (PDF, görsel) yoksa ya da kayıttaki özetle uyuşmuyorsa gönderilmez
            p = Path(r["dosya"] or "")
            if not p.is_file() or (r["sha256"] and hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]):
                depo.gonderim_sonucu(r["id"], "gonderilmedi", hata="Dosya yok ya da kayıttan sonra değişmiş; gönderilmedi")
                say["gonderilmedi"] += 1
                continue
        try:
            dis_id = gonderici(r)
            depo.gonderim_sonucu(r["id"], "kabul_edildi", dis_id=dis_id); say["kabul_edildi"] += 1
        except Gonderilmedi as e:
            depo.gonderim_sonucu(r["id"], "gonderilmedi", hata=str(e)[:300]); say["gonderilmedi"] += 1
        except YenidenDene as e:
            depo.gonderim_geri_birak(r["id"], str(e)[:300]); say["yeniden"] += 1
            break
        except Exception as e:
            depo.gonderim_sonucu(r["id"], "belirsiz", hata=f"Gönderim sonucu belirsiz; otomatik tekrar yok. {type(e).__name__}: {str(e)[:200]}")
            say["belirsiz"] += 1
    return say


# ───────────────────────── komut satırı ─────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("goc")
    a = alt.add_parser("isle")
    a.add_argument("--ayar", required=True)
    a.add_argument("--tek", action="store_true", help="bir iş işle ve çık")
    a.add_argument("--bos-bekle", type=float, default=0, help="kuyruk boşsa bu kadar saniye bekleyip yeniden bak (0: çık)")
    ns = ap.parse_args(argv)
    depo = Depo()
    if ns.komut == "goc":
        print("uygulanan göçler:", depo.goc_uygula() or "yok (güncel)")
        return 0
    settings = json.loads(Path(ns.ayar).read_text(encoding="utf-8"))
    sahip = isleyici_adi()
    dur = {"istendi": False}
    # SIGTERM (servis yeniden başlatma): elindeki işi bitirir, sonra çıkar; iş yarıda kalıp kira beklemez
    signal.signal(signal.SIGTERM, lambda *_: dur.__setitem__("istendi", True))
    while not dur["istendi"]:
        r = bir_is(depo, settings, sahip)
        if r is not None:
            # günlüğe bayinin metni ya da numarası yazılmaz
            print(json.dumps({k: r.get(k) for k in ("durum", "is_id", "eylem", "giden", "proje_id", "revizyon_id")}, ensure_ascii=False), flush=True)
            if ns.tek:
                return 0
            continue
        if ns.bos_bekle <= 0:
            return 0
        bitis = time.time() + ns.bos_bekle
        while time.time() < bitis and not dur["istendi"]:
            time.sleep(min(0.1, ns.bos_bekle))
    return 0


if __name__ == "__main__":
    sys.exit(main())
