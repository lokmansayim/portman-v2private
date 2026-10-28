"""İE-07 · Meta onaylı şablon mesajları (Lokman, 11 Ekim 2026, Karar 2): metinler, değişkenler ve giden satırı üreticisi.

Şablonlar Meta'ya Lokman WhatsApp Manager'dan gönderir (docs/kanal/2026-10-11_Meta_sablon_basvurusu.md); onaylanan adlar
settings.json'a `sablon_patron_bildirim` ve `sablon_bayi_dosyalar_hazir` anahtarlarıyla girer (vps/ayar.sh); İE-08 8b'nin dört şablonu
`sablon_muhendis_kontrol`, `sablon_muhendis_hatirlatma`, `sablon_bayi_karsilama`, `sablon_bayi_bilgi_hazir` (docs/kanal/2026-10-14_…_8b.md). Satıra Meta adı
yazılmaz: gönderici (kanal/gonderici.py) gönderim anında ayardan çözer; ad tanımsızsa satır `gonderilmedi: sablon_yok` olur.
Şablon 24 saat penceresi dışında da gider (utility, ücretli). Bu modül worker'ı ve depo'yu yüklemez (depo ve panel de kullanır).
"""
from __future__ import annotations

import hashlib
import re
import time

from meta_api import sablon_metni               # {{n}} yerleşimi tek yerde (kanal/meta_api.py); noqa: F401

PATRON_BILDIRIM = {
    "anahtar": "sablon_patron_bildirim",
    "metin": "Portman: {{1}} kodlu bayinin {{2}} numaralı talebi sizi bekliyor. Ayrıntıyı panelden görebilirsiniz.",
    "dugme": "url",                         # "Panele git": sabit taban https://<alan>/panel/{{1}} + dinamik sonek konusma/<numara>
    "ornek": ["B1234", "PM-B1234-20261011-1"],
}
BAYI_DOSYALAR_HAZIR = {
    "anahtar": "sablon_bayi_dosyalar_hazir",
    "metin": "Merhaba {{1}}, {{2}} numaralı projenizin dosyaları hazır. Bu mesaja yanıt verirseniz dosyaları buradan gönderebiliriz.",
    "dugme": "quick_reply",                 # "Dosyaları gönder": payload dosya:<is_emri_no>
    "ornek": ["Ahmet Bey", "PM-B1234-20261011-1"],
}
# İE-08 8b (docs/kanal/2026-10-14_Meta_sablon_basvurusu_8b.md; Lokman 14 Ekim). Gövdeler Meta'ya başvurulanla birebir aynı kalır.
MUHENDIS_KONTROL = {
    "anahtar": "sablon_muhendis_kontrol",
    "metin": "Portman: {{1}} numaralı işin {{2}} revizyonu bayi tarafından onaylandı ve teknik kontrolünüzü bekliyor. Dosyaları almak için Gönder'e basın.",
    "dugme": "quick_reply",                 # "Gönder": payload muh:gonder:<is_emri_no>:<rev>
    "ornek": ["PM-B1234-20261014-1", "r03"],
}
MUHENDIS_HATIRLATMA = {
    "anahtar": "sablon_muhendis_hatirlatma",
    "metin": "Hatırlatma: {{1}} numaralı işin teknik kontrolü {{2}} saattir sizi bekliyor. Dosyaları yeniden almak için Gönder'e basın.",
    "dugme": "quick_reply",                 # "Gönder": payload şablon 1 ile aynı
    "ornek": ["PM-B1234-20261014-1", "2"],
}
BAYI_KARSILAMA = {
    "anahtar": "sablon_bayi_karsilama",
    "metin": "Merhaba {{1}}, Portman bayi kaydınız onaylandı. Plan taleplerinizi bu sohbete yazabilirsiniz; nasıl çalıştığını görmek için aşağıdaki düğmeye basın.",
    "dugme": "quick_reply",                 # "Nasıl çalışır?": payload bilgi:nasil
    "ornek": ["Ahmet Bey"],
}
BAYI_BILGI_HAZIR = {
    "anahtar": "sablon_bayi_bilgi_hazir",
    "metin": "Merhaba {{1}}, talebinizle ilgili bilgi hazır. Bu mesaja yanıt verirseniz bilgiyi buradan iletebiliriz.",
    "dugme": "quick_reply",                 # "Bilgiyi gönder": payload bilgi:hazir
    "ornek": ["Ahmet Bey"],
}
MUHENDIS_YUK_ONEKI = "muh:"                 # mühendisin düğmeleri: muh:<gonder|patron|duzeltme>:<is_emri_no>:<rev>
MUHENDIS_ISLEMLERI = ("gonder", "patron", "duzeltme")
BILGI_NASIL = "bilgi:nasil"                 # karşılama şablonunun düğmesi → "Nasıl çalışır?" PDF'i (LLM'siz)
BILGI_HAZIR = "bilgi:hazir"                 # bilgi hazır şablonunun düğmesi → sabit cevap + Patron'a bildirim (LLM'siz)
BAYI_BILGI_CEVABI = "Teşekkürler, bilgiyi bu sohbetten iletiyoruz."
DOSYA_YUK_ONEKI = "dosya:"                  # bayinin hızlı yanıt düğmesi: payload "dosya:<is_emri_no>"
BAYI_DOSYA_CEVABI = "Teşekkürler, dosyalarınızı bu sohbetten iletiyoruz."     # Lokman onayı, 11.10.2026 (ekleme B); aynen kalır
VARSAYILAN_HITAP = "Sayın Bayimiz"
# İE-21 · 3D bağlantısı (Bayi Rehberi §2 "Bilmeniz gerekenler": "3D'yi aç" butonu modeli telefonun tarayıcısında açar; tek parmakla
# çevirir, iki parmakla yaklaştırırsınız). Şablon değil: planla aynı turda, 24 saat penceresinde giden bağlantı butonu (cta_url; düğme ≤ 20).
UCB_DUGME = "3D'yi aç"
UCB_METNI = "{no} r{rev:02d} planının 3D modeli. Telefonunuzun tarayıcısında açılır: tek parmakla çevirin, iki parmakla yaklaştırın."


def ucb_metni(is_emri_no: str, rev: int) -> str:
    return UCB_METNI.format(no=is_emri_no, rev=int(rev))


def satir_id(gelen_id: str, sira: int) -> str:
    """kanal/worker.py::satir_id ve kanal/depo.py::satir_id ile aynı (testle denetlenir)."""
    return "out_" + hashlib.sha256(f"{gelen_id}|{sira}".encode()).hexdigest()[:24]


_IS_EMRI_NO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{0,59}")


def is_emri_no_gecerli(no) -> bool:
    """Düğme payload'undan ya da kayıttan gelen İş Emri no: yalnız harf, rakam, tire, alt çizgi; en çok 60 karakter (Meta değişkeni güvenli)."""
    return bool(no) and _IS_EMRI_NO.fullmatch(str(no)) is not None


def talep_kimligi(is_emri_no: str | None, son_is_emri_no: str | None, mesaj_id: str) -> str:
    """Patron şablonunun {{2}} değişkeni hiçbir zaman boş gitmez: işin İş Emri no'su; yoksa taslağın son İş Emri no'su; o da yoksa
    'T-' + mesajın kimlik izinin ilk 8 hanesi (depo.kimlik_izi = md5[:10] ile aynı önek; günlükte ve kanıt çıktısında bu izle aranır)."""
    for aday in (is_emri_no, son_is_emri_no):
        if aday and is_emri_no_gecerli(str(aday).strip()):
            return str(aday).strip()
    return "T-" + hashlib.md5(str(mesaj_id).encode()).hexdigest()[:8]


def bayi_kodu(bayi: dict | None, sender: str) -> str:
    kod = str((bayi or {}).get("kod") or "").strip()
    return kod[:40] if kod else "B" + str(sender or "")[-4:]


def hitap_metni(bayi: dict | None) -> str:
    """{{1}} bayi şablonunda: hitap; boşsa ad; o da boşsa 'Sayın Bayimiz' (D-06)."""
    for alan in ("hitap", "ad"):
        v = str((bayi or {}).get(alan) or "").strip()
        if v:
            return v[:80]
    return VARSAYILAN_HITAP


def sablon_satiri(gelen_id: str, sira: int, to: str, tur: str, sablon: dict, govde: list, dugme_degeri: str,
                  pencere_kapaliysa: bool, kaynak: str = "ajan") -> dict:
    """Giden satırı (worker.giden_metin biçimi; kind 'template'). Meta adı ve dil satıra yazılmaz (gönderim anında ayardan:
    sablon_* ve sablon_dil). govde: değişkenler sırayla ({{1}}, {{2}}); dugme_degeri: url soneki ya da quick_reply payload'u."""
    simdi = int(time.time())
    govde = [str(g) for g in govde]
    dugme = {"sub_type": sablon["dugme"], "index": 0}
    dugme["text" if sablon["dugme"] == "url" else "payload"] = str(dugme_degeri)
    return {"id": satir_id(gelen_id, sira), "kind": "template", "to": to, "body": sablon_metni(sablon["metin"], govde)[:4000], "tur": tur,
            "inbound_id": gelen_id, "seq": sira, "state": "pending", "wamid": None, "media_id": None, "attempts": 0, "error": None,
            "delivery_state": None, "created_at": simdi, "updated_at": simdi, "kaynak": kaynak,
            "sablon_anahtari": sablon["anahtar"], "sablon": {"govde": govde, "dugmeler": [dugme]},
            "pencere_kapaliysa": bool(pencere_kapaliysa)}


def patron_bildirim_satiri(gelen: dict, sira: int, bayi: dict | None, is_emri_no: str | None, son_is_emri_no: str | None,
                           kaynak: str = "ajan") -> dict:
    """Patron'a şablonla bildirim (yönlendirme, hata, dosya penceresi): {{1}} bayi kodu, {{2}} talep kimliği; düğme paneldeki
    konuşma sayfasına. Metin satırı ayrıca yazılır; gönderici pencere açıksa metni gönderir ve bu satırı 'sablon_gereksiz' yapar."""
    sender = str(gelen.get("sender") or "")
    return sablon_satiri(gelen["id"], sira, "PATRON", "bildirim", PATRON_BILDIRIM,
                         [bayi_kodu(bayi, sender), talep_kimligi(is_emri_no, son_is_emri_no, gelen["id"])],
                         f"konusma/{sender}", pencere_kapaliysa=True, kaynak=kaynak)


def bayi_dosyalar_hazir_satiri(gelen_id: str, sira: int, numara: str, bayi: dict | None, is_emri_no: str, kaynak: str = "panel") -> dict:
    """Bayiye 'dosyalarınız hazır' şablonu (panelden): {{1}} hitap, {{2}} İş Emri no; hızlı yanıt payload dosya:<no>. Her zaman gider."""
    return sablon_satiri(gelen_id, sira, numara, "bildirim", BAYI_DOSYALAR_HAZIR, [hitap_metni(bayi), str(is_emri_no)],
                         DOSYA_YUK_ONEKI + str(is_emri_no), pencere_kapaliysa=False, kaynak=kaynak)


# ───────────────────────── İE-08 8b ─────────────────────────
def muhendis_yuku(islem: str, is_emri_no: str, rev: int) -> str:
    """Mühendisin düğme kimliği (şablonun hızlı yanıtı ve dosya mesajının düğmeleri): muh:<islem>:<no>:<rev>."""
    if islem not in MUHENDIS_ISLEMLERI:
        raise ValueError(f"mühendis işlemi: {islem!r}")
    return f"{MUHENDIS_YUK_ONEKI}{islem}:{is_emri_no}:{int(rev)}"


def muhendis_yuku_coz(kimlik: str | None) -> tuple[str, str, int] | None:
    """muh:<islem>:<no>:<rev> → (islem, no, rev); tanınmıyorsa None (İş Emri no'su da denetlenir)."""
    p = str(kimlik or "").split(":")
    if len(p) != 4 or p[0] + ":" != MUHENDIS_YUK_ONEKI or p[1] not in MUHENDIS_ISLEMLERI or not is_emri_no_gecerli(p[2]) or not p[3].isdigit():
        return None
    return p[1], p[2], int(p[3])


def muhendis_kontrol_satiri(gelen_id: str, sira: int, is_emri_no: str, rev: int, kaynak: str = "ajan") -> dict:
    """Mühendise teknik kontrol bildirimi (bayinin onay mesajına bağlı; alıcı sembolik MUHENDIS, gönderimde aktif mühendis kartına
    çözülür). Her zaman şablon: ilk temas ve düğme (pencere açık olsa da)."""
    return sablon_satiri(gelen_id, sira, "MUHENDIS", "bildirim", MUHENDIS_KONTROL, [str(is_emri_no), f"r{int(rev):02d}"],
                         muhendis_yuku("gonder", is_emri_no, rev), pencere_kapaliysa=False, kaynak=kaynak)


def muhendis_hatirlatma_satiri(gelen_id: str, sira: int, is_emri_no: str, rev: int, saat: int, kaynak: str = "ajan") -> dict:
    return sablon_satiri(gelen_id, sira, "MUHENDIS", "hatirlatma", MUHENDIS_HATIRLATMA, [str(is_emri_no), str(max(1, int(saat)))],
                         muhendis_yuku("gonder", is_emri_no, rev), pencere_kapaliysa=False, kaynak=kaynak)


def bayi_karsilama_satiri(gelen_id: str, sira: int, numara: str, bayi: dict | None, kaynak: str = "panel") -> dict:
    """Panelden hiç yazmamış aktif karta karşılama (İE-07 bulgusu b): {{1}} hitap; hızlı yanıt bilgi:nasil."""
    return sablon_satiri(gelen_id, sira, numara, "bildirim", BAYI_KARSILAMA, [hitap_metni(bayi)], BILGI_NASIL, pencere_kapaliysa=False, kaynak=kaynak)


def bayi_bilgi_hazir_satiri(gelen_id: str, sira: int, numara: str, bayi: dict | None, kaynak: str = "panel") -> dict:
    """Panelden her aktif karta 'bilgi hazır' (planı olmasa da; İE-07 bulgusu a): {{1}} hitap; hızlı yanıt bilgi:hazir."""
    return sablon_satiri(gelen_id, sira, numara, "bildirim", BAYI_BILGI_HAZIR, [hitap_metni(bayi)], BILGI_HAZIR, pencere_kapaliysa=False, kaynak=kaynak)
