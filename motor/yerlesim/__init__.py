"""İE-15 · K2 · Çatı ve tavan katmanları: tavan omegası, aşık, çatı kaplaması, baş makas betopanı, dere ve iniş.

Kurallar `kurallar/yerlesim/prefabrik.json`'dadır; oradaki değerlerin çoğu başka dosyadan okunur (`okunan`): liste kuralları
(`kurallar/liste/prefabrik.json`) ve onların sabitlediği kural kitabı seti (`kitap_seti`). Burada sayı yazılmaz.

K3'ün elektrik katmanı `elektrik.py`'dedir (kural `elektrik_yerlesimi`; kart modeli yalnız istenince kurar). K3b'nin alt çerçeve ve çatı
kenarları katmanı `kenar.py`'dedir (montaj rehberinin kartsız yedi parçası; kuralları `kenar.KENAR` ve `kenar_gosterim`; o da istenince).

`katmanlar(ie, plan, makaslar, yerlesim, liste)` parçaları döner: {kural, parca, boy_cm?, geo, bilgi, aciklama}. Parçanın kartı kart
modelinde bulunur (`motor/kart_model.py`; kartın `yerlesim` alanı). Kuralı uygulanamayan katman (çatı tipi, kaplama, iniş kuralı, tek sıra
betopanın örtmediği üçgen) parça üretmez, "kural yok" yazar; varsayılan okumalar ve kurulamayan yerler `uyarilar`'dadır. Kesim planı `kesim.py`'de, IFC'ye yazım `yaz.py`'de, planların çizimi `cizim.py`'de.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import cati, girdi, tavan

KOK = Path(__file__).resolve().parents[2]
LISTE_DOSYASI = "kurallar/liste/prefabrik.json"
KURALLAR = ("tavan_omegasi_yerlesimi", "asik_sirasi", "cati_kaplamasi", "bas_makas_betopani_yerlesimi", "dere_hatti", "kesim_plani", "gosterim")
PARCA_ADI = {"omega": "OMEGA", "asik": "ASIK", "panel": "KAPLAMA", "levha": "BETOPAN", "dere": "DERE", "inis": "INIS",    # modelde parçanın adı
             "tavan_armaturu": "DUY", "glop": "GLOP", "anahtar_tekli": "ANAHTAR", "anahtar_cift": "ANAHTAR_CIFT", "priz_tekli": "PRIZ",
             "priz_cift": "PRIZ_CIFT", "uydu_prizi": "UYDU", "zil": "ZIL", "sigorta_kutusu": "SIGORTA", "kablo_priz": "KABLO_PRIZ",
             "kablo_aydinlatma": "KABLO_AYDINLATMA",
             "alt_cerceve": "ALT_CERCEVE", "sacak_omegasi": "SACAK_OMEGASI", "sacak_saci": "SACAK_SACI", "alin_saci": "ALIN_SACI",
             "bas_makas_z": "BAS_MAKAS_Z", "c_kapama": "C_KAPAMA", "mahya": "MAHYA"}
ELEKTRIK = "elektrik_yerlesimi"                                     # K3 (`elektrik.py`); K2'nin katmanlarından ayrı, istenince kurulur
CATI_KATMANLARI = (("asik_sirasi", "aşık", "IfcMember"), ("cati_kaplamasi", "çatı kaplaması", "IfcCovering"),
                   ("bas_makas_betopani_yerlesimi", "baş makas betopanı", "IfcPlate"), ("dere_hatti", "dere ve iniş", "IfcPipeSegment"))


def kitap_oku(liste: dict) -> dict:
    """Liste kurallarının sabitlediği kural kitabı seti (`kurallar/liste/<kitap_seti>`)."""
    return json.loads((KOK / "kurallar" / "liste" / liste["kitap_seti"]).read_text(encoding="utf-8"))


def oku(ref: str, liste: dict, kitap: dict):
    """`okunan` yolu: `kurallar/liste/prefabrik.json › kurallar.<ad>[.<alt>]` ya da `kitap › <ad>[.<alt>]`. Yol boyunca `deger` açılır
    (liste üretecindeki `_ortak` gibi)."""
    kaynak, yol = ref.split(" › ")
    if kaynak == LISTE_DOSYASI:
        v = liste
    elif kaynak == "kitap":
        v = kitap
    else:
        raise ValueError(f"okunan yolunun kaynağı tanınmıyor: {ref}")
    for a in yol.split("."):
        if not isinstance(v, dict) or a not in v:
            raise KeyError(f"okunan yol bulunamadı: {ref}")
        v = v[a]
        if isinstance(v, dict) and "deger" in v:
            v = v["deger"]
    return v


def degerler(yerlesim: dict, liste: dict, kitap: dict | None = None) -> dict[str, dict]:
    """Her kuralın değerleri: `okunan` (İş Emri'nden okunanlar hariç) çözülmüş, `deger` açılmış."""
    kitap = kitap if kitap is not None else kitap_oku(liste)
    out = {}
    for ad, k in yerlesim["kurallar"].items():
        d = {}
        for alt, v in k.items():
            if isinstance(v, dict) and "okunan" in v and not v["okunan"].startswith("İş Emri"):
                d[alt] = oku(v["okunan"], liste, kitap)
            elif isinstance(v, dict) and "deger" in v:
                d[alt] = v["deger"]
        out[ad] = d
    return out


def _cm(m: float) -> float:
    return round(m * 100, 6)


def katmanlar(ie: dict, plan: dict, makaslar: list[dict], yerlesim: dict, liste: dict) -> dict:
    """K2'nin parçaları. `plan`: `motor.ifc_uret.hazirla(ie)`; `makaslar`: kart modelindeki makasların yeri ({ad, rol, konum})."""
    kitap = kitap_oku(liste)
    D = degerler(yerlesim, liste, kitap)
    K = yerlesim["kurallar"]
    g = girdi.kur(ie, plan, makaslar)
    kesit = D["gosterim"]["kesit_cm"]
    parcalar, kural_yok = [], []

    # tavan omegası (karar B)
    T = D["tavan_omegasi_yerlesimi"]
    tam = _cm(T["parca_boyu"] - T["pay"])
    uyarilar = list(g["uyarilar"])
    hatlar = tavan.hatlar(g, {"aralik_asma": _cm(T["aralik_asma"]), "aralik_ters": _cm(T["aralik_ters"]), "en_kisa": T["en_kisa_cm"]}, uyarilar)
    ow, oh = kesit["omega"]
    for i, h in enumerate(hatlar, 1):
        h["no"] = i
        sondan = g["baslangic"]["y" if h["eksen"] == "x" else "x"] == "max"            # hattın koştuğu eksende dizilimin başladığı uç
        h["parcalar"], h["bosluk_cm"] = tavan.parcala(h["r0"], h["r1"], tam, T["en_kisa_cm"], sondan)
        for a, b in h["parcalar"]:
            s = h["s"]
            kutu = ([s - ow / 2, a, g["duvar_h"] - oh, s + ow / 2, b, g["duvar_h"]] if h["eksen"] == "x"
                    else [a, s - ow / 2, g["duvar_h"] - oh, b, s + ow / 2, g["duvar_h"]])
            parcalar.append({"kural": "tavan_omegasi_yerlesimi", "parca": "omega", "boy_cm": round(b - a, 4),
                             "geo": {"tip": "kutu", "kutu": kutu},
                             "bilgi": {"Tavan": g["tavan"], "Yer": h["yer"], "Hat": i, "Mahal": h["mahal"]},
                             "aciklama": f"{h['eksen']} = {s:g}, {a:g}–{b:g}" + (f" ({h['mahal']})" if h["mahal"] else f" ({h['not']})")})

    # çatı: yalnız kuralın çatı tiplerinde
    for ad, adi, sinif in CATI_KATMANLARI:
        izin = K[ad].get("cati_tipleri")
        if izin and g["cati_tipi"] not in izin:
            kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"İş Emri'nin çatısı \"{g['cati_tipi']}\"; {ad} yalnız "
                                                                      f"{', '.join(izin)} çatıda (bugünkü IFC çatıyı hep beşik çizer)"})
            continue
        if ad == "asik_sirasi":
            A = D[ad]
            parcalar += cati.asik(g, {"kesit_asik": kesit["asik"], "aralik": _cm(A["aralik"]), "tam": _cm(A["parca_boyu"] - A["pay"]),
                                      "en_kisa": A["en_kisa_cm"]})
        elif ad == "cati_kaplamasi":
            C = D[ad]
            yazili = girdi.kucuk(next((v for k, v in g["ozellikler"].items() if girdi.kucuk(k) == "çatı kaplaması"), ""))
            tur = next((t for t in C["kaplamalar"] if t in yazili), None)
            if tur is None:
                kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"İş Emri'nin çatı kaplaması \"{yazili or 'yazılı değil'}\"; K2 yalnız "
                                                                          f"{', '.join(C['kaplamalar'].values())} kaplamasını kurar (kartı yok)"})
                continue
            for p in cati.kaplama(g, {"kesit_asik": kesit["asik"], "kalinlik_kaplama": kesit["kaplama"], "tasma_m": C["tasma"],
                                      "yuvarlama_mm": C["yuvarlama_mm"], "kapatma_cm": _cm(C["kapatma"])}):
                p["bilgi"]["Kaplama"] = tur
                parcalar.append(p)
        elif ad == "bas_makas_betopani_yerlesimi":
            B = D[ad]
            levhalar, neden = cati.betopan(g, {"katsayi": B["katsayi"], "levha_m2": B["levha_m2"], "levha_cm": B["levha_cm"],
                                               "kalinlik_betopan": kesit["betopan"]})
            if neden:
                kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"{ad}: {neden}"})
            parcalar += levhalar
        else:
            R = D[ad]
            dere = cati.dere(g, {"kesit_dere": kesit["dere"], "kesit_inis": kesit["inis"], "orta_esik_cm": _cm(R["orta_esik"]),
                                 "kose_basina": R["kose_basina"]})
            if R["orta_kurali"] != K[ad]["orta_kurali"]["beklenen"]:
                kural_yok.append({"parca": "iniş", "sinif": "IfcPipeFitting",
                                  "neden": f"liste kuralı inis_orta \"{R['orta_kurali']}\"; dere hattının inişi yalnız \"esik\" kuralıyla kurulur"})
                dere = [p for p in dere if p["parca"] != "inis"]
            parcalar += dere
    return {"parcalar": parcalar, "kural_yok": kural_yok, "uyarilar": uyarilar, "hatlar": hatlar, "girdi": g, "cerceve": cati.cerceve(g),
            "degerler": D}
