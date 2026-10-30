"""İE-22 · WhatsApp'tan bayi kaydı (Kurulum Panosu satır 111; bayi rehberi §9 "Bayi nasıl eklenir"; docs/is_emirleri/IE-22.md).

Akış (CIO planı ve kıyası, 29 Ekim 2026; proje dosyaları Bayi_Kaydi/plan.md):
  1. Kartı hiç olmayan numara yazar (pasif kart, test ve mühendis kartı bu akışa girmez: bugünkü sabit cevap). Webhook mesajı yazdığı
     işlemde kayıt talebini açar ve adını sorar; ad gelince firmayı sorar (`Adim`; depo.kayitsiz_mesaj_kaydet).
  2. Firma gelince bayiye teşekkür; Patron'a düğmeli mesaj [Onayla] [Reddet] (kayit:onay:<id> / kayit:red:<id>). Patron'un 24 saat
     penceresi kapalıysa onaylı Patron şablonu gider (talep kimliği KAYIT-<id>; düğme paneldeki konuşma sayfasına).
  3. Patron'un düğmesi ajanda LLM'siz işlenir (`isle`; kalici.bir_is). Onayla → kart açılır (aktif, rol bayi, kaynak whatsapp) ve bayiye
     karşılama şablonu ("Nasıl çalışır?" düğmeli) bayinin son mesajına bağlı gider. Reddet → kart açılmaz, bayiye (pencere açıksa) kısa
     metin; numara RED_BEKLEME_GUN gün yeni talep açmaz, Patron panelden reddi geri alabilir. Kart, talep ve satırlar işle aynı işlemde.
  4. Panel yedektir: aynı kararlar bayinin konuşma sayfasından (`karar_satirlari`; depo.kayit_karari_yaz).
Frenler: gönderen başına 24 saatte en çok CEVAP_SINIRI bot cevabı (dolarsa konuşma durur: talep ilerlemez, soru sorulmadan durum
atlanmaz; 24 saat sonra zaman aşımıyla baştan); günde en çok `bayi_kaydi.gunluk_en_cok` yeni talep (aşılırsa bugünkü sabit cevap);
cevapsız talep 24 saatte düşer; onay beklerken 24 saatte bir "onay bekliyor" (talebin kendi zamanıyla, sabit cevabın sayacından ayrı);
Patron'a talep başına tek bildirim.
`bayi_kaydi.acik` kapalıyken (varsayılan) bu modül çağrılmaz ve davranış bugünküyle aynıdır.
LLM çağrılmaz; numara Patron metnine yazılmaz (bayi kodu yazılır). Worker'ı yüklemez (webhook ve panel de kullanır).
"""
from __future__ import annotations

import re

import sablonlar as S
from depo import kod_turet, metin_satiri

YUK_ONEKI = "kayit:"                 # Patron'un düğmeleri: kayit:<onay|red>:<talep id>
ISLEMLER = ("onay", "red")
CEVAP_SINIRI = 5                     # gönderen başına 24 saatte en çok bot cevabı (kayıt soruları; olağan akış 3, iki yeniden soru payı)
ZAMAN_ASIMI_SN = 86400               # ad ya da firma beklenen talep bu kadar cevapsız kalırsa düşer; sonraki mesaj baştan başlar
RED_BEKLEME_GUN = 30                 # reddedilen numara bu kadar gün yeni talep açmaz (CIO, 29.10); Patron panelden geri alabilir
GUNLUK_EN_COK = 10                   # varsayılan: 24 saatte açılan yeni talep tavanı (ayar bayi_kaydi.gunluk_en_cok)
ACIK_DURUMLAR = ("ad", "firma", "onay_bekliyor")
DURUM_ADI = {"ad": "ad bekleniyor", "firma": "firma bekleniyor", "onay_bekliyor": "onay bekliyor", "onaylandi": "onaylandı",
             "reddedildi": "reddedildi", "zaman_asimi": "zaman aşımı"}

SORU_AD = ("Merhaba, bu hat PortatifEv bayilerinin Portman planlama hattıdır. Bayimizseniz kaydınızı açalım: adınızı ve soyadınızı yazar "
           "mısınız? Bayi değilseniz lütfen PortatifEv ofisiyle görüşün.")
SORU_AD_YENIDEN = "Kaydınız için adınızı ve soyadınızı yazıyla iletir misiniz?"
SORU_FIRMA = "Teşekkürler. Firmanızın adı nedir?"
SORU_FIRMA_YENIDEN = "Kaydınız için firmanızın adını yazıyla iletir misiniz?"
TESEKKUR = "Teşekkürler. Kayıt talebinizi PortatifEv'e ilettim; onaylanınca bu sohbetten haber vereceğiz."
ONAY_BEKLIYOR = "Kayıt talebiniz onay bekliyor; onaylanınca bu sohbetten haber vereceğiz."
RED_BAYIYE = "Bayi kaydınız şu an açılamadı. Ayrıntı için PortatifEv ofisiyle görüşebilirsiniz."
PATRON_ALTBILGI = "Panelden de karar verebilirsiniz."

_TELEFON = re.compile(r"\d(?:[\s\-().]*\d){6,}")    # yedi ve daha çok rakam dizisi (ayraçlı da): numara ad ya da firma sayılmaz
_WA_GOVDE, _WA_ALTBILGI, _WA_BUTON_BASLIK = 1024, 60, 20     # worker.WA_* ile aynı


def _ayar(ayar: dict | None) -> dict:
    b = (ayar or {}).get("bayi_kaydi")
    return b if isinstance(b, dict) else {}


def acik_mi(ayar: dict | None) -> bool:
    return _ayar(ayar).get("acik") is True


def kimlik(talep_id) -> str:
    """Patron şablonunun {{2}} değişkeni ve metinlerdeki talep adı (sablonlar.is_emri_no_gecerli kalıbına uyar)."""
    return f"KAYIT-{int(talep_id)}"


def kod(numara: str) -> str:
    """Kartın türetilen kodu (depo.kod_turet: bayi_yaz ve onayla açılan kart aynı kuralı kullanır)."""
    return kod_turet(numara)


def _temiz(m) -> str:
    return " ".join(str(m or "").split())


def _metin_degeri(gelen: dict, en_az: int, en_cok: int) -> str | None:
    if gelen.get("type") != "text":
        return None
    m = _temiz(gelen.get("text"))
    if not en_az <= len(m) <= en_cok or sum(ch.isalpha() for ch in m) < 2 or _TELEFON.search(m) or "http" in m.lower() or "@" in m:
        return None
    return m


def ad_coz(gelen: dict) -> str | None:
    """Bayinin adı ve soyadı: yazı, 3–80 karakter, en az iki harf, telefon numarasına ya da bağlantıya benzemez."""
    return _metin_degeri(gelen, 3, 80)


def firma_coz(gelen: dict) -> str | None:
    """Firma adı: yazı, 2–120 karakter; aynı denetim."""
    return _metin_degeri(gelen, 2, 120)


# ───────────────────────── 1–2 · kayıtsız numaranın mesajları (webhook; depo.kayitsiz_mesaj_kaydet) ─────────────────────────
def karar(b: dict, gelen: dict) -> dict:
    """Webhook adımı (saf; depo işlemin içinde çağırır). b: {"talep": numaranın son talebi ya da None (yas_sn: son güncellemeden beri,
    karar_yas_sn: karardan beri, hatirlatma_yas_sn: son "onay bekliyor"dan beri), "cevap_24s": bu numaraya son 24 saatteki kayıt cevabı,
    "yeni_24s": son 24 saatte açılan talep, "gunluk_en_cok"}. Dönen {"islem": "sabit"} ise mesaj bugünkü sabit cevap yolundan geçer;
    {"islem": "sus"} ise cevap sınırı doldu, talep olduğu gibi kalır; değilse {"islem": yeni | guncelle | bekliyor, "durum", "ad"?,
    "firma"?, "cevap": bayiye metin ya da None, "patrona": bool, "kapat": düşen açık talebin id'si?}."""
    t = b.get("talep")
    sus = int(b.get("cevap_24s") or 0) >= CEVAP_SINIRI
    if t is not None and t["durum"] == "reddedildi" and float(t.get("karar_yas_sn") or 0) < RED_BEKLEME_GUN * 86400:
        return {"islem": "sabit"}
    if t is not None and t["durum"] == "onay_bekliyor":
        h = t.get("hatirlatma_yas_sn")
        hatirlat = not sus and (h is None or float(h) >= 86400)
        return {"islem": "bekliyor", "durum": "onay_bekliyor", "cevap": ONAY_BEKLIYOR if hatirlat else None, "patrona": False}
    acik = t is not None and t["durum"] in ("ad", "firma") and float(t.get("yas_sn") or 0) < ZAMAN_ASIMI_SN
    if sus:            # konuşma durur: soru sorulmadan durum atlanmaz (bayi firmanın sorulduğunu bilmeden talep ilerlemesin)
        return {"islem": "sus", "durum": t["durum"], "cevap": None, "patrona": False} if acik else {"islem": "sabit"}
    if not acik:
        if int(b.get("yeni_24s") or 0) >= int(b.get("gunluk_en_cok") or GUNLUK_EN_COK):
            return {"islem": "sabit"}
        kapat = t["id"] if t is not None and t["durum"] in ("ad", "firma") else None
        return {"islem": "yeni", "durum": "ad", "cevap": SORU_AD, "patrona": False, "kapat": kapat}
    if t["durum"] == "ad":
        ad = ad_coz(gelen)
        if ad is None:
            return {"islem": "guncelle", "durum": "ad", "cevap": SORU_AD_YENIDEN, "patrona": False}
        return {"islem": "guncelle", "durum": "firma", "ad": ad, "cevap": SORU_FIRMA, "patrona": False}
    firma = firma_coz(gelen)
    if firma is None:
        return {"islem": "guncelle", "durum": "firma", "cevap": SORU_FIRMA_YENIDEN, "patrona": False}
    return {"islem": "guncelle", "durum": "onay_bekliyor", "firma": firma, "cevap": TESEKKUR, "patrona": True}


def _kes(m: str, n: int) -> str:
    m = _temiz(m)
    return m if len(m) <= n else m[:n - 1] + "…"


def _govde(m: str, n: int) -> str:
    """worker._govde ile aynı: satır sonları kalır (BK-10 F)."""
    out: list[str] = []
    for s in str(m or "").splitlines():
        s = _temiz(s)
        if s or (out and out[-1]):
            out.append(s)
    m = "\n".join(out).strip()
    return m if len(m) <= n else m[:n - 1] + "…"


def dugmeli_satir(gelen: dict, metin: str, sira: int, to: str, tur: str, butonlar: list[tuple[str, str]], altbilgi: str | None = None) -> dict:
    """Düğmeli satır: worker.giden_etkilesim (butonlu) ile aynı biçim (testle denetlenir); webhook worker'ı yüklemez."""
    r = metin_satiri(gelen, metin[:_WA_GOVDE], sira, to, tur)
    i: dict = {"body": {"text": _govde(metin, _WA_GOVDE)}}
    if altbilgi:
        i["footer"] = {"text": _kes(altbilgi, _WA_ALTBILGI)}
    i["type"] = "button"
    i["action"] = {"buttons": [{"type": "reply", "reply": {"id": str(bid)[:256], "title": _kes(bas, _WA_BUTON_BASLIK)}} for bid, bas in butonlar[:3]]}
    r.update(kind="interactive", interactive=i, is_emri_no=None, revizyon=None)
    return r


def yuk(islem: str, talep_id) -> str:
    if islem not in ISLEMLER:
        raise ValueError(f"kayıt işlemi: {islem!r}")
    return f"{YUK_ONEKI}{islem}:{int(talep_id)}"


def yuk_coz(kimlik_) -> tuple[str, int] | None:
    """kayit:<onay|red>:<id> → (islem, id); tanınmıyorsa None."""
    p = str(kimlik_ or "").split(":")
    if len(p) != 3 or p[0] + ":" != YUK_ONEKI or p[1] not in ISLEMLER or not p[2].isdigit() or len(p[2]) > 12:
        return None
    return p[1], int(p[2])


def patron_talep_satiri(gelen: dict, sira: int, talep: dict) -> dict:
    """Patron'a kayıt talebi [Onayla] [Reddet] (alıcı sembolik PATRON; pencere açıkken gider; kapalıysa eşlik eden şablon)."""
    no = kimlik(talep["id"])
    metin = (f"Portman kayıt talebi {no}: {talep['ad']} · {talep['firma']} · kod {kod(talep['numara'])}. Onaylarsanız bayi kartı açılır ve "
             "bayiye karşılama şablonu gider.")
    return dugmeli_satir(gelen, metin, sira, "PATRON", "bildirim", [(yuk("onay", talep["id"]), "Onayla"), (yuk("red", talep["id"]), "Reddet")],
                         PATRON_ALTBILGI)


def satirlar(gelen: dict, talep: dict, k: dict) -> list[dict]:
    """Webhook adımının giden satırları (gelen mesaja bağlı): 1 bayiye cevap; talep tamamlandıysa 2 Patron'a düğmeli mesaj, 3 Patron şablonu
    (pencere_kapaliysa ve kardes_dugmeli: gönderici pencere açık ve düğmeli mesaj gittiyse 'sablon_gereksiz' yapar)."""
    out = []
    if k.get("cevap"):
        out.append(metin_satiri(gelen, k["cevap"], 1, gelen["sender"], "kayit"))
    if k.get("patrona"):
        out.append(patron_talep_satiri(gelen, 2, talep))
        s = S.sablon_satiri(gelen["id"], 3, "PATRON", "bildirim", S.PATRON_BILDIRIM, [kod(talep["numara"]), kimlik(talep["id"])],
                            f"konusma/{talep['numara']}", pencere_kapaliysa=True)
        s["kardes_dugmeli"] = True                       # eşlik ettiği satır düğmeli (depo.kardes_metin_durumu)
        out.append(s)
    return out


class Adim:
    """depo.kayitsiz_mesaj_kaydet'in kayıt adımı (depo bu modülü içe aktarmaz: Kapı M paketi yalnız depo.py'yle de çalışır)."""

    def __init__(self, gunluk_en_cok: int = GUNLUK_EN_COK):
        self.gunluk_en_cok = int(gunluk_en_cok)

    karar = staticmethod(karar)
    satirlar = staticmethod(satirlar)


def adim(ayar: dict | None) -> Adim | None:
    """Ayar açıksa webhook'un kayıt adımı; kapalıysa None (bugünkü sabit cevap)."""
    if not acik_mi(ayar):
        return None
    n = _ayar(ayar).get("gunluk_en_cok")
    return Adim(int(n) if isinstance(n, int) and not isinstance(n, bool) and n >= 0 else GUNLUK_EN_COK)


# ───────────────────────── 3–4 · Patron'un kararı (ajan ve panel) ─────────────────────────
def karar_satirlari(talep: dict, islem: str, kart_var: bool, kaynak: str = "sistem") -> list[dict]:
    """Karardan sonra bayiye giden satırlar; bayinin son mesajına (talep.son_mesaj_id) bağlanır (depo._cipa_satir_yaz kimlik ve sırayı
    verir). Onay: karşılama şablonu ({{1}} ad; hitap kartta boş). Red: kısa metin (pencere kapalıysa gönderici düşürür). kart_var: kart
    karardan önce (elle) açılmıştı; talep yalnız kapanır, bayiye bir şey gitmez."""
    cipa = {"id": talep["son_mesaj_id"], "sender": talep["numara"]}
    if kart_var:
        return []
    if islem == "onay":
        return [S.bayi_karsilama_satiri(cipa["id"], 0, talep["numara"], {"ad": talep["ad"]}, kaynak=kaynak)]
    r = metin_satiri(cipa, RED_BAYIYE, 0, talep["numara"], "kayit")
    r["kaynak"] = kaynak
    return [r]


def patron_sonuc_metni(talep: dict, islem: str, kart_var: bool, mod: str | None = None) -> str:
    etiket = f"{kod(talep['numara'])} · {talep['ad']} · {talep['firma']}"
    if kart_var:
        return f"{kimlik(talep['id'])}: bu numaranın kartı zaten var; talep kapatıldı, bayiye mesaj gönderilmedi."
    if islem == "red":
        return (f"Kayıt reddedildi: {etiket}. Bu numara {RED_BEKLEME_GUN} gün yeni kayıt talebi açmaz; panelden reddi geri alabilirsiniz.")
    m = f"Kayıt açıldı: {etiket}. Bayiye karşılama şablonu gidiyor; hitap ve bölgeyi panelden yazabilirsiniz."
    if mod not in ("kayitli", "hepsi"):
        m += f" Not: kanal şu an '{mod}' modunda; bayinin mesajları mod 'kayitli' olunca işlenir."
    return m


def isle(depo, gelen: dict, settings: dict | None = None) -> dict:
    """Patron'un kayit:<islem>:<id> düğmesi (kalici.bir_is; LLM yok). Dönen: kalici'nin çıktı sözlüğü; karar `kayit_karari` olarak işle aynı
    işlemde yazılır (depo._isi_bitir) ve yazım anında talep artık onay beklemiyorsa ya da kart durumu değiştiyse Cakisma (iş yeniden
    sıraya girer, ikinci turda "zaten karara bağlandı" denir)."""
    import etkilesim as ET
    reply_id = str(gelen.get("reply_id") or "")
    out: dict = {"satirlar": [], "sonuc": {"eylem": "kayit", "gerekce": None, "buton": reply_id}}

    def metin(m: str) -> None:
        out["satirlar"].append(metin_satiri(gelen, m, len(out["satirlar"]) + 1, gelen["sender"], "cevap"))
    y = yuk_coz(reply_id)
    ctx = gelen.get("context_id")
    satir = depo.giden_satiri(ctx) if (y and ctx) else None
    if y is None or (satir is not None and reply_id not in ET.mesaj_kimlikleri(satir)):
        metin("Bu düğmeyi tanıyamadım; kayıt talebine panelden bakabilirsiniz.")
        out["sonuc"]["gerekce"] = "kayıt düğmesi doğrulanamadı"
        return out
    islem, tid = y
    t = depo.kayit_talebi(tid)
    out["sonuc"]["kayit"] = {"id": tid, "islem": islem}
    if t is None:
        metin(f"{kimlik(tid)} kayıt talebini bulamadım.")
        out["sonuc"]["gerekce"] = "kayıt talebi yok"
        return out
    if t["durum"] != "onay_bekliyor":
        metin(f"{kimlik(tid)} zaten karara bağlandı ({DURUM_ADI.get(t['durum'], t['durum'])}).")
        out["sonuc"]["gerekce"] = "kayıt talebi zaten karara bağlandı"
        return out
    kart_var = depo.bayi_oku(t["numara"]) is not None
    metin(patron_sonuc_metni(t, islem, kart_var, str((settings or {}).get("mode") or "patron")))
    out["kayit_karari"] = {"id": tid, "islem": islem, "kart_var": kart_var}
    cipa = karar_satirlari(t, islem, kart_var)
    if cipa:
        out["cipa_satirlari"] = [{"mesaj_id": t["son_mesaj_id"], "satirlar": cipa}]
    out["sonuc"]["gerekce"] = "kayıt onaylandı" if islem == "onay" else "kayıt reddedildi"
    return out
