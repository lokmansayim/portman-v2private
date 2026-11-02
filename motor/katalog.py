"""Malzeme kataloğu (MALZEME_KATALOGU.json v1.4.3) — kod arama ve yeni kod tahsisi.

Kod aileleri: D dış pano, I iç pano, P pencere, K kapı, B bağlantı, V veranda.
Kodlar aile içinde kalıcıdır; mevcut kodun ölçüsü/işlevi değiştirilmez, yeni ölçüye yeni kod verilir.
"""
from __future__ import annotations
import json, re
from pathlib import Path

KATALOG_YOLU = Path(__file__).resolve().parent / "malzeme_katalogu.json"
OTOMATIK_NOT = "Portman motor tarafından otomatik tahsis edildi; teyit edilmeli."
VASISTAS_EN_COK_BOY_CM = 60          # BK-13: boy ≤ 60 vasistas (pafta yazısı gibi; `sunum.VASISTAS_ESIGI_CM`)


def pencere_turu(olcu: str) -> str:
    """BK-13: bugünkü üç ölçü dışındaki pencereli panonun türü ("150x140" → "P150x140"); etiketi `Katalog.pano` yazar."""
    m = re.fullmatch(r"(\d+)x(\d+)", olcu)
    if not m:
        raise ValueError(f"pencere ölçüsü okunamadı: {olcu}")
    return f"P{int(m[1])}x{int(m[2])}"


def _kind_from_label(label: str) -> str:
    l = label.replace("İ", "i").replace("I", "ı").lower()
    olc = lambda o: re.search(rf"(?<!\d){o}(?!\d)", l.replace("x", "×"))   # BK-13: "160×40" P03 değil
    if olc("120×120"): return "P01"
    if olc("120×180"): return "P02"
    if olc("60×40"): return "P03"
    m = re.search(r"(\d+)×(\d+) (?:pencereli|vasistaslı) pano", l)       # BK-13: öteki ölçülerin etiketi
    if m: return f"P{int(m[1])}x{int(m[2])}"
    if "kapısız" in l: return "OPEN"
    if "iç kapılı" in l: return "K01"
    if "dış kapılı" in l: return "K02"
    return "DOLU"


class Katalog:
    def __init__(self, path=KATALOG_YOLU):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.malzemeler = self.data["malzemeler"]
        self.yeni = []          # bu işte tahsis edilen yeni kodlar
        self.t_dis_cm, self.t_ic_cm, self.yukseklik_cm = 10.0, 6.0, 250.0   # deneme: Cizici İş Emri'nden ayarlar
        self._index = {}
        for code, m in self.malzemeler.items():
            self._index[self._key_of(code, m)] = code

    def _key_of(self, code, m):
        fam = code[0]; dims = m.get("dimensions_mm") or []
        if fam in "DI":
            return (fam, round(float(dims[0]), 1), _kind_from_label(m["label"]), round(float(dims[1]), 1), round(float(dims[2]), 1))
        if fam == "P":
            return ("P", round(float(dims[0]), 1), round(float(dims[1]), 1))
        if fam == "K":
            return ("K", round(float(dims[0]), 1))
        if fam == "B":
            return ("B", tuple(sorted(round(float(v), 1) for v in dims[:2] if v is not None)))
        if fam == "V":
            lab = m["label"].replace("İ", "i").replace("I", "ı").lower()
            yon = "YAN" if "yan" in lab else ("ON" if "ön" in lab else "DIKME")
            return ("V", round(float(dims[0]), 1), yon)
        return (fam, code)

    def _tahsis(self, fam, key, label, group, dims, note=""):
        nums = [int(c[1:]) for c in self.malzemeler if c[0] == fam and c[1:].isdigit()]
        code = f"{fam}{(max(nums) + 1) if nums else 1:02d}"
        entry = {"code": code, "group": group, "label": label, "dimensions_mm": dims, "note": note or OTOMATIK_NOT, "unit": "adet"}
        self.malzemeler[code] = entry; self._index[key] = code; self.yeni.append(entry)
        return code

    def pano(self, dis: bool, boy_cm: float, kind: str, yukseklik_cm: float | None = None) -> str:
        fam = "D" if dis else "I"; L = round(boy_cm * 10, 1)
        yukseklik_cm = self.yukseklik_cm if yukseklik_cm is None else yukseklik_cm
        kal = round((self.t_dis_cm if dis else self.t_ic_cm) * 10, 1)
        key = (fam, L, kind, kal, round(yukseklik_cm * 10, 1))
        if key in self._index:
            return self._index[key]
        m = re.fullmatch(r"P(\d+)x(\d+)", kind)              # BK-13: üç ölçü dışındaki pencereli pano
        if m:
            en, boy = int(m[1]), int(m[2])
            return self._tahsis(fam, key, f"{en}×{boy} " + ("vasistaslı pano" if boy <= VASISTAS_EN_COK_BOY_CM else "pencereli pano"),
                                "Dış duvar panoları" if dis else "İç duvar panoları", [L, int(kal) if kal == int(kal) else kal, round(yukseklik_cm * 10)],
                                note="Pencere ayrı kalem; pano tek parça sayıldı. " + OTOMATIK_NOT)
        lab = {"DOLU": "Özel dolu pano" if abs(boy_cm - 125.5) > 1e-6 else "Dolu pano",
               "P01": "120×120 pencereli pano", "P02": "120×180 pencereli pano", "P03": "60×40 vasistaslı pano",
               "K01": "İç kapılı özel pano" if abs(boy_cm - 125.5) > 1e-6 else "İç kapılı pano",
               "K02": "Dış kapılı özel pano" if abs(boy_cm - 125.5) > 1e-6 else "Dış kapılı pano",
               "OPEN": "Kapısız geçişli pano"}[kind]
        return self._tahsis(fam, key, lab, "Dış duvar panoları" if dis else "İç duvar panoları", [L, int(kal) if kal == int(kal) else kal, round(yukseklik_cm * 10)])

    def pencere(self, en_cm: float, boy_cm: float, esik_cm: float | None = None) -> str:
        key = ("P", round(en_cm * 10, 1), round(boy_cm * 10, 1))
        if key in self._index: return self._index[key]
        ad = "Vasistas" if boy_cm <= VASISTAS_EN_COK_BOY_CM else "Pencere"      # BK-13: P01–P03 gibi ad ve eşik notu
        note = "" if esik_cm is None else f"Ölçü en × yükseklik; eşik {round(esik_cm * 10)} mm. " + OTOMATIK_NOT
        return self._tahsis("P", key, f"{ad} {int(en_cm)}×{int(boy_cm)}", "Kapı ve pencereler", [round(en_cm * 10, 1), round(boy_cm * 10, 1), None], note=note)

    def kapi(self, aciklik_cm: float, dis: bool) -> str:
        key = ("K", round(aciklik_cm * 10, 1))
        if key in self._index: return self._index[key]
        return self._tahsis("K", key, ("Dış kapı" if dis else "İç kapı") + f" {int(aciklik_cm)}", "Kapı ve pencereler", [round(aciklik_cm * 10, 1), None, None],
                            note=f"{int(aciklik_cm*10)} mm plandaki açıklıktır; ürün ölçüsü siparişte teyit edilmeli.")

    def baglanti(self, tur: str) -> str:
        """tur: 'ic_kose' (30×60) | 'dis_kose' (100×50) | 'uclu_h' | 'dikme'"""
        td, ti = round(self.t_dis_cm * 10, 1), round(self.t_ic_cm * 10, 1)
        keys = {"ic_kose": ("B", (ti / 2, ti)), "dis_kose": ("B", (td / 2, td)), "uclu_h": ("B", (ti,)), "dikme": ("B", (100.0, 100.0)),
                "uclu_h_dis": ("B", tuple(sorted((td, ti))) if td != ti else (td, ti, "uclu_h_dis"))}   # İE-11: dış duvardaki T (3'lü H dış); anahtar `_key_of` gibi sıralı (60, 100); BK-18: eşit kalınlıkta (100, 100) dikmenin anahtarı olur, ayrı anahtar
        key = keys[tur]
        if key in self._index: return self._index[key]
        labels = {"ic_kose": (f"{ti:g}×{ti / 2:g} iç köşe bağlantısı", [ti / 2, ti, None]), "dis_kose": (f"{td:g}×{td / 2:g} köşe bağlantısı", [td / 2, td, None]),
                  "uclu_h": (f"Üçlü H bağlantı {ti:g}", [ti, None, None]), "dikme": ("Veranda dikmesi", [100, 100, None]),
                  "uclu_h_dis": (f"Üçlü H bağlantı dış {td:g}×{ti:g}", [td, ti, None])}
        lab, dims = labels[tur]
        return self._tahsis("B", key, lab, "Bağlantı ve veranda", dims)

    def veranda_profil(self, boy_cm: float, yon: str) -> str:
        key = ("V", round(boy_cm * 10, 1), yon)
        if key in self._index: return self._index[key]
        return self._tahsis("V", key, f"Veranda {'yan' if yon == 'YAN' else 'ön'} profil gösterimi", "Bağlantı ve veranda", [round(boy_cm * 10, 1), 100, None],
                            note="Dış sınır boyu; gerçek profil kesiti/kesim boyu teyit edilmeli.")

    def kaydet_kopya(self, path):
        out = dict(self.data); out["malzemeler"] = self.malzemeler
        out["not"] = "Portman motor çalışma kopyası; yeni kodlar teyit edilmeden ana kataloğa yazılmaz."
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
