"""İE-08 8b · mühendis teknik kontrolü (M1–M3; docs/is_emirleri/IE-08.md › 8b; şablonlar docs/kanal/2026-10-14_Meta_sablon_basvurusu_8b.md).

Akış (Lokman, 14 Ekim 2026; CIO plan sayfası › Görev 4b):
  1. Bayi çelik planda Onayla'ya basar, onay revizyona bağlanır (`kalici.onay_denetimi`) → `onay_kancasi` kontrol kaydı açar ve aktif
     mühendis kartına `portman_muhendis_kontrol_v1` şablonu yazar (alıcı sembolik MUHENDIS; gönderici karttan çözer). Kart yoksa
     Patron'a söylenir, iş durmaz.
  2. Mühendis "Gönder"e basar (pencere açılır) → bayinin onayladığı revizyonun görseli, TASLAK pafta PDF'i, yükleme listesi Excel'i
     (sunucuda üretilir, D-17) ve DXF (düz metin olarak yüklenir, görünen ad .dxf) + [Patron'a gönder] [Düzeltme iste].
  3. Mühendis listeyi düzeltip Excel'i gönderirse kontrolün yeni liste sürümü olur. "Patron'a gönder" → Patron'a "mühendis onayladı,
     fiyat sizde" + son Excel (pencere kapalıysa `portman_patron_bekliyor_v1`); "Düzeltme iste" → mühendisin bir sonraki yazısı not olur,
     Patron'a gider; bayiye "kontrol sürüyor" (revizyon hakkından düşmez: bayinin konuşmasına dokunulmaz).
  4. `hatirlatma_turu` (ajan döngüsünden dakikada bir): mühendise saat başı, yalnız 08:00–20:00 (İstanbul); gece onayında süre 08:00'de
     başlar; 3 saat dolunca Patron'a bir kez. Patron'a fiyat için 2 saatte bir, en çok 3 kez; panelde "Fiyat verildi" ya da panelden o
     bayiye gönderim durdurur. Her hatırlatma ücretlidir (şablon).

LLM çağrılmaz. Mühendisin ve bayinin numarası günlüğe ve Patron metnine yazılmaz (bayi kodu yazılır). Satırlar ve kontrol güncellemesi
işle aynı işlemde yazılır (`depo._isi_bitir`: `muhendis_kontrolu`, `kontrol_guncelle`, `cipa_satirlari`).
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import meta_api as M
import sablonlar as S
import worker as W
from depo import Depo

ISTANBUL = ZoneInfo("Europe/Istanbul")
MESAI = (8, 20)                       # hatırlatmalar yalnız 08:00–20:00 (İstanbul); gece onayında süre 08:00'de başlar
SAAT = 3600
CEVAP_SURESI_SN = 3 * SAAT            # mühendisin cevap süresi; dolunca Patron'a bir kez
HATIRLATMA_ARALIGI_SN = SAAT          # mühendise saat başı
PATRON_ARALIGI_SN = 2 * SAAT          # Patron'a fiyat hatırlatması 2 saatte bir
PATRON_EN_COK = 3
NOT_EN_COK = 600
NOTLAR_GOVDEDE_EN_COK = 6            # kısa parça notu bundan çoksa düğmeli mesajda sayı, notların hepsi ayrı metinde (D-10: hepsi gösterilir)
DUZELTME_NOTU = "duzeltme_notu"
BAYI_KONTROL_SURUYOR = "Planınızın teknik kontrolü sürüyor; revizyon hakkınız düşmez. Sonucu size bildireceğiz."


def mesaide_mi(t: float) -> bool:
    return MESAI[0] <= dt.datetime.fromtimestamp(t, ISTANBUL).hour < MESAI[1]


def sure_baslangici(t: float) -> float:
    """Cevap süresinin başladığı an: mesai içindeyse onay anı; 20:00'den sonra ertesi gün 08:00, 08:00'den önce aynı gün 08:00."""
    yerel = dt.datetime.fromtimestamp(t, ISTANBUL)
    if mesaide_mi(t):
        return float(t)
    gun = yerel.date() + (dt.timedelta(days=1) if yerel.hour >= MESAI[1] else dt.timedelta())
    return dt.datetime(gun.year, gun.month, gun.day, MESAI[0], tzinfo=ISTANBUL).timestamp()


def mesai_suresi(a: float, b: float) -> float:
    """[a, b] aralığının 08:00–20:00 (İstanbul) içine düşen saniyesi: cevap süresi ve "N saattir" gece saymaz (Lokman 14.10; inceleme)."""
    if b <= a:
        return 0.0
    toplam = 0.0
    gun = dt.datetime.fromtimestamp(a, ISTANBUL).date()
    son = dt.datetime.fromtimestamp(b, ISTANBUL).date()
    while gun <= son:
        bas = dt.datetime(gun.year, gun.month, gun.day, MESAI[0], tzinfo=ISTANBUL).timestamp()
        bit = dt.datetime(gun.year, gun.month, gun.day, MESAI[1], tzinfo=ISTANBUL).timestamp()
        toplam += max(0.0, min(b, bit) - max(a, bas))
        gun += dt.timedelta(days=1)
    return toplam


def celik_plani_mi(d: dict | None) -> bool:
    return (((d or {}).get("son_is_emri") or {}).get("yapi") or {}).get("sistem") == "celik"


def _etiket(no: str, rev: int) -> str:
    return f"{no} r{int(rev):02d}"


def _bayi_kodu(k: dict) -> str:
    return S.bayi_kodu({"kod": k.get("bayi_kod")}, str(k.get("bayi") or ""))


def _patron_sablonu(cipa_id: str, k: dict) -> dict:
    """Patron'a şablon (pencere kapalıysa): {{1}} bayi kodu, {{2}} İş Emri no; düğme bayinin konuşma sayfası."""
    return S.sablon_satiri(cipa_id, 0, "PATRON", "bildirim", S.PATRON_BILDIRIM, [_bayi_kodu(k), str(k["is_emri_no"])],
                           f"konusma/{k['bayi']}", pencere_kapaliysa=True)


# ───────────────────────── 1 · bayinin onayı ─────────────────────────
def onay_kancasi(depo: Depo, gelen: dict, d: dict | None, cikti: dict, simdi: float | None = None) -> None:
    """kalici.bir_is: onay revizyona bağlandıysa (onay denetimi kabul) ve plan çelikse kontrol kaydı + mühendis şablonu (yerinde)."""
    sonuc = cikti.get("sonuc") or {}
    onay = sonuc.get("onay") or {}
    if (gelen.get("role") or "bayi") not in ("bayi", "test") or not celik_plani_mi(d) or sonuc.get("gerekce") != "plan onaylandı" \
            or not onay.get("kabul") or not onay.get("is_emri_no"):
        return
    no, rev = str(onay["is_emri_no"]), int(onay.get("rev") or 1)
    simdi = time.time() if simdi is None else simdi
    numara = depo.muhendis_numarasi()
    satirlar = cikti["satirlar"]
    sira = max((int(s.get("seq") or 0) for s in satirlar), default=0) + 1
    if numara:
        satirlar.append(S.muhendis_kontrol_satiri(gelen["id"], sira, no, rev))
        durum = "bekliyor"
    else:
        satirlar.append(W.giden_metin(gelen, f"Portman: {_etiket(no, rev)} bayi tarafından onaylandı ama aktif mühendis kartı yok; teknik kontrol "
                                             "bildirimi gitmedi. Panelden mühendis kartını girin.", sira, "PATRON", "bildirim"))
        satirlar.append(_patron_sablonu(gelen["id"], {"bayi_kod": (gelen.get("bayi") or {}).get("kod"), "bayi": gelen["sender"], "is_emri_no": no}))
        satirlar[-1].update(seq=sira + 1, id=W.satir_id(gelen["id"], sira + 1))       # Patron'un penceresi kapalıysa da ulaşsın
        durum = "kart_yok"
    cikti["muhendis_kontrolu"] = {"is_emri_no": no, "rev": rev, "muhendis": numara, "durum": durum, "sure_baslangici": sure_baslangici(simdi)}
    sonuc["muhendis"] = {"durum": durum}


# ───────────────────────── 2–3 · mühendisin mesajları ─────────────────────────
class _Cikti:
    def __init__(self, gelen: dict):
        self.gelen = gelen; self.satirlar: list[dict] = []; self.guncelle: list = []; self.cipa: list = []
        self.sonuc = {"eylem": "muhendis", "gerekce": None}

    def ekle(self, r: dict) -> None:
        n = len(self.satirlar) + 1
        r["seq"] = n; r["id"] = W.satir_id(self.gelen["id"], n); self.satirlar.append(r)

    def metin(self, m: str, to: str | None = None, tur: str = "cevap") -> None:
        self.ekle(W.giden_metin(self.gelen, m, 0, to, tur))

    def sozluk(self) -> dict:
        return {"satirlar": self.satirlar, "sonuc": self.sonuc, "kontrol_guncelle": self.guncelle, "cipa_satirlari": self.cipa}


def isle(depo: Depo, gelen: dict) -> dict:
    """rol = muhendis kartının mesajı (kalici.bir_is; LLM yok). Düğme (muh:<islem>:<no>:<rev>), Excel dosyası ya da düzeltme notu."""
    c = _Cikti(gelen)
    sender = str(gelen.get("sender") or "")
    yuk = S.muhendis_yuku_coz(gelen.get("reply_id"))
    if yuk:
        islem, no, rev = yuk
        k = depo.muhendis_kontrolu(no, rev)
        c.sonuc.update(buton=gelen.get("reply_id"), is_emri_no=no, revizyon=rev)
        if k is None or str(k.get("muhendis") or "") != sender:
            c.metin("Bu düğmenin işini bulamadım. Açık işler için son bildirimdeki Gönder düğmesini kullanın.")
            c.sonuc["gerekce"] = "kontrol bulunamadı"
        elif islem == "gonder":
            _dosyalar(depo, c, k)
        elif k["durum"] not in ("bekliyor", "duzeltme"):
            c.metin(f"{_etiket(no, rev)} için kararınız kaydedildi; Patron'a iletildi.")
            c.sonuc["gerekce"] = "karar zaten verildi"
        elif islem == "patron":
            _patrona(depo, c, k)
        else:
            _duzeltme_iste(c, k)
        return c.sozluk()
    if gelen.get("type") == "document":
        _liste_surumu(depo, c, sender)
        return c.sozluk()
    metin = " ".join(str(gelen.get("text") or "").split())
    k = depo.muhendisin_acik_kontrolu(sender, bekleyen=DUZELTME_NOTU) if metin else None
    if k is not None:
        _not(c, k, metin)
        return c.sozluk()
    acik = depo.muhendisin_acik_kontrolu(sender)
    c.metin((f"Açık teknik kontrol: {_etiket(acik['is_emri_no'], acik['rev'])}. Dosyalar için bildirimdeki Gönder düğmesine basın; listeyi "
             "düzelttiyseniz Excel'i bu sohbete gönderin.") if acik else "Şu an teknik kontrol bekleyen iş yok.")
    c.sonuc["gerekce"] = "yardım"
    return c.sozluk()


def kontrol_notlari(pdf_yolu: str | None) -> list[str] | None:
    """Paftada komşusuna katılan 15 cm'den kısa parçaların HEPSİ (D-10: `pafta_ozet.json › kontrol_notlari`, 8b'de mühendise gösterilir;
    KT-03'te 17). Özet yoksa ya da okunamıyorsa None: mühendise "kısa parça notları okunamadı" yazılır (yok ile okunamadı ayrılır)."""
    ozetler = sorted(Path(pdf_yolu).parent.glob("*_pafta_ozet.json")) if pdf_yolu else []
    if not ozetler:
        return None
    try:
        return [f"{n.get('zincir')} {float(n.get('parca_cm') or 0):g} cm (@{float(n.get('konum_cm') or 0):g})"
                for n in (json.loads(ozetler[0].read_text(encoding="utf-8")).get("kontrol_notlari") or [])]
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _belge(c: _Cikti, yol: Path, ad: str, aciklama: str, mime: str, no: str, rev: int, sha: str | None = None) -> None:
    r = W.giden_belge(c.gelen, yol, ad, aciklama, 0, no, rev, sha or W._sha(yol))
    r["mime"] = mime
    c.ekle(r)


def _excel_yolu(rv: dict, no: str, rev: int) -> Path | None:
    """Revizyonun Excel'i; 8b'den önce çizilmiş revizyonda yoksa şimdi üretilir (bir kez; dosya varsa yeniden yazılmaz)."""
    ekler = rv.get("ekler") or {}
    if (ekler.get("excel") or {}).get("dosya") and Path(ekler["excel"]["dosya"]).is_file():
        return Path(ekler["excel"]["dosya"])
    js = (ekler.get("yukleme_listesi") or {}).get("dosya")
    if not js or not Path(js).is_file():
        return None
    hedef = Path(js).parent / f"Portman_{no}_r{int(rev):02d}_yukleme_listesi.xlsx"
    if hedef.is_file():
        return hedef
    x = W.liste_exceli(Path(js), Path(js).parent, no, rev)
    return Path(x["dosya"]) if "dosya" in x else None


def dogrulama_satiri(rv: dict) -> str | None:
    """İE-14 (Lokman 15.10, soru 1): yalnız yeni üretilen planda (kod `YENI-`) mühendis mesajına tek satır doğrulama özeti. Onaylanan
    revizyonun kendisinden hesaplanır (r02+'da r01'in raporu bayatlar): gömülü tanımdan plan denetimi + revizyon klasöründeki çizim kaydı
    (`plan_dogrulama.rapor`). Mühendis kabulü satıra girmez (o adım mühendisin). Hesaplanamazsa bunu söyler; istisna fırlatmaz."""
    y = ((rv or {}).get("is_emri") or {}).get("yapi") or {}
    if not str(y.get("kod") or "").upper().startswith("YENI-"):
        return None
    try:
        from beyin import plan_dogrulama as D
        from beyin.plan_denetim import denetle
        from beyin.plan_sema import tanimdan
        tanim = y["tanim"]
        cikti = Path(rv["pdf_yolu"]).parent if rv.get("pdf_yolu") else None
        r = D.rapor(denetle(tanimdan(tanim), {}), tanim, cikti)
        return "Yeni plan (otomatik üretildi) doğrulaması: " + D.ozet({a: v for a, v in r["kalemler"].items() if a != "muhendis_kabulu"}) + "."
    except Exception as e:                                       # mesaj düşmez; mühendis bilir
        W.log("mühendis doğrulama satırı hesaplanamadı:", W.maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return "Yeni plan (otomatik üretildi): doğrulama özeti hesaplanamadı."


def _dosyalar(depo: Depo, c: _Cikti, k: dict) -> None:
    no, rev = k["is_emri_no"], int(k["rev"])
    rv = depo.revizyon_kaydi(no, rev) or {}
    ekler = rv.get("ekler") or {}
    eksik = []
    g = ekler.get("kart") or ekler.get("gorsel")                  # bayinin onayladığı planın görseli (r02+'da kart; önce–sonra değil)
    if g and g.get("kaynak") == "once_sonra" and not ekler.get("kart"):
        g = None                                                  # kart yoksa önce–sonra "onaylanan plan" diye gitmez
    if g and Path(str(g.get("file") or "")).is_file():
        c.ekle(W.giden_gorsel(c.gelen, Path(g["file"]), g.get("filename") or Path(g["file"]).name, f"{_etiket(no, rev)} · bayinin onayladığı plan",
                              0, g.get("sha256") or W._sha(Path(g["file"])), no, rev))
    else:
        eksik.append("görsel")
    if rv.get("pdf_yolu") and Path(rv["pdf_yolu"]).is_file():
        _belge(c, Path(rv["pdf_yolu"]), f"Portman_{no}_r{rev:02d}.pdf", f"{_etiket(no, rev)} · görünüşlü pafta (TASLAK)", "application/pdf", no, rev,
               rv.get("pdf_sha256"))
    else:
        eksik.append("pafta PDF")
    x = _excel_yolu(rv, no, rev)
    if x is not None:
        _belge(c, x, x.name, f"{_etiket(no, rev)} · yükleme listesi (Excel)", S_XLSX, no, rev)
    else:
        eksik.append("Excel")
    dxf = ekler.get("dxf") or {}
    if dxf.get("dosya") and Path(dxf["dosya"]).is_file():
        _belge(c, Path(dxf["dosya"]), f"Portman_{no}_r{rev:02d}.dxf", f"{_etiket(no, rev)} · düzenlenebilir çizim (DXF)", S_DXF, no, rev, dxf.get("sha256"))
    else:
        eksik.append("DXF")
    notlar = kontrol_notlari(rv.get("pdf_yolu"))
    if notlar is None:
        eksik.append("kısa parça notları (pafta özeti okunamadı)")
    notlar = notlar or []
    kisa = "Kontrol edilecek kısa parçalar (paftada komşusuna katıldı): " + "; ".join(notlar) + "."
    if len(notlar) > NOTLAR_GOVDEDE_EN_COK:                       # hepsi ayrı metinde; düğmeli mesajda yalnız sayı
        c.metin(f"{_etiket(no, rev)} · {kisa}")
        kisa = f"Kısa parça notu: {len(notlar)} (ayrı mesajda)."
    dg = dogrulama_satiri(rv)
    govde = (f"{_etiket(no, rev)} teknik kontrol dosyaları yukarıda."
             + (f" Eksik: {', '.join(eksik)}." if eksik else "") + (f" {kisa}" if notlar else ""))
    if dg and len(govde) + len(dg) + 260 <= 1024:               # düğmeli mesaj gövdesi 1024 sınırı (WhatsApp); sığmazsa ayrı metin
        govde += f" {dg}"
    elif dg:
        c.metin(f"{_etiket(no, rev)} · {dg}")
    if k["durum"] in ("bekliyor", "duzeltme"):
        govde += (" Listeyi düzelttiyseniz Excel'i bu sohbete gönderin, sonra Patron'a gönder'e basın. Ciddi düzeltme gerekiyorsa "
                  "Düzeltme iste'ye basıp notunuzu yazın.")
        c.ekle(W.giden_etkilesim(c.gelen, govde, 0, butonlar=[(S.muhendis_yuku("patron", no, rev), "Patron'a gönder"),
                                                               (S.muhendis_yuku("duzeltme", no, rev), "Düzeltme iste")], is_emri_no=no, revizyon=rev))
    else:
        c.metin(govde + " Kararınız kaydedildi; Patron'a iletildi.")
    if k.get("t_dosya") is None:
        c.guncelle.append((k["id"], {"dosya_gonderildi": Depo.SIMDI}))
    c.sonuc["gerekce"] = "dosyalar gönderildi" + (f" (eksik: {', '.join(eksik)})" if eksik else "")


def _son_muhendis_exceli(depo: Depo, k: dict) -> tuple[Path | None, int | None]:
    """Mühendisin gönderdiği son Excel (indirildiyse; revizyon klasörüne kopyalanır: gönderici yalnız projects/ altından gönderir)."""
    for s in reversed(list(k.get("listeler") or [])):
        if s.get("kaynak") != "muhendis":
            continue
        d = depo.mesajin_dosyasi(s.get("mesaj_id") or "")
        if not d or not d.get("yol") or not Path(d["yol"]).is_file():
            return None, int(s.get("surum") or 0)
        rv = depo.revizyon_kaydi(k["is_emri_no"], k["rev"]) or {}
        if not rv.get("pdf_yolu"):
            return None, int(s.get("surum") or 0)
        hedef = Path(rv["pdf_yolu"]).parent / "muhendis" / f"Portman_{k['is_emri_no']}_r{int(k['rev']):02d}_yukleme_listesi_muhendis_s{int(s['surum'])}.xlsx"
        hedef.parent.mkdir(parents=True, exist_ok=True)
        if not hedef.is_file():
            shutil.copyfile(d["yol"], hedef)
        return hedef, int(s["surum"])
    return None, None


def _patrona(depo: Depo, c: _Cikti, k: dict) -> None:
    no, rev = k["is_emri_no"], int(k["rev"])
    yol, surum = _son_muhendis_exceli(depo, k)
    if yol is not None:
        liste = f"Mühendisin düzelttiği liste (sürüm {surum}) ektedir."
    else:
        yol = _excel_yolu(depo.revizyon_kaydi(no, rev) or {}, no, rev)
        liste = ("Mühendisin gönderdiği Excel henüz indirilmedi; sunucunun listesi ektedir, mühendisinki panelde görünür." if surum
                 else "Sunucunun ürettiği liste ektedir." if yol else "Liste Excel'i üretilemedi; panelden bakın.")
    c.metin(f"Portman: {_etiket(no, rev)} ({_bayi_kodu(k)}) mühendis onayladı; fiyat sizde. {liste} Fiyatı bayiye iletince panelde "
            "'Fiyat verildi'ye basın.", "PATRON", "bildirim")
    c.ekle(_patron_sablonu(c.gelen["id"], k))
    if yol is not None:
        r = W.giden_belge(c.gelen, yol, yol.name, f"{_etiket(no, rev)} · yükleme listesi", 0, no, rev, W._sha(yol))
        r.update(to="PATRON", tur="bildirim", mime=S_XLSX)
        c.ekle(r)
    c.metin(f"Teşekkürler. {_etiket(no, rev)} Patron'a iletildi; fiyat Patron'da.")
    c.guncelle.append((k["id"], {"durum": "patrona_gonderildi", "karar_zamani": Depo.SIMDI, "bekleyen": None, "patron_durum": "bekliyor",
                                 "patron_son_hatirlatma": Depo.SIMDI}))
    c.sonuc["gerekce"] = "mühendis onayladı: Patron'a gönderildi"


def _duzeltme_iste(c: _Cikti, k: dict) -> None:
    no, rev = k["is_emri_no"], int(k["rev"])
    c.metin(f"{_etiket(no, rev)}: düzeltme notunuzu tek mesajla yazın; Patron'a ileteceğim. Bayiye kontrolün sürdüğünü bildirdim.")
    c.cipa.append({"mesaj_id": k["onay_mesaj_id"], "satirlar": [{**W.giden_metin({"id": k["onay_mesaj_id"], "sender": k["bayi"]}, BAYI_KONTROL_SURUYOR, 0),
                                                                  "kaynak": "sistem"}]})
    c.guncelle.append((k["id"], {"durum": "duzeltme", "karar_zamani": Depo.SIMDI, "bekleyen": DUZELTME_NOTU}))
    c.sonuc["gerekce"] = "mühendis düzeltme istedi"


def _not(c: _Cikti, k: dict, metin: str) -> None:
    no, rev = k["is_emri_no"], int(k["rev"])
    notu = W.maske_numaralar(metin)[:NOT_EN_COK]
    c.metin(f"Portman: {_etiket(no, rev)} ({_bayi_kodu(k)}) için mühendis düzeltme istedi: \"{notu}\". Panelden bakabilirsiniz.", "PATRON", "bildirim")
    c.ekle(_patron_sablonu(c.gelen["id"], k))
    c.metin("Notunuz Patron'a iletildi. Düzeltilmiş listeyi Excel olarak gönderebilir, hazır olunca Patron'a gönder'e basabilirsiniz.")
    c.guncelle.append((k["id"], {"not_": notu, "bekleyen": None}))
    c.sonuc["gerekce"] = "düzeltme notu Patron'a"


def _liste_surumu(depo: Depo, c: _Cikti, sender: str) -> None:
    k = depo.muhendisin_acik_kontrolu(sender)
    ad = str(c.gelen.get("filename") or "")
    if k is None:
        c.metin("Bu dosyayı bir işe bağlayamadım: teknik kontrol bekleyen iş yok. Dosya panelde duruyor.")
        c.sonuc["gerekce"] = "dosya: açık kontrol yok"
        return
    no, rev = k["is_emri_no"], int(k["rev"])
    if not ad.lower().endswith(".xlsx"):
        c.metin(f"Yalnız Excel (.xlsx) dosyası {_etiket(no, rev)} için liste sürümü olarak bağlanır; dosyanız panelde duruyor.")
        c.sonuc["gerekce"] = "dosya: Excel değil"
        return
    listeler = list(k.get("listeler") or [])
    surum = max((int(s.get("surum") or 0) for s in listeler), default=1) + 1      # sürüm 1 sunucunun listesi
    listeler.append({"surum": surum, "kaynak": "muhendis", "mesaj_id": c.gelen["id"], "dosya_adi": ad[:120], "zaman": int(time.time())})
    c.guncelle.append((k["id"], {"listeler": listeler}))
    c.ekle(W.giden_etkilesim(c.gelen, f"Excel alındı: {_etiket(no, rev)}, liste sürümü {surum}. Hazırsa Patron'a gönder'e basın.", 0,
                             butonlar=[(S.muhendis_yuku("patron", no, rev), "Patron'a gönder"), (S.muhendis_yuku("duzeltme", no, rev), "Düzeltme iste")],
                             is_emri_no=no, revizyon=rev))
    c.sonuc.update(gerekce="liste sürümü", is_emri_no=no, revizyon=rev)


# ───────────────────────── 4 · hatırlatmalar ─────────────────────────
def hatirlatma_turu(depo: Depo, simdi: float | None = None) -> dict:
    """Ajan döngüsünden dakikada bir. Her kontrol için satırlar ve sayaç güncellemesi tek işlemde (depo.kontrol_satir_ekle)."""
    simdi = time.time() if simdi is None else simdi
    say = {"muhendis": 0, "gecikme": 0, "patron": 0, "hata": 0}
    if not mesaide_mi(simdi):
        return say
    testler = set(depo.test_kartlari())                          # kuru koşu kartının onayı hatırlatma doğurmaz (satırlar zaten tutulur)
    for k in depo.hatirlatma_adaylari():
        if k["bayi"] in testler:
            continue
        try:
            satirlar, guncelle = _hatirlatmalar(k, simdi, say)
            if satirlar or guncelle:                               # arada mühendis karar verdiyse ya da Fiyat verildi dendiyse yazılmaz
                depo.kontrol_satir_ekle(k["id"], k["onay_mesaj_id"], satirlar, guncelle,
                                        beklenen={"durum": k["durum"], "patron_durum": k["patron_durum"]})
        except Exception as e:                                     # bir kontrol düşerse öteki hatırlatmalar sürer
            say["hata"] += 1
            W.log("hatırlatma hatası:", k.get("id"), type(e).__name__)
    return say


def _hatirlatmalar(k: dict, simdi: float, say: dict) -> tuple[list[dict], dict]:
    no, rev = k["is_emri_no"], int(k["rev"])
    cipa = {"id": k["onay_mesaj_id"], "sender": k["bayi"]}
    satirlar: list[dict] = []; guncelle: dict = {}
    if k["durum"] == "bekliyor" and k.get("muhendis") and simdi >= float(k["t_baslangic"]):
        gecen = mesai_suresi(float(k["t_baslangic"]), simdi)      # gece sayılmaz
        n = int(k.get("hatirlatma_sayisi") or 0)
        son = k.get("t_son_hatirlatma")
        if gecen >= HATIRLATMA_ARALIGI_SN * (n + 1) and (son is None or simdi - float(son) >= HATIRLATMA_ARALIGI_SN - 60):
            satirlar.append(S.muhendis_hatirlatma_satiri(k["onay_mesaj_id"], 0, no, rev, int(gecen // SAAT)))
            guncelle.update(hatirlatma_sayisi=n + 1, son_hatirlatma=simdi); say["muhendis"] += 1
        if gecen >= CEVAP_SURESI_SN and k.get("t_gecikme") is None:
            satirlar.append(W.giden_metin(cipa, f"Portman: {_etiket(no, rev)} ({_bayi_kodu(k)}) için mühendis {int(gecen // SAAT)} saattir cevap "
                                                "vermedi (cevap süresi 3 saat).", 0, "PATRON", "bildirim"))
            satirlar.append(_patron_sablonu(k["onay_mesaj_id"], k))
            guncelle["gecikme_bildirildi"] = simdi; say["gecikme"] += 1
    if k["patron_durum"] == "bekliyor" and int(k.get("patron_hatirlatma_sayisi") or 0) < PATRON_EN_COK:
        son = k.get("t_patron_son") or k.get("t_karar")
        if son is not None and mesai_suresi(float(son), simdi) >= PATRON_ARALIGI_SN:
            satirlar.append(W.giden_metin(cipa, f"Hatırlatma: {_etiket(no, rev)} ({_bayi_kodu(k)}) için fiyat bekleniyor; mühendis onayladı. Fiyatı "
                                                "bayiye iletince panelde 'Fiyat verildi'ye basın.", 0, "PATRON", "bildirim"))
            satirlar.append(_patron_sablonu(k["onay_mesaj_id"], k))
            guncelle.update(patron_hatirlatma_sayisi=int(k.get("patron_hatirlatma_sayisi") or 0) + 1, patron_son_hatirlatma=simdi)
            say["patron"] += 1
    for s in satirlar:
        s["kaynak"] = "sistem"
    return satirlar, guncelle


S_XLSX = M.XLSX
S_DXF = M.DXF_MIME
