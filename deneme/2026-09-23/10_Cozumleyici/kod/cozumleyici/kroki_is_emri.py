"""Portman çözümleyici — Ölçülü Kroki (cm) → İş Emri (serbest aks, K16-b denemesi).

Katalog çıkarıcısı (motor/cikarici.py) planı 125,5 modülüne oturtur; bayi planı modülde değilse duvarları
±30 cm taşır, kapı düşürür. Bayiler ise ölçüyü temele / ruhsata göre verir ve üretimde özel pano kullanılır.
Bu modül bayinin ölçüsünü korur: akslar bayinin duvar eksenlerinden okunur (yapi.aks_cm), pano ayrıştırmayı
Motor yapar (her koşu başından 125,5; kalan özel pano sonda).

Akış: duvar parçaları → aks adayları (Motor kuralına göre: sol/sağ dış duvar iç yüzü, ön/arka dış duvar ekseni,
iç duvar ekseni, bina içindeki dış duvarın oda tarafı yüzü) → yakın adaylar birleşir (≤ 15 cm, kayma raporlanır)
→ hücre ızgarası → her hücre, duvar birleşiminin boşluğu (oda) ile eşlenir → mahaller → pencere/kapı → pano indeksi
(Motor aday listesiyle) → G.kur ile doğrulama. Hiçbir kayma sessiz değildir; hepsi rapor['sapmalar']'a yazılır.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

from shapely.geometry import box as sbox, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G           # noqa: E402
from motor.cikarici import Cikarici, AD_ESLEME, _norm as c_norm   # noqa: E402

BIRLESTIR_CM = 15.0


def _r(v, n=1):
    return round(float(v), n)


class KrokiIsEmri:
    def __init__(self, kroki: dict, kod: str, bayi: dict | None = None):
        self.k = kroki
        self.kod = kod
        self.bayi = bayi or {"kod": "BAYI", "ad": "?"}
        self.W, self.H = kroki["dis_kutu_cm"]["W"], kroki["dis_kutu_cm"]["H"]
        self.sapmalar: list[str] = []
        self.notlar: list[str] = []
        # bayinin yazdığı dış ölçü sözleşme ölçüsüdür: çizimden ≤ 2 cm farklıysa yazılan alınır
        yaz = kroki.get("olcu_yazilari_cm", {})
        for ad, attr in (("genislik", "W"), ("derinlik", "H")):
            v = yaz.get(ad)
            if v and abs(v - getattr(self, attr)) <= 2.0:
                if abs(v - getattr(self, attr)) > 0.05:
                    self.notlar.append(f"Dış {ad}: çizim {getattr(self, attr)} → bayinin yazdığı {v} cm alındı")
                setattr(self, attr, float(v))

    # ------------------------------------------------------------------ 1. duvar grupları
    def duvarlar(self):
        parca = [tuple(r) for r in self.k["duvar_parcalari"]]
        self.duvar_birlesim = unary_union([sbox(*r).buffer(0.3, join_style=2) for r in parca]).buffer(-0.3, join_style=2)
        gruplar = []   # (yon, c_orta, kalinlik, a0, a1, yuz0, yuz1)
        for r in parca:
            w, h = r[2] - r[0], r[3] - r[1]
            if max(w, h) < 15:
                continue       # köşe parçası
            if w >= h:
                gruplar.append(("x", (r[1] + r[3]) / 2, h, r[0], r[2], r[1], r[3]))
            else:
                gruplar.append(("y", (r[0] + r[2]) / 2, w, r[1], r[3], r[0], r[2]))
        # aynı eksen + kalınlıktaki parçaları birleştir
        birlesik = []
        for g in sorted(gruplar, key=lambda t: (t[0], round(t[1], 0), t[3])):
            son = birlesik[-1] if birlesik else None
            if son and son[0] == g[0] and abs(son[1] - g[1]) < 1.5 and abs(son[2] - g[2]) < 1.5 and g[3] <= son[4] + 2:
                birlesik[-1] = (son[0], son[1], son[2], son[3], max(son[4], g[4]), son[5], son[6])
            else:
                birlesik.append(g)
        self.duvar_kosulari = birlesik
        return birlesik

    # ------------------------------------------------------------------ 2. odalar (duvar birleşiminin boşlukları)
    def odalar(self):
        u = self.duvar_birlesim
        polys = [u] if isinstance(u, Polygon) else list(u.geoms)
        ana = max(polys, key=lambda p: p.area)
        self.govde_dis = Polygon(ana.exterior)
        bosluklar = [Polygon(i) for i in ana.interiors if Polygon(i).area > 1.0e4]   # ≥ 1 m²
        etiketler = [m for m in self.k["mahaller"]]
        oda = []
        for b in bosluklar:
            icindeki = [m for m in etiketler if b.contains(Point(m["x"], m["y"]))]
            oda.append({"poly": b, "etiketler": icindeki})
        dis = [m for m in etiketler if not self.govde_dis.contains(Point(m["x"], m["y"]))]
        self.oda_bosluklari, self.dis_etiketler = oda, dis
        return oda

    # ------------------------------------------------------------------ 3. akslar
    def akslar(self):
        W, H = self.W, self.H
        adaylar = {"x": [(10.0, "sol dış duvar iç yüzü", None)], "y": [(5.0, "ön dış duvar ekseni", None)]}
        for yon, c, t, a0, a1, f0, f1 in self.duvar_kosulari:
            if a1 - a0 < 40:
                continue
            if yon == "y":
                if f0 < 1.5 or f1 > W - 1.5:
                    continue                    # sol/sağ çevre duvarı (sabit aks)
                if t >= 8.5:
                    # bina içindeki dış duvar: aks oda tarafındaki yüzde (Motor 'aks_disinda')
                    orta_y = (a0 + a1) / 2
                    sol_oda = any(o["poly"].contains(Point(f0 - 20, orta_y)) for o in self.oda_bosluklari)
                    aks = f0 if sol_oda else f1
                    adaylar["x"].append((aks, f"dış duvar ({_r(f0)}–{_r(f1)}) oda yüzü", c))
                else:
                    adaylar["x"].append((c, f"iç duvar ekseni ({_r(t)} cm)", c))
            else:
                if f0 < 1.5 or f1 > H - 1.5:
                    continue
                adaylar["y"].append((c, f"{'dış' if t >= 8.5 else 'iç'} duvar ekseni ({_r(t)} cm)", c))
        adaylar["x"].append((W - 10.0, "sağ dış duvar iç yüzü", None))
        adaylar["y"].append((H - 5.0, "arka dış duvar ekseni", None))
        self.aks = {}
        for yon in ("x", "y"):
            lst = sorted(adaylar[yon])
            kume = [[lst[0]]]
            for a in lst[1:]:
                if a[0] - kume[-1][-1][0] <= BIRLESTIR_CM:
                    kume[-1].append(a)
                else:
                    kume.append([a])
            out = []
            for k in kume:
                sabit = [a for a in k if a[2] is None]
                ic = [a for a in k if a[1].startswith("iç duvar")]
                # öncelik: sabit çevre aksı > iç duvar ekseni (pano dizilimini taşıyan) > ortalama
                v = sabit[0][0] if sabit else (sum(a[0] for a in ic) / len(ic) if ic else sum(a[0] for a in k) / len(k))
                for a in k:
                    if abs(a[0] - v) > 0.5:
                        self.sapmalar.append(f"Aks {yon}={_r(v)}: {a[1]} {_r(a[0])} → {_r(v)} ({_r(v - a[0]):+} cm kaydırıldı; iki duvar tek aksa alındı)")
                out.append(round(v, 2))
            # modüle yuvarlama: ardışık aks aralığı k·62,75'e ≤ 1 cm yakınsa tam modül alınır (çizim/ölçek hatası);
            # değilse aralık korunur ve Motor kalanı özel pano yapar
            son = out[-1]
            for i in range(1, len(out) - 1):
                d = out[i] - out[i - 1]
                kk = round(d / (G.MOD / 2))
                if kk >= 1 and abs(d - kk * G.MOD / 2) <= 1.0:
                    yeni = round(out[i - 1] + kk * G.MOD / 2, 2)
                    if abs(yeni - out[i]) > 0.3:
                        self.notlar.append(f"Aks {yon}: {out[i]} → {yeni} (aralık {_r(d, 2)} ≈ {kk}×62,75; modüle yuvarlandı)")
                    out[i] = yeni
            out[-1] = son
            self.aks[yon] = out
        self.nx2, self.ny2 = len(self.aks["x"]) - 1, len(self.aks["y"]) - 1
        G.aks_ayarla(self.aks["x"], self.aks["y"])
        return self.aks

    # ------------------------------------------------------------------ 4. hücre → mahal
    def mahaller(self):
        ax, ay = self.aks["x"], self.aks["y"]
        # oda adları: aynı kökten çok varsa alana göre numarala (çıkarıcı ile aynı kural)
        kayit = []
        for o in self.oda_bosluklari:
            if not o["etiketler"]:
                kayit.append((o, None)); continue
            if len(o["etiketler"]) > 1:
                self.sapmalar.append(f"Bir odada {len(o['etiketler'])} etiket: {[e['ad'] for e in o['etiketler']]} — ilki alındı")
            kayit.append((o, o["etiketler"][0]))
        kokler = {}
        for o, e in kayit:
            if e is None:
                continue
            n = c_norm(e["ad"])
            hit = next(((kok, tur) for anahtar, kok, tur, acik in AD_ESLEME if anahtar in n), (e["ad"].upper(), "diger"))
            kokler.setdefault(hit[0], []).append((o, e, hit[1]))
        self.oda_adi = {}
        for kok, lst in kokler.items():
            lst.sort(key=lambda t: -(t[1]["m2_etiket"] or t[0]["poly"].area / 1e4))
            for i, (o, e, tur) in enumerate(lst):
                ad = kok if len(lst) == 1 else f"{kok} {i + 1}"
                o["ad"], o["tur"], o["etiket"] = ad, tur, e
        for j, (o, e) in enumerate(kayit):
            if e is None:
                o["ad"], o["tur"], o["etiket"] = f"MAHAL-{j}", "diger", None
                self.sapmalar.append(f"Etiketsiz kapalı oda ({_r(o['poly'].area / 1e4, 2)} m²) — MAHAL-{j} adı verildi")
        # bina dışı (veranda) bölge
        dis_ad = None
        if self.dis_etiketler:
            e = self.dis_etiketler[0]
            n = c_norm(e["ad"])
            hit = next(((kok, tur) for anahtar, kok, tur, acik in AD_ESLEME if anahtar in n), ("VERANDA", "veranda"))
            dis_ad, dis_tur, self.dis_etiket = hit[0], hit[1], e
        hucre = {}
        for u in range(self.nx2):
            for v in range(self.ny2):
                cx, cy = (ax[u] + ax[u + 1]) / 2, (ay[v] + ay[v + 1]) / 2
                P = Point(cx, cy)
                sahip = next((o["ad"] for o in self.oda_bosluklari if o["poly"].contains(P)), None)
                if sahip is None and not self.govde_dis.contains(P) and dis_ad:
                    sahip = dis_ad
                if sahip is None:
                    # duvar üstüne düşen dar hücre: en yakın odaya ver
                    en = min(self.oda_bosluklari, key=lambda o: o["poly"].distance(P))
                    sahip = en["ad"]
                    self.sapmalar.append(f"Hücre ({u},{v}) merkezi duvarda/dışarıda; en yakın oda {sahip} alındı")
                hucre[(u, v)] = sahip
        self.hucre = hucre
        mahal = []
        adlar = [o["ad"] for o in self.oda_bosluklari] + ([dis_ad] if dis_ad else [])
        turler = {o["ad"]: o["tur"] for o in self.oda_bosluklari}
        if dis_ad:
            turler[dis_ad] = dis_tur
        for ad in adlar:
            cells = {c for c, s in hucre.items() if s == ad}
            if not cells:
                self.sapmalar.append(f"{ad}: ızgarada hücresi yok (çok dar?) — İş Emri'ne alınmadı")
                continue
            mahal.append({"ad": ad, "tur": turler[ad], "konum_pano": Cikarici.dikdortgenler(cells)})
        self.mahal_listesi = mahal
        return mahal

    # ------------------------------------------------------------------ 5. açıklıklar
    def _oda_at(self, x, y):
        P = Point(x, y)
        for o in self.oda_bosluklari:
            if o["poly"].contains(P):
                return o["ad"]
        if not self.govde_dis.contains(P):
            return self._dis_ad()
        return None

    def _dis_ad(self):
        dis = [m["ad"] for m in self.mahal_listesi if m["tur"] in G.ACIK_MAHAL_TURLERI]
        return dis[0] if dis else G.OUT

    def acikliklar(self):
        out = []
        for p in self.k["pencereler"]:
            x0, y0, x1, y1 = p["kutu"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            yatay = (x1 - x0) >= (y1 - y0)
            if yatay:
                a, b = self._oda_at(cx, cy - 25), self._oda_at(cx, cy + 25)
            else:
                a, b = self._oda_at(cx - 25, cy), self._oda_at(cx + 25, cy)
            acik = lambda n: n in (None, G.OUT) or any(m["ad"] == n and m["tur"] in G.ACIK_MAHAL_TURLERI for m in self.mahal_listesi)
            if not acik(a) and acik(b):
                mahal, duvar = a, ("arka" if yatay else "sag")
            elif not acik(b) and acik(a):
                mahal, duvar = b, ("on" if yatay else "sol")
            else:
                self.sapmalar.append(f"Pencere {p['olcu']} ({_r(cx)},{_r(cy)}): iki yanı da oda/dış değil ({a}/{b}) — atlandı")
                continue
            olcu = p["olcu"] or ("120x120" if abs(p["en_cizim"] - 120) < 5 else "60x40")
            if olcu not in G.PENCERE_OLCULERI:
                self.sapmalar.append(f"Pencere {olcu}: katalog dışı — atlandı (kural tablosu bekliyor)")
                continue
            out.append({"tur": "pencere", "olcu": olcu, "mahal": mahal, "duvar": duvar,
                        "_k": {"yon": "x" if yatay else "y", "orta": cx if yatay else cy, "c": cy if yatay else cx}})
        for d in self.k["kapilar"]:
            hx, hy = d["mentese"]; kx, ky = d["kapali_uc"]; ox, oy = d["kanat_ucu"]
            yatay = abs(hy - ky) < abs(hx - kx)
            orta = ((hx + kx) / 2) if yatay else ((hy + ky) / 2)
            c = hy if yatay else hx
            if yatay:
                acilis = 1 if oy > c else -1
                icine = self._oda_at(orta, c + 30 * acilis); disindan = self._oda_at(orta, c - 30 * acilis)
            else:
                acilis = 1 if ox > c else -1
                icine = self._oda_at(c + 30 * acilis, orta); disindan = self._oda_at(c - 30 * acilis, orta)
            if None in (icine, disindan) or icine == disindan:
                self.sapmalar.append(f"Kapı ({_r(hx)},{_r(hy)}): iki yanı çözülemedi ({disindan}→{icine}) — atlandı")
                continue
            if G.OUT in (icine, disindan):
                self.sapmalar.append(f"Kapı ({_r(hx)},{_r(hy)}) bina dışına açılıyor; Motor v1 desteklemiyor — atlandı")
                continue
            acik_t = {m["ad"] for m in self.mahal_listesi if m["tur"] in G.ACIK_MAHAL_TURLERI}
            tur = "dis_kapi" if (icine in acik_t or disindan in acik_t) else "ic_kapi"
            h_ofs = ((hx if yatay else hy) - orta)
            sag = ((h_ofs > 0) if acilis > 0 else (h_ofs < 0)) if yatay else ((h_ofs < 0) if acilis > 0 else (h_ofs > 0))
            std = 82 if tur == "ic_kapi" else 90
            if abs(d["genislik_cizim"] - std) > 1:
                self.sapmalar.append(f"{disindan}→{icine} kapısı: çizimde {_r(d['genislik_cizim'])} cm, İş Emri {std} (standart)")
            out.append({"tur": tur, "olcu": std, "arasi": [disindan, icine], "mentese": "sag" if sag else "sol",
                        "_k": {"yon": "x" if yatay else "y", "orta": orta, "c": c}})
        self.aciklik_listesi = out
        return out

    # ------------------------------------------------------------------ 6. İş Emri + pano indeksleri
    def is_emri(self) -> dict:
        ie = {
            "is_emri_no": f"PM-BAYI-{self.kod}", "revizyon": 1,
            "talep": {"bayi": self.bayi, "musteri_adi": self.kod,
                      "metin": f"{self.k['kaynak']['dosya']} bayi planından çözümleyici ile çıkarıldı (serbest aks denemesi)"},
            "yapi": {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": 250, "olcu_kaynagi": "bayi_plani",
                     "referans_model": None, "grid": {"x_pano": self.nx2 / 2, "y_pano": self.ny2 / 2},
                     "aks_cm": {"x": self.aks["x"], "y": self.aks["y"]},
                     "kisa_kenar": "x", "giris_cephesi": "on", "dis_dusey_duvar": "aks_disinda"},
            "mahaller": self.mahal_listesi, "acik_sinirlar": [],
            "acikliklar": [],
            "cati": {"tip": "besik", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "kisa_kenar"},
            "cikti": {"pdf": True, "dxf": True, "pafta": "A2", "icerik": ["aksli_plan", "alanli_kopya", "montaj_kopyasi", "on_gorunus", "cati_profili", "ozellik_tablosu"]},
            "varsayimlar": [f"Ölçü bayinin planından (dış {self.W}×{self.H} cm); akslar bayinin duvar eksenlerinden. Ön cephe = sayfa altı."],
            "eksikler": [],
        }
        if self.W > self.H:
            raise ValueError("Kısa kenar x olmalı (plan döndürülmeli)")
        plan0 = G.kur({**ie, "acikliklar": []})
        # kıymık pano (< 5 cm) denetimi: koşu ucu modüle ≤ 1 cm uzaksa ilgili aksı kaydır ve yeniden kur
        for _ in range(6):
            kiymik = [p for p in plan0.panolar if p.boy < 5.0]
            if not kiymik:
                break
            p = kiymik[0]; d = p.duvar
            liste = self.aks["x"] if d.yon == "x" else self.aks["y"]
            uc = p.a1
            i = min(range(1, len(liste) - 1), key=lambda j: abs(liste[j] - uc), default=None)
            if i is None or abs(liste[i] - uc) > 8.0:
                self.sapmalar.append(f"Kıymık pano {p.boy} cm (duvar {d.id}) — aks bulunamadı, düzeltilmedi"); break
            eski = liste[i]; liste[i] = round(liste[i] - p.boy, 2)
            (self.notlar if p.boy <= 1.0 else self.sapmalar).append(
                f"Kıymık pano {p.boy} cm (duvar {d.id}): aks {d.yon} {eski} → {liste[i]} ({-p.boy:+} cm; koşu modüle oturtuldu — bayi bu köşede özel panoyu koşu başına koyuyor, Motor sona)")
            G.aks_ayarla(self.aks["x"], self.aks["y"])
            ie["yapi"]["aks_cm"] = {"x": self.aks["x"], "y": self.aks["y"]}
            plan0 = G.kur({**ie, "acikliklar": []})
        NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
        self.aciklik_sapmalari = []
        for ac in self.aciklik_listesi:
            k = ac["_k"]
            if ac["tur"] == "pencere":
                w = G.PENCERE_OLCULERI[ac["olcu"]][0]
                cand = G._edges_of_room_side(plan0.duvarlar, ac["mahal"], NORMAL[ac["duvar"]])
            else:
                w = float(ac["olcu"]); cand = G._edges_between(plan0.duvarlar, ac["arasi"][0], ac["arasi"][1])
            panolar = []
            for d, k0, k1 in cand:
                lo = G.X(k0 / 2) if d.yon == "x" else G.Y(k0 / 2)
                hi = G.X(k1 / 2) if d.yon == "x" else G.Y(k1 / 2)
                for p in d.panolar:
                    mid = (p.a0 + p.a1) / 2
                    if mid - w / 2 >= lo - 1e-6 and mid + w / 2 <= hi + 1e-6 and p.boy >= w + 4 and p not in [q for _, q in panolar]:
                        panolar.append((d, p))
            panolar.sort(key=lambda dp: dp[1].a0)
            ad = ac.get("mahal") or "→".join(ac["arasi"])
            if not panolar:
                self.sapmalar.append(f"{ac['tur']} {ad}: bu duvarda {int(w)} cm'lik açıklığı alacak tam pano yok — atlandı")
                continue
            en = min(range(len(panolar)), key=lambda i: abs((panolar[i][1].a0 + panolar[i][1].a1) / 2 - k["orta"]))
            p = panolar[en][1]
            fark = k["orta"] - (p.a0 + p.a1) / 2
            ac2 = {kk: v for kk, v in ac.items() if kk != "_k"}
            ac2["pano"] = en
            ie["acikliklar"].append(ac2)
            self.aciklik_sapmalari.append({"aciklik": f"{ac['tur']} {ad}", "bayi_merkez": _r(k["orta"]), "motor_merkez": _r((p.a0 + p.a1) / 2), "fark_cm": _r(fark)})
            if abs(fark) > 3:
                self.sapmalar.append(f"{ac['tur']} {ad}: bayi merkezi {_r(k['orta'])}, Motor pano merkezi {_r((p.a0 + p.a1) / 2)} → {_r(fark):+} cm (açıklık panoda ortalanır kuralı)")
        # son kurulum; hata veren açıklığı düşür (çıkarıcı ile aynı davranış)
        for _ in range(12):
            try:
                self.plan = G.kur(ie); break
            except G.IsEmriHatasi as e:
                msg = str(e)
                dusen = next((i for i, a in enumerate(ie["acikliklar"]) if str(a) in msg), None)
                if dusen is None:
                    raise
                a = ie["acikliklar"].pop(dusen)
                self.sapmalar.append(f"Açıklık düşürüldü (Motor: {msg[:110]})")
                ie["eksikler"].append(f"{a.get('tur')} {a.get('mahal') or a.get('arasi')}: {msg[:90]}")
        self.ie = ie
        return ie

    def calistir(self):
        self.duvarlar(); self.odalar(); self.akslar(); self.mahaller(); self.acikliklar()
        return self.is_emri()

    def rapor(self) -> dict:
        alan = []
        for m in self.mahal_listesi:
            etiket = next((o["etiket"]["m2_etiket"] for o in self.oda_bosluklari if o.get("ad") == m["ad"] and o.get("etiket")), None)
            if etiket is None and getattr(self, "dis_etiket", None) and m["tur"] in G.ACIK_MAHAL_TURLERI:
                etiket = self.dis_etiket.get("m2_etiket")
            mm = self.plan.mahaller.get(m["ad"])
            bayi_bosluk = next((o["poly"].area / 1e4 for o in self.oda_bosluklari if o.get("ad") == m["ad"]), None)
            alan.append({"mahal": m["ad"], "bayi_etiket_m2": etiket, "bayi_cizim_net_m2": _r(bayi_bosluk, 2) if bayi_bosluk else None,
                         "motor_net_m2": _r(mm.alan_m2, 2) if mm else None})
        return {"aks_cm": self.aks, "grid": {"x": self.nx2 / 2, "y": self.ny2 / 2}, "alanlar": alan,
                "aciklik_sapmalari": self.aciklik_sapmalari, "sapmalar": self.sapmalar, "notlar": self.notlar,
                "motor_uyarilari": self.plan.uyarilar}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("kroki"); ap.add_argument("--kod", required=True); ap.add_argument("--cikti", required=True)
    ap.add_argument("--motor", action="store_true")
    a = ap.parse_args(argv)
    kroki = json.loads(Path(a.kroki).read_text(encoding="utf-8"))
    out = Path(a.cikti); out.mkdir(parents=True, exist_ok=True)
    c = KrokiIsEmri(kroki, a.kod)
    ie = c.calistir()
    rap = c.rapor()
    (out / "is_emri.json").write_text(json.dumps(ie, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "donusum_raporu.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    if a.motor:
        from motor import dxf_out
        res = dxf_out.uret(ie, out / "motor", pdf_hatada=True)
        print("Motor:", {k: v for k, v in res.items() if k in ("dxf", "pdf", "tani_pdf", "validation_passed", "duration_s")})


if __name__ == "__main__":
    main()
