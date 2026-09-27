"""Portman çözümleyici — vektör PDF (AutoCAD/ArchiCAD çıktısı) → Ölçülü Kroki (cm) + normalize DXF.

Amaç: bayinin gönderdiği CAD çıkışlı PDF'i, LLM'e güvenmeden, PDF'in kendi geometrisinden okumak.
Çıktı iki şeydir:
  1. kroki.json  — kaynaktan bağımsız ara biçim (cm; orijin ön-sol dış köşe, +x sağa, +y arkaya).
                   Her değerin yanında nereden okunduğu (kanıt) durur.
  2. normalize.dxf — çıkarıcının (motor/cikarici.py) beklediği katman düzeninde çizim
                   (DUVAR / Pencere / Kapı / Veranda + MTEXT etiketler). Böylece bayi PDF'i de katalog DXF'i
                   ile aynı hattan (çıkarıcı → İş Emri → Motor) geçer.

Ölçek iki bağımsız yoldan bulunur ve karşılaştırılır:
  (a) Pano modülü: duvar parçalarının en sık boyu = 125,5 cm varsayımı.
  (b) Ölçü yazıları: en büyük yatay/düşey ölçü değeri ↔ dış duvar kutusu.
İkisi %0,5'ten fazla ayrışırsa kroki "ÖLÇEK ŞÜPHELİ" işaretlenir (insan kontrolü şart).

LLM yok. Katman adları çizimciye göre değişir; burada tanınanlar KATMAN_* sözlüklerinde. Tanınmayan çizim
stili (ör. her şey tek katmanda) → CozumlemeHatasi → görsel/LLM yoluna düşer.
"""
from __future__ import annotations
import json, math, re, statistics, unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
import ezdxf
from shapely.geometry import box as sbox, Polygon, MultiPolygon
from shapely.ops import unary_union

MOD = 125.5
KATMAN_DUVAR = {"0", "duvar", "dis duvar", "ic duvar"}
KATMAN_PENCERE = {"pencere"}
KATMAN_KAPI = {"kapi"}
KATMAN_YAZI = {"yazi", "olcu", "text"}
PENCERE_RE = re.compile(r"^(\d{2,3})\s*[/xX×]\s*(\d{2,3})$")
M2_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m\s*[2²]", re.I)
SAYI_RE = re.compile(r"^\d{2,4}(?:[.,]\d{1,2})?$")
ODA_KELIMELERI = ("yatak", "oda", "salon", "mutfak", "banyo", "wc", "hol", "veranda", "antre", "koridor", "balkon",
                  "teras", "yasam", "kiler", "depo", "giyinme", "calisma", "dus", "lavabo", "camasir")


class CozumlemeHatasi(Exception):
    pass


def _norm(s: str) -> str:
    tr = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")
    s = unicodedata.normalize("NFKD", (s or "").translate(tr)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def _r(v, n=1):
    return round(float(v), n)


class VektorPDF:
    def __init__(self, pdf_yolu: str | Path, sayfa: int = 0):
        self.yol = Path(pdf_yolu)
        self.doc = pymupdf.open(str(self.yol))
        self.p = self.doc[sayfa]
        self.kanit: list[str] = []
        self.uyari: list[str] = []
        self.cizimler = self.p.get_drawings()

    # ------------------------------------------------------------------ 1. katman envanteri
    def envanter(self):
        c = Counter()
        for d in self.cizimler:
            for it in d["items"]:
                c[(d.get("layer") or "", it[0])] += 1
        self.katmanlar = c
        adlar = sorted({k[0] for k in c})
        self.kanit.append(f"PDF katmanları (OCG): {', '.join(a or '(adsız)' for a in adlar)}")
        return c

    def _katman_ogeleri(self, ad_kumesi, tur):
        out = []
        for d in self.cizimler:
            if _norm(d.get("layer") or "") in ad_kumesi:
                for it in d["items"]:
                    if it[0] == tur:
                        out.append((d, it))
        return out

    # ------------------------------------------------------------------ 2. duvar parçaları + ölçek
    def duvar_parcalari(self):
        quads = [it[1].rect for d, it in self._katman_ogeleri(KATMAN_DUVAR, "qu")]
        if len(quads) < 8:
            raise CozumlemeHatasi(f"Duvar katmanında dörtgen parça yok/az ({len(quads)}); bu çizim stili desteklenmiyor → görsel/LLM yolu")
        # tekilleştir
        tek = {}
        for r in quads:
            k = tuple(round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1))
            tek[k] = r
        self.ham_parcalar = list(tek.values())
        # ölçek (a): modül — uzun kenarların en sık değeri (pt)
        uzun = [max(r.width, r.height) for r in self.ham_parcalar]
        kisa = [min(r.width, r.height) for r in self.ham_parcalar]
        kova = Counter(round(u, 0) for u in uzun if u > 5)
        tepe, adet = kova.most_common(1)[0]
        yakin = [u for u in uzun if abs(u - tepe) <= 1.0]
        mod_pt = statistics.median(yakin)
        self.olcek_mod = MOD / mod_pt
        self.kanit.append(f"Ölçek (a) pano modülü: {len(yakin)} duvar parçasının boyu ≈ {mod_pt:.2f} pt → 125,5 cm varsayımıyla {self.olcek_mod:.5f} cm/pt")
        # duvar parçası = kalınlığı 4–11,5 cm (pencere bloğu 13 cm → dışarıda)
        s = self.olcek_mod
        self.duvar_pt = [r for r, k in zip(self.ham_parcalar, kisa) if 4.0 <= k * s <= 11.5]
        self.pencere_blok_pt = [r for r, k in zip(self.ham_parcalar, kisa) if 11.5 < k * s <= 16 and max(r.width, r.height) * s >= 50]
        xs = [v for r in self.duvar_pt for v in (r.x0, r.x1)]; ys = [v for r in self.duvar_pt for v in (r.y0, r.y1)]
        self.kutu_pt = (min(xs), min(ys), max(xs), max(ys))
        return self.duvar_pt

    def metinler(self):
        out = []
        for b in self.p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = " ".join(sp["text"] for sp in l["spans"]).strip()
                if not t:
                    continue
                bb = l["bbox"]; dx, dy = l["dir"]
                out.append({"t": t, "cx": (bb[0] + bb[2]) / 2, "cy": (bb[1] + bb[3]) / 2, "h": abs(bb[3] - bb[1]) if abs(dx) > 0.5 else abs(bb[2] - bb[0]),
                            "yatay": abs(dx) > 0.5, "bbox": bb})
        self.yazilar = out
        return out

    def olcek_dogrula(self):
        """(b) ölçü yazıları: kutu dışında duran en büyük yatay ve düşey sayı ↔ dış kutu ölçüsü."""
        x0, y0, x1, y1 = self.kutu_pt
        wpt, hpt = x1 - x0, y1 - y0
        sayilar = []
        for y in self.yazilar:
            t = y["t"].replace(",", ".")
            if SAYI_RE.match(y["t"]):
                sayilar.append((float(t), y))
        yatay = [v for v, y in sayilar if y["yatay"] and (y["cy"] < y0 or y["cy"] > y1)]
        dusey = [v for v, y in sayilar if not y["yatay"] and (y["cx"] < x0 or y["cx"] > x1)]
        self.olcek_yazi = {}
        for ad, degerler, pt in (("genislik", yatay, wpt), ("derinlik", dusey, hpt)):
            if not degerler:
                continue
            v = max(degerler)
            # birim: cm mi mm mi? modül ölçeğine göre hangisi yakınsa
            aday_cm = v if abs(v / pt - self.olcek_mod) < abs(v / 10 / pt - self.olcek_mod) else v / 10
            self.olcek_yazi[ad] = (aday_cm, aday_cm / pt)
        mesaj = []
        self.olcek = self.olcek_mod
        self.olcek_supheli = False
        for ad, (cm, s) in self.olcek_yazi.items():
            fark = (s / self.olcek_mod - 1) * 100
            mesaj.append(f"{ad} yazısı {cm:g} cm → {s:.5f} cm/pt (modülden fark %{fark:+.2f})")
            if abs(fark) > 0.5:
                self.olcek_supheli = True
        if mesaj:
            self.kanit.append("Ölçek (b) ölçü yazıları: " + "; ".join(mesaj))
        if self.olcek_yazi and not self.olcek_supheli:
            self.olcek = statistics.mean(v[1] for v in self.olcek_yazi.values())
            self.kanit.append(f"Kullanılan ölçek: ölçü yazılarından {self.olcek:.5f} cm/pt (bayinin yazdığı ölçü sözleşme ölçüsüdür; modül ile tutarlı)")
        if self.olcek_supheli:
            self.uyari.append("ÖLÇEK ŞÜPHELİ: pano modülü ile ölçü yazıları %0,5'ten fazla ayrışıyor — insan kontrolü şart")
        elif not self.olcek_yazi:
            self.uyari.append("Ölçü yazısı bulunamadı; ölçek yalnız pano modülünden (tek kanıt)")
        return self.olcek

    # ------------------------------------------------------------------ 3. koordinat dönüşümü (ön = sayfa altı)
    def cm(self, x, y):
        x0, y0, x1, y1 = self.kutu_pt
        return ((x - x0) * self.olcek, (y1 - y) * self.olcek)

    def rect_cm(self, r):
        a = self.cm(r.x0, r.y1); b = self.cm(r.x1, r.y0)
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))

    # ------------------------------------------------------------------ 4. pencereler
    def pencereler(self):
        parca = [self.rect_cm(it[1].rect) for d, it in self._katman_ogeleri(KATMAN_PENCERE, "qu")]
        parca += [self.rect_cm(it[1].rect) for d, it in self._katman_ogeleri(KATMAN_PENCERE, "re")]
        parca += [self.rect_cm(r) for r in self.pencere_blok_pt]
        kumeler = []
        for b in parca:
            b = list(b)
            for k in kumeler:
                if not (b[0] > k[2] + 2 or b[2] < k[0] - 2 or b[1] > k[3] + 2 or b[3] < k[1] - 2):
                    k[0], k[1], k[2], k[3] = min(k[0], b[0]), min(k[1], b[1]), max(k[2], b[2]), max(k[3], b[3]); break
            else:
                kumeler.append(b)
        degisti = True
        while degisti:
            degisti = False
            for i in range(len(kumeler)):
                for j in range(i + 1, len(kumeler)):
                    a, b = kumeler[i], kumeler[j]
                    if not (a[0] > b[2] + 2 or a[2] < b[0] - 2 or a[1] > b[3] + 2 or a[3] < b[1] - 2):
                        kumeler[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]; kumeler.pop(j); degisti = True; break
                if degisti:
                    break
        # küçük (yalnız kasa köşesi) kümeleri aynı duvar hattında eşle: 60/40 gibi pencerelerde orta parça çizilmez
        kucuk = [k for k in kumeler if max(k[2] - k[0], k[3] - k[1]) < 25]
        buyuk = [k for k in kumeler if max(k[2] - k[0], k[3] - k[1]) >= 25]
        kullanildi = set()
        for i, a in enumerate(kucuk):
            if i in kullanildi:
                continue
            en_iyi = None
            for j, b in enumerate(kucuk):
                if j <= i or j in kullanildi:
                    continue
                ayni_yatay = abs((a[1] + a[3]) / 2 - (b[1] + b[3]) / 2) < 4
                ayni_dusey = abs((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2) < 4
                m = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                boy = (m[2] - m[0]) if ayni_yatay else ((m[3] - m[1]) if ayni_dusey else 0)
                if 40 <= boy <= 210 and (en_iyi is None or boy < en_iyi[0]):
                    en_iyi = (boy, j, m)
            if en_iyi:
                kullanildi.update({i, en_iyi[1]}); buyuk.append(en_iyi[2])
        kumeler = buyuk
        etiketler = []
        for y in self.yazilar:
            m = PENCERE_RE.match(y["t"].strip())
            if m:
                x, yy = self.cm(y["cx"], y["cy"])
                etiketler.append({"x": x, "y": yy, "en": int(m.group(1)), "boy": int(m.group(2)), "metin": y["t"]})
        W, H = self.W, self.H
        out = []
        for k in kumeler:
            yatay = (k[2] - k[0]) >= (k[3] - k[1])
            en = (k[2] - k[0]) if yatay else (k[3] - k[1])
            if en < 40:
                continue
            cx, cy = (k[0] + k[2]) / 2, (k[1] + k[3]) / 2
            et = min(etiketler, key=lambda e: math.hypot(e["x"] - cx, e["y"] - cy)) if etiketler else None
            uzak = math.hypot(et["x"] - cx, et["y"] - cy) if et else 1e9
            if yatay:
                duvar = "on" if cy < H / 2 else "arka"
            else:
                duvar = "sol" if cx < W / 2 else "sag"
            olcu = None
            if et and uzak < 120:
                olcu = f"{et['en']}x{et['boy']}"
                if abs(et["en"] - en) > 8:
                    self.uyari.append(f"Pencere ({_r(cx)},{_r(cy)}): etiket {et['metin']} ama çizim eni {_r(en)} cm")
            else:
                self.uyari.append(f"Pencere ({_r(cx)},{_r(cy)}) eni {_r(en)} cm: yakında ölçü etiketi yok")
            out.append({"kutu": [_r(v) for v in k], "en_cizim": _r(en), "olcu": olcu, "duvar_yonu": duvar,
                        "etiket": et["metin"] if et and uzak < 120 else None, "etiket_uzaklik_cm": _r(uzak)})
        self.pencere_listesi = out
        self.kanit.append(f"Pencere: {len(out)} adet (Pencere katmanı + pencere blokları), {sum(1 for p in out if p['olcu'])} tanesi etiketle eşleşti")
        return out

    # ------------------------------------------------------------------ 5. kapılar (kanat çizgisi + yay)
    def kapilar(self):
        cizgi = [(it[1], it[2]) for d, it in self._katman_ogeleri(KATMAN_KAPI, "l")]
        yay = [(it[1], it[4]) for d, it in self._katman_ogeleri(KATMAN_KAPI, "c")]
        TOL = 0.8
        def ayni(p, q): return abs(p.x - q.x) < TOL and abs(p.y - q.y) < TOL
        out = []
        kullanilan = set()
        for a, b in cizgi:
            for i, (y0, y1) in enumerate(yay):
                if i in kullanilan:
                    continue
                for acik_uc, mentese in ((a, b), (b, a)):
                    for ortak, kapali in ((y0, y1), (y1, y0)):
                        if ayni(acik_uc, ortak):
                            kullanilan.add(i)
                            H_ = self.cm(mentese.x, mentese.y); A_ = self.cm(acik_uc.x, acik_uc.y); K_ = self.cm(kapali.x, kapali.y)
                            g = math.hypot(A_[0] - H_[0], A_[1] - H_[1])
                            out.append({"mentese": [_r(v) for v in H_], "kanat_ucu": [_r(v) for v in A_], "kapali_uc": [_r(v) for v in K_], "genislik_cizim": _r(g)})
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
        self.kapi_listesi = out
        self.kanit.append(f"Kapı: {len(out)} adet (kanat çizgisi + açılış yayı eşleşmesi)")
        if len(out) < len(cizgi):
            self.uyari.append(f"{len(cizgi) - len(out)} kapı kanadı yayla eşleşmedi")
        return out

    # ------------------------------------------------------------------ 6. mahal etiketleri
    def mahaller(self):
        yaz = [y for y in self.yazilar if y["yatay"]]
        out, kullan = [], set()
        for i, y in enumerate(yaz):
            n = _norm(y["t"])
            if not any(k in n for k in ODA_KELIMELERI) or M2_RE.search(y["t"]):
                continue
            # altındaki m² satırı
            m2 = None
            for j, z in enumerate(yaz):
                if j == i or j in kullan:
                    continue
                if 0 < z["cy"] - y["cy"] < 2.2 * max(y["h"], 1) and abs(z["cx"] - y["cx"]) < 25:
                    mm = M2_RE.search(z["t"])
                    if mm:
                        m2 = float(mm.group(1).replace(",", ".")); kullan.add(j); break
            x, yy = self.cm(y["cx"], y["cy"])
            out.append({"ad": y["t"].strip(), "x": _r(x), "y": _r(yy), "m2_etiket": m2})
        self.mahal_listesi = out
        top = sum(m["m2_etiket"] or 0 for m in out)
        self.kanit.append(f"Mahal etiketi: {len(out)} ({', '.join(m['ad'] for m in out)}); etiket alanları toplamı {top:.2f} m²")
        return out

    # ------------------------------------------------------------------ 7. veranda (kesik çizgi, duvar dışında)
    def veranda(self):
        seg = []
        for d, it in self._katman_ogeleri(KATMAN_DUVAR, "l"):
            a, b = self.cm(it[1].x, it[1].y), self.cm(it[2].x, it[2].y)
            L = math.hypot(a[0] - b[0], a[1] - b[1])
            if L < 2 or L > 25 or (abs(a[0] - b[0]) > 0.3 and abs(a[1] - b[1]) > 0.3):
                continue
            if any(p["kutu"][0] - 3 <= min(a[0], b[0]) and max(a[0], b[0]) <= p["kutu"][2] + 3 and
                   p["kutu"][1] - 3 <= min(a[1], b[1]) and max(a[1], b[1]) <= p["kutu"][3] + 3 for p in self.pencere_listesi):
                continue
            # bina kutusu dışında ya da kutunun boş köşesinde kalan kısa kesikli parçalar
            if min(a[1], b[1]) < -2 or max(a[0], b[0]) > self.W + 2 or min(a[0], b[0]) < -2 or max(a[1], b[1]) > self.H + 2:
                seg.append((a, b))
        if not seg:
            self.veranda_kutu = None
            return None
        xs = [p[0] for s in seg for p in s]; ys = [p[1] for s in seg for p in s]
        self.veranda_kutu = [_r(min(xs)), _r(min(ys)), _r(max(xs)), _r(max(ys))]
        self.veranda_segs = seg
        self.kanit.append(f"Veranda sınırı (kesik çizgi, bina kutusu dışı): {len(seg)} parça, kutu {self.veranda_kutu}")
        return self.veranda_kutu

    # ------------------------------------------------------------------ 8. özel pano analizi (bayinin kendi pano dizilimi)
    def pano_dizilimi(self):
        """Duvar parçalarını dış cephe ve iç duvar koşularına göre dizip boylarını pano birimine çevirir.
        Standart dışı boylar (125,5 / 62,75 / köşe değil) = özel pano."""
        par = [self.rect_cm(r) for r in self.duvar_pt]
        W, H = self.W, self.H
        cephe = {"sol": [], "sag": [], "on": [], "arka": []}
        ic = []
        for r in par:
            w, h = r[2] - r[0], r[3] - r[1]
            if w >= h:  # yatay parça
                if r[1] < 1.5: cephe["on"].append((r[0], r[2], w, h))
                elif r[3] > H - 1.5: cephe["arka"].append((r[0], r[2], w, h))
                else: ic.append(("x", r[1], r[0], r[2], w, h))
            else:
                if r[0] < 1.5: cephe["sol"].append((r[1], r[3], h, w))
                elif r[2] > W - 1.5: cephe["sag"].append((r[1], r[3], h, w))
                else: ic.append(("y", r[0], r[1], r[3], h, w))
        def sinif(L, t):
            if abs(L - MOD) <= 1.2: return "tam"
            if abs(L - MOD / 2) <= 1.2: return "yarim"
            if L <= 11: return "kose"
            return "ozel"
        rap = {}
        for ad, lst in cephe.items():
            lst.sort()
            dizi = [(_r(L), sinif(L, t)) for a0, a1, L, t in lst]
            rap[ad] = {"parcalar": dizi, "ozel": [L for L, s in dizi if s == "ozel"],
                       "tam": sum(1 for _, s in dizi if s == "tam"), "yarim": sum(1 for _, s in dizi if s == "yarim")}
        ozel_ic = sorted({_r(p[4]) for p in ic if sinif(p[4], p[5]) == "ozel" and p[4] > 20})
        self.pano_raporu = {"cephe": rap, "ic_ozel_boylar": ozel_ic}
        oz = {k: v["ozel"] for k, v in rap.items() if v["ozel"]}
        self.kanit.append(f"Bayinin pano dizilimi — cephelerde özel pano: {oz or 'yok'}; iç duvarlarda özel boylar: {ozel_ic}")
        return self.pano_raporu

    # ------------------------------------------------------------------ hepsi
    def calistir(self):
        self.envanter(); self.duvar_parcalari(); self.metinler(); self.olcek_dogrula()
        x0, y0, x1, y1 = self.kutu_pt
        self.W, self.H = (x1 - x0) * self.olcek, (y1 - y0) * self.olcek
        self.kanit.append(f"Dış kutu (duvar dış yüzleri): {self.W:.1f} × {self.H:.1f} cm")
        self.pencereler(); self.kapilar(); self.mahaller(); self.veranda(); self.pano_dizilimi()
        return self.kroki()

    def kroki(self) -> dict:
        duvarlar = [[_r(v) for v in self.rect_cm(r)] for r in self.duvar_pt]
        return {
            "sema": "portman.olculu_kroki/0.1",
            "kaynak": {"dosya": self.yol.name, "tur": "vektor_pdf", "olcek_cm_pt": round(self.olcek, 5),
                       "olcek_supheli": self.olcek_supheli, "on_cephe": "sayfa_alti (varsayım)"},
            "dis_kutu_cm": {"W": _r(self.W), "H": _r(self.H)},
            "olcu_yazilari_cm": {k: v[0] for k, v in self.olcek_yazi.items()},
            "duvar_parcalari": duvarlar,
            "pencereler": self.pencere_listesi,
            "kapilar": self.kapi_listesi,
            "mahaller": self.mahal_listesi,
            "veranda_kutu": self.veranda_kutu,
            "pano_dizilimi": self.pano_raporu,
            "kanit": self.kanit,
            "uyari": self.uyari,
        }

    # ------------------------------------------------------------------ normalize DXF (çıkarıcı düzeni)
    def normalize_dxf(self, yol: str | Path):
        doc = ezdxf.new("R2010", setup=True)
        for ad in ("DUVAR", "Pencere", "Kapı", "Veranda", "YAZI"):
            if ad not in doc.layers:
                doc.layers.add(ad)
        msp = doc.modelspace()
        # duvarlar: parçaların birleşimi → dış/iç sınır halkaları (pano ekleri kaybolur; çıkarıcı yüz çizgisi arar)
        parcalar = [sbox(*self.rect_cm(r)) for r in self.duvar_pt]
        birlesim = unary_union([p.buffer(0.05, join_style=2) for p in parcalar]).buffer(-0.05, join_style=2)
        polys = [birlesim] if isinstance(birlesim, Polygon) else list(birlesim.geoms)
        for poly in polys:
            for halka in [poly.exterior, *poly.interiors]:
                pts = [(round(x, 2), round(y, 2)) for x, y in halka.coords]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "DUVAR"})
        for p in self.pencere_listesi:
            k = p["kutu"]
            msp.add_lwpolyline([(k[0], k[1]), (k[2], k[1]), (k[2], k[3]), (k[0], k[3])], close=True, dxfattribs={"layer": "Pencere"})
        for kp in self.kapi_listesi:
            msp.add_lwpolyline([tuple(kp["kapali_uc"]), tuple(kp["mentese"]), tuple(kp["kanat_ucu"])], dxfattribs={"layer": "Kapı"})
        if getattr(self, "veranda_segs", None):
            for a, b in self.veranda_segs:
                msp.add_line(a, b, dxfattribs={"layer": "Veranda"})
        for m in self.mahal_listesi:
            metin = m["ad"] + (f"\\P{m['m2_etiket']} m²" if m["m2_etiket"] is not None else "")
            t = msp.add_mtext(metin, dxfattribs={"layer": "YAZI", "char_height": 12, "attachment_point": 5})
            t.dxf.insert = (m["x"], m["y"])
        for y in self.yazilar:
            if PENCERE_RE.match(y["t"].strip()):
                x, yy = self.cm(y["cx"], y["cy"])
                t = msp.add_mtext(y["t"].strip(), dxfattribs={"layer": "YAZI", "char_height": 10, "attachment_point": 5})
                t.dxf.insert = (x, yy)
        doc.saveas(str(yol))
        return yol


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("--cikti", required=True)
    a = ap.parse_args(argv)
    out = Path(a.cikti); out.mkdir(parents=True, exist_ok=True)
    v = VektorPDF(a.pdf)
    kroki = v.calistir()
    (out / "kroki.json").write_text(json.dumps(kroki, ensure_ascii=False, indent=1), encoding="utf-8")
    v.normalize_dxf(out / "normalize.dxf")
    print("\n".join(kroki["kanit"])); print("UYARI:", *kroki["uyari"], sep="\n - ")


if __name__ == "__main__":
    main()
