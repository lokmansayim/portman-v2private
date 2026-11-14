"""İE-39: havuz evinde bayinin "sağa yarım pano uzat / kısalt" komutu.

Kural (D-90; Lokman, 14 Kasım 2026 09:29:42 UTC, karar kartı "Onaylıyor musunuz: dış duvar yarım pano kayar, o duvara değen odalar
uzar?" → "Doğru, işe başlansın"; seçenek metni "Veranda ya da çatı açıklığı değişen evde komut durur."). Kısaltma ve dört yön Lokman'ın
09:46:48 sözü. İlk dilim (kart 09:53:57 UTC, "Sağ ve ön, bugünkü kural"): yalnız sağ ve ön dış duvar; öteki duvarda ve kuralın tutmadığı
evde komut gerekçeyle durur (K21). Varsayımlar (Lokman'ın sözü değil, İE-39 › Varsayımlar): N yarım pano; kapı, pencere ve kayan duvardan
uzak panolar yerinde kalmazsa komut durur; mühürlü evde komut durur.

Kod yalnız İş Emri'ni değiştirir; planı Motor kurar (D-28: LLM yalnız okur; ölçüyü kod verir). Motor değişmez.

Çerçeveler: İş Emri'nin `konum_cm`, `ek_akslar_cm`, `girintiler`, dayanak, karkaslı pano ve sınır parçaları Motor çerçevesindedir (arka-solda
y arkadan); dikme, veranda, kubbe ve cumba uçları ve Motor'un kurduğu Plan gerçek çerçevededir (ön y = 0). Kayan duvarın bandındaki (dış
yüzden bir dış duvar kalınlığı) her değer duvarla birlikte kayar, öteki değerler yerinde kalır. Motor sayımı o duvardan başlıyorsa (sol;
arka-solda arka) duvar dışındaki her değer d kadar kayar: fiziksel olarak yine yalnız o duvar kayar.

Kullanım: python -m beyin.yarim_pano <İş Emri.json> --cephe sag --adim 1 <çıktı klasörü>
"""
from __future__ import annotations

import argparse, copy, io, json, math, re, shutil, sys, tempfile, contextlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G  # noqa: E402

MOD = G.MOD
YARIM = MOD / 2
TOL = 0.01
DILIM = ("sag", "on")                     # İE-39 ilk dilim (Lokman, kart 14 Kasım 2026 09:53:57 UTC)
CEPHE_ADI = {"sag": "sağ", "sol": "sol", "on": "ön", "arka": "arka"}
# Lokman'ın mühürlediği planlar (AGENTS.md › Mühürlü konular): bu evlerde komut yalnız Lokman'ın sözüyle açılır.
MUHURLU_EVLER = {"PA-01": "M-07", "PA-02": "M-07", "PA-03": "M-07", "PA-05": "M-07", "PA-22": "M-12"}
ACIK_MAHAL = tuple(sorted(G.ACIK_MAHAL_TURLERI))   # Motor'un açık mahal türleri (veranda, balkon, sundurma, teras)
ACIK_AD = ("VERANDA", "BALKON", "SUNDURMA", "TERAS")
YER_TOL = 0.05                            # yer kıyasında tolerans (cm): kaydırma yuvarlamadan önce yapılır
OLCU_TOLERANSI = 0.5                      # Motor'un dış ölçüyü tam panoya tamamlaması (D-30) en çok bu kadar sapabilir (cm)


class KomutDurdu(Exception):
    """Komut otomatik uygulanamaz. `kod` kısa neden (testler ve kayıt), `neden` Türkçe cümle (kayıt ve bayi mesajı, K21)."""

    def __init__(self, kod: str, neden: str):
        super().__init__(neden)
        self.kod = kod
        self.neden = neden


# ---------------------------------------------------------------- yardımcılar

def _arka_sol(ie: dict) -> bool:
    return ((ie["yapi"].get("dizilim") or {}).get("baslangic", "on-sol")) == "arka-sol"


def yan(cephe: str, ie: dict) -> tuple[str, str, str]:
    """Cephe → (eksen, Motor çerçevesinde kenar 'min' | 'max', gerçek çerçevede kenar 'min' | 'max')."""
    ayna_y = _arka_sol(ie)
    if cephe == "sag":
        return "x", "max", "max"
    if cephe == "sol":
        return "x", "min", "min"
    if cephe == "on":
        return "y", ("max" if ayna_y else "min"), "min"
    if cephe == "arka":
        return "y", ("min" if ayna_y else "max"), "max"
    raise KomutDurdu("cephe", f"bilinmeyen cephe: {cephe}")


def _t_dis(ie: dict) -> float:
    return float((ie["yapi"].get("duvar_kalinligi_cm") or {}).get("dis", 10.0))


def _ilk_aks(ie: dict, eksen: str) -> float:
    t = _t_dis(ie)
    return t if eksen == ie["yapi"].get("kisa_kenar", "x") else t / 2.0


def kaydirici(L: float, kenar: str, t: float, d: float):
    """Tek eksende değer eşlemesi: L eski dış ölçü, kenar 'min' | 'max', t dış duvar kalınlığı, d kayma (cm)."""
    if kenar == "max":
        return lambda v: round(float(v) + d, 4) if float(v) >= L - t - TOL else float(v)
    return lambda v: float(v) if float(v) <= t + TOL else round(float(v) + d, 4)


def _tr(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _sessiz_kur(ie: dict):
    with contextlib.redirect_stdout(io.StringIO()):
        return G.kur(ie)


# ---------------------------------------------------------------- İş Emri dönüşümü

def kaydir(ie0: dict, cephe: str, d: float) -> tuple[dict, dict]:
    """İş Emri'nin `cephe` dış duvarını d cm kaydırır (d > 0 dışarı, d < 0 içeri). Dönüş: (yeni İş Emri, bilgi). Motor'u çağırmaz.
    Durma: oda kapanır ya da 125,5 / 4'ten daralır, veranda (balkon, teras) uzar ya da kısalır, kayan duvarda veranda / kubbe / cumba var,
    girinti, karkaslı pano ya da cumba açıklığı değişir."""
    ie = copy.deepcopy(ie0)
    eksen, kenar_m, kenar_g = yan(cephe, ie)
    i0, i1 = (0, 2) if eksen == "x" else (1, 3)
    t = _t_dis(ie)
    yapi = ie["yapi"]
    L = float(yapi["dis_olcu_cm"][eksen])
    km = kaydirici(L, kenar_m, t, d)                    # Motor çerçevesi
    kg = kaydirici(L, kenar_g, t, d)                    # gerçek çerçeve
    bilgi = {"cephe": cephe, "d": d, "uzayan": [], "kayan_ek_akslar": []}

    # 1) mahaller: duvara değen kenar kayar, o oda uzar (ya da kısalır)
    for m in ie["mahaller"]:
        if "konum_cm" not in m:
            raise KomutDurdu("konum", f"{m.get('ad', '?')} odasının yeri santimle yazılı değil")
        yeni = []
        for r in m["konum_cm"]:
            r2 = list(r)
            r2[i0], r2[i1] = km(r[i0]), km(r[i1])
            if r2[i1] - r2[i0] < MOD / 4:
                raise KomutDurdu("oda", f"{m['ad']} {_tr(r2[i1] - r2[i0])} cm'ye iner")
            yeni.append(r2)
        if any(abs((b[i1] - b[i0]) - (a[i1] - a[i0])) > TOL for a, b in zip(m["konum_cm"], yeni)):
            acik = m.get("tur") in ACIK_MAHAL or any(k in m["ad"].upper() for k in ACIK_AD)
            if acik:
                raise KomutDurdu("veranda", f"{m['ad']} kayan duvara değiyor; veranda uzamaz")
            bilgi["uzayan"].append({"ad": m["ad"], "tur": m.get("tur")})
        m["konum_cm"] = yeni

    # 2) dış ölçü ve ızgara
    yapi["dis_olcu_cm"][eksen] = round(L + d, 4)
    bas = _ilk_aks(ie, eksen)
    son = L + d - bas
    yapi["grid"][f"{eksen}_pano"] = math.ceil((son - bas) / YARIM - 1e-6) / 2.0

    # 3) Motor çerçevesindeki öteki değerler
    ek = yapi.get("ek_akslar_cm") or {}
    for anahtar in (eksen, f"{eksen}_yardimci"):
        if ek.get(anahtar):
            yeni = [km(v) for v in ek[anahtar]]
            bilgi["kayan_ek_akslar"] += [(anahtar, a, b) for a, b in zip(ek[anahtar], yeni) if abs(a - b) > TOL]
            ek[anahtar] = yeni
    diz = yapi.get("dizilim") or {}
    for dy in diz.get("dis_pano_dayanagi") or []:
        if eksen in dy:
            dy[eksen] = km(dy[eksen])
            dy["aralik_cm"] = [km(v) for v in dy["aralik_cm"]]
        elif "duvar_cm" in dy:
            dy["duvar_cm"] = km(dy["duvar_cm"])
    for kp in diz.get("karkasli_panolar") or []:
        if kp["yon"] == eksen:
            eski = list(kp["aralik_cm"])
            kp["aralik_cm"] = [km(v) for v in kp["aralik_cm"]]
            if abs((kp["aralik_cm"][1] - kp["aralik_cm"][0]) - (eski[1] - eski[0])) > TOL:
                raise KomutDurdu("karkasli", "kayan duvara değen karkaslı pano uzar")
            if kp.get("aciklik_ortasi_cm"):
                kp["aciklik_ortasi_cm"] = [None if v is None else km(v) for v in kp["aciklik_ortasi_cm"]]
        else:
            kp["eksen_cm"] = km(kp["eksen_cm"])
    for k_ in diz.get("kose_uzayan") or []:
        k_[eksen] = km(k_[eksen])
    j = 0 if eksen == "x" else 1
    for b in yapi.get("birlesimler") or []:
        if "nokta_cm" in b:
            b["nokta_cm"][j] = km(b["nokta_cm"][j])
    for g in ie.get("girintiler") or []:
        e = list(g)
        g[i0], g[i1] = km(g[i0]), km(g[i1])
        if abs((g[i1] - g[i0]) - (e[i1] - e[i0])) > TOL:
            raise KomutDurdu("girinti", "kayan duvara değen girinti uzar")
    for anahtar in ("acik_sinirlar", "duvarli_sinirlar"):
        for s in ie.get(anahtar) or []:
            if isinstance(s, dict) and s.get("parca_cm") and eksen in s["parca_cm"]:
                p = s["parca_cm"]
                p[eksen] = [km(v) for v in p[eksen]] if isinstance(p[eksen], list) else km(p[eksen])

    # 4) gerçek çerçevedeki değerler
    ie["dikmeler"] = [[kg(p[0]) if j == 0 else p[0], kg(p[1]) if j == 1 else p[1]] for p in ie.get("dikmeler") or []]
    boyuna = ("on", "arka") if eksen == "x" else ("sol", "sag")
    for v in ie.get("verandalar") or []:
        if v.get("cephe") == cephe:
            raise KomutDurdu("veranda", f"kayan duvarda {v.get('ad') or 'veranda'} var")
        if v.get("cephe") in boyuna:
            b0, b1 = kg(v["bas_cm"]), kg(v["bit_cm"])
            if abs((b1 - b0) - (float(v["bit_cm"]) - float(v["bas_cm"]))) > TOL:
                raise KomutDurdu("veranda", f"{v.get('ad') or 'veranda'} kayan duvara değiyor; veranda uzamaz")
            v["bas_cm"], v["bit_cm"] = b0, b1
    for kb in ie.get("kubbeler") or []:
        if kb.get("cephe") == cephe:
            raise KomutDurdu("kubbe", "kayan duvarda kubbe var")
        if kb.get("cephe") in boyuna:
            kb["bas_cm"] = kg(kb["bas_cm"])
    cati = ie.get("cati") or {}
    for c in cati.get("cumbalar") or []:
        if c.get("cephe") == cephe:
            raise KomutDurdu("cumba", "kayan duvarda cumba var")
        if c.get("cephe") in boyuna:
            b0, b1 = kg(c["bas_cm"]), kg(c["bit_cm"])
            if abs((b1 - b0) - (float(c["bit_cm"]) - float(c["bas_cm"]))) > TOL:
                raise KomutDurdu("cumba", "cumbanın açıklığı değişir")
            c["bas_cm"], c["bit_cm"] = b0, b1
    yy = cati.get("yan_yana_cumbalar")
    if yy and "bolme_cm" in yy and yy.get("cephe") in boyuna:
        yy["bolme_cm"] = kg(yy["bolme_cm"])
    return ie, bilgi


# ---------------------------------------------------------------- açıklıklar: yer korunur

def _eslesen(plan, ac: dict) -> list:
    """İş Emri açıklığının Plan'daki yeri: [(duvar yönü, duvar ekseni, açıklık ortası)]."""
    out = []
    for p in plan.panolar:
        for a in p.aciklar:
            if a.tur != ac["tur"] or (str(a.olcu) != str(ac["olcu"]) and str(a.olcu).replace("/", "x") != str(ac["olcu"])):
                continue
            if "arasi" in ac:
                if not a.arasi or set(a.arasi) != set(ac["arasi"]):
                    continue
            elif a.mahal != ac.get("mahal"):
                continue
            if a.pano_is_emri != ac.get("pano"):
                continue
            b0, b1 = p.bosluk(a)
            out.append((p.duvar.yon, round(p.duvar.c, 2), round((b0 + b1) / 2, 2)))
    return out


def _aday_sayisi(ie: dict, i: int) -> int | None:
    """Açıklığın aday pano sayısı (Motor'un hata iletisinden; `beyin/varyant._aday_sayisi` gibi)."""
    dene = copy.deepcopy(ie)
    dene["acikliklar"][i]["pano"] = 999
    try:
        _sessiz_kur(dene)
    except G.IsEmriHatasi as e:
        m = re.search(r"\(aday (\d+)\)", str(e))
        return int(m.group(1)) if m else None
    return None


def dizinleri_esle(ie0: dict, ie1: dict, p0, cephe: str, d: float) -> tuple[dict, list]:
    """Pano dizinle yazılmış her açıklık için yeni İş Emri'nde yeri eskisine (kayan bantta d kadar ötesine) en yakın panoyu seçer.
    Dönüş: (İş Emri, [(açıklık, kayma cm)]); kayma > 0,5 cm olanlar yer korunamadı demektir."""
    eksen, _km, kenar_g = yan(cephe, ie0)
    L = p0.W if eksen == "x" else p0.H
    kg = kaydirici(L, kenar_g, _t_dis(ie0), d)
    ie = copy.deepcopy(ie1)
    kaymalar = []
    for i, ac in enumerate(ie0["acikliklar"]):
        if ac.get("pano") is None:
            continue
        e0 = _eslesen(p0, ac)
        if len(e0) != 1:
            continue
        yon, c, m = e0[0]
        bek = (yon, kg(c) if yon != eksen else c, kg(m) if yon == eksen else m)
        n = _aday_sayisi(ie, i)
        if n is None:
            continue
        dene = copy.deepcopy(ie)
        en_iyi = None
        for k in range(n):
            dene["acikliklar"][i]["pano"] = k
            try:
                pk = _sessiz_kur(dene)
            except G.IsEmriHatasi:
                continue
            e1 = _eslesen(pk, {**ac, "pano": k})
            if len(e1) != 1 or e1[0][0] != yon or abs(e1[0][1] - bek[1]) > 1:
                continue
            fark = abs(e1[0][2] - bek[2])
            if en_iyi is None or fark < en_iyi[1] - 1e-6:
                en_iyi = (k, fark)
        if en_iyi is not None:
            ie["acikliklar"][i]["pano"] = en_iyi[0]
            if en_iyi[1] > OLCU_TOLERANSI:
                kaymalar.append((_aciklik_adi(ac), round(en_iyi[1], 2)))
    return ie, kaymalar


def _aciklik_adi(ac: dict) -> str:
    yer = ac.get("mahal") or "–".join(ac.get("arasi", []))
    return f"{ac['tur']} {ac['olcu']} {yer}"


def aciklik_yerleri(plan) -> list:
    """Plan'daki kapı ve pencerelerin yerleri (kubbe dışı): (tür, ölçü, menteşe, duvar yönü, duvar ekseni, açıklık ortası); yuvarlanmaz."""
    out = []
    for p in plan.panolar:
        for ac in p.aciklar:
            if ac.tur == "kubbe":
                continue
            b0, b1 = p.bosluk(ac)
            out.append((ac.tur, str(ac.olcu), ac.mentese, p.duvar.yon, float(p.duvar.c), (b0 + b1) / 2))
    return out


def _esle(bek: list, var: list) -> tuple[list, list]:
    """İki yer listesini eşler: ilk dört alan aynı, iki sayı `YER_TOL` içinde. Dönüş: (eşlenmeyen beklenen, eşlenmeyen var)."""
    kalan = list(var)
    eksik = []
    for k in bek:
        for i, v in enumerate(kalan):
            if k[:4] == v[:4] and abs(k[4] - v[4]) <= YER_TOL and abs(k[5] - v[5]) <= YER_TOL:
                del kalan[i]
                break
        else:
            eksik.append(k)
    return eksik, kalan


def aciklik_farki(p0, p1, eksen: str, kenar_g: str, d: float, t: float) -> list:
    """Kayan duvarın bandı dışındaki her açıklık yerinde mi (bandındakiler d kadar kaymış mı), menteşesi aynı mı? Yerinde olmayanlar."""
    L = p0.W if eksen == "x" else p0.H
    kg = kaydirici(L, kenar_g, t, d)
    bek = [(tur, olcu, me, yon, c, kg(m)) if yon == eksen else (tur, olcu, me, yon, kg(c), m)
           for tur, olcu, me, yon, c, m in aciklik_yerleri(p0)]
    eksik, fazla = _esle(bek, aciklik_yerleri(p1))
    return sorted({f"{k[0]} {k[1]}" for k in eksik + fazla})


# ---------------------------------------------------------------- çatı ve panolar

def cati_acikliklari(plan, ie: dict) -> list:
    """Çatı şeritlerinin makas açıklıkları (cm; `motor/cati_serit.seritler`)."""
    from motor import cati_serit as CS
    with contextlib.redirect_stdout(io.StringIO()):
        sr = CS.seritler(CS.cati_izi(plan, ie), ie)
    return [round(b1 - b0, 2) for _a0, _a1, b0, b1 in sr]


def _otele(r: tuple, eksen: str, v: float) -> tuple:
    if eksen == "x":
        return (r[0] + v, r[1], r[2] + v, r[3])
    return (r[0], r[1] + v, r[2], r[3] + v)


def _var_mi(r: tuple, kume: list) -> bool:
    return any(all(abs(a - b) <= YER_TOL for a, b in zip(r, k)) for k in kume)


def pano_siniflari(p0, p1, eksen: str, kenar_g: str, d: float) -> tuple[dict, dict]:
    """Panolar: 'ayni' (yeri ve boyu aynı), 'kaydi' (duvarla birlikte d kadar kaydı), 'degisti' (boyu ya da yeri değişti; sonrakinde
    yeni, öncekinde kalkan). Dönüş: (sonraki planın sınıfları, önceki planın sınıfları), pano id → sınıf. Plan gerçek çerçevededir: önde
    (gerçek çerçevede en küçük kenar) yerinde kalan panoların koordinatı d kadar artar. Kaydırma yuvarlamadan önce, kıyas `YER_TOL` ile."""
    sabit = d if kenar_g == "min" else 0.0
    kayan = 0.0 if kenar_g == "min" else d
    once = [tuple(p.rect()) for p in p0.panolar]
    sonra = [tuple(p.rect()) for p in p1.panolar]
    o_sabit = [_otele(r, eksen, sabit) for r in once]
    o_kayan = [_otele(r, eksen, kayan) for r in once]
    # Eşleme birebir (PR-2): her önceki pano en çok bir sonraki panoyla eşleşir; önce yerinde kalanlar, sonra kayanlar. Tam pano (125,5)
    # kaymada yeni pano komşusunun kaymış kopyasına benzer; birebir eşlemede yeni pano "degisti" (pembe) olur, sayılar tutar.
    def _bul(r, adaylar, kullanilan):
        return next((i for i, k in enumerate(adaylar) if i not in kullanilan and all(abs(a - b) <= YER_TOL for a, b in zip(r, k))), None)
    s1, s0 = {}, {}
    kullanilan: set[int] = set()
    eslesme: dict[int, tuple[int, str]] = {}
    for j, r in enumerate(sonra):
        i = _bul(r, o_sabit, kullanilan)
        if i is not None:
            kullanilan.add(i)
            eslesme[j] = (i, "ayni")
    for j, r in enumerate(sonra):
        if j in eslesme:
            continue
        i = _bul(r, o_kayan, kullanilan)
        if i is not None:
            kullanilan.add(i)
            eslesme[j] = (i, "kaydi")
    onceki_sinif = {i: s for i, s in eslesme.values()}
    for j, p in enumerate(p1.panolar):
        s1[id(p)] = eslesme[j][1] if j in eslesme else "degisti"
    for i, p in enumerate(p0.panolar):
        s0[id(p)] = onceki_sinif.get(i, "degisti")
    return s1, s0


def bant_disi_degisen(p1, siniflar: dict, eksen: str, kenar_g: str, d: float, t: float) -> list:
    """Kayan duvardan uzakta (dış yüzden dış duvar + 2 pano + uzama) boyu ya da yeri değişen panolar: kural "öteki duvarlar yerinde"."""
    L1 = p1.W if eksen == "x" else p1.H
    bant = t + 2 * MOD + max(d, 0.0) + 1.0
    out = []
    for p in p1.panolar:
        if siniflar.get(id(p)) != "degisti":
            continue
        x0, y0, x1, y1 = p.rect()
        a0, a1 = (x0, x1) if eksen == "x" else (y0, y1)
        uzaklik = (L1 - a1) if kenar_g == "max" else a0
        if uzaklik > bant:
            out.append(p)
    return out


def ozel_artik(ie: dict, cephe: str) -> float:
    """Kayan duvarın ucunda 62,75 ızgarasından artan özel parça (cm). Lokman, 14 Kasım 2026 kart 14:57:40 UTC ("Seçin: 85 m² evde
    'sağa yarım pano uzat' sonrası dış ölçü kaç olsun?" → "1202,25 cm, 26,5 silinir"; 13:24 sözü "bayi 62,75 eklerse kalan 26,5 panoyu
    sil"): komut önce bu parçayı siler, duvar 62,75 ızgarasına oturur, sonra adım eklenir. Koşu = dış ölçü − 2 × ilk aks; ızgaraya
    `OLCU_TOLERANSI`'ndan yakın eksik ızgarada sayılır (dönüş eksi: Motor'un D-30 tamamlaması gibi). Motor dizilimi kayan kenarın
    öbür ucundan başlıyorsa (önde `on-sol`) artık kayan duvarda değildir: 0."""
    eksen, kenar_m, _kenar_g = yan(cephe, ie)
    if kenar_m != "max":
        return 0.0
    kosu = float(ie["yapi"]["dis_olcu_cm"][eksen]) - 2 * _ilk_aks(ie, eksen)
    k = math.floor((kosu + OLCU_TOLERANSI) / YARIM)
    return round(kosu - k * YARIM, 4)


def dizilim_izi(plan) -> list:
    """Planın pano dizilimi: (duvar yönü, duvar ekseni, a0, a1), sıralı; iki planın dizilimi aynı mı kıyası için."""
    return sorted((p.duvar.yon, round(p.duvar.c, 2), round(p.a0, 2), round(p.a1, 2)) for p in plan.panolar)


def tek_pano(ie0: dict, ie1: dict, p0, p1, kaymalar: list, cephe: str, d: float):
    """Lokman, 14 Kasım 2026 13:12–13:24 UTC: duvarda 125,5'ler çıkar, kalan tek parça son (özel) panodur; özel durum yokken 62,75
    bölünmez ("62,75 ile 89,25 tek pano haline gelir … 125,5 + 26,5 olur"; aynı akstaki iç duvar da). Komutun çıktısında İş Emri'nin
    `dizilim.son_pano: son_aks`ı (kesilmiş son panonun önünde yarım pano) `kosu` olur. Dizilim değişmiyorsa İş Emri aynen kalır
    (onaylı örnek bayt bayt). Dönüş: (İş Emri, Plan, kaymalar)."""
    if ((ie1["yapi"].get("dizilim") or {}).get("son_pano")) != "son_aks":
        return ie1, p1, kaymalar
    ie_k = copy.deepcopy(ie1)
    ie_k["yapi"]["dizilim"]["son_pano"] = "kosu"
    try:
        ie_k, kay_k = dizinleri_esle(ie0, ie_k, p0, cephe, d)
        p_k = _sessiz_kur(ie_k)
    except Exception as e:
        raise KomutDurdu("motor", f"tek pano dizilimi kurulamadı: {str(e)[:120]}")
    if dizilim_izi(p_k) == dizilim_izi(p1):
        return ie1, p1, kaymalar
    return ie_k, p_k, kay_k


# ---------------------------------------------------------------- komut

def uygula(ie0: dict, cephe: str, adim: int) -> dict:
    """Bayinin komutu: `cephe` dış duvarı `adim` yarım pano (62,75 cm) kayar; adim > 0 uzat, adim < 0 kısalt. Önce duvarın ucundaki
    özel parça silinir (`ozel_artik`; 85 m² evde 26,5 cm): sağa 1 yarım pano 1166 → 1202,25 cm.
    Dönüş: {is_emri, once, sonra, d, d_motor, uzayan, alanlar, siniflar, sayilar, notlar}. Kural tutmazsa KomutDurdu (K21)."""
    if not isinstance(adim, int) or adim == 0:
        raise KomutDurdu("adim", "yarım pano sayısı sıfırdan farklı bir tam sayı olmalı")
    if cephe not in CEPHE_ADI:
        raise KomutDurdu("cephe", f"bilinmeyen cephe: {cephe}")
    if cephe not in DILIM:
        raise KomutDurdu("dilim", f"{CEPHE_ADI[cephe]} duvar için komut henüz yok; bugün yalnız sağ ve ön duvar")
    ev = ie0["yapi"].get("referans_model")
    if ev in MUHURLU_EVLER:
        raise KomutDurdu("muhur", f"{ev} planı Lokman'ın onayıyla mühürlü ({MUHURLU_EVLER[ev]})")
    if ie0["yapi"].get("sistem") != "prefabrik":
        raise KomutDurdu("sistem", "komut yalnız prefabrik evde")
    silinen = ozel_artik(ie0, cephe)
    d = round(adim * YARIM - silinen, 4)              # kayan duvarın ucundaki özel parça silinir, sonra adım (Lokman, kart 14:57:40)
    eksen, _kenar_m, kenar_g = yan(cephe, ie0)
    t = _t_dis(ie0)
    try:
        p0 = _sessiz_kur(ie0)
    except Exception as e:
        raise KomutDurdu("motor", f"evin planı kurulamadı: {str(e)[:120]}")
    ie1, bilgi = kaydir(ie0, cephe, d)
    try:
        ie1, kaymalar = dizinleri_esle(ie0, ie1, p0, cephe, d)
        p1 = _sessiz_kur(ie1)
        ie1, p1, kaymalar = tek_pano(ie0, ie1, p0, p1, kaymalar, cephe, d)
    except KomutDurdu:
        raise
    except Exception as e:
        raise KomutDurdu("motor", f"yeni plan kurulamadı: {str(e)[:120]}")
    if kaymalar:
        raise KomutDurdu("aciklik", "kapı ya da pencere yerinde kalmıyor: " + ", ".join(a for a, _k in kaymalar))
    try:
        a0, a1 = cati_acikliklari(p0, ie0), cati_acikliklari(p1, ie1)
    except Exception as e:
        raise KomutDurdu("cati", f"çatı açıklığı okunamadı: {str(e)[:120]}")
    if a0 != a1:
        raise KomutDurdu("cati", f"çatı açıklığı değişir ({' / '.join(_tr(v) for v in a0)} → {' / '.join(_tr(v) for v in a1)} cm)")
    d_motor = round((p1.W - p0.W) if eksen == "x" else (p1.H - p0.H), 4)
    notlar = []
    if abs(d_motor - d) > OLCU_TOLERANSI:
        raise KomutDurdu("olcu", f"Motor dış ölçüyü {_tr(d)} yerine {_tr(d_motor)} cm değiştirdi")
    if abs(d_motor - d) > TOL:
        notlar.append(f"Motor son panoyu tam panoya tamamladı (D-30): dış ölçü {_tr(d)} yerine {_tr(d_motor)} cm değişti")
    fark = aciklik_farki(p0, p1, eksen, kenar_g, d_motor, t)
    if fark:
        raise KomutDurdu("aciklik", "kapı ya da pencere yerinde kalmıyor: " + ", ".join(fark))
    siniflar, siniflar_once = pano_siniflari(p0, p1, eksen, kenar_g, d_motor)
    uzak = bant_disi_degisen(p1, siniflar, eksen, kenar_g, d_motor, t)
    if uzak:
        raise KomutDurdu("dizilim", f"kayan duvardan uzakta {len(uzak)} pano değişir; öteki duvarlar yerinde kalmıyor")
    alan0 = {m.ad: round(m.alan_m2, 2) for m in p0.mahaller.values()}
    alan1 = {m.ad: round(m.alan_m2, 2) for m in p1.mahaller.values()}
    acik_degisen = [m.ad for m in p1.mahaller.values() if m.acik and alan1.get(m.ad) != alan0.get(m.ad)]
    if acik_degisen:                                 # Motor'un açık mahali (veranda, balkon, sundurma, teras) uzamaz (D-90)
        raise KomutDurdu("veranda", f"{', '.join(acik_degisen)} kayan duvara değiyor; veranda uzamaz")
    yon = "uzadı" if adim > 0 else "kısaldı"
    ie1["revizyon"] = int(ie0.get("revizyon") or 1) + 1
    ie1["varsayimlar"] = list(ie0.get("varsayimlar") or []) + [
        f"Bayi komutu (İE-39): {CEPHE_ADI[cephe]} dış duvar {abs(adim)} yarım pano {yon}"
        + (f" (uçtaki {_tr(silinen)} cm özel pano silindi; duvar {_tr(abs(d))} cm kaydı)" if silinen > TOL else f" ({_tr(abs(d))} cm)") + "; "
        f"dış ölçü {_tr(p0.W)} × {_tr(p0.H)} → {_tr(p1.W)} × {_tr(p1.H)} cm; "
        f"değişen odalar: {', '.join(u['ad'] for u in bilgi['uzayan']) or 'yok'}."]
    return {"is_emri": ie1, "once": p0, "sonra": p1, "cephe": cephe, "adim": adim, "d": d, "d_motor": d_motor,
            "silinen": silinen if silinen > TOL else 0.0,
            "eksen": eksen, "kenar": kenar_g,
            "uzayan": [{"ad": u["ad"], "once_m2": alan0.get(u["ad"]), "sonra_m2": alan1.get(u["ad"])} for u in bilgi["uzayan"]],
            "kayan_ek_akslar": bilgi["kayan_ek_akslar"], "siniflar": siniflar, "siniflar_once": siniflar_once,
            "sayilar": {"once": len(p0.panolar), "sonra": len(p1.panolar), **Counter(siniflar.values())},
            "dis_olcu": {"once": [p0.W, p0.H], "sonra": [p1.W, p1.H]}, "notlar": notlar}


def ozet(s: dict) -> dict:
    """`uygula` sonucunun JSON'a yazılabilir özeti (Plan nesneleri olmadan)."""
    return {k: v for k, v in s.items() if k not in ("is_emri", "once", "sonra", "siniflar", "siniflar_once")}


def uret(ie0: dict, cephe: str, adim: int, hedef: Path, govde: str | None = None) -> dict:
    """Komutu uygular; yeni İş Emri'ni, önce/sonra pano dizilimini ve ön onay çizimini (`motor/dxf_out.uret`, K23) yazar.
    Çizim doğrulaması geçmezse KomutDurdu('cizim')."""
    from motor import dxf_out, dizilim_kiyas
    hedef = Path(hedef)
    hedef.mkdir(parents=True, exist_ok=True)
    s = uygula(ie0, cephe, adim)
    ie1 = s["is_emri"]
    govde = govde or f"{(ie0['yapi'].get('referans_model') or 'EV').replace('-', '')}_{cephe}_{'arti' if adim > 0 else 'eksi'}{abs(adim)}"
    with tempfile.TemporaryDirectory() as td:            # K23: doğrulama geçmeden hedefe hiçbir dosya yazılmaz
        with contextlib.redirect_stdout(io.StringIO()):
            m = dxf_out.uret(ie1, Path(td) / "cizim", ad_govde=govde)
        if not m.get("validation_passed"):
            raise KomutDurdu("cizim", "yeni planın çizim doğrulaması geçmedi")
        shutil.copytree(Path(td) / "cizim", hedef / "cizim", dirs_exist_ok=True)
    (hedef / f"{govde}_is_emri.json").write_text(json.dumps(ie1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    yon = "uzat" if adim > 0 else "kısalt"
    baslik = f"Sonra · {CEPHE_ADI[cephe]} duvar {abs(adim)} yarım pano {yon}"
    dizilim_kiyas.once_sonra(s["once"], s["sonra"], s["siniflar"], hedef / f"{govde}_once_sonra.png", baslik,
                             kayma=s["d_motor"], eksen=s["eksen"], kenar=s["kenar"], siniflar_once=s["siniflar_once"])
    from motor import bayi_gorseli as BG
    v = json.loads((hedef / "cizim" / "validation.json").read_text(encoding="utf-8"))
    with contextlib.redirect_stdout(io.StringIO()):
        BG.plan_gorseli(ie1, hedef / f"{govde}_plan_bayi.png", v)
    oz = {**ozet(s), "dosyalar": {"is_emri": f"{govde}_is_emri.json", "once_sonra": f"{govde}_once_sonra.png",
                                  "plan_bayi": f"{govde}_plan_bayi.png", "pdf": f"cizim/{m.get('pdf')}",
                                  "dxf": f"cizim/{m.get('dxf')}"}}
    (hedef / f"{govde}_ozet.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return oz


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Havuz evinde dış duvarı yarım pano uzat ya da kısalt (İE-39).")
    ap.add_argument("is_emri", type=Path)
    ap.add_argument("hedef", type=Path)
    ap.add_argument("--cephe", required=True, choices=sorted(CEPHE_ADI))
    ap.add_argument("--adim", required=True, type=int, help="yarım pano sayısı; artı uzat, eksi kısalt")
    ap.add_argument("--govde", default=None)
    a = ap.parse_args(argv)
    ie0 = json.loads(a.is_emri.read_text(encoding="utf-8"))
    try:
        oz = uret(ie0, a.cephe, a.adim, a.hedef, a.govde)
    except KomutDurdu as e:
        print(json.dumps({"durdu": e.kod, "neden": e.neden}, ensure_ascii=False))
        return 2
    print(json.dumps(oz, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
