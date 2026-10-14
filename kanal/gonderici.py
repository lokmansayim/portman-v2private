"""İE-06 · Gönderici servisi (systemd portman-gonderici): Postgres'teki giden satırlarını Meta'ya gönderir, gelen medyayı indirir,
nabız yazar. Hosting'teki worker.php cron tiki + feature.php pm_kanal_tick / pm_kanal_send / pm_kanal_medya'nın yerine.

Kurallar (feature.php ile aynı; docs/is_emirleri/IE-06.md):
  - öz-test satırı ya da imzalı webhook'tan gelmeyen ebeveyn asla gönderilmez; alıcı = gelen mesajın göndereni (PATRON bildirimi hariç);
  - 24 saatlik serbest cevap penceresi dışına gönderilmez (held → 'gonderilmedi: reply_window_closed'); İE-07: kind 'template'
    (Meta onaylı şablon) pencere dışında da gider; 'pencere_kapaliysa' işaretli şablon pencere açıkken 'sablon_gereksiz' (metin
    satırı gitti); şablon adı ayarda yoksa 'sablon_yok'. Panelden yazılan satır (giden.kaynak = 'panel') bayinin son mesajına
    bağlıdır; penceresi o son mesajın zamanıyla ölçülür (Patron bildirimi gibi);
  - dry_run: satırlar gönderilmez, sonradan da gönderilmez; enabled değilse hiçbir şey gönderilmez;
  - BK-07: rol='test' kartından (kuru koşu) doğan ya da ona giden satır dry_run'dan bağımsız her zaman tutulur ('test_karti');
  - messages POST'u başladıktan sonra her hata 'belirsiz' sayılır ve otomatik tekrar edilmez; medya yükleme/doğrulama hatası
    POST'tan önce olduğu için bir kez daha denenir (document/image/interactive), etkileşim sınırı hatası denenmez;
  - yüklenen medyanın kimliği satırda saklanır, yeniden denemede yeniden yüklenmez.
Sırlar /etc/portman/whatsapp.env'den (systemd EnvironmentFile); günlüğe anahtar, numara ve metin yazılmaz.
Komut satırı: python kanal/gonderici.py [--tek] (PORTMAN_PG_DSN, PORTMAN_KANAL_DIR, WA_* ortam değişkenleri)
"""
from __future__ import annotations

import hashlib
import os
import re
import signal
import sys
import time
import traceback
from pathlib import Path

KOD = Path(__file__).resolve().parent
for _yol in (KOD.parent, KOD):
    if str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))

import ayarlar as AY                                                       # noqa: E402
import kalici as K                                                         # noqa: E402
import meta_api as M                                                       # noqa: E402
import nabiz as NB                                                         # noqa: E402
from depo import Depo, kimlik_izi, maske                                   # noqa: E402

SURUM = "gonderici-v2.0"
SEMBOLIK = ("PATRON", "MUHENDIS")   # gönderim anında karttan çözülen alıcılar (rol patron / muhendis, aktif)
ILK_TEMAS_KAYNAGI = "panel ilk temas"   # depo.ilk_temas_ekle ile aynı
PENCERE_SN = 86400
MEDYA_YENIDEN = 2                   # feature.php: upload_failed satır en çok 2 deneme
TUR_BEKLEME_SN = 3
_dur = {"istendi": False}


def log(*p) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "gonderici", *p, flush=True)


class GonderenMeta:
    """kalici.gonder'in gönderici işlevi: satır → Meta messages POST → wamid. Hatalar: Gonderilmedi (kesin), YenidenDene (bir kez daha),
    öteki (belirsiz)."""

    def __init__(self, depo: Depo, istemci: M.GraphIstemci, veri: Path | str, ayar_oku=None):
        self.depo = depo; self.istemci = istemci; self.veri = Path(veri)
        self.ayar_oku = ayar_oku or (lambda: AY.oku(self.veri))

    _TEST_KARTI_TAZE_SN = 10                                      # test kartı kümesi 10 sn önbellekte: her satır için iki sorgu atılmasın

    def _test_karti_mi(self, numara: str) -> bool:
        if not numara or not M.numara_gecerli(numara):
            return False
        simdi = time.time()
        z, kume = getattr(self, "_test_kartlari", (0.0, frozenset()))
        if simdi - z > self._TEST_KARTI_TAZE_SN:
            kume = frozenset(self.depo.test_kartlari()); self._test_kartlari = (simdi, kume)
        return numara in kume

    def __call__(self, r: dict) -> str:
        gelen = r.get("gelen") or {}
        sablon = r["kind"] == "template"                            # İE-07: Meta onaylı şablon; pencere dışında da gider
        kaynak = str(r.get("kaynak") or "ajan")
        # İE-08 8b M4: panelin hiç yazmamış karta açtığı başlangıç kaydı (depo.ilk_temas_ekle) gerçek bir gelen mesaj değildir; ona bağlı
        # yalnız panelden giden şablon (karşılama, bilgi hazır) gönderilir, alıcı kaydın kartıdır
        ilk_temas = gelen.get("source") == ILK_TEMAS_KAYNAGI and kaynak == "panel" and sablon
        if not ilk_temas:
            if not str(r.get("mesaj_id") or "").startswith("wamid."):
                raise K.Gonderilmedi("Gönderilmedi: test_cannot_send")
            if gelen.get("source") != "Meta imzalı webhook" or str(gelen.get("phone_number_id") or "") != self.istemci.ayar.phone_number_id:
                raise K.Gonderilmedi("Gönderilmedi: inbox_not_verified")
        bildirim = r["alici"] in SEMBOLIK                          # PATRON; İE-08 8b: MUHENDIS (aktif mühendis kartı)
        # İE-07: Patron panelden yazdı; İE-08 8b: 'sistem' (mühendis kararı, hatırlatma) bayinin onay mesajına bağlı. İkisinde de pencere
        # alıcının son mesajından ölçülür
        panel = kaynak in ("panel", "sistem")
        alici = (self.depo.patron_numarasi() if r["alici"] == "PATRON" else self.depo.muhendis_numarasi()) if bildirim else str(r["alici"])
        if not alici or not M.numara_gecerli(alici):
            raise K.Gonderilmedi("Gönderilmedi: recipient_unknown")
        if not bildirim and alici != str(gelen.get("sender") or ""):
            raise K.Gonderilmedi("Gönderilmedi: recipient_mismatch")
        self.depo.alici_cozuldu_kaydet(r["id"], alici)              # düşen satır da (pencere kapalı, sablon_yok) panelde alıcının sayfasında görünsün
        # BK-07 (S3): rol='test' kartı (kuru koşu; vps/kuru_kosu.sh) her zaman tutulur, dry_run ayarından bağımsız: kartın kendi
        # mesajından doğan her satır (bayi cevabı, PDF, PATRON metni ve şablonu) ve panelden karta yazılan satır. Meta'ya medya bile
        # yüklenmez. Gerçek bayinin ve Patron'un satırları etkilenmez.
        gonderen_numara = str(gelen.get("sender") or "")
        if self._test_karti_mi(gonderen_numara) or (alici != gonderen_numara and self._test_karti_mi(alici)):
            raise K.Gonderilmedi("Gönderilmedi: test_karti (kuru koşu kartı; satır her zaman tutulur, dry_run gerekmez)")
        son = self.depo.son_gelen_zamani(alici) if (bildirim or panel) else float(gelen.get("timestamp") or 0)
        acik = bool(son) and time.time() - float(son) < PENCERE_SN
        satir = dict(r.get("satir") or {}); satir.update(id=r["id"], kind=r["kind"], body=r["govde"])
        if not sablon and not acik:
            raise K.Gonderilmedi("Gönderilmedi: reply_window_closed")
        if sablon:
            if satir.get("pencere_kapaliysa") and acik:
                # Eşlik eden metin satırı (aynı mesaj, aynı alıcı, daha küçük sıra) gerçekten gittiyse ücretli şablona gerek yok;
                # metin düştüyse (belirsiz, gönderilmedi) şablon gider; metin hâlâ sıradaysa bu satır bekler.
                metin_durumu = self.depo.kardes_metin_durumu(r["mesaj_id"], r["alici"], int(r.get("sira") or 0))
                if metin_durumu == "kabul_edildi":
                    raise K.Gonderilmedi("Gönderilmedi: sablon_gereksiz (pencere açık, metin satırı gitti)")
                if metin_durumu in ("bekliyor", "gonderiliyor"):
                    raise K.YenidenDene("Şablon bekliyor: metin satırı henüz sonuçlanmadı")
            ayar = self.ayar_oku(); anahtar = str(satir.get("sablon_anahtari") or "")
            ad = ayar.get(anahtar) if anahtar else None
            if not isinstance(ad, str) or not ad:
                log("şablon tanımsız:", anahtar or "-", r["id"])
                raise K.Gonderilmedi(f"Gönderilmedi: sablon_yok ({anahtar or '-'}): ayar.sh ile Meta şablon adı girilmeli")
            s = dict(satir.get("sablon") or {})
            satir["sablon"] = {**s, "ad": ad, "dil": str(ayar.get("sablon_dil") or "tr")}
        medya_id = None; baslik_medya = None
        try:
            if r["kind"] in ("document", "image") or (r["kind"] == "interactive" and M.baslik_gorseli_var(satir)):
                izinli = M.BELGE_TURLERI if r["kind"] == "document" else ("image/png", "image/jpeg")    # 8b: Excel ve DXF mühendise
                gercek, mime = M.dosya_denetle(r.get("dosya"), izinli, self.veri, r.get("sha256"))
                medya = str(r.get("medya_id") or "")
                if not re.fullmatch(r"[0-9]{1,40}", medya):
                    medya = self.istemci.medya_yukle(gercek, mime, str(satir.get("filename") or gercek.name))
                    self.depo.medya_id_kaydet(r["id"], medya)
                if r["kind"] == "interactive":
                    baslik_medya = medya
                else:
                    medya_id = medya
            yuk = M.mesaj_yuku(satir, alici, medya_id=medya_id, baslik_medya_id=baslik_medya)
        except M.DosyaGecersiz as e:
            raise K.Gonderilmedi(f"Yükleme/doğrulama başarısız; gönderilmedi. {e}") from None
        except (M.EtkilesimGecersiz, M.SablonGecersiz, ValueError) as e:
            raise K.Gonderilmedi(f"Yükleme/doğrulama başarısız; gönderilmedi. {e}") from None
        except M.MetaHatasi as e:                                   # medya yüklenemedi: POST başlamadı
            if int(r.get("deneme") or 0) < MEDYA_YENIDEN:
                raise K.YenidenDene(f"Medya yüklenemedi; bir kez daha denenecek. {str(e)[:160]}") from None
            raise K.Gonderilmedi(f"Yükleme/doğrulama başarısız; gönderilmedi. {str(e)[:160]}") from None
        if self.ayar_oku().get("enabled") is not True:
            raise K.YenidenDene("Gönderilmedi: disabled_before_send")
        cevap = self.istemci.gonder(yuk)                            # buradan sonra her hata belirsizdir (kalici.gonder)
        return M.kabul_edilen_wamid(cevap, alici)


# ───────────────────────── gelen medya ─────────────────────────
_AD = re.compile(r"[^A-Za-z0-9._-]+")
_UZANTI = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf", "audio/ogg": ".ogg", "audio/mpeg": ".mp3",
           "video/mp4": ".mp4", "application/msword": ".doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
           "application/vnd.ms-excel": ".xls", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx", "text/plain": ".txt"}


def guvenli_ad(dosya_adi: str | None, mime: str, medya_id: str) -> str:
    ad = _AD.sub("_", Path(str(dosya_adi or "")).name).strip("._")[:80]
    if not ad or ad.startswith("."):
        ad = f"medya_{medya_id}" + _UZANTI.get((mime or "").split(";")[0].strip(), "")
    return ad


def medya_indir(depo: Depo, istemci: M.GraphIstemci, veri: Path | str, en_fazla: int = 5) -> dict:
    say = {"indirildi": 0, "hata": 0}
    for row in depo.bekleyen_gelen_dosyalar(en_fazla):
        try:
            icerik, mime = istemci.medya_indir(row["medya_id"])
            mime = row.get("mime") or mime
            hedef_dir = Path(veri) / "gelen_medya" / kimlik_izi(row["mesaj_id"])
            hedef_dir.mkdir(parents=True, exist_ok=True)
            hedef = hedef_dir / guvenli_ad(row.get("dosya_adi"), mime, row["medya_id"])
            gecici = hedef.with_name(hedef.name + ".tmp"); gecici.write_bytes(icerik); os.replace(gecici, hedef)
            try:
                os.chmod(hedef, 0o600)
            except OSError:
                pass
            depo.gelen_dosya_indirildi(row["id"], str(hedef), mime, len(icerik), hashlib.sha256(icerik).hexdigest())
            say["indirildi"] += 1
        except Exception as e:
            depo.gelen_dosya_hatasi(row["id"], f"{type(e).__name__}: {M.maskele(str(e), istemci.ayar.access_token)[:200]}")
            say["hata"] += 1
            log("medya indirilemedi:", kimlik_izi(row["mesaj_id"]), type(e).__name__)
    return say


# ───────────────────────── tur ve döngü ─────────────────────────
def tur(depo: Depo, gonderen: GonderenMeta, istemci: M.GraphIstemci, veri: Path | str, ayar: dict | None = None) -> dict:
    ayar = ayar if ayar is not None else AY.oku(veri)
    say: dict = {"enabled": ayar.get("enabled") is True, "dry_run": ayar.get("dry_run") is True}
    if say["enabled"]:
        if say["dry_run"]:
            say["tutuldu"] = depo.dry_run_tut()
        else:
            say.update(K.gonder(depo, gonderen, en_fazla=20))
    if istemci.ayar.access_token:
        say["medya"] = medya_indir(depo, istemci, veri)
    NB.yaz(veri, "gonderici", surum=SURUM, **{k: v for k, v in say.items() if k != "medya"}, medya=say.get("medya"))
    return say


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tek", action="store_true", help="bir tur ve çık")
    ns = ap.parse_args(argv)
    veri = Path(os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data")
    depo = Depo(); meta = M.MetaAyar.ortamdan(); istemci = M.GraphIstemci(meta)
    gonderen = GonderenMeta(depo, istemci, veri)
    signal.signal(signal.SIGTERM, lambda *_: _dur.__setitem__("istendi", True))
    log("başladı", SURUM, "veri", veri, "WhatsApp ayarı", "tam" if meta.tam_mi() else "EKSİK (whatsapp.env)")
    while not _dur["istendi"]:
        try:
            say = tur(depo, gonderen, istemci, veri)
            if say.get("kabul_edildi") or say.get("gonderilmedi") or say.get("belirsiz") or say.get("yeniden"):
                log("tur:", {k: v for k, v in say.items() if k in ("kabul_edildi", "gonderilmedi", "belirsiz", "yeniden", "tutuldu")})
        except Exception as e:
            log("tur hatası:", type(e).__name__, M.maskele(str(e), meta.access_token)[:160])
            if ns.tek:
                print(traceback.format_exc()[-800:]); return 1
            time.sleep(15); continue
        if ns.tek:
            return 0
        bitis = time.time() + TUR_BEKLEME_SN
        while time.time() < bitis and not _dur["istendi"]:
            time.sleep(0.2)
    log("durduruldu (SIGTERM)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
