"""İE-08 8a PR-2 · Çelik hattının kural katmanı yardımcıları (LLM yok; motor modülleri içe aktarılmaz).

- Aday kaydındaki çelik modeller (`motor: genel`, tanım `modeller/<kod>.json`) için İş Emri zarfı: tanım gömülmez, yolu ve sha256'sı
  yazılır; çizim `kanal/worker.py` → `motor.genel.uret` ile (A3). Değişiklikler (`yapi.degisiklikler`) sırayla uygulanır (A4, PR-2b).
- Antet bilgisi (`bilgi`; D-09): bayinin adı ve **bayi kartındaki** numara (`bayi["numara"]`; kart = Postgres `bayiler.numara`); gönderici
  kimliği (`k.gonderen`) ve LLM'in çıkardığı `musteri.telefon` kullanılmaz; kart numarası yoksa ya da gönderenle aynı değilse numara
  yazılmaz ("..."); yalnız `rol = bayi` kartı numara yazdırır (Patron ve test kartı yazdırmaz).
- Bina özellikleri: bayinin söyledikleri şablon satırlarıyla eşleşirse o satıra, eşleşmeyen "Anahtar: değer" olarak özel isteklere (K21:
  uydurulmaz, sessizce düşmez).
- Çatı seçimi: katalog modelinin çatı varyantları numaralı seçenek olarak gider (İE-05 devir §3.1 kural 5); bayinin kendi metninde tek
  bir çatı seçimi (varyant harfi ya da kodu, "katalog çatısı") geçiyorsa set sorulmaz (K18: kural bayinin sözünü okur). Okuma
  `celik_okuma.cati_okumasi` / `cati_secenekleri`'nde (PR-2b; buradaki eski `cati_secimi` değişimin kaynağını ve olumsuzluğu ayırmıyordu,
  geometri hakemi beşinci turda kaldırıldı).
"""
from __future__ import annotations
import hashlib
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# `motor/genel/sablon_pafta.OZELLIK_SIRASI` ile aynı liste (testler/kalici/test_celik_akisi.py denetler); matplotlib içe aktarılmasın diye kopya
OZELLIK_ALANLARI = ["Bina Yüksekliği", "Dış Duvarlar", "İç Duvarlar", "Panel Türü", "Çatı Şekli", "Çatı Eğimi", "Çatı Kaplaması", "Çatı Kaplama Rengi",
                    "Dış Kapı", "İç Kapılar", "Pencereler", "Vasistaslar", "Dış Boya Rengi", "İç Boya Rengi", "Köşe ve Söveler"]
_TR = str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").translate(_TR).lower()).strip()


_ESLE = {_norm(a): a for a in OZELLIK_ALANLARI}
_ESLE.update({"dis boya": "Dış Boya Rengi", "ic boya": "İç Boya Rengi", "cati rengi": "Çatı Kaplama Rengi", "cati kaplama rengi": "Çatı Kaplama Rengi",
              "kaplama rengi": "Çatı Kaplama Rengi", "sove": "Köşe ve Söveler", "soveler": "Köşe ve Söveler", "kose": "Köşe ve Söveler",
              "dis kapi": "Dış Kapı", "ic kapi": "İç Kapılar", "ic kapilar": "İç Kapılar", "pencere": "Pencereler"})


def ozellikleri_esle(bina_ozellikleri: dict | None) -> tuple[dict, list[str]]:
    """Bayinin pafta tablosu alanları → (şablon satırına yazılacaklar, eşleşmeyenler "Anahtar: değer")."""
    oz, kalan = {}, []
    for k, v in (bina_ozellikleri or {}).items():
        if v in (None, ""):
            continue
        ad = _ESLE.get(_norm(str(k)))
        if ad:
            oz[ad] = str(v)
        else:
            kalan.append(f"{k}: {v}")
    return oz, kalan


def tanim_sha(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def tanim_yolu(aday: dict) -> Path:
    return ROOT / aday["tanim"]


_NUMARA = re.compile(r"(?<!\d)\d{10,15}(?!\d)")


def numarasiz(metin: str) -> str:
    """D-09 "başka numara reddedilir": serbest metin alanlarında (sevk adresi, özel istekler, özellikler) 10–15 haneli rakam dizileri
    paftaya girmez; yerine "…" yazılır (bayi mesajında müşterinin numarası geçse de PDF'e basılmaz; KVKK denetçisi 12.10)."""
    return _NUMARA.sub("…", metin or "")


def bayi_adi(bayi: dict | None) -> str:
    """Bayinin adı; kart adsızsa `depo.gelen_bayisi` numarayı ad olarak verir — o antete yazılmaz (D-09; KVKK denetçisi 12.10)."""
    ad = str((bayi or {}).get("ad") or "").strip()
    return "" if re.fullmatch(r"[\d\s+().-]{8,}", ad) else ad


def bayi_telefonu(bayi: dict | None, gonderen: str | None) -> str | None:
    """D-09: yalnız `rol = bayi` kartının kendi numarası, gönderenle aynıysa; aksi hâlde None (antette '...')."""
    if not bayi or (bayi.get("rol") or "bayi") != "bayi":
        return None
    n = str(bayi.get("numara") or "").strip()
    if not n or (gonderen and str(gonderen).strip() != n):
        return None
    return n


def zarf(aday: dict, bayi: dict, gonderen: str | None, ts: dict, son_is_emri: dict | None, degisiklikler: list[dict] | None = None,
         kaynak: str = "") -> dict:
    """Çelik İş Emri zarfı (sistem celik, motor genel). Numara ve revizyon prefabrikle aynı kuralla (`karar._is_emri_uret`; G-2)."""
    seq = int(time.time()) % 100000
    ie = {"sema": "portman.is_emri_celik/0.1", "is_emri_no": f"PM-{bayi.get('kod', 'BAYI')}-{time.strftime('%Y%m%d')}-{seq}",
          "revizyon": int((son_is_emri or {}).get("revizyon") or 0) + 1,
          "yapi": {"sistem": "celik", "motor": "genel", "referans_model": aday.get("referans_model") or aday["kod"], "kod": aday["kod"],
                   "gosterim": aday.get("gosterim") or aday["kod"], "tanim": aday["tanim"], "tanim_sha256": aday.get("tanim_sha256"),
                   "yontem": "panel", "kat": aday.get("kat"), "degisiklikler": list(degisiklikler or [])},
          "sunum": {"musteri_projesi": bool(aday.get("musteri_projesi")), "cati_adi": (aday.get("sunum") or {}).get("cati_adi")},
          "talep": {"bayi": {"kod": bayi.get("kod"), "ad": bayi.get("ad")}, "kaynak": kaynak or f"aday {aday['kod']}",
                    "musteri_adi": (ts.get("musteri") or {}).get("ad") or "", "metin": ts.get("ozet", "")},
          "eksikler": []}
    oz, kalan = ozellikleri_esle(ts.get("bina_ozellikleri"))
    ie["bilgi"] = {"bayi_adi": bayi_adi(bayi), "bayi_telefonu": bayi_telefonu(bayi, gonderen),
                   "sevk_adresi": numarasiz((ts.get("musteri") or {}).get("sevk_adresi") or ""), "ozellikler": {k: numarasiz(v) for k, v in oz.items()},
                   "ozel_istekler": [numarasiz(str(x)) for x in list(ts.get("ozel_istekler") or []) + kalan], "cizen": "Portman", "kontrol": "Portman", "onay": "Portman"}
    return ie


def kaynak_notu(aday: dict) -> str:
    g = aday.get("gosterim") or aday["kod"]
    ca = (aday.get("sunum") or {}).get("cati_adi")
    return f"{g}" + (f" ({ca})" if ca and not aday.get("musteri_projesi") else "")
