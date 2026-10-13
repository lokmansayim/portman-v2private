"""İE-04 · Gelen buton ve liste cevaplarının çözümü (kanal v1.3).

Kimlik dilbilgisi (docs/is_emirleri/IE-04-mesaj-katmani.md): s:<set>:<kod> seçim · o:<is_emri_no>:<rev> onay ·
r:<is_emri_no>:<rev> revizyon isteği · q:<alan>:<deger> bekleyen sorunun kısa cevabı.

Kural: görünen başlık metni tek başına seçim kimliği sayılmaz. Kimlik çözülür; cevabın verildiği giden mesaj (context_id →
giden satırı) bulunabiliyorsa kimliğin o mesajın butonları arasında olduğu doğrulanır; sonra güncellik denetlenir. Güncel
değilse hiçbir durum değişmez, bayiye eski buton olduğu ve güncel durumun ne olduğu söylenir. Geçerli kimlik LLM çağrılmadan
deterministik bir Talep'e çevrilir. Serbest metin bu dosyaya girmez (LLM yolu değişmez).
"""
from __future__ import annotations
import re

BUTON_ID = re.compile(r"^(s|o|r|q):([^:]{1,120}):([^:]{1,60})$")
KISA_CEVAP = {  # q:<alan>:<deger> → kural katmanının okuyacağı metin
    "pencere_islem": {"degistir": "değiştir", "ekle": "ekle"},
    "yeni_mi_degisiklik": {"yeni": "yeni", "degisiklik": "değişiklik"},
    "oncelik": {"butce": "bütçe", "yasam": "yaşam alanı", "montaj": "kısa montaj", "yok": "fark etmez"},
    "okuma": {"1": "1", "2": "2", "0": "hiçbiri"},        # İE-08 PR-2b: çelik pencere okuması "1 / 2 / Hiçbiri"
}


def mesaj_kimlikleri(satir: dict | None) -> set[str]:
    """Bir giden satırın (hosting biçimi) taşıdığı buton ve liste satırı kimlikleri."""
    if not satir or satir.get("kind") != "interactive":
        return set()
    i = satir.get("interactive") or {}
    a = i.get("action") or {}
    ids = {str(b.get("id") or (b.get("reply") or {}).get("id")) for b in (a.get("buttons") or []) if isinstance(b, dict)}   # Meta biçimi: {type: reply, reply: {id, title}}
    for sec in a.get("sections") or []:
        for r in (sec.get("rows") or []):
            if isinstance(r, dict):
                ids.add(str(r.get("id")))
    return ids


def _talep(niyet: str, ozet: str, **alan) -> dict:
    return {"niyet": niyet, "guven": "yuksek", "ozet": ozet, **alan}


def coz(gelen: dict, d: dict | None, giden_bul=None) -> dict:
    """reply_id çözümü. Dönen sözlük:
      {"gecerli": True, "tur": secim|onay|revize|soru, "talep": {...}, "metin": str, "kimlik": str, "not": str}
      {"gecerli": False, "kimlik": str, "neden": str, "mesaj": bayiye gidecek metin}
    d: işten önceki konuşma durumu. giden_bul(context_id) → giden satırın hosting biçimi (satir) ya da None."""
    d = d or {}
    kimlik = str(gelen.get("reply_id") or "").strip()
    m = BUTON_ID.match(kimlik)
    if not m:
        return {"gecerli": False, "kimlik": kimlik, "neden": "kimlik çözülemedi",
                "mesaj": "Bu butonu tanıyamadım; isteğinizi yazarak iletirseniz devam ederim."}
    tur, a, b = m.group(1), m.group(2), m.group(3)
    # Cevap hangi mesaja verildi: kimlik o mesajın butonları arasında olmalı (varsa)
    ctx = gelen.get("context_id")
    if ctx and giden_bul is not None:
        satir = giden_bul(ctx)
        if satir is not None and kimlik not in mesaj_kimlikleri(satir):
            return {"gecerli": False, "kimlik": kimlik, "neden": "kimlik cevaplanan mesajın butonlarında yok",
                    "mesaj": "Bu cevabı hangi mesaja verdiğinizi doğrulayamadım; isteğinizi yazarak iletirseniz devam ederim."}
    ie = d.get("son_is_emri") or {}
    guncel = (str(ie.get("is_emri_no") or ""), int(ie.get("revizyon") or 0))
    st = d.get("secenek_seti") or {}
    if tur == "s":
        if st.get("id") != a or st.get("durum") != "acik":
            if st.get("id") == a and st.get("durum") == "secildi":
                neden, mesaj = "set zaten seçilmiş", (f"Bu seçenek listesinden {st.get('secilen_kod')} zaten seçildi. "
                                                      + (f"Güncel plan {guncel[0]} r{guncel[1]:02d}. " if guncel[0] else "") + "Değişiklik isterseniz yazın.")
            elif st.get("durum") == "acik":
                neden, mesaj = "eski seçenek seti", "Bu butonlar eski bir seçenek listesine ait; güncel listeyi az önce gönderdim, oradan seçin ya da kodu yazın."
            else:
                neden, mesaj = "açık seçenek seti yok", ("Bu seçenek listesi artık geçerli değil. "
                                                      + (f"Güncel plan {guncel[0]} r{guncel[1]:02d}. " if guncel[0] else "") + "Yeni seçenek için talebinizi yazın.")
            return {"gecerli": False, "kimlik": kimlik, "neden": neden, "mesaj": mesaj}
        if b not in {x.get("kod") for x in st.get("adaylar") or []}:
            return {"gecerli": False, "kimlik": kimlik, "neden": "kod sette yok", "mesaj": "Bu seçenek listede yok; listeden seçin ya da kodu yazın."}
        return {"gecerli": True, "tur": "secim", "kimlik": kimlik, "metin": f"{b} olsun",
                "talep": _talep("yeni_talep", f"{b} seçildi", katalog_kodu=b), "not": f"seçim butonu: {b}"}
    if tur in ("o", "r"):
        try:
            rev = int(b)
        except ValueError:
            rev = -1
        if (a, rev) != guncel or d.get("asama") != "onay_bekliyor":
            if guncel[0]:
                mesaj = (f"Bu buton {a} r{rev:02d} planına ait; güncel plan {guncel[0]} r{guncel[1]:02d}. "
                         + ("Güncel planı onaylamak ya da değiştirmek için onun mesajındaki butonları kullanın ya da yazın." if d.get("asama") == "onay_bekliyor"
                            else "Bu plan için onay beklenmiyor; isteğinizi yazın."))
            else:
                mesaj = f"Bu buton {a} r{rev:02d} planına ait; şu an açık bir plan yok. İsteğinizi yazın."
            return {"gecerli": False, "kimlik": kimlik, "neden": "eski revizyon butonu" if (a, rev) != guncel else "onay beklenmiyor", "mesaj": mesaj}
        if tur == "o":
            return {"gecerli": True, "tur": "onay", "kimlik": kimlik, "metin": "onaylıyorum",
                    "talep": _talep("onay", f"{a} r{rev:02d} onaylandı (buton)"), "not": f"onay butonu: {a} r{rev:02d}"}
        return {"gecerli": True, "tur": "revize", "kimlik": kimlik, "metin": "revize et",
                "talep": _talep("red", f"{a} r{rev:02d} için değişiklik istendi (buton)"), "not": f"revizyon butonu: {a} r{rev:02d}"}
    # q: bekleyen sorunun kısa cevabı
    if d.get("son_soru_alani") != a:
        return {"gecerli": False, "kimlik": kimlik, "neden": "soru artık askıda değil",
                "mesaj": "Bu buton cevaplanmış ya da kapanmış bir soruya ait; güncel isteğinizi yazın."}
    metin = KISA_CEVAP.get(a, {}).get(b)
    if metin is None:
        return {"gecerli": False, "kimlik": kimlik, "neden": "bilinmeyen kısa cevap", "mesaj": "Bu cevabı tanıyamadım; lütfen yazarak cevaplayın."}
    return {"gecerli": True, "tur": "soru", "kimlik": kimlik, "metin": metin,
            "talep": _talep("diger", f"kısa cevap: {metin}"), "not": f"soru butonu: {a} = {b}"}
