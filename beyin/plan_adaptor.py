"""İE-14 r3 · P1: ortak plan sözleşmesinin (`plan_sema.PlanSozlesmesi`, `portman.plan/0.1`) motor adaptörleri.

İki motor birleşmez (Lokman, 14.10.2026): pano motoru (`motor/`, P6001) ve genel motor (`motor/genel/`) olduğu gibi kalır; sözleşme ikisinin
üstünde durur, adaptörler çevirir.
- Çelik, yazma: sözleşme → Yapı Tanımı 0.5 (`motor/genel/plan_derle.derle`).
- Çelik, okuma: Yapı Tanımı → sözleşme (`plan_sema.tanimdan`; 5 cm sapma düzeltmesiyle).
- Prefabrik, okuma (prototip): İş Emri (pano birimli `konum_pano`, mahal + duvar açıklıkları) → sözleşme. Ölçüler pano aksından
  (× 125,5 cm); dış yüz ölçüsü motorun kuralıdır (dış düşey duvar aks dışında vb.), sözleşmeye girmez. Yazma yönü yok (14a dışı).

`denetle`: aileden bağımsız sözleşme denetimi — şema, döşeme (boşluksuz ve örtüşmesiz), oda programı, kapılarla erişim, açıklıkların
mahali. Çelikte ayrıca tam plan denetimi (`plan_denetim.denetle`) koşar; o, derleme ve geometriyi de kapsar.
"""
from __future__ import annotations

from collections import deque

from pydantic import ValidationError

from beyin.plan_sema import PlanSozlesmesi, cekirdek, sozlesme, tanimdan

PANO = 125.5                       # motor/geometry.py MOD (tam pano)
DUVAR_CEPHE = {"on": "G", "arka": "K", "sol": "B", "sag": "D"}
PREFABRIK_ISLEV = {"salon": "salon", "mutfak": "mutfak", "yatak_odasi": "yatak_odasi", "banyo": "banyo", "veranda": "veranda",
                   "antre_hol": "hol", "hol": "hol", "antre": "hol"}


# ── çelik ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def celik_oku(tanim: dict, yol: str = "banka") -> dict:
    """Bankadaki çelik Yapı Tanımı → sözleşme. Kaynak kodu iç kayıttır."""
    p = tanimdan(tanim)
    p.pop("gerekce", None)
    return sozlesme(p, "tek_kat_celik", {"yol": yol, "kod": tanim.get("kod")})


def celik_yaz(soz: dict, kod: str = "YENI", ad: str | None = None) -> dict:
    """Sözleşme → Yapı Tanımı 0.5 (genel motor girdisi). Geçersizse `plan_derle.PlanHatasi`."""
    from motor.genel.plan_derle import derle
    if soz["aile"] != "tek_kat_celik":
        raise ValueError(f"çelik adaptörü yalnız tek kat çelik yazar ({soz['aile']})")
    return derle(cekirdek(soz), kod=kod, ad=ad)


# ── prefabrik (okuma prototipi) ──────────────────────────────────────────────────────────────────────────────────────────
def prefabrik_oku(is_emri: dict) -> dict:
    """Prefabrik İş Emri → sözleşme (pano aksından cm). Tanınmayan mahal türü 'depo' sayılır ve varsayım olarak yazılır."""
    y = is_emri["yapi"]
    g = y["grid"]
    varsayim = ["ölçüler pano aksından (× 125,5 cm); dış yüz ölçüsü pano motorunun kuralıdır"]
    mahaller = []
    for m in is_emri["mahaller"]:
        islev = PREFABRIK_ISLEV.get(m.get("tur"))
        if islev is None:
            islev = "depo"
            varsayim.append(f"mahal türü '{m.get('tur')}' sözleşmede 'depo' sayıldı")
        e = {"ad": m["ad"], "islev": islev, "dikdortgenler": [[round(v * PANO, 2) for v in r] for r in m["konum_pano"]]}
        if islev == "veranda":
            e["ortu"] = "cati"
        mahaller.append(e)
    kapilar, pencereler = [], []
    for a in is_emri.get("acikliklar") or []:
        if a["tur"] == "pencere":
            pencereler.append({"mahal": a["mahal"], "cephe": DUVAR_CEPHE[a["duvar"]], "olcu": a["olcu"], "adet": 1})
        elif a["tur"] in ("dis_kapi", "ic_kapi", "gecis"):
            ara = list(a.get("arasi") or [])
            if len(ara) == 1:
                ara = ["dis"] + ara
            kapilar.append({"arasinda": ara})
    ct = is_emri.get("cati") or {}
    s = {"dis_olcu": {"en": round(g["x_pano"] * PANO, 2), "boy": round(g["y_pano"] * PANO, 2)}, "mahaller": mahaller,
         "kapilar": kapilar, "pencereler": pencereler,
         "cati": {"tip": ct.get("tip"), **({"egim_yuzde": ct["egim_yuzde"]} if ct.get("egim_yuzde") else {})} if ct else None,
         "acik_sinirlar": [list(x["arasi"]) for x in is_emri.get("acik_sinirlar") or []]}
    out = sozlesme(s, "tek_kat_prefabrik", {"yol": "prefabrik_is_emri", "kod": y.get("referans_model")}, varsayimlar=varsayim)
    out["olcu_kaynagi"] = "pano_aksi"
    return PlanSozlesmesi.model_validate(out).model_dump()


# ── aileden bağımsız sözleşme denetimi ───────────────────────────────────────────────────────────────────────────────────
def _doseme(soz: dict) -> list[str]:
    """Mahaller dış dikdörtgeni boşluksuz ve örtüşmesiz doldurur mu (ondalıklı ölçüde de: sıkıştırılmış koordinat ızgarası)."""
    W, H = soz["dis_olcu"]["en"], soz["dis_olcu"]["boy"]
    rs = [(m["ad"], r) for m in soz["mahaller"] for r in m["dikdortgenler"]]
    xs = sorted({0.0, float(W)} | {float(v) for _, r in rs for v in (r[0], r[2])})
    ys = sorted({0.0, float(H)} | {float(v) for _, r in rs for v in (r[1], r[3])})
    hata = []
    for _, r in rs:
        if r[0] < -1e-6 or r[1] < -1e-6 or r[2] > W + 1e-6 or r[3] > H + 1e-6 or r[2] <= r[0] or r[3] <= r[1]:
            hata.append(f"dikdörtgen dış ölçünün dışında ya da boş: {r}")
    bos, ust = 0.0, []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            kim = [ad for ad, r in rs if r[0] < cx < r[2] and r[1] < cy < r[3]]
            if not kim:
                bos += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
            elif len(set(kim)) > 1 or len(kim) > 1:
                ust.append(tuple(sorted(set(kim))))
    if bos > 1:
        hata.append(f"mahale ait olmayan boşluk {bos / 1e4:.2f} m²")
    for k in sorted(set(ust)):
        hata.append(f"örtüşme: {', '.join(k)}")
    return hata


def denetle(soz: dict, oda_programi: str | None = None) -> dict:
    """Aileden bağımsız denetim. Dönüş: {gecerli, kalemler: {sozlesme, doseme, program, erisim, aciklik: [ihlal]}}."""
    from beyin.plan_denetim import program_coz
    k = {"sozlesme": [], "doseme": [], "program": [], "erisim": [], "aciklik": []}
    try:
        soz = PlanSozlesmesi.model_validate(soz).model_dump()
    except ValidationError as e:
        k["sozlesme"] = [f"{'.'.join(str(x) for x in er['loc'])}: {er['msg']}" for er in e.errors()][:12]
        return {"gecerli": False, "kalemler": k}
    k["doseme"] = _doseme(soz)
    adlar = {m["ad"]: m["islev"] for m in soz["mahaller"]}
    if len(adlar) != len(soz["mahaller"]):
        k["sozlesme"].append("mahal adları tekil olmalı")
    prog = program_coz(oda_programi)
    say = {i: sum(1 for v in adlar.values() if v == i) for i in ("yatak_odasi", "salon", "banyo")}
    if prog and (say["yatak_odasi"], say["salon"]) != prog:
        k["program"].append(f"oda programı {prog[0]}+{prog[1]}, planda {say['yatak_odasi']}+{say['salon']}")
    if say["banyo"] < 1:
        k["program"].append("banyo yok")
    for pc in soz["pencereler"]:
        if pc["mahal"] not in adlar:
            k["aciklik"].append(f"pencere: '{pc['mahal']}' adlı mahal yok")
    ver = {a for a, i in adlar.items() if i == "veranda"}
    komsu: dict[str, set[str]] = {a: set() for a in adlar if a not in ver} | {"dis": set()}
    for kp in soz["kapilar"]:
        a, b = ["dis" if x in ver else x for x in (list(kp["arasinda"]) + ["", ""])[:2]]
        if a not in komsu or b not in komsu:
            k["aciklik"].append(f"kapı: {kp['arasinda']} tanınmayan mahal")
            continue
        komsu[a].add(b)
        komsu[b].add(a)
    for a, b in soz.get("acik_sinirlar") or []:
        if a in komsu and b in komsu:
            komsu[a].add(b)
            komsu[b].add(a)
    gor, q = {"dis"}, deque(["dis"])
    while q:
        u = q.popleft()
        for v in komsu[u]:
            if v not in gor:
                gor.add(v)
                q.append(v)
    k["erisim"] = [f"{a}: girişten kapılarla ulaşılamıyor" for a in komsu if a not in gor]
    return {"gecerli": not any(k.values()), "kalemler": k}
