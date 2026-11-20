"""İE-42 · çatı cevabı: havuz + LLM okur, kod karar verir (Lokman, 17 Kasım 2026: kart 04:57:27 "LLM okusun, kod karar versin";
04:58:54 "50 tur koştuğun veriyi havuza al"; plan kartı 05:09:29 "Onaylıyorum").

- Havuz (`beyin/veri/cati_cevabi_havuzu.json`): geometri hakeminin 50 turda yazdığı mesajlar ve doğru okumaları.
- `baglam`: çatı seti açıkken LLM'e giden bağlama çatı listesi ve havuzdan en benzer örnekler eklenir (aynı tek çağrı, K05). Havuzdaki
  okuma doğrudan karar olmaz: benzer iki mesaj ters anlama gelebilir; örnek yalnız LLM'in okumasına yardım eder.
- `okuma`: LLM'in `cati_cevabi` alanı listeye göre denetlenir; kararı `karar._cati_adimi` (onaydan sonra) ve `karar._prefabrik_cati_istegi`
  (onaydan önceki prefabrik set, 20 Kasım 2026) verir. Alan yoksa bugünkü kural yolu.
Ağ yok, ücret yok; benzerlik harf üçlüsü örtüşmesiyle (bağımlılık yok)."""
from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

HAVUZ_YOLU = Path(__file__).resolve().parent / "veri" / "cati_cevabi_havuzu.json"
ORNEK_SAYISI = 10
BENZERLIK_ESIGI = 0.8
_OKUMA_YAZISI = {"secti": "seçti {n}", "kararsiz": "kararsız", "secim_yok": "seçim yok"}


def _norm(s: str) -> str:
    s = (s or "").replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\wçğıöşü ]+", " ", s)).strip()


def _ucluler(s: str) -> frozenset:
    s = f"  {_norm(s)}  "
    return frozenset(s[i:i + 3] for i in range(len(s) - 2))


@lru_cache(maxsize=1)
def havuz() -> tuple:
    """(örnek satırları, ölçüm satırları); örnek satırı (üçlüler, satır)."""
    if not HAVUZ_YOLU.exists():
        return (), ()
    satirlar = json.loads(HAVUZ_YOLU.read_text(encoding="utf-8"))["satirlar"]
    ornek = tuple((_ucluler(x["m"]), x) for x in satirlar if not x.get("olcum"))
    olcum = tuple(x for x in satirlar if x.get("olcum"))
    return ornek, olcum


def benzerler(metin: str, n: int = ORNEK_SAYISI, yapi: str | None = None) -> list[dict]:
    """Havuzdan mesaja en benzer n örnek (Dice benzerliği; eşitlikte havuz sırası). Ölçüm satırları dönmez; aynı metin dönmez."""
    u = _ucluler(metin)
    if not u:
        return []
    nm = _norm(metin)
    puan = []
    for i, (v, x) in enumerate(havuz()[0]):
        if _norm(x["m"]) == nm:
            continue
        p = 2 * len(u & v) / (len(u) + len(v)) + (0.1 if yapi and x.get("yapi") == yapi else 0)
        puan.append((-p, i, x))
    puan.sort(key=lambda a: (a[0], a[1]))
    secilen: list[tuple[frozenset, dict]] = []                 # çeşitlilik: birbirinin neredeyse aynısı örnek bir kez
    for _, i, x in puan:
        v = havuz()[0][i][0]
        if all(2 * len(v & w) / (len(v) + len(w)) < BENZERLIK_ESIGI for w, _ in secilen):
            secilen.append((v, x))
            if len(secilen) == n:
                break
    return [x for _, x in secilen]


def _acik_set(k) -> dict | None:
    """Açık çatı seti: plan onayından sonraki set (İE-42) ya da onaydan önce açılan prefabrik çatı seti (İE-37; Lokman, kart 20 Kasım
    2026 08:04:29 "Evet, LLM okusun"). Onaydan önceki çelik çatı seti (İE-25) bugünkü kural yolunda kalır."""
    d = k.d
    st = d.get("secenek_seti") or {}
    if st.get("durum") != "acik" or st.get("tur") != "cati_varyanti":
        return None
    if d.get("cati_adimi"):
        return st if d.get("asama") == "onay_bekliyor" else None
    adaylar = st.get("adaylar") or []
    return st if adaylar and all(a.get("yapi_turu") == "prefabrik" for a in adaylar) else None


def baglam(k, metin: str) -> str:
    """Çatı seti açıksa LLM bağlamına eklenecek metin (liste ve benzer örnekler); değilse boş. Kişi adı ve numara yok."""
    st = _acik_set(k)
    if not st or not (metin or "").strip():
        return ""
    from beyin import secenek as SC
    liste = []
    for a in st.get("adaylar") or []:
        ad = (a.get("sunum") or {}).get("cati_adi") or a.get("cati_adi")
        liste.append(f"{a.get('sira')}. {SC.gosterim(a)}" + (f" ({ad})" if ad else "") + (" — evin kendi çatısı" if a.get("sira") == 1 else ""))
    yapi = ((k.d.get("son_is_emri") or {}).get("yapi") or {}).get("sistem") == "celik" and "celik" or "prefabrik"
    ornek = "; ".join(f"«{x['m']}» → {_OKUMA_YAZISI[x['durum']].format(n=x.get('secilen'))}" for x in benzerler(metin, yapi=yapi))
    return ("çatı seti açık: bayiye şu çatılar soruldu: " + " | ".join(liste) + ". Bayinin cevabını cati_cevabi alanına oku"
            + (f"; benzer örnekler (listede 1 evin çatısı, 2 ve 3 öteki çatılar): {ornek}" if ornek else ""))


def okuma(cevap, st: dict) -> dict | None:
    """LLM'in `cati_cevabi` alanı → {"durum", "kod", "ek_istek"}; alan yoksa None (bugünkü kural yolu). Listede olmayan numara kararsızdır."""
    if cevap is None:
        return None
    c = cevap if isinstance(cevap, dict) else cevap.model_dump()
    durum, ek = c.get("durum"), bool(c.get("ek_istek"))
    if durum == "secti":
        aday = next((a for a in st.get("adaylar") or [] if a.get("sira") == c.get("secilen")), None)
        if aday is None or not aday.get("kod"):
            return {"durum": "kararsiz", "kod": None, "ek_istek": ek}
        return {"durum": "secti", "kod": str(aday["kod"]), "ek_istek": ek}
    if durum in ("kararsiz", "secim_yok"):
        return {"durum": durum, "kod": None, "ek_istek": ek}
    return {"durum": "kararsiz", "kod": None, "ek_istek": ek}
