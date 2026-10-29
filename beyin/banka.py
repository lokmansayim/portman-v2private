"""İE-09 · Model bankasının atölye kısmı (D-20): `modeller/banka/<DOSYA>/kart.json`'dan yalnız `kabul` modeller, aday kaydı biçiminde.

Çekirdek banka `beyin/veri/adaylar.json`'dur (yedi model; referans girdi, değişmez). Atölyede kabul edilen her model kendi klasöründe durur:
`tanim.json` (Yapı Tanımı 0.5), `kart.json` (`portman.model_karti/0.1`; `araclar/atolye.py` yazar), `kontrol.json` (modelin kontrol
dosyası) ve `kart.png` (aday kartı görseli). Referans girdi kalıpları (`modeller/*.json`) alt klasöre inmez: yeni model referansı değiştirmez.

Okuyanlar: `beyin.katalog.Katalog` (adaylar.json'un ardından), `araclar/aday_kabul.py` (K-A10, sunucuda aynı betik) ve
`araclar/kabul_paketi.py`. İE-14 uyarlaması (`plan_uretici._banka`) atölye bankasını okumaz (İE-09 PR-1, CIO 29 Ekim 2026: sunum yalnız Katalog'dan). Canlı yolda hata fırlatılmaz: geçersiz kart (tanım yok, özet tutmuyor, kod çakışıyor)
alınmaz; `denetle()` bunları sayar, atölye ve `testler/genel/test_banka.py` boş liste bekler.

Görünürlük (K-A10, D-20): atölye modeli bayiye yalnız kabul kaydı açıkça verilmişse sunulur; kabul kümesi verilmeyen Katalog'da (harness,
yerel testler) görünmez. Çatı varyantı (`taban_model` dolu) bayiye ayrı model olarak sunulmaz (taban modelle aynı plan): çatı setine
girmesi ayrı iştir (bugünkü set katalog çatısı, K, L; WhatsApp'ta üç düğme)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANKA_DIR = ROOT / "modeller" / "banka"
ADAYLAR_JSON = ROOT / "beyin" / "veri" / "adaylar.json"
KART_SEMASI = "portman.model_karti/0.1"
KONTROL_SEMASI = "portman.banka_kontrol/0.1"


def dosya_adi(kod: str) -> str:
    """Klasör adı ASCII (Mac/Linux/git uyumu; `aday_kaydet` ile aynı): Ç8801D → C8801D."""
    return str(kod).replace("Ç", "C").replace("-", "").replace(" ", "")


def kartlar(kok: Path = BANKA_DIR) -> list[dict]:
    """Bütün kartlar (her durumda), klasör sırasıyla; okunamayan kart `_hata` taşır. `_klasor` kartın klasörüdür (yazılmaz)."""
    out = []
    if not kok.is_dir():
        return out
    for k in sorted(p for p in kok.iterdir() if p.is_dir() and (p / "kart.json").is_file()):
        try:
            kart = json.loads((k / "kart.json").read_text(encoding="utf-8"))
        except Exception as e:                                             # canlı yol düşmez; denetle() sayar
            kart = {"_hata": f"kart okunamadı: {type(e).__name__}"}
        out.append({**kart, "_klasor": k})
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sorunlar(kart: dict, cekirdek: set[str], gorulen: set[str], kok_dizin: Path) -> list[str]:
    s = []
    if kart.get("_hata"):
        return [kart["_hata"]]
    if kart.get("sema") != KART_SEMASI:
        s.append(f"şema {kart.get('sema')!r}")
    a = kart.get("aday") or {}
    kod = str(a.get("kod") or "").upper()
    if not kod or kod != str(kart.get("kod") or "").upper():
        s.append("aday kaydının kodu kartla aynı değil")
    if kod in cekirdek:
        s.append(f"kod çekirdek bankada da var ({kod})")
    if kod in gorulen:
        s.append(f"kod bankada iki kez var ({kod})")
    if kart["_klasor"].name != dosya_adi(kod):
        s.append(f"klasör adı {kart['_klasor'].name}, beklenen {dosya_adi(kod)}")
    tanim = kok_dizin / str(a.get("tanim") or "")
    if not a.get("tanim") or not tanim.is_file():
        s.append("tanım dosyası yok")
    elif a.get("tanim_sha256") != _sha(tanim):
        s.append("tanımın özeti aday kaydıyla aynı değil (kabulden sonra değişmiş; D-07: yeni kod ya da sürüm)")
    gorsel = Path(os.path.normpath(kok_dizin / "is_emri" / str(a.get("gorsel") or "")))   # "../modeller/banka/…" (Katalog SABLON_DIR'e göre)
    if not a.get("gorsel") or not gorsel.is_file():
        s.append("aday kartı görseli yok")
    if not (kart["_klasor"] / "kontrol.json").is_file():
        s.append("kontrol dosyası yok")
    return s


def _tara(kok: Path, adaylar_yolu: Path) -> tuple[list[dict], list[tuple[str, list[str]]]]:
    kok_dizin = kok.parent.parent                                          # modeller/banka → depo kökü (tanım ve görsel yolları ona göre)
    cekirdek = {str(a.get("kod")).upper() for a in (json.loads(adaylar_yolu.read_text(encoding="utf-8")) if adaylar_yolu.exists() else [])}
    gecerli, sorunlu, gorulen = [], [], set()
    for kart in kartlar(kok):
        if kart.get("durum") != "kabul" and not kart.get("_hata"):
            continue
        s = _sorunlar(kart, cekirdek, gorulen, kok_dizin)
        if s:
            sorunlu.append((kart["_klasor"].name, s))
            continue
        a = dict(kart["aday"])
        gorulen.add(str(a["kod"]).upper())
        gecerli.append({**a, "banka": True, "taban_model": kart.get("taban_model")})
    return gecerli, sorunlu


def kayitlar(kok: Path = BANKA_DIR, adaylar_yolu: Path = ADAYLAR_JSON) -> list[dict]:
    """`kabul` kartların aday kayıtları (`banka: True`, `taban_model`); sorunlu kart alınmaz."""
    return _tara(kok, adaylar_yolu)[0]


def denetle(kok: Path = BANKA_DIR, adaylar_yolu: Path = ADAYLAR_JSON) -> list[tuple[str, list[str]]]:
    """Alınmayan `kabul` kartlar ve nedenleri: [(klasör, [sorun, …])]. Boş liste beklenir."""
    return _tara(kok, adaylar_yolu)[1]
