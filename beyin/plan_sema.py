"""İE-14 · plan şeması: LLM'in bir talepten (ya da revizyondan) ürettiği tek kat çelik plan taslağı.

LLM koordinatı yalnız oda düzeyinde verir: her mahal, dış yüze göre (köken binanın güneybatı dış köşesi, +x doğu, +y kuzey, cm)
5 cm ızgarada dikdörtgenlerin birleşimidir. Duvar kutuları, kapı ve pencere konumları ve çatı düzlemleri koddan çıkar
(`motor/genel/plan_derle.py`); denetim `beyin/plan_denetim.py`. Şema `beyin/sema.py`'den ayrıdır: prefabrik ve P6001 yolunun
çıkarım sözleşmesi değişmez (İE-14 › Amaç).

`tanimdan()`: bankadaki bir Yapı Tanımı'nı aynı şemaya geri çevirir (LLM'e örnek ve kör üretim kıyası için). Mahal bölgeleri
`yapi.kur`'dan gelir; dikdörtgenlere ayrılır ve duvar eksenine yaslanır (yaklaşık; çizim için değil, örnek için).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

IZGARA = 5                      # cm; mahal köşeleri bu ızgarada (kurallar/plan/oda_kurallari.json › izgara_cm ile aynı)
ISLEVLER = ("salon", "mutfak", "yatak_odasi", "banyo", "hol", "depo", "veranda")
CEPHELER = ("G", "K", "B", "D")          # güney (y = 0), kuzey (y = boy), batı (x = 0), doğu (x = en)
PENCERE_OLCULERI = ("120x120", "120x180", "60x40", "120x100", "120x160", "160x120", "160x180", "180x180", "80x120", "120x50",
                    "80x180", "60x60")


class DisOlcu(BaseModel):
    en: int = Field(..., description="Doğu–batı dış ölçü, cm (dış yüzden dış yüze; verandayla birlikte)")
    boy: int = Field(..., description="Kuzey–güney dış ölçü, cm")


class Mahal(BaseModel):
    ad: str = Field(..., description="Bayiye görünen ad: 'Salon', 'Mutfak', 'Yatak Odası 1', 'Banyo', 'Hol', 'Veranda' …")
    islev: Literal["salon", "mutfak", "yatak_odasi", "banyo", "hol", "depo", "veranda"]
    dikdortgenler: list[list[int]] = Field(..., min_length=1, description="[[x0, y0, x1, y1], …] cm, 5 cm ızgarada, dış yüze göre; L biçimli mahal "
                                                           "birden çok dikdörtgenle")
    ortu: Optional[Literal["cati", "pergola", "acik"]] = Field(None, description="Yalnız veranda: çatının altında mı, pergola mı, açık mı")


class Kapi(BaseModel):
    arasinda: list[str] = Field(..., description="İki mahal adı; dış kapı için ['dis', '<mahal>']. Açılım yönünü kod seçer (kapı odaya açılır)")
    cephe: Optional[Literal["G", "K", "B", "D"]] = Field(None, description="Yalnız dış kapı: hangi cephede (verilmezse kod seçer)")


class Pencere(BaseModel):
    mahal: str
    cephe: Literal["G", "K", "B", "D"]
    olcu: Literal["120x120", "120x180", "60x40", "120x100", "120x160", "160x120", "160x180", "180x180", "80x120", "120x50", "80x180", "60x60"] = \
        Field(..., description="en x yükseklik, cm")
    adet: int = Field(1, ge=1, le=4)


class Cati(BaseModel):
    tip: Literal["besik", "kirma"]
    mahya_yonu: Optional[Literal["x", "y"]] = Field(None, description="Mahya doğu–batı (x) ya da kuzey–güney (y); verilmezse uzun kenar "
                                                                     "boyunca. Kırmada mahya her zaman uzun kenar boyuncadır")
    egim_yuzde: Optional[float] = Field(None, ge=10, le=60, description="Yüzde; verilmezse %33")


class PlanTaslagi(BaseModel):
    """Tek kat çelik plan taslağı (İE-14a). Kapalı kısım dikdörtgendir; veranda varsa bir cephe boyunca tam uzunlukta şerittir."""
    dis_olcu: DisOlcu
    mahaller: list[Mahal]
    kapilar: list[Kapi]
    pencereler: list[Pencere]
    cati: Cati
    dis_karkas: Optional[Literal[80, 140]] = Field(None, description="Dış duvar karkası (mm); verilmezse 80. 140'lık: kalın dış duvar")
    gerekce: str = Field("", description="Kısa: yerleşimin mantığı (bayiye gitmez, kayda girer)")
    uygulanamayan: list[str] = Field(default_factory=list, description="Yalnız revizyonda: bu planla uygulayamadığın istekler, bayinin "
                                                                      "sözüyle (ör. 'çift kat olsun'); uygulananlar buraya yazılmaz")


ARAC_ADI = "plan_kaydet"
ARAC_ACIKLAMA = "Tek kat çelik plan taslağını kaydet (İE-14 plan şeması). Yalnız bu araçla cevap ver."


def sema() -> dict:
    return PlanTaslagi.model_json_schema()


# ── bankadaki tanımdan plan şemasına (örnek ve kör üretim kıyası) ──────────────────────────────────────────────────────
def _yuvarla(v: float) -> int:
    return int(round(v / IZGARA) * IZGARA)


def _bolge_dikdortgenleri(geo, eksenler_x: list[float], eksenler_y: list[float], en: int, boy: int) -> list[list[int]]:
    """Bölgeyi (net mahal çokgeni) duvar eksenlerine yaslanmış dikdörtgenlere ayırır: köşe koordinatları en yakın eksene çekilir,
    çokgen bu ızgarada hücrelere bölünür, satır satır birleştirilir."""
    from shapely.geometry import box

    def cek(v, eks, ust):
        if v < 20:                     # dış duvarın iç yüzü → dış yüz (0)
            return 0
        if v > ust - 20:
            return ust
        return min(eks, key=lambda e: abs(e - v)) if eks else v
    xs = sorted({_yuvarla(cek(x, eksenler_x, en)) for x, _ in geo.exterior.coords})
    ys = sorted({_yuvarla(cek(y, eksenler_y, boy)) for _, y in geo.exterior.coords})
    hucre = []
    for j in range(len(ys) - 1):
        satir = []
        for i in range(len(xs) - 1):
            mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            b = box(xs[i], ys[j], xs[i + 1], ys[j + 1])
            from shapely.geometry import Point
            if geo.buffer(15).contains(Point(mx, my)) and geo.buffer(15).intersection(b).area > 0.5 * b.area:
                satir.append(i)
        # ardışık hücreleri birleştir
        bas = None
        for i in range(len(xs)):
            icinde = i in satir
            if icinde and bas is None:
                bas = i
            if (not icinde or i == len(xs) - 2) and bas is not None:
                son = i if icinde else i - 1
                hucre.append([xs[bas], ys[j], xs[son + 1], ys[j + 1]])
                bas = None
    # dikey birleştirme: aynı x aralığında üst üste dikdörtgenler
    hucre.sort(key=lambda r: (r[0], r[2], r[1]))
    birlesik: list[list[int]] = []
    for r in hucre:
        if birlesik and birlesik[-1][0] == r[0] and birlesik[-1][2] == r[2] and birlesik[-1][3] == r[1]:
            birlesik[-1][3] = r[3]
        else:
            birlesik.append(list(r))
    return birlesik


def tanimdan(tanim: dict) -> dict:
    """Bankadaki Yapı Tanımı → plan şeması sözlüğü (doğrulanmamış; LLM örneği). Dış ölçü, mahaller (eksene yaslı dikdörtgenler),
    kapılar (açıklığın duvarının iki yanındaki mahaller), pencereler (mahal, cephe, ölçü), çatı tipi."""
    from motor.genel import yapi as Y
    g = Y.kur(tanim)
    bol = {ad: b for ad, b in g["bolgeler"].items() if b["sinif"] != "dis"}
    from shapely.ops import unary_union
    dis = unary_union([b["ham"] for b in bol.values()] + [d["geo"] for d in g["duvarlar"]])
    x0, y0, x1, y1 = dis.bounds
    ox, oy = round(x0 - tanim["yuz_kaplamalari"]["dis"]["kalinlik"], 2), round(y0 - tanim["yuz_kaplamalari"]["dis"]["kalinlik"], 2)
    en = _yuvarla(x1 - x0 + 2 * tanim["yuz_kaplamalari"]["dis"]["kalinlik"])
    boy = _yuvarla(y1 - y0 + 2 * tanim["yuz_kaplamalari"]["dis"]["kalinlik"])
    eks_x = [0.0, float(en)] + [(d["kutu"][0] + d["kutu"][2]) / 2 - ox for d in tanim["duvarlar"] if d["kutu"][2] - d["kutu"][0] < d["kutu"][3] - d["kutu"][1]]
    eks_y = [0.0, float(boy)] + [(d["kutu"][1] + d["kutu"][3]) / 2 - oy for d in tanim["duvarlar"] if d["kutu"][2] - d["kutu"][0] >= d["kutu"][3] - d["kutu"][1]]
    from shapely.affinity import translate
    mahaller = []
    for tm in tanim["mahaller"]:
        islev = (tm.get("islev") or ["depo"])[0]
        if islev not in ISLEVLER:
            islev = "depo"
        geo = translate(bol[tm["ad"]]["ham"], -ox, -oy)
        e = {"ad": tm["ad"], "islev": islev, "dikdortgenler": _bolge_dikdortgenleri(geo, eks_x, eks_y, en, boy)}
        if tm.get("sinif") == "veranda":
            e["ortu"] = tm.get("ortu", "cati")
        mahaller.append(e)
    duvar = {d["ad"]: d for d in tanim["duvarlar"]}
    kapilar, pencereler = [], []
    for a in tanim["acikliklar"]:
        d = duvar.get(a["duvar"])
        if d is None:
            continue
        kx0, ky0, kx1, ky1 = d["kutu"]
        yatay = (kx1 - kx0) >= (ky1 - ky0)
        orta = a["bas"] + a["en"] / 2
        p1, p2 = ((orta, ky0 - 20), (orta, ky1 + 20)) if yatay else ((kx0 - 20, orta), (kx1 + 20, orta))
        from shapely.geometry import Point

        def kim(p):
            for ad, b in bol.items():
                if b["ham"].buffer(1).contains(Point(p)):
                    return ad
            return "dis"
        a1, a2 = kim(p1), kim(p2)
        if a["tur"] == "pencere":
            mah = a.get("mahal") or (a2 if a1 == "dis" else a1)
            cephe = ("G" if p1[1] < (y0 + y1) / 2 else "K") if yatay else ("B" if p1[0] < (x0 + x1) / 2 else "D")
            olcu = min(PENCERE_OLCULERI, key=lambda o: abs(int(o.split("x")[0]) - a["en"]) + abs(int(o.split("x")[1]) - a["yuk"]))
            pencereler.append({"mahal": mah, "cephe": cephe, "olcu": olcu, "adet": 1})
        elif a["tur"] in ("dis_kapi", "ic_kapi", "gecit"):
            ikisi = [a1, a2]
            if "dis" in ikisi:
                ikisi = ["dis", a2 if a1 == "dis" else a1]
            kapilar.append({"arasinda": ikisi})
    ct = tanim.get("cati", {})
    tip = "kirma" if "kirma" in str(ct.get("tip", "")) else "besik"
    return {"dis_olcu": {"en": en, "boy": boy}, "mahaller": mahaller, "kapilar": kapilar, "pencereler": pencereler,
            "cati": {"tip": tip}, "gerekce": f"bankadaki {tanim.get('kod', '')} (yaklaşık çeviri)"}
