"""İE-14 r3 · P4: LLM-önce okuma ile bugünkü kural okumasının (`celik_okuma`) yan yana kıyası (Lokman 14.10.2026, 4. madde).

Kural okuması karar verir; LLM okuması gölgede koşar ve kaydedilir (kanal: `llm_once_revizyon.mod = "golge"`; çevrimdışı:
`araclar/okuma_kiyas.py`). `celik_okuma.py` silinmez ve küçülmez; geçiş kararı kıyas raporundan sonra Lokman'ındır.

İki okuma aynı biçime çevrilir (okuma öğeleri):
- ("pencere", açıklık, en, yük): tek adaylı, ölçülü pencere değişikliği
- ("pencere_soru", adaylar, ölçü|None): birden çok aday ya da ölçüsüz → soru
- ("cati", kod) · ("cati_soru",) · ("dis140",)
Ayrıca "okunamayan" cümleler: bayiye "otomatik uygulayamadım" diye yazılacak ya da yönlendirilecek olanlar. Olumsuz cümlenin uygulanmaması
okunamama değildir (doğru okumadır).

Sınıflar: aynı · farklı · yalnız_llm (kural hiçbir değişiklik okumadı, LLM okudu) · yalnız_kural · ikisi_de_okuyamadi · ikisi_de_bos.
Hangisinin doğru olduğu insan etiketidir (Lokman ya da mühendis); kıyas yalnız farkı gösterir.
"""
from __future__ import annotations

from beyin import celik_okuma as CO, degisiklik_okuyucu as DO

SINIFLAR = ("aynı", "farklı", "yalnız_llm", "yalnız_kural", "ikisi_de_okuyamadi", "ikisi_de_bos")


def kural_okumasi(metin: str, t: dict, katalog_aday: dict | None = None, y: dict | None = None) -> dict:
    """`celik_okuma.oku` → {ogeler: [..], okunamayan: [cümle], olumsuz: [cümle]}."""
    r = CO.oku(metin, t, katalog_aday, y=y)
    ogeler = set()
    for p in r["pencereler"]:
        if p.get("olumsuz") or p.get("ekle_kaldir"):
            continue
        ad = sorted(a["aciklik"] for a in p.get("adaylar") or [])
        olcu = tuple(p["olcu"]) if p.get("olcu") else None
        if olcu and len(ad) == 1:
            ogeler.add(("pencere", ad[0], int(olcu[0]), int(olcu[1])))
        else:
            ogeler.add(("pencere_soru", tuple(ad), olcu))
    if r["cati"]:
        ogeler.add(("cati", str(r["cati"]).upper().replace("-", "")))
    elif r["cati_belirsiz"]:
        ogeler.add(("cati_soru",))
    if r["dis140"]:
        ogeler.add(("dis140",))
    return {"ogeler": sorted(ogeler, key=str), "okunamayan": list(r["baska"]) + list(r["belirsiz"]) + list(r["ekle_kaldir"]),
            "olumsuz": list(r["olumsuz"])}


def llm_okumasi(sonuc: dict, pencereler: list[dict], cati_kodlari: set[str]) -> dict:
    """`degisiklik_okuyucu` sonucu (kodla ayıklanmış) → aynı biçim. Hata durumunda `hata`."""
    if sonuc.get("durum") != "tamam":
        return {"ogeler": [], "okunamayan": [], "hata": sonuc.get("hata") or sonuc.get("durum")}
    d = DO.denetle(sonuc, pencereler, cati_kodlari)
    ogeler = set()
    for o in d["ops"]:
        if o["op"] == "pencere_olcu":
            ogeler.add(("pencere", o["aciklik"], int(o["en"]), int(o["yuk"])))
        elif o["op"] == "cati_varyanti":
            ogeler.add(("cati", str(o["kod"]).upper().replace("-", "")))
        elif o["op"] == "dis_karkas_140":
            ogeler.add(("dis140",))
    if d["sor"]:
        olcu = tuple(d["sor"]["olcu"]) if d["sor"].get("olcu") else None
        ogeler.add(("pencere_soru", tuple(sorted(a["aciklik"] for a in d["sor"]["adaylar"])), olcu))
    return {"ogeler": sorted(ogeler, key=str), "okunamayan": list(d["uygulanamaz"])}


def sinifla(kural: dict, llm: dict) -> str:
    k, l_ = set(map(tuple, kural["ogeler"])), set(map(tuple, llm["ogeler"]))
    ko, lo = bool(kural.get("okunamayan")), bool(llm.get("okunamayan"))
    if llm.get("hata"):
        return "farklı"
    if not k and not l_:
        if ko and lo:
            return "ikisi_de_okuyamadi"
        if not ko and not lo:
            return "ikisi_de_bos"
        return "yalnız_llm" if lo else "yalnız_kural"         # biri isteği fark edip "uygulayamadım" dedi, öteki sessiz kaldı
    if k == l_ and ko == lo:
        return "aynı"
    if not k and l_:
        return "yalnız_llm"
    if k and not l_:
        return "yalnız_kural"
    return "farklı"


def kiyas(metin: str, t: dict, katalog_aday: dict | None, llm_sonuc: dict | None, pencereler: list[dict] | None = None,
          cati_kodlari: set[str] | None = None, y: dict | None = None) -> dict:
    """Tek cümle/mesaj için iki okuma ve sınıf. `llm_sonuc` yoksa sınıf 'llm_yok'."""
    kural = kural_okumasi(metin, t, katalog_aday, y)
    if llm_sonuc is None:
        return {"kural": kural, "llm": None, "sinif": "llm_yok"}
    if pencereler is None:
        pencereler = CO.pencere_adaylari(t, y)
    llm = llm_okumasi(llm_sonuc, pencereler, cati_kodlari or set())
    return {"kural": kural, "llm": llm, "sinif": sinifla(kural, llm)}
