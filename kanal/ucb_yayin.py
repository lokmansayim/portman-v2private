"""İE-21 · Bayiye 3D sayfasının yayını (Kurulum Panosu satır 80; Bayi Rehberi: "3D'yi aç" butonu modeli telefonun tarayıcısında açar).

Kayıttaki sayfa (`projects/<no>/rNN/3d/index.html`, `motor/ucb_sayfa.py`) bayt bayt `<veri>/yayin/3d/<anahtar>/index.html`'e kopyalanır;
nginx yalnız bu dizini `/3d/<anahtar>/` altında, yalnız GET ile sunar (`vps/nginx/portman.conf`; dizini `vps/nginx_uygula.sh` açar).
Anahtar 22 karakterlik rastgele dizgedir (128 bit). Adreste İş Emri numarası yoktur: numara tahmin edilebilir ve kodsuz bayide telefonun son
dört hanesini taşır (`sablonlar.bayi_kodu`). Rastgele olduğu için yarışan iki iş (`kalici.Cakisma`) birbirinin sayfasını ezmez; kaydı
yazılmayan işin kopyası bağlantısız kalır (bayiye gitmez, silinmez).
Bağlantı yalnız `ucb_taban_url` doluysa ve yayın dizini varsa üretilir; yoksa url None olur ve bayiye söz veren mesaj gitmez. İzinler açıkça
verilir (worker umask 077; nginx okuyabilsin): dizin 755, sayfa 644. Yazma hatası akışı durdurmaz (`yayin_hata`).
Canlı açılış `vps/ucb_ac.sh`: `python kanal/ucb_yayin.py ornek --veri <data> --taban https://<alan>/3d` depodaki P6001'den örnek sayfa yayımlar.
"""
from __future__ import annotations
import json, os, re, secrets, shutil, sys, tempfile
from pathlib import Path

ANAHTAR = re.compile(r"[A-Za-z0-9_-]{22}")          # vps/nginx/portman.conf'taki desenle aynı (testle denetlenir)


def anahtar_uret() -> str:
    return secrets.token_urlsafe(16)                # 16 bayt → 22 karakter, URL'de güvenli


def yayinla(html: Path, settings: dict, kok: Path) -> dict:
    """Sayfayı yayın dizinine koyar. Dönen: {"url", "anahtar"} ya da {"url": None} (ayar yok) ya da {"url": None, "yayin_hata"}."""
    taban = str(settings.get("ucb_taban_url") or "").rstrip("/")
    if not taban:
        return {"url": None}
    if not taban.startswith("https://"):
        return {"url": None, "yayin_hata": "ucb_taban_url https:// ile başlamalı"}
    kok = Path(kok)
    if not kok.is_dir():
        return {"url": None, "yayin_hata": f"yayın dizini yok ({kok.name}); sunucuda vps/nginx_uygula.sh açar"}
    try:
        for _ in range(3):
            anahtar = anahtar_uret()
            d = kok / anahtar
            try:
                os.mkdir(d)
            except FileExistsError:
                continue
            os.chmod(d, 0o755)
            gecici = d / ".index.html.yeni"             # nginx deseni yalnız index.html'i sunar; yarım dosya görünmez
            shutil.copyfile(html, gecici)
            os.chmod(gecici, 0o644)
            os.replace(gecici, d / "index.html")
            return {"url": f"{taban}/{anahtar}/", "anahtar": anahtar}
        return {"url": None, "yayin_hata": "boş anahtar bulunamadı"}
    except OSError as e:
        return {"url": None, "yayin_hata": f"{type(e).__name__}: {str(e)[:200]}"}


def ornek(veri: Path, taban: str, kod: Path) -> dict:
    """Depodaki P6001 İş Emri'nden (referans plan; kişi ve bayi verisi yok) ajanın koduyla örnek sayfa üretir ve yayımlar."""
    from motor import ifc_uret as IU, ucb_sayfa as US
    ie = json.loads((kod / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    d = Path(tempfile.mkdtemp(prefix="portman_ucb_ornek_"))
    IU.uret(ie, d / "ornek.ifc", baslik="Portman — 3D örnek (P6001)")
    html = US.uret(d / "ornek.ifc", d / "index.html", baslik="P6001 örnek")
    return {"sayfa": str(html), **yayinla(html, {"ucb_taban_url": taban}, Path(veri) / "yayin" / "3d")}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="İE-21 3D sayfası yayını (vps/ucb_ac.sh)")
    ap.add_argument("islem", choices=["ornek"])
    ap.add_argument("--veri", required=True)
    ap.add_argument("--taban", required=True)
    ns = ap.parse_args()
    KOD = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(KOD))
    print(json.dumps(ornek(Path(ns.veri), ns.taban, KOD), ensure_ascii=False))
