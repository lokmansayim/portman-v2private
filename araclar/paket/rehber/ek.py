"""İE-17 PR-2 köşe kırması ve kubbe (63 m², AP-24): rehberin şablonunda (`sahne.js`) yeri olmayan parçalar, "ek parça" olarak.

Şablonun çatısı beşik yüzlerini kurar; köşe kırmasının tek eğimli mahal çatısı ve kubbe onun dışındadır. Bu parçalar rehbere iki
kaynaktan, kendi geometrileriyle gelir; rehber kendi geometrisini kurmaz (D-28 madde 1):

- **Kart modelinden** (`<kod>_model.ifc`, motorun 3B modeli): mahalin çatısının makasları (kısa ve çapraz makas, MA-06, MA-07), aşıkları,
  kaplaması, deresi ve inişleri; kubbenin pencereleri ve çatısı. Parça IFC'deki üçgenleriyle (`ifc_ucgen`) sahneye gelir.
- **Orijinal üretim çizimlerinden** (Lokman, 24 Kasım 2026 07:35:17: "Montaj Rehberlerinde bundan sonra orjinal üretim çizimleri
  dursun"): kubbenin çelik karkas duvarları, üst bandı ve makasları FrameBuilder dosyalarından (`araclar/uretim/veri/kubbe.json`, BK-76).
  Her çerçeve motorun kubbesindeki yerine (pano, bant, makas) oturtulur; çerçevenin kendi ölçüsü değişmez.
- **Çatı makasları da üretim çizimlerinden** (Lokman, 26 Kasım 2026 05:38:00 UTC: "… makasları yeniden üret doğru yerleşimde gerçek
  üretilecek makaslar olacak"): evin üretim dosyası `uretim_makaslari.json`'da kayıtlıysa ana, cumba, kısa ve çapraz makaslar
  `araclar/uretim/` çerçevelerinden çizilir; şablon makası ve kart modelinin makas üçgenleri çizilmez. Makasın yeri ve sayısı Motor'un
  çatı tanımındandır (`uretim_makaslari`); çerçeve adı ↔ yer eşlemesi kayıtta.

Veri biçimi (`sahne.js` › Ek parçalar): her parça {adim, sira, ad, kod, satir, mat} ve geometri olarak `mesh` ({v: [x, y, z, …] cm,
f: [i, j, k, …]}, plan çerçevesi) ya da `cubuk` ([x0, y0, z0, x1, y1, z1, en, derinlik, nx, ny, nz]: p→q boyunca kutu, derinlik n yönünde;
üretim makasının çubuğunda dört sayı daha: ağız yönü, sac, sırttan eksene uzaklık, dudak → dudaklı C kesit).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
URETIM = KOK / "araclar" / "uretim" / "veri" / "kubbe.json"
MAKAS_KAYDI = Path(__file__).with_name("uretim_makaslari.json")


def ifc_ozellik(ifc_yolu: Path, desen: str) -> dict[str, dict]:
    """Kart modelinde adı desene uyan parçaların bütün özellik setleri, tek sözlükte: {ad: {anahtar: değer}}."""
    import ifcopenshell
    import ifcopenshell.util.element as ue

    f = ifcopenshell.open(str(ifc_yolu))
    out = {}
    for p in f.by_type("IfcProduct"):
        if re.match(desen, p.Name or ""):
            d = {}
            for v in ue.get_psets(p).values():
                d.update({k: x for k, x in v.items() if k != "id"})
            out[p.Name] = d
    return out


def ifc_ucgen(ifc_yolu: Path, adlar: set[str]) -> dict[str, dict]:
    """Kart modelindeki parçaların üçgenleri (cm, plan çerçevesi): {ad: {v: [...], f: [...]}}."""
    import ifcopenshell
    import ifcopenshell.geom
    import numpy as np

    f = ifcopenshell.open(str(ifc_yolu))
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)
    out = {}
    for p in f.by_type("IfcProduct"):
        if (p.Name or "") not in adlar:
            continue
        s = ifcopenshell.geom.create_shape(st, p)
        v = (np.array(s.geometry.verts).reshape(-1, 3) * 100).round(2)
        out[p.Name] = {"v": [float(x) for x in v.reshape(-1)], "f": [int(i) for i in s.geometry.faces]}
    return out


def _birlesik(parcalar: list[dict]) -> dict:
    """Birden çok üçgen kümesini tek kümeye toplar."""
    v, f = [], []
    for p in parcalar:
        n = len(v) // 3
        v += p["v"]
        f += [i + n for i in p["f"]]
    return {"v": v, "f": f}


def _kaydir(m: dict, dz: float, dx: float = 0.0) -> dict:
    """Üçgen kümesini düşeyde (`dz`) ve x boyunca (`dx`) kaydırır (cm)."""
    if not dz and not dx:
        return m
    return {"v": [round(x + (dz if i % 3 == 2 else dx if i % 3 == 0 else 0.0), 2) for i, x in enumerate(m["v"])], "f": m["f"]}


def mahal(ifc_yolu: Path, mahal_adlari: set[str], ls, makassiz: bool = False, dz: float = 0.0, yuzsuz: bool = False,
          dx: dict | None = None) -> tuple[list[dict], set[str]]:
    """Köşe kırmasının parçaları kart modelinden. Dönen: (ek parçalar, şablonun atlaması gereken IFC adları). `makassiz`: makaslar
    üretim çizimlerinden gelir (`uretim_makaslari`), kart modelinin makas üçgenleri çizilmez. `dz`: aşık, kaplama, dere ve inişin
    düşey kayması (cm): kart modeli üst başlığı 10 cm derin çizer ve çatı parçalarını onun üstüne koyar; rehberde makasın üstü (aşık
    oturma yüzü) saçak ucunda duvar üstü + 0,25 + topuktur. `yuzsuz`: mahalin çatısı şablonun yüzüdür (`girinti._mahal_yuzleri`); aşık ve
    kaplama oradan çizilir, kart modelinin aşık ve kaplama üçgenleri çizilmez (dere ve iniş yine kart modelinden). `dx`: mahal adı → x
    boyunca kayma (cm; `mahal_kaymalari`): dere ve iniş makasın saçak ucuyla birlikte kayar."""
    if not mahal_adlari:
        return [], set()
    OZ = ifc_ozellik(ifc_yolu, r"^(MAKAS_\d+|ASIK_\d+|CATI_\d+|DERE_\d+|INIS_\d+)$")
    mahalde = lambda o: (o.get("CatiParcasi") or o.get("Cati") or o.get("Duzlem")) in mahal_adlari   # noqa: E731
    makaslar = sorted(n for n, o in OZ.items() if n.startswith("MAKAS_") and mahalde(o))
    import ifcopenshell
    f = ifcopenshell.open(str(ifc_yolu))
    uyeler = {mk: sorted(p.Name for p in f.by_type("IfcProduct") if (p.Name or "").startswith(mk + "_")) for mk in makaslar}
    tek = {n for n, o in OZ.items() if not n.startswith("MAKAS_") and mahalde(o)}
    U = ifc_ucgen(ifc_yolu, tek | ({u for us in uyeler.values() for u in us} if not makassiz else set()))
    mahal_adi = lambda o: o.get("CatiParcasi") or o.get("Cati") or o.get("Duzlem")                 # noqa: E731
    U = {n: (_kaydir(m, dz, (dx or {}).get(mahal_adi(OZ[n]), 0.0)) if n in tek else m) for n, m in U.items()}
    ek, sira = [], 0
    for mk in ([] if makassiz else makaslar):
        o = OZ[mk]
        kalem = o.get("BOMKalem", mk)
        ek.append({"adim": "makas", "sira": 100 + sira, "ad": kalem.split(" · ")[0], "kod": o.get("KartKodu"), "mat": "truss",
                   "mesh": _birlesik([U[u] for u in uyeler[mk] if u in U]),
                   "satir": [["Bu parça", f"{kalem} ({mk})"], ["Liste", ls(kalem)],
                             ["Kaynak", "yer ve sayı çatı tanımından (çizim, liste ve 3B modelle aynı); geometri kart modelinden"]]})
        sira += 1
    for n in sorted(tek):
        if yuzsuz and n.startswith(("ASIK_", "CATI_")):
            continue
        o = OZ[n]
        cati = o.get("Cati") or o.get("Duzlem")
        if n.startswith("ASIK_"):
            ek.append({"adim": "asik", "sira": 300 + sira, "ad": "Aşık (omega)", "kod": o.get("KartKodu"), "mat": "asik", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} · {n}"], ["Liste", ls("Aşık")], ["Kaynak", "kart modeli"]]})
        elif n.startswith("CATI_"):
            ek.append({"adim": "kaplama", "sira": 300 + sira, "ad": "Trapez sac", "kod": None, "mat": "roof", "mesh": U[n], "osb": True,
                       "satir": [["Bu parça", f"{cati} · tek eğimli yüz"], ["Liste", ls(f"Trapez sac · {cati}")],
                                 ["Kaynak", "kart modelinin çatı yüzeyi; levhalar ayrı gösterilmedi"]]})
        elif n.startswith("DERE_"):
            ek.append({"adim": "dere", "sira": 300 + sira, "ad": "Metal dere", "kod": o.get("KartKodu"), "mat": "gutter", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} saçağı · {n}"], ["Liste", ls("Metal dere")], ["Kaynak", "kart modeli"]]})
        elif n.startswith("INIS_"):
            ek.append({"adim": "dere", "sira": 300 + sira, "ad": "Metal dere inişi", "kod": o.get("KartKodu"), "mat": "gutter", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} · {n}"], ["Liste", ls("Metal dere inişi aparatı")], ["Kaynak", "kart modeli"]]})
        sira += 1
    return ek, tek | set(makaslar)


# ---------- çatı makasları: orijinal üretim çizimleri ----------
BOY_PAYI = 0.2              # cm: üretim çerçevesinin alt başlığı ile Motor'un makas boyu arasında izin verilen fark
MAHAL_DZ = 0.25 - 10.0      # cm: kart modeli makasın üstünü (aşık oturma yüzü) saçak ucunda duvar üstü + 20'de çizer (10 cm topuk + 10 cm
                            # derin üst başlık); üretim makasında ve şablonda duvar üstü + 0,25 + 10 (topuk). Köşe kırmasının aşığı,
                            # kaplaması, deresi ve inişi bu kadar iner; aşık üretim makasının üst başlığına oturur
DAYANAK_PAYI = 2.5          # cm: veranda makasının son ana makasın yüzüne otururken ekseni boyunca en çok kayması (63 m²: 1,24 ve 1,6)
YARIK_ARASI = 8.0           # cm: kalkan betopanında iki kesim arasında makasın eninden (sırt 80 mm) dar şerit kalmaz; kesimler birleşir


def uretim_esleme(ie: dict) -> dict | None:
    """Evin üretim makas kaydı (`uretim_makaslari.json`, İş Emri numarasıyla), çerçeveleri ve çubuğun gerçek kesiti (`kesit`); kayıt
    yoksa None (şablon makası)."""
    tum = json.loads(MAKAS_KAYDI.read_text(encoding="utf-8"))
    kayit = tum["evler"].get(str(ie.get("is_emri_no")))
    if kayit is None:
        return None
    yol = KOK / kayit["uretim"]
    girdi = json.loads(yol.with_name("girdi.json").read_text(encoding="utf-8"))
    # D-157: çapraz makas Motor'un plan boyundan yüksek uçta `uc_payi_mm` kadar kısa üretilir (üretim girdisi tek kaynak)
    return dict(kayit, kesit=tum["kesit"], cerceveler={f["cerceve"]: f for f in json.loads(yol.read_text(encoding="utf-8"))},
                uc_payi={m["ad"]: float(m.get("uc_payi_mm", 0.0)) / 10 for m in girdi["makaslar"]})


def _alt_baslik(fr: dict) -> float:
    """Çerçevenin alt başlığının boyu (cm): x = 0'dan başlayan, ekseni 27 mm'de yatay çubuk (`dis_olcu_mm` dış ölçüdür, boy değil)."""
    alt = [p for p in fr["parcalar"] if p["x1"] == 0 and p["y1"] == p["y2"] and abs(p["y1"] - p["kanat"] / 2) < 0.01]
    if len(alt) != 1:
        raise ValueError(f"{fr['cerceve']}: alt başlık bulunamadı ({len(alt)} aday)")
    return alt[0]["x2"] / 10


def _gercek_kesit(KS: dict, p: dict) -> dict:
    """Çubuğun gerçek kesiti (`uretim_makaslari.json` › `kesit`): kanat ve dudak, mm. Kayıtta olmayan kesitle rehber kurulmaz."""
    k = KS.get(f"{p['kesit']}{p['sirt']:g}")
    if k is None or p["yon"] not in ("LABEL_NRM", "LABEL_INV"):
        raise ValueError(f"üretim makası {p['ad']}: kesit {p['kesit']} {p['sirt']:g}, etiket {p['yon']}; rehber kayıtlı C kesiti ve iki etiket yönünü çizer")
    return k


def _uc_tasmasi(fr: dict, KS: dict, bastan: bool) -> float:
    """Çerçevenin yüksek ucunda çubukların alt başlığın ucundan taşması (cm, ≥ 0): `bastan` ise uç x = 0'dadır (kısa makas), değilse
    alt başlığın öteki ucundadır (çapraz makas). Çubuğun düzlemdeki dört köşesinden, gerçek kesitle: sırt eksenden `kanat / 2` (27 mm),
    ağız kenarı öteki yanda `gerçek kanat − kanat / 2` (18 mm); yan `_makas_cubuklari`'ndaki ağız yönüyle aynı. 63 m²'de taşan parça üst
    başlığın ağız köşesidir (kalıp: `araclar/uretim/makas.py` › `YUKSEK_UCU`)."""
    xs = []
    for p in fr["parcalar"]:
        k = _gercek_kesit(KS, p)
        dx, dy = p["x2"] - p["x1"], p["y2"] - p["y1"]
        L = math.hypot(dx, dy)
        wx, s = dy / L, (-1 if p["yon"] == "LABEL_NRM" else 1)                # w = (dy, −dx): eksenin sağı
        for a in (-s * p["kanat"] / 2, s * (k["kanat_mm"] - p["kanat"] / 2)):
            xs += [p["x1"] + wx * a, p["x2"] + wx * a]
    return max(0.0, -min(xs) if bastan else max(xs) - _alt_baslik(fr) * 10) / 10


def mahal_kaymalari(UM: dict, T: dict, kisa: dict[str, list[dict]], bas: float, Hata=ValueError) -> dict[str, float]:
    """Köşe kırmasının çatısı kısa makaslarıyla birlikte x boyunca ne kadar kayık durur (mahal adı → cm, işaretli; saçağa doğru).
    Motor kısa makasın yüksek ucunu duvar çizgisine koyar. Rehberde makas son ana makasın yüzüne üst başlığının ucuyla değer (Soru 14 ve
    Soru 16): yüz duvar çizgisinden `yarı sırt − bas` dışarıda (şablonun baş makası, 0,3 cm), üst başlığın ucu alt başlığı `_uc_tasmasi`
    kadar geçer (0,94 cm). Aşık makasın üst başlığına oturur; bu yüzden mahalin yüzü (aşık, OSB, kaplama), deresi ve inişi de o kadar
    kayar (`girinti._mahal_yuzleri`, `mahal`). `kisa`: mahal adı → Motor'un kısa makasları (`ifc_uret._kirma_mahal_makaslari`);
    `bas`: baş makasın duvar dış yüzünden konumu (`girinti.BAS`). `uretim_makaslari` aynı kaymayı kendi hesabıyla doğrular."""
    ana = next(q for q in T["parcalar"] if q["rol"] == "ana")
    out = {}
    for ad, ms in kisa.items():
        ks = set()
        for m, cer in zip(sorted(ms, key=lambda m: m["konum"]), UM["kisa"]):
            sacak, yuksek = m["ust"]
            if abs(yuksek[1] - sacak[1]) > 1e-6:
                raise Hata(f"üretim makası {cer}: kısa makas x boyunca uzanmıyor; mahal çatısının kayması yalnız x boyunca kuruldu")
            fr, yon = UM["cerceveler"][cer], (1.0 if sacak[0] > yuksek[0] else -1.0)
            kenar = min(ana["a"], key=lambda a: abs(a - yuksek[0]))
            konum = kenar + bas if kenar == ana["a"][0] else kenar - bas
            yuz = konum + yon * fr["parcalar"][0]["sirt"] / 20
            ks.add(round(yon * ((yuz - yuksek[0]) * yon + _uc_tasmasi(fr, UM["kesit"], True)), 3))
        if len(ks) != 1:
            raise Hata(f"{ad}: kısa makasların kayması tek değer değil ({sorted(ks)})")
        out[ad] = ks.pop()
    return out


def _makas_cubuklari(fr: dict, A, B, z0: float, KS: dict) -> list[list[float]]:
    """Üretim makasını plan doğrusu A→B üzerine oturtur: çerçevenin x = 0'ı A'da, alt yüzü `z0` kotunda, düzlemi düşey. Çubuk üretim
    dosyasının ekseninden (mm → cm) ve gerçek kesitle çizilir: dudaklı C; sırt (80) makasın düzlemine dik, iki kanat (45) düzlemde,
    dudak (10) kanat ucundan içe. Üretim dosyasının ekseni vida hattıdır: sırttan `kanat / 2` (dosyadaki 54'ün yarısı, 27 mm); sırt
    eksenin ağzın tersindeki yanında kalır, bu yüzden makasın dış ölçüsü değişmez. Sondaki dört sayı: ağzın yönü (şablonun enine ekseni
    `w = n × d` boyunca +1 ya da −1), sac kalınlığı, sırttan eksene uzaklık, dudak (cm). Ağız üretim dosyasının etiket yönünden
    (`araclar/uretim/islem.py` › `Parca`: LABEL_NRM'de ağız eksenin solunda, LABEL_INV'de sağında); çerçevede `w` eksenin sağıdır, bu
    yüzden NRM −1, INV +1."""
    (ax, ay), (bx, by) = A, B
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    out = []
    for p in fr["parcalar"]:
        k = _gercek_kesit(KS, p)
        x1, y1, x2, y2 = (p[k_] / 10 for k_ in ("x1", "y1", "x2", "y2"))
        P = (ax + ux * x1, ay + uy * x1, z0 + y1)
        Q = (ax + ux * x2, ay + uy * x2, z0 + y2)
        out.append([round(v, 2) for v in (*P, *Q, k["kanat_mm"] / 10, p["sirt"] / 10, -uy, ux, 0)] +
                   [-1 if p["yon"] == "LABEL_NRM" else 1, p["kalinlik"] / 10, p["kanat"] / 20, k["dudak_mm"] / 10])
    return out


def uretim_makaslari(UM: dict, makas: list[dict], mahal_makaslari: list[dict], z0: float, ls, Hata=ValueError,
                     kaymalar: dict | None = None) -> list[dict]:
    """Çatı makasları üretim çizimlerinden (ek parça, adım "makas"). `makas`: rehberin ana ve cumba makasları (`girinti.cati`; yer Motor'un
    çatı tanımından, baş makas ve iç uç makası rehberin kalkan hizasında); `mahal_makaslari`: köşe kırmasının kısa ve çapraz makasları
    (`motor.ifc_uret._kirma_mahal_makaslari`). Çerçeve adı kayıttaki sırayla eşlenir; sayı ya da alt başlık boyu Motor'unkiyle tutmazsa
    `Hata`. Çerçevenin x = 0'ı: beşik makasında ön saçak ucu, kısa makasta duvar (yüksek) ucu, çapraz makasta saçak köşesi
    (`araclar/uretim/makas.py`). Eşlenen her şablon makası `uretim` adını alır (`sahne.js` onu çizmez; yeri ve adı öteki parçalar için kalır)."""
    FR = UM["cerceveler"]
    ek = []

    def parca(ad, kod, kalem, A, B, yer, cati, sira):
        fr = FR[ad]
        L, Lf = math.hypot(B[0] - A[0], B[1] - A[1]), _alt_baslik(fr)
        pay = UM.get("uc_payi", {}).get(ad, 0.0)          # D-157: çerçeve A'dan (saçak köşesi) başlar, yüksek uçta `pay` kadar kısa biter
        if abs(L - Lf - pay) > BOY_PAYI:
            raise Hata(f"üretim makası {ad}: alt başlık {Lf * 10:g} mm + uç payı {pay * 10:g} mm, Motor'un makası {L * 10:g} mm")
        kesit = sorted({(p["kesit"], p["sirt"], _gercek_kesit(UM["kesit"], p)["kanat_mm"], _gercek_kesit(UM["kesit"], p)["dudak_mm"], p["kalinlik"])
                        for p in fr["parcalar"]})
        ek.append({"adim": "makas", "sira": sira, "ad": kalem.split(" · ")[0], "kod": kod, "mat": "truss", "uretim": ad,
                   "cubuk": _makas_cubuklari(fr, A, B, z0, UM["kesit"]),
                   "satir": [["Bu parça", f"{ad} · alt başlık {str(round(Lf * 10, 1)).replace('.', ',').removesuffix(',0')} mm · {fr['ozet']['cubuk']} çubuk"],
                             ["Yer", yer], ["Çatı", cati],
                             ["Profil", "; ".join(f"{k} kesit: sırt {s:g} mm, kanat {w:g} mm, dudak {u:g} mm, sac {str(t).replace('.', ',')} mm"
                                                  for k, s, w, u, t in kesit)],
                             ["Liste", ls(kalem)],
                             ["Kaynak", "orijinal üretim çizimi (çelik üretim dosyası); yer ve sayı çatı tanımından (çizim, liste ve 3B modelle aynı)"]]})

    for aile in ("ana", "cumba"):
        ms = sorted((m for m in makas if m["aile"] == aile), key=lambda m: m["konum"])
        if len(ms) != len(UM[aile]):
            raise Hata(f"üretim dosyasında {len(UM[aile])} {aile} makası, çatı tanımında {len(ms)}")
        for m, ad in zip(ms, UM[aile]):
            if m.get("yon") != "y":
                raise Hata("üretim makası yalnız y boyunca uzanan makasta kuruldu (63 m²)")
            cati = m["cati"]
            kalem = ("Makas (baş)" if m["rol"] == "bas" else "Makas (orta)") if aile == "ana" else "Cumba makası · " + cati.split(" beşiği")[0]
            parca(ad, m.get("kod") or ("MA-01" if m["rol"] == "bas" else "MA-02"), kalem, (m["konum"], m["bas"]), (m["konum"], m["son"]),
                  f"{m['ad']} · x = {str(m['konum']).replace('.', ',')} cm (sol dış yüzden)", cati, len(ek))
            m["uretim"] = ad
    kisa = sorted((m for m in mahal_makaslari if m["rol"] == "kisa"), key=lambda m: m["konum"])
    capraz = [m for m in mahal_makaslari if m["rol"] != "kisa"]
    ana_x = [m["konum"] for m in makas if m["aile"] == "ana"]
    for ms, anahtar, kod in ((kisa, "kisa", "MA-06"), (capraz, "capraz", "MA-07")):
        if len(ms) != len(UM[anahtar]):
            raise Hata(f"üretim dosyasında {len(UM[anahtar])} {anahtar} makas, çatı tanımında {len(ms)}")
        for m, ad in zip(ms, UM[anahtar]):
            sacak, yuksek = m["ust"]                                              # [saçak ucu, yüksek uç]
            A, B = (yuksek, sacak) if anahtar == "kisa" else (sacak, yuksek)
            # Soru 14 (Lokman, 26 Kasım 2026 23:33:13 UTC kartı "B: Son ana makasa, paftadaki gibi"): veranda makası son ana makasın
            # yüzüne dayanır. Motor yüksek ucu duvar çizgisine koyar; rehberde ana makasın dış yüzü oradan `BAS_DIS` dışarıdadır.
            # Soru 16 (Lokman, 27 Kasım 2026 06:03:53 UTC kartı "A: Üretim dosyası aynı kalsın"): üretim dosyasında üst başlığın ucu
            # alt başlığın ucunu geçer (`_uc_tasmasi`; 63 m²: 0,94 ve 0,93 cm). Makas o kadar geride durur: ana makasa üst başlığın
            # ucuyla değer, alt başlığın ucu ile ana makas arasında boşluk kalır. Çerçeve ekseni boyunca kayar (boyu değişmez).
            fr, yari = FR[ad], FR[ad]["parcalar"][0]["sirt"] / 20
            yon = 1.0 if sacak[0] > yuksek[0] else -1.0                           # veranda ana makasın hangi yanında (x boyunca)
            if abs(yuksek[0] - sacak[0]) < 1.0:
                raise Hata(f"üretim makası {ad}: veranda makası x boyunca uzanmıyor; dayanak yüzü yalnız y boyunca uzanan ana makasta kuruldu")
            yuz = min(ana_x, key=lambda x: abs(x - yuksek[0])) + yon * yari       # son ana makasın verandaya bakan yüzü
            L = math.hypot(B[0] - A[0], B[1] - A[1])
            ux, uy = (B[0] - A[0]) / L, (B[1] - A[1]) / L
            tas = _uc_tasmasi(fr, UM["kesit"], anahtar == "kisa")
            if anahtar == "kisa":                                                 # x = −taşma (üst başlığın ucu) yüzde
                kay = (yuz - A[0]) / ux + tas
            else:                                                                 # x = alt başlık boyu + taşma; yüze yakın köşe yüzde
                kay = (yuz + yon * abs(uy) * yari - A[0]) / ux - _alt_baslik(fr) - tas
            if not -0.01 <= kay * (1 if anahtar == "kisa" else -1) <= DAYANAK_PAYI:
                raise Hata(f"üretim makası {ad}: son ana makasın yüzüne ({yuz:g}) {kay:.2f} cm kayma; beklenen 0–{DAYANAK_PAYI:g} cm")
            if anahtar == "kisa" and kaymalar is not None and abs(ux * kay - kaymalar.get(m["duzlemler"][0], 1e9)) > 0.005:
                raise Hata(f"üretim makası {ad}: kayma {ux * kay:.3f} cm, mahalin çatısı {kaymalar.get(m['duzlemler'][0])} cm kaydırıldı")
            A, B = (A[0] + ux * kay, A[1] + uy * kay), (B[0] + ux * kay, B[1] + uy * kay)
            yer = (f"y = {str(round(m['konum'], 2)).replace('.', ',')} cm (ön dış yüzden)" if anahtar == "kisa" else
                   "kırma hattı boyunca, saçak köşesinden duvara")
            parca(ad, kod, m["kalem"], A, B, yer, m["kalem"].split(" · ")[-1], 100 + len(ek))
            bosluk = f"{tas:.1f}".replace(".", ",")
            ek[-1]["satir"].insert(2, ["Dayanak", "Makas son ana makasa dayanır (paftadaki gibi). Üst başlığın ucu ana makasa değer. Alt başlık ile ana makas "
                                                  f"arasında {bosluk} cm boşluk kalır. Kalkan betopanı makasın geçtiği yerde kesilir."])
            ek[-1]["dayanak"] = {"yuz": round(yuz, 3), "yon": yon, "kayma": round(abs(kay), 3), "yari": yari, "tasma": round(tas, 3)}
    return ek


def kalkan_yariklari(ekler: list[dict], bet0: float, bet1: float) -> list[dict]:
    """Soru 14 (B): veranda makaslarının kalkan betopanından geçtiği yerler. `bet0`–`bet1`: betopanın iç ve dış yüzü (ana makasın yüzünden
    dışarı, cm). Dönen: [{"x": ana makasın yüzü, "s": [y0, y1] (plan, cm), "z": makasın o yerdeki üst kotu, "uretim": ad}]. Yer çubukların
    plandaki izinden (eksen ± sırt / 2), kot çubukların dosyadaki dış ölçüsünden (eksen ± 27 mm)."""
    from shapely.geometry import Polygon, box
    out = []
    for e in ekler:
        d = e.get("dayanak")
        if not d:
            continue
        x0, x1 = sorted((d["yuz"] + d["yon"] * bet0, d["yuz"] + d["yon"] * bet1))
        serit = box(x0, -1e6, x1, 1e6)
        ys, zs = [], []
        for c in e["cubuk"]:
            (px, py, pz), (qx, qy, qz) = c[0:3], c[3:6]
            Lp = math.hypot(qx - px, qy - py)
            Lt = math.dist((px, py, pz), (qx, qy, qz))
            nx, ny = c[8], c[9]                                                   # plan normali (sırt yönü)
            if Lp < 1e-6:                                                         # dikme: planda nokta; düzlemdeki eni eksen ± 2,7
                iz = Polygon([(px + sx * 2.7 * ny + sn * nx * d["yari"], py - sx * 2.7 * nx + sn * ny * d["yari"])
                              for sx, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            else:
                tx, ty = (qx - px) / Lp, (qy - py) / Lp
                pay = 2.7 * abs(qz - pz) / Lt                                     # eğik çubuğun ucunda dış ölçünün plandaki taşması
                a, b = (px - tx * pay, py - ty * pay), (qx + tx * pay, qy + ty * pay)
                iz = Polygon([(a[0] - nx * d["yari"], a[1] - ny * d["yari"]), (b[0] - nx * d["yari"], b[1] - ny * d["yari"]),
                              (b[0] + nx * d["yari"], b[1] + ny * d["yari"]), (a[0] + nx * d["yari"], a[1] + ny * d["yari"])])
            kes = iz.intersection(serit)
            if kes.is_empty or kes.area < 1e-6:
                continue
            ys += [kes.bounds[1], kes.bounds[3]]
            kos = Lp / Lt if Lt > 1e-6 else 0.0                                   # çubuğun düşeyle değil yatayla açısının kosinüsü
            zs.append(max(pz, qz) + (2.7 * kos if Lp > 1e-6 else 0.0))
        if ys:
            out.append({"x": d["yuz"], "s": [round(min(ys), 2), round(max(ys), 2)], "z": round(max(zs), 2), "uretim": e["uretim"]})
    return out


# ---------- kubbe: orijinal üretim çizimleri ----------
EN, DER = 5.4, 8.0          # C 80 × 54: çerçevenin düzleminde 5,4 cm, duvarın içine doğru 8 cm (FrameBuilder dosyası, BK-76)


def _cerceve_cubuklari(fr: dict, A, B, z0: float, nrm, merkez: bool = True) -> list[list[float]]:
    """Üretim çerçevesini plan doğrusu A→B üzerine (yerel x A'dan B'ye, yerel y yukarı, taban `z0`) oturtur. Çerçeve doğrunun ortasına
    ortalanır (`merkez`); çubuklar eksenlerinden (mm → cm)."""
    (ax, ay), (bx, by) = A, B
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    W = fr["ozet"]["dis_olcu_mm"][0] / 10
    x_bas = (L - W) / 2 if merkez else 0.0
    out = []
    for p in fr["parcalar"]:
        x1, y1, x2, y2 = (p[k] / 10 for k in ("x1", "y1", "x2", "y2"))
        P = (ax + ux * (x_bas + x1), ay + uy * (x_bas + x1), z0 + y1)
        Q = (ax + ux * (x_bas + x2), ay + uy * (x_bas + x2), z0 + y2)
        out.append([round(v, 2) for v in (*P, *Q, EN, DER, *nrm)])
    return out


def kubbe(HZ: dict, ifc_yolu: Path, ls) -> tuple[list[dict], set[str]]:
    """Kubbenin parçaları: duvar, bant ve makas üretim çizimlerinden; pencere ve çatı kart modelinden. Dönen: (ek parçalar, motorun
    kubbe parçalarından şablonun çizmediği adlar (bilgi))."""
    KB = HZ.get("kubbeler") or []
    if not KB:
        return [], set()
    if len(KB) != 1:
        raise ValueError(f"{len(KB)} kubbe; üretim çizimleri tek kubbenin (63 m²)")
    kb = KB[0]
    FR = {f["cerceve"]: f for f in json.loads(URETIM.read_text(encoding="utf-8"))}
    ek = []
    H_DUVAR = FR["KUBBE-DUVAR1"]["ozet"]["dis_olcu_mm"][1] / 10
    # duvarlar: yan 1, ön 2, yan 3 — motorun kubbesindeki pano sırası (yan, ön, yan; `_kubbe_girdisi`)
    duvar_ad = {0: "KUBBE-DUVAR1", 1: "KUBBE-DUVAR2", 2: "KUBBE-DUVAR3"}
    for i, q in enumerate(kb["panolar"]):
        fr = FR[duvar_ad[i]]
        (ax, ay), (bx, by) = q["dis_kenar"]
        dx, dy = q["disari"]
        A, B = (ax - dx * 5, ay - dy * 5), (bx - dx * 5, by - dy * 5)          # duvarın ekseni: dış yüzden 5 cm içeride
        ek.append({"adim": "kubbe_duvar", "sira": i, "ad": f"Kubbe duvarı · {fr['dosya'].removesuffix('.csv')}", "kod": None, "mat": "steel",
                   "cubuk": _cerceve_cubuklari(fr, A, B, 0.0, [dx, dy, 0]),
                   "satir": [["Bu parça", f"{fr['dosya'].removesuffix('.csv')} · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · "
                                          f"{fr['ozet']['cubuk']} çubuk"],
                             ["Profil", "C 80 × 54, 0,8 mm (üretim dosyası)"],
                             ["Yer", f"kubbenin {'ön' if q['tur'] == 'on' else 'yan'} duvarı ({q['boy']:g} cm pano yerine)"],
                             ["Kaynak", "orijinal üretim çizimi (FrameBuilder); yerleşim motorun kubbesinden"]]})
    # üst bant: düz duvarda kubbenin tabanının üstünde (motorun "Kubbe özel pano 100 × 2500 × 500" yeri)
    fr = FR["KUBBE-DUVAR4"]
    x0, y0, x1, y1 = kb["taban"]
    xm = (x0 + x1) / 2
    z_bant = HZ["bina"]["duvar_h"] - fr["ozet"]["dis_olcu_mm"][1] / 10
    ek.append({"adim": "kubbe_duvar", "sira": 3, "ad": "Kubbe üst bandı · KUBBE-DUVAR-4", "kod": None, "mat": "steel",
               "cubuk": _cerceve_cubuklari(fr, (xm, y0), (xm, y1), z_bant, [1, 0, 0]),
               "satir": [["Bu parça", f"KUBBE-DUVAR-4 · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm"],
                         ["Yer", "düz duvarda kubbenin üstü; üstü duvar üstü kotunda (yer varsayım)"], ["Liste", ls("Kubbe özel pano")],
                         ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    # makaslar: biri düz duvar boyunca (KMK14), ikisi tepeden ön köşelere (KMK15, KMK16)
    tx, ty = kb["tepe"]
    z_m = kb["sacak_kotu"] - 2.7
    fr = FR["KMK14"]
    L14 = fr["ozet"]["dis_olcu_mm"][0] / 10
    ek.append({"adim": "makas", "sira": 200, "ad": "Kubbe makası · K-MKS-14", "kod": None, "mat": "truss",
               "cubuk": _cerceve_cubuklari(fr, (tx, ty - L14 / 2), (tx, ty + L14 / 2), z_m, [1, 0, 0]),
               "satir": [["Bu parça", f"K-MKS-14 · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · {fr['ozet']['cubuk']} çubuk"],
                         ["Yer", "düz duvar boyunca, kubbenin tepesinde ortalı (yer varsayım)"], ["Liste", ls("Kubbe makası")],
                         ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    s0, s3 = kb["sacak"][1], kb["sacak"][2]                                     # saçağın iki ön köşesi
    for j, (ad, kose) in enumerate((("KMK15", s0), ("KMK16", s3))):
        fr = FR[ad]
        L = fr["ozet"]["dis_olcu_mm"][0] / 10
        dx, dy = kose[0] - tx, kose[1] - ty
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        A = (tx + ux * L, ty + uy * L)                                          # alçak ucu köşeye doğru, yüksek ucu tepede
        ek.append({"adim": "makas", "sira": 201 + j, "ad": f"Kubbe makası · K-MKS-{ad[3:]}", "kod": None, "mat": "truss",
                   "cubuk": _cerceve_cubuklari(fr, A, (tx, ty), z_m, [-uy, ux, 0], merkez=False),
                   "satir": [["Bu parça", f"K-MKS-{ad[3:]} · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · {fr['ozet']['cubuk']} çubuk"],
                             ["Yer", "tepeden kubbenin ön köşesine (yer varsayım)"], ["Liste", ls("Kubbe makası")],
                             ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    # kart modelinden: pencereler ve kubbenin çatısı (OSB + membran + shingle)
    OZ = ifc_ozellik(ifc_yolu, r"^(CATI_KUBBE_\d+_\d+|PENCERE_.*)$")
    pen = {n for n in OZ if n.startswith("PENCERE_") and _kubbede(ifc_yolu, n, kb)}
    U = ifc_ucgen(ifc_yolu, pen | {n for n in OZ if n.startswith("CATI_KUBBE")})
    for n in sorted(pen):
        ek.append({"adim": "kubbe_duvar", "sira": 10, "ad": f"PVC pencere {n.split('_')[1].replace('x', '/')} (kubbe)", "kod": None, "mat": "pvc",
                   "mesh": U[n], "satir": [["Bu parça", n], ["Kaynak", "kart modeli (yer motorun kubbesinden)"]]})
    for n in sorted(x for x in U if x.startswith("CATI_KUBBE")):
        ek.append({"adim": "kaplama", "sira": 400, "ad": "Kubbe çatısı (OSB + membran + shingle)", "kod": None, "mat": "roof", "mesh": U[n],
                   "satir": [["Bu parça", n], ["Liste", f"{ls('Kubbe OSB 11 mm')}; {ls('Kubbe üstü membran')}; {ls('Kubbe antrasit shingle')}"],
                             ["Kaynak", "kart modelinin kubbe çatısı"]]})
    return ek, {n for n in pen}


def _kubbede(ifc_yolu: Path, ad: str, kb: dict) -> bool:
    from .veri import ifc_kutulari
    k = ifc_kutulari(ifc_yolu, "^" + re.escape(ad) + "$").get(ad)
    if not k:
        return False
    xs = [p[0] for p in kb["dis"]]
    ys = [p[1] for p in kb["dis"]]
    return min(xs) - 15 <= (k[0] + k[3]) / 2 <= max(xs) + 15 and min(ys) - 15 <= (k[1] + k[4]) / 2 <= max(ys) + 15
