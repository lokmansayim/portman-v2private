"""İE-07 · Meta onaylı şablon mesajları (Lokman, 11 Ekim 2026, Karar 2): metinler, değişkenler ve giden satırı üreticisi.

Şablonlar Meta'ya Lokman WhatsApp Manager'dan gönderir (docs/kanal/2026-10-11_Meta_sablon_basvurusu.md); onaylanan adlar
settings.json'a `sablon_patron_bildirim` ve `sablon_bayi_dosyalar_hazir` anahtarlarıyla girer (vps/ayar.sh). Satıra Meta adı
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
DOSYA_YUK_ONEKI = "dosya:"                  # bayinin hızlı yanıt düğmesi: payload "dosya:<is_emri_no>"
BAYI_DOSYA_CEVABI = "Teşekkürler, dosyalarınızı bu sohbetten iletiyoruz."     # Lokman onayı, 11.10.2026 (ekleme B); aynen kalır
VARSAYILAN_HITAP = "Sayın Bayimiz"


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
