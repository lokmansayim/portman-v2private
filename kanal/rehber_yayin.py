"""İE-34 · Bayiye montaj rehberinin yayını (Kurulum Panosu satır 179; Lokman, 9 Kasım 2026: "şimdilik 'Montaj Rehberi' gitsin").

Rehber `main`'deki koddan bulutta üretilir (`python -m araclar.paket --is-emri <İş Emri> <çıktı> --render`, İE-18; D-28). Lokman dosyayı
sunucuya koyar ve `vps/rehber_yayinla.sh` ile yayımlar; betik bu modülü portman kullanıcısıyla koşar, dosyayı standart girdiden verir.
Modül dosyayı denetler ve 3D sayfasıyla aynı işlevle (`ucb_yayin.yayinla`: 22 karakterlik rastgele anahtar, dizin 755, sayfa 644, yarım
dosya görünmez) bayt bayt `<veri>/yayin/rehber/<anahtar>/index.html`'e koyar; nginx `/rehber/<anahtar>/` ile sunar (`vps/nginx/portman.conf`).

Denetim (biri düşerse yayın yok):
- UTF-8, boş değil, en çok 16 MiB;
- İE-18 rehberinin imleri: başlık "… Montaj Rehberi", telefon ayarı (viewport; yoksa telefonda masaüstü düzeni açılır), pafta verisi,
  three.js 0.160.0 içe aktarma haritası; doldurulmamış yer tutucu yok;
- dış adresler yalnız nginx'in CSP'sinin izin verdiği üç ad: cdn.jsdelivr.net, fonts.googleapis.com, fonts.gstatic.com;
- telefon numarasına benzeyen dizge yok (`beyin/numara.py`'nin deseni; gömülü görseller ve ondalık sayılar denetimden önce çıkarılır,
  çünkü base64 ve 0.8791666… ya da 0,8791666… gibi uzun ondalıklar numara sanılır).
Ayar yok: her yayın Lokman'ın kendi komutudur; bağlantıyı bayiye Lokman panelden yollar.

    python kanal/rehber_yayin.py --veri /opt/portman/data --taban https://<alan>/rehber < rehber.html
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    _KOD = Path(__file__).resolve().parent.parent
    for _y in (_KOD, _KOD / "kanal"):
        if str(_y) not in sys.path:
            sys.path.insert(0, str(_y))

import ucb_yayin as UY                      # noqa: E402

EN_COK = 16 * 1024 * 1024
IZINLI = ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com")     # vps/nginx/portman.conf › /rehber/ CSP'si (testle denetlenir)
IMLER = {
    "telefon ayarı": '<meta name="viewport" content="width=device-width',      # İE-34: Lokman 9 Kasım 13:36 kartı "Evet, telefon düzeni"
    "pafta verisi": '<script type="application/json" id="pafta">',
    "içe aktarma haritası": '<script type="importmap">',
    "three.js 0.160.0": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
}
YER_TUTUCU = ("__DATA__", "__SCRIPT__", "__GORSELLER__", "__KAGIT__", "__CHIP__", "__SPEC__", "__NOTE__", "__KISA__", "__PROJE__")
_BASLIK = re.compile(r"<title>([^<]{1,200}) Montaj Rehberi</title>")
_ADRES = re.compile(r"(?:https?:)?//([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?=[/:?\"'\s)>]|$)")
_GOMULU = re.compile(r"data:[a-z0-9/+.-]+;base64,[A-Za-z0-9+/=]+", re.I)
_ONDALIK = re.compile(r"\d+[.,]\d+")      # 0.8791666… ve 0,8791666…


def denetle(veri: bytes) -> tuple[list[str], dict]:
    """Dönen: (sorunlar, bilgi). Sorun yoksa liste boştur; bilgi başlığı, boyutu ve sha256'yı taşır."""
    bilgi = {"boyut": len(veri), "sha256": hashlib.sha256(veri).hexdigest()}
    if not veri:
        return ["dosya boş"], bilgi
    if len(veri) > EN_COK:
        return [f"dosya {len(veri)} bayt, en çok {EN_COK}"], bilgi
    try:
        s = veri.decode("utf-8")
    except UnicodeDecodeError as e:
        return [f"UTF-8 değil ({e.start}. bayt)"], bilgi
    sorun = []
    m = _BASLIK.search(s)
    if m:
        bilgi["baslik"] = f"{m.group(1)} Montaj Rehberi"
    else:
        sorun.append("başlık \"… Montaj Rehberi\" yok")
    sorun += [f"rehber imi yok: {ad}" for ad, im in IMLER.items() if im not in s]
    sorun += [f"doldurulmamış yer tutucu: {y}" for y in YER_TUTUCU if y in s]
    temiz = _GOMULU.sub("", s)
    dis = sorted({h.lower() for h in _ADRES.findall(temiz)} - set(IZINLI))
    if dis:
        sorun.append("izinsiz dış adres: " + ", ".join(dis[:5]))
    from beyin import numara
    tel = sum(1 for x in numara.DESEN.finditer(_ONDALIK.sub("0", temiz)) if 10 <= len(re.sub(r"\D", "", x.group(0))) <= 15)
    if tel:
        sorun.append(f"telefon numarasına benzeyen {tel} dizge var")
    return sorun, bilgi


def yayinla(veri: bytes, kok: Path, taban: str) -> dict:
    """Denetimden geçen rehberi yayımlar. Dönen: {"url", "anahtar", "boyut", "sha256", "baslik"} ya da {"url": None, "sorunlar" | "yayin_hata"}."""
    sorun, bilgi = denetle(veri)
    if sorun:
        return {"url": None, "sorunlar": sorun, **bilgi}
    with tempfile.TemporaryDirectory(prefix="portman_rehber_") as d:
        gecici = Path(d) / "rehber.html"
        gecici.write_bytes(veri)
        sonuc = UY.yayinla(gecici, {"ucb_taban_url": taban}, Path(kok))
    return {**sonuc, **bilgi}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="İE-34 montaj rehberinin yayını (vps/rehber_yayinla.sh)")
    ap.add_argument("dosya", nargs="?", default="-", help="rehber.html; '-' ya da boş: standart girdi")
    ap.add_argument("--veri", required=True, help="sunucuda /opt/portman/data")
    ap.add_argument("--taban", required=True, help="https://<alan>/rehber")
    ap.add_argument("--yalniz-denetle", action="store_true", help="yayımlamadan denetle")
    ns = ap.parse_args()
    icerik = sys.stdin.buffer.read() if ns.dosya == "-" else Path(ns.dosya).read_bytes()
    if ns.yalniz_denetle:
        s, b = denetle(icerik)
        print(json.dumps({"sorunlar": s, **b}, ensure_ascii=False))
        sys.exit(1 if s else 0)
    print(json.dumps(yayinla(icerik, Path(ns.veri) / "yayin" / "rehber", ns.taban), ensure_ascii=False))
