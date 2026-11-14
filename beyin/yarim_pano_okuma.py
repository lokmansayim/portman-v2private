"""İE-39 PR-2 · bayinin "sağa yarım pano uzat" cümlesi (D-90). LLM yok: kural bayinin kendi mesajını okur (K18).

Okunan komut İş Emri'ne `beyin.yarim_pano.uygula` ile uygulanır (karar katmanı). Bu modül yalnız metni okur:

- Komut bir cümlede (nokta, ünlem, soru işareti, noktalı virgül, satır sonu) "pano", bir duvar sözü (sağ, sol, ön, arka) ve bir fiil
  (uzat, büyüt, genişlet; kısalt, küçült, daralt) taşır. Cümlede birden çok fiil varsa her fiil kendinden önceki parçanın duvarını ve
  miktarını alır ("sağa yarım pano uzat, öne de yarım pano kısalt").
- Miktar: "yarım pano" = 1 yarım pano (62,75 cm); "N yarım pano" = N. "pano", "1 pano", "bir pano" tam panodur (125,5 cm = 2 yarım pano;
  Lokman, kart 14 Kasım 2026 12:54:43 UTC "125,5 cm (tam pano)"); "N pano" = 2N yarım pano. Miktarsız cümle ("sağa uzat") komut değildir.
- Sol ve arka duvar da okunur; uygulamada bugünkü dilim (sağ, ön) dışında kalır ve bayiye gerekçe gider (`yarim_pano.DILIM`).
- Komut sayılmayan biçimler `belirsiz` döner, bayiye sorulur ya da söylenir (K21, sessiz düşmez): duvarı yazılmamış ("yarım pano uzat"),
  iki zıt fiil, olumsuz fiil ("uzatmayın"), oda adı taşıyan cümle ("salonu sağa yarım pano büyüt": bu oda büyütmedir, ev komutu değil),
  soru ("uzatılabilir mi?"; "uzatır mısınız?" gibi rica biçimi komuttur).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TAM_PANO_ADIM = 2          # "1 pano" = 125,5 cm = 2 yarım pano (Lokman, kart 14 Kasım 2026 12:54:43 UTC)
_SAYI = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5}


def kucuk(s: str) -> str:
    """Türkçe küçük harf (İ → i, I → ı); boşluk tekilleşir."""
    s = (s or "").replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", s).strip()


_CUMLE = re.compile(r"[^.!?;\n]+[.!?;\n]*")      # cümle, bitiş işaretiyle (soru işareti okunur)
_HARF = "a-zçğıöşü0-9"
_DUVAR = {   # sözcük başı; ek listesi kapalı ("önce", "solucan", "arkadaş" duvar değil; "ön onay" duvar değil)
    "sag": re.compile(rf"(?<![{_HARF}])sağ(?:a|dan|da|daki|ı|ını|ındaki|ında)?(?![{_HARF}])"),
    "sol": re.compile(rf"(?<![{_HARF}])sol(?:a|dan|da|daki|u|unu|undaki|unda)?(?![{_HARF}])"),
    "on": re.compile(rf"(?<![{_HARF}])ön(?:e|den|de|deki|ü|ünü|ündeki|ünde)?(?![{_HARF}])(?! onay)"),
    "arka": re.compile(rf"(?<![{_HARF}])arka(?:ya|dan|da|daki|sı|sını|sındaki|sında)?(?![{_HARF}])"),
}
_FIIL = re.compile(rf"(?<![{_HARF}])(uzat|büyüt|genişlet|kısalt|küçült|daralt)([{_HARF}]*)")
_ARTI = {"uzat", "büyüt", "genişlet"}
# olumsuz ek fiil kökünden hemen sonra: "uzatma", "uzatmayın", "büyütmesin", "kısaltmayalım", "uzatmadık", "uzatmaz", "uzatmayacağız".
# "uzatmak", "uzatmanızı" olumludur.
_OLUMSUZ_EK = re.compile(r"^(?:[ıiuü]l)?m[ae](?:$|y|s|d|z)")
_SORU = re.compile(rf"(?<![{_HARF}])m[ıiuü](?:y[ıi]z|s[ıiuü]n(?:[ıiuü]z)?|d[ıiuü]r)?(?![{_HARF}])")     # soru eki ayrı sözcük
_RICA = re.compile(rf"(?<![{_HARF}])m[ıiuü]s[ıiuü]n[ıiuü]z(?![{_HARF}])")      # "uzatır mısınız", "uzatabilir misiniz"
_MIKTAR = re.compile(rf"(?:(?<![{_HARF},.])(\d+|bir|iki|üç|dört|beş)\s+)?(yarım\s+)?pano(?:[{_HARF}]*)")
_KESIRLI = re.compile(r"\d+[,.]\d+\s*(?:yarım\s+)?pano|buçuk|çeyrek")       # "1,5 pano", "bir buçuk pano": miktar okunmaz
_ODA = re.compile(rf"(?<![{_HARF}])(salon|oda|mutfak|banyo|wc|tuvalet|hol|antre|koridor|veranda|balkon|teras|sundurma|yatak)"
                  rf"(?:[{_HARF}]*)")


@dataclass
class Komut:
    cephe: str          # sag | sol | on | arka
    adim: int           # yarım pano sayısı; > 0 uzat, < 0 kısalt
    soz: str            # bayinin cümlesi (kayıt ve bayi mesajı)


@dataclass
class Belirsiz:
    soz: str
    neden: str          # bayiye giden kısa gerekçe


def _miktar(parca: str) -> int | None:
    """Parçadaki pano miktarı (yarım pano sayısı); yoksa None."""
    m = None
    for m in _MIKTAR.finditer(parca):
        pass
    if m is None:
        return None
    sayi = m.group(1)
    n = 1 if sayi is None else (int(sayi) if sayi.isdigit() else _SAYI[sayi])
    return n if m.group(2) else n * TAM_PANO_ADIM


def _cumle_oku(cumle: str) -> tuple[list[Komut], list[Belirsiz]]:
    soru_isareti = "?" in cumle
    cumle = cumle.rstrip(".!?;").strip()
    c = kucuk(cumle)
    if "pano" not in c or not _FIIL.search(c):
        return [], []
    fiiller = list(_FIIL.finditer(c))
    if _ODA.search(c):
        return [], [Belirsiz(cumle, "oda adı geçen pano isteği oda büyütmedir; yarım pano komutu evin dış duvarını kaydırır")]
    if any(_OLUMSUZ_EK.match(f.group(2)) for f in fiiller):
        return [], [Belirsiz(cumle, "olumsuz istek")]
    if (soru_isareti or _SORU.search(c)) and not _RICA.search(c):
        return [], [Belirsiz(cumle, "soru biçiminde istek")]
    komutlar: list[Komut] = []
    bas = 0
    for i, f in enumerate(fiiller):
        parca = c[bas:] if i == len(fiiller) - 1 else c[bas:f.end()]     # son fiilden sonraki söz de onundur ("uzat sağa")
        bas = f.end()
        duvarlar = [cephe for cephe, r in _DUVAR.items() if r.search(parca)]
        miktar = None if _KESIRLI.search(parca) else _miktar(parca)
        if not duvarlar:
            return [], [Belirsiz(cumle, "hangi duvarın kayacağı yazılı değil")]
        if miktar is None:
            return [], [Belirsiz(cumle, "kaç pano kayacağı yazılı değil")]
        isaret = 1 if f.group(1) in _ARTI else -1
        komutlar += [Komut(cephe, isaret * miktar, cumle) for cephe in duvarlar]
    return komutlar, []


def oku(metin: str | None) -> tuple[list[Komut], list[Belirsiz]]:
    """Mesajdaki yarım pano komutları ve komut sayılmayan pano istekleri (cümle sırasıyla)."""
    komutlar: list[Komut] = []
    belirsiz: list[Belirsiz] = []
    for m in _CUMLE.finditer(metin or ""):
        k, b = _cumle_oku(m.group(0))
        komutlar += k
        belirsiz += b
    return komutlar, belirsiz


def soz_komut_mu(aciklama: str | None, komutlar: list[Komut], belirsiz: list[Belirsiz] | None = None) -> bool:
    """LLM'in değişiklik açıklaması (bayinin sözüyle yazılır) okunan bir pano isteğinin kopyası mı? Kopya taslağa ikinci kez girmez."""
    a = kucuk(aciklama)
    if not a:
        return False
    if "pano" in a and _FIIL.search(a):
        return True
    for s in [x.soz for x in komutlar] + [x.soz for x in (belirsiz or [])]:
        s = kucuk(s)
        if a in s or s in a:
            return True
    return False


def birlestir(komutlar: list[dict]) -> list[dict]:
    """Taslakta biriken komutlar ({cephe, adim}) duvar başına toplanır; ilk geliş sırası korunur, toplamı sıfır olan duvar düşer."""
    toplam: dict[str, int] = {}
    for c in komutlar:
        toplam[c["cephe"]] = toplam.get(c["cephe"], 0) + int(c["adim"])
    return [{"cephe": a, "adim": n} for a, n in toplam.items() if n]
