"""SKP sahnesinden inceleme seçimi: çatı ve dışlanan kök grupların KALICI kimlikle kaydı.

Codex'in prepare_viewer_data.py betiği çatı ve dışlanan grupları okuyucunun sıra numaralarıyla (ör. P9401 çatı = 223)
tutuyordu. Sıra numarası SKP okunuş sırasına bağlıdır; aynı numaralar başka bir SKP'ye (ya da yeniden okunan sürüme)
uygulanırsa yanlış parça seçilir. Burada seçim, SketchUp'ın kalıcı kimliği (`source_id`, SUEntityGetPersistentID) ve
kaynak dosyanın SHA256'sı ile kaydedilir:

  - `secim_kaydi_uret`: Codex'in sıra numaralı listelerinden kalıcı kimlikli kayıt üretir (bir kez; veri/secim_<kod>.json).
  - `sec`: kayıttaki kalıcı kimliklerle sahneden seçimi yeniden kurar. SHA farklıysa ya da bir kimlik sahnede tek bir kök
    grupta bulunamazsa DURUR; sessizce en yakın parçayı seçmez.

Seçim mantığı prepare_viewer_data.py ile aynıdır (gizli düğüm, dışlanan kök, P9401 ikinci kopya kuralı, boş geometri,
aşama numarası, sıralama). Doku küçük resimleri (PIL ile yeniden kodlanan data URI) burada üretilmez.
"""
from __future__ import annotations

import json
from pathlib import Path

INC = 0.0254


class SecimHatasi(RuntimeError):
    pass


def _kokler(sahne: dict) -> dict[int, dict]:
    return {n["id"]: n for n in sahne["nodes"] if n.get("parent") == 0}


def _kok_kimligi(dugumler: list[dict], n: dict) -> int:
    while n["parent"] not in (0, None):
        n = dugumler[n["parent"]]
    return n["id"]


def secim_kaydi_uret(sahne: dict, kod: str, cati_sira: set[int], dislanan_sira: set[int],
                     kopya_x_min_esigi_m: float | None = None, kaynak_dosya: str = "", revizyon: str = "SKP-inceleme-01") -> dict:
    kokler = _kokler(sahne)

    def kayit(sira: int) -> dict:
        n = kokler.get(sira)
        if n is None:
            raise SecimHatasi(f"{kod}: sıra {sira} bir kök grup değil")
        return {"sira": sira, "kalici_kimlik": n["source_id"], "ad": n["name"]}

    k = {"model": kod, "revizyon": revizyon, "kaynak_dosya": kaynak_dosya, "kaynak_sha256": sahne["sha256"],
         "birim": {"kaynak": sahne.get("source_units"), "hedef": sahne.get("units"), "katsayi": sahne.get("conversion")},
         "cati_kokleri": [kayit(s) for s in sorted(cati_sira)],
         "dislanan_kokler": [kayit(s) for s in sorted(dislanan_sira)],
         "kopya_kurali": None,
         "not": "Sıra numarası yalnız bu SHA256'lı okuma içindir; eşleme kalıcı kimlikle yapılır."}
    if kopya_x_min_esigi_m is not None:
        k["kopya_kurali"] = {"aciklama": "Kök grubun sınır kutusu x_min değeri eşiği aşarsa (ikinci yapı kopyası) dışarıda",
                             "x_min_esigi_m": kopya_x_min_esigi_m,
                             "dislanan": [{"sira": n["id"], "kalici_kimlik": n["source_id"], "ad": n["name"]}
                                          for n in kokler.values()
                                          if n["bbox_parent_inches"][0][0] * INC > kopya_x_min_esigi_m]}
    return k


def _cozumle(sahne: dict, kayit: dict) -> tuple[set[int], set[int], float | None]:
    if sahne.get("sha256") != kayit["kaynak_sha256"]:
        raise SecimHatasi(f"{kayit['model']}: sahnenin SHA256'sı kayıttakinden farklı; seçim uygulanmaz")
    kalici: dict[int, list[int]] = {}
    for n in _kokler(sahne).values():
        kalici.setdefault(n["source_id"], []).append(n["id"])

    def bul(liste: list[dict]) -> set[int]:
        out = set()
        for e in liste:
            adaylar = kalici.get(e["kalici_kimlik"], [])
            if len(adaylar) != 1:
                raise SecimHatasi(f"{kayit['model']}: kalıcı kimlik {e['kalici_kimlik']} ({e['ad']}) {len(adaylar)} kök grupta")
            out.add(adaylar[0])
        return out

    esik = (kayit.get("kopya_kurali") or {}).get("x_min_esigi_m")
    return bul(kayit["cati_kokleri"]), bul(kayit["dislanan_kokler"]), esik


def sec(sahne: dict, kayit: dict) -> dict:
    """Kayda göre seçili düğümleri ve ağları döndürür (selected.json'daki nodes/meshes ile aynı biçim)."""
    cati, dislanan, esik = _cozumle(sahne, kayit)
    dugumler, agler = sahne["nodes"], sahne["meshes"]
    secilen, secilen_ag = [], {}
    for n in dugumler:
        if n["hidden"]:
            continue
        ust = _kok_kimligi(dugumler, n)
        r = dugumler[ust]
        if ust in dislanan:
            continue
        if esik is not None and ust and r["bbox_parent_inches"][0][0] * INC > esik:
            continue
        g = agler[n["geometry"]]
        if not g["triangles"]:
            continue
        cati_mi = ust in cati
        sinir = r.get("bbox_parent_inches", [[0, 0, 0], [0, 0, 0]])
        minz, maxz = sinir[0][2] * INC, sinir[1][2] * INC
        asama = 3 if cati_mi else (0 if maxz < .65 or ust == 0 else (1 if n["face_count"] > 70 and maxz - minz > 2 else 2))
        oge = {k: n[k] for k in ["id", "name", "source_id", "world_transform", "material", "geometry"] if k in n}
        oge.update(root=ust, roof=cati_mi, stage=asama)
        secilen.append(oge)
        if n["geometry"] not in secilen_ag:
            secilen_ag[n["geometry"]] = {k: g[k] for k in ["vertices", "triangles", "uv", "materials"]}
            secilen_ag[n["geometry"]]["vertices"] = [[round(x, 7) for x in v] for v in g["vertices"]]
    secilen.sort(key=lambda n: (n["stage"], n["root"], n["id"]))
    malzeme = {k: {"name": m["name"], "color": m["color"], "doku_var": bool(m["texture"])} for k, m in sahne["materials"].items()}
    return {"nodes": secilen, "meshes": secilen_ag, "materials": malzeme}


def karsilastir(secim: dict, secili: dict) -> dict:
    """Yeniden kurulan seçimi selected.json ile karşılaştırır (düğümler, ağlar, malzeme adı/rengi; doku verisi hariç)."""
    dugum_ayni = secim["nodes"] == secili["nodes"]
    ag_ayni = secim["meshes"] == secili["meshes"]
    malzeme_ayni = secim["materials"] == {k: {"name": m["name"], "color": m["color"], "doku_var": bool(m["texture"])}
                                          for k, m in secili["materials"].items()}
    return {"ayni": dugum_ayni and ag_ayni and malzeme_ayni, "dugum_ayni": dugum_ayni, "ag_ayni": ag_ayni,
            "malzeme_ayni": malzeme_ayni,
            "dugum": [len(secim["nodes"]), len(secili["nodes"])], "ag": [len(secim["meshes"]), len(secili["meshes"])],
            "cati_dugumu": sum(n["roof"] for n in secim["nodes"])}


def kayit_oku(yol: str | Path) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))
