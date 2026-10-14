"""Serbest metindeki telefon numaralarının maskelenmesi (K09, D-09; BK-08 madde 9, 14.10.2026).

Tek desen, üç kullanım: paftaya giden serbest alanlar (`celik.numarasiz`), günlük / hata / Patron metinleri (`kanal.worker.maske_numaralar`)
ve D-01 yönlendirme gerekçesindeki bekleyen mesaj alıntısı (`karar._eski_taslak_sor`). Önceki desen yalnız 10–15 bitişik haneyi
yakalıyordu; boşluklu, tireli, parantezli ya da `+90`'lı yazılmış numara maskelenmeden geçiyordu.

Desen bilinen biçimlerle sınırlıdır (açgözlü bir "rakam ve boşluk" dizisi ölçü listelerini de yutardı):
- Türkiye: `+90` / `0090` / `0` önekli ya da `(0xxx)` parantezli alan kodu `[2-5]xx` / `8xx`, sonra 3-2-2 ya da 3-4 hane; öneksiz yalnız
  cep numarası (`5xx …`; "350 400 30 25" gibi ölçü listesi numara sayılmaz);
- uluslararası: `+` ülke kodu ve 2–5 hane grubu (toplam 10–15 hane);
- bitişik: 10–15 hane (önceki davranış).
Ayırıcı tek boşluk (bölünmez ve ince boşluk dahil) ya da tire (en tire dahil); nokta, virgül ve `x` ayırıcı değildir (ondalık, tarih ve
ölçü numara sayılmaz); arkasından birim (cm, m, m²) ya da çarpı ve sayı gelen dizi de numara sayılmaz. Bilinen sınır: birimsiz ve
numara biçiminde yazılmış ölçü dizisi ("540 300 20 10", "+10 120 180 240") numara sayılır; öneksiz sabit hat ("212 000 07 77") sayılmaz.
"""
from __future__ import annotations
import re

_AYR = "[ \u00a0\u2009\u202f\u2011\u2013-]?"            # boşluk, bölünmez boşluk (WhatsApp kopyası), ince boşluk, tire, en tire
_BIRIM = r"(?!\s*(?:(?:cm|mm|m2|m)\b|m²|[x×]\s*\d))"      # ölçü: arkasından birim ya da çarpı + sayı gelen dizi numara değil
_ONEK = rf"(?:(?:\+|00)90{_AYR}|0{_AYR})"
_ALAN = rf"(?:{_ONEK}(?:\([2-58]\d{{2}}\)|[2-58]\d{{2}})|\(0[2-58]\d{{2}}\)|\(5\d{{2}}\)|5\d{{2}})"   # öneksiz yalnız cep (5xx)
_TR = rf"{_ALAN}{_AYR}\d{{3}}(?:{_AYR}\d{{2}}{_AYR}\d{{2}}|{_AYR}\d{{4}})"
_ULUS = rf"\+\d{{1,3}}(?:{_AYR}(?:\(\d{{1,4}}\)|\d{{1,4}})){{2,5}}"
_BITISIK = r"\+?\d{10,15}"
DESEN = re.compile(rf"(?<![\d+])(?:{_TR}|{_ULUS}|{_BITISIK})(?!\d){_BIRIM}")


def _rakamlar(s: str) -> str:
    return re.sub(r"\D", "", s)


def maskele(metin: str, son_dort: bool = False) -> str:
    """Numaraları "…" ile değiştirir; `son_dort` ise "…" + son dört hane (günlük ve Patron metni; kimin numarası olduğu izlenebilir)."""
    def yerine(m: re.Match) -> str:
        r = _rakamlar(m.group(0))
        if not 10 <= len(r) <= 15:
            return m.group(0)
        return "…" + r[-4:] if son_dort else "…"
    return DESEN.sub(yerine, metin or "")
