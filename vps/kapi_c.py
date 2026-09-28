#!/usr/bin/env python3
"""PORTMAN · Kapı C (İE-02): eşleşme anahtarı ve OpenAI anahtarının kontrollü yenilenmesi. VPS'te root olarak, Mac'ten:

    ssh root@<VPS> 'python3 - <adım>' < kapi_c.py

Adımlar (sırası betik tarafından denetlenir; önceki adım geçmeden sonraki çalışmaz):
    hazirla         salt okunur denetim + eski iki anahtarı İPTAL DENETİMİ İÇİN geçici, root'a özel klasöre alır
    yenile          agent.env'de yeni eşleşme anahtarı (servis yeniden başlatılmaz; çalışan ajan eski anahtarla sürer)
    ara             hosting yeni eşleşme anahtarını kabul ediyor, eskisini reddediyor mu; panel yeni OpenAI anahtarını mı veriyor
    yeniden_baslat  servisi yeniden başlatır; süreç yeni anahtarla mı, hosting kabul ediyor mu, günlükte 401 var mı
    bitir           eski OpenAI anahtarı OpenAI'de geçersiz mi (401), eski eşleşme anahtarı hosting'te geçersiz mi (401);
                    sonra geçici klasörü siler
    temizle         yarıda bırakılırsa geçici klasörü siler
    durum           hangi adımların geçtiğini yazar

Hiçbir anahtar değeri ekrana, günlüğe ya da dosya adına yazılmaz; yalnız SHA-256'nın ilk 12 hanesi (parmak izi) yazılır.
OpenAI denetimi yalnız GET /v1/models'tır (ücretsiz; token harcamaz); hata mesajı anahtarın bir parçasını içerebildiği için
yalnız hata KODU yazılır. Eski anahtarlar yalnız /root/.portman_kapi_c (0700) içinde 0600 dosyalarda, iptal denetimine dek durur;
geri yükleme için KULLANILMAZ (betiğin hiçbir adımı eski anahtarı yeniden etkinleştirmez).
Test için: PM_ENV, PM_HOME, PM_KAPI_C_DIR, PM_OPENAI_BASE, PM_SYSTEMCTL, PM_BEKLE_SN.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SURUM = "kapi_c 2026-09-28"
ENV = Path(os.environ.get("PM_ENV", "/etc/portman/agent.env"))
HOME = Path(os.environ.get("PM_HOME", "/opt/portman"))
DEPO = Path(os.environ.get("PM_KAPI_C_DIR", "/root/.portman_kapi_c"))
OPENAI = os.environ.get("PM_OPENAI_BASE", "https://api.openai.com/v1").rstrip("/")
SYSTEMCTL = os.environ.get("PM_SYSTEMCTL", "systemctl")
SERVIS = "portman-agent"
BEKLE = int(os.environ.get("PM_BEKLE_SN", "20"))
_GIZLI: list[str] = []            # bu çalıştırmada görülen değerler: hiçbir çıktı satırı bunları (ya da 8 karakterlik parçalarını) içeremez


def iz(v: str) -> str:
    return hashlib.sha256(v.strip().encode()).hexdigest()[:12]


def yaz(satir: str = "") -> None:
    for g in _GIZLI:
        if len(g) >= 8 and any(g[i:i + 8] in satir for i in range(len(g) - 7)):
            satir = "   [çıktı satırı gizlendi]"; break
    print(satir, flush=True)


def gizli(v: str | None) -> str | None:
    if v:
        _GIZLI.append(v.strip())
    return v


def dur(neden: str, sonraki: str = "") -> None:
    yaz(f"DUR: {neden}")
    if sonraki:
        yaz(f"YAPILACAK: {sonraki}")
    sys.exit(1)


# ───────── okuma yardımcıları ─────────
def env_oku() -> dict:
    d = {}
    for s in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in s and not s.lstrip().startswith("#"):
            k, v = s.split("=", 1); v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            d[k.strip()] = v
    gizli(d.get("PORTMAN_API_TOKEN"))
    return d


def sc(*arg: str) -> str:
    r = subprocess.run([SYSTEMCTL, *arg], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.stdout.strip()


def surec_anahtari() -> tuple[str, str | None]:
    pid = sc("show", SERVIS, "-p", "MainPID", "--value") or "0"
    try:
        for kv in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0"):
            if kv.startswith(b"PORTMAN_API_TOKEN="):
                return pid, gizli(kv.split(b"=", 1)[1].decode())
    except OSError:
        pass
    return pid, None


def istek(url: str, basliklar: dict, zaman_asimi: int = 25) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "portman-kapi-c", **basliklar}), timeout=zaman_asimi) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except OSError as e:
        return 0, type(e).__name__.encode()


def hosting_ayar(api: str, anahtar: str) -> tuple[int, dict]:
    kod, govde = istek(api.split("?")[0] + "?op=settings", {"X-Portman-Token": anahtar.strip()})
    try:
        j = json.loads(govde.decode()) if kod == 200 else {}
    except ValueError:
        j = {}
    gizli(j.get("openai_key"))
    return kod, j


def openai_dene(anahtar: str) -> tuple[int, str]:
    """GET /v1/models (ücretsiz). Dönüş: (HTTP kodu, yalnız hata kodu). Hata mesajı yazılmaz: anahtarın parçasını içerir."""
    kod, govde = istek(OPENAI + "/models", {"Authorization": "Bearer " + anahtar.strip()})
    hata = ""
    if kod != 200:
        try:
            hata = str((json.loads(govde.decode()).get("error") or {}).get("code") or "")
        except (ValueError, AttributeError):
            hata = ""
    return kod, "".join(ch for ch in hata if ch.isalnum() or ch in "_-")[:40]


def openai_gecerli(kod: int, hata: str) -> bool:
    return kod == 200 or (kod == 403 and "permission" in hata)          # kısıtlı anahtar: tanındı ama bu uç noktaya izni yok


# ───────── geçici depo ─────────
def depo_durum() -> dict:
    p = DEPO / "durum.json"
    return json.loads(p.read_text()) if p.exists() else {}


def depo_yaz(ad: str, veri) -> None:
    DEPO.mkdir(mode=0o700, parents=True, exist_ok=True); os.chmod(DEPO, 0o700)
    p = DEPO / ad
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(veri, ensure_ascii=False) if ad.endswith(".json") else veri)
    os.chmod(p, 0o600)


def depo_oku(ad: str) -> str | None:
    p = DEPO / ad
    return gizli(p.read_text(encoding="utf-8")) if p.exists() else None


def adim_kaydet(ad: str, veri: dict) -> None:
    d = depo_durum(); d[ad] = {**veri, "zaman": int(time.time())}; depo_yaz("durum.json", d)


def depo_sil() -> bool:
    if DEPO.exists():
        for p in DEPO.iterdir():
            try:
                with open(p, "r+b") as f:
                    f.write(b"\0" * max(p.stat().st_size, 1)); f.flush(); os.fsync(f.fileno())
            except OSError:
                pass
            p.unlink()
        DEPO.rmdir()
    return not DEPO.exists()


def gerek(d: dict, adim: str, onceki: str) -> None:
    if adim not in d or not d[adim].get("gecti"):
        dur(f"'{adim}' adımı geçmemiş.", f"önce '{onceki}' adımını çalıştır.")


def kontrol(liste: list[tuple[str, bool]]) -> bool:
    for ad, ok in liste:
        yaz(f"   {'✓' if ok else '✗'} {ad}")
    return all(ok for _, ok in liste)


def bekleyen_sayisi() -> int:
    return len(list((HOME / "data" / "pending").glob("*.json")))


# ───────── adımlar ─────────
def hazirla() -> None:
    d = depo_durum()
    if d:
        dur("önceki bir C denemesinin geçici klasörü duruyor" + (" ve eşleşme anahtarı zaten yenilenmiş" if "yenile" in d else "") + ".",
            "yarım kalan denemeyi sürdür ('durum' ile bak) ya da baştan başlamak için 'temizle'.")
    e = env_oku(); dosya = e.get("PORTMAN_API_TOKEN", ""); api = e.get("PORTMAN_API_URL", "")
    pid, surec = surec_anahtari()
    kod, ayar = hosting_ayar(api, dosya) if dosya and api else (0, {})
    eski_oai = ayar.get("openai_key") or ""
    oai_kod, oai_hata = openai_dene(eski_oai) if eski_oai else (0, "anahtar_yok")
    yaz(f"== Kapı C · hazırlık · {SURUM} · {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    yaz(f"   servis: {sc('is-active', SERVIS) or '?'} · PID {pid} · gönderilemeyip bekleyen sonuç: {bekleyen_sayisi()}")
    yaz(f"   eşleşme anahtarı: dosya {iz(dosya) if dosya else 'yok'} · çalışan süreç {iz(surec) if surec else 'okunamadı'}")
    yaz(f"   hosting op=settings (bu anahtarla): HTTP {kod}")
    yaz(f"   hosting'in verdiği OpenAI anahtarı: {iz(eski_oai) if eski_oai else 'YOK'} · OpenAI GET /models: HTTP {oai_kod} {oai_hata}".rstrip())
    ok = kontrol([("servis çalışıyor", sc("is-active", SERVIS) == "active"),
                  ("dosyadaki ve süreçteki eşleşme anahtarı aynı (yarım kalmış yenileme yok)", bool(dosya) and surec is not None and iz(dosya) == iz(surec)),
                  ("hosting bugünkü anahtarı kabul ediyor", kod == 200),
                  ("hosting bir OpenAI anahtarı veriyor", bool(eski_oai)),
                  ("bugünkü OpenAI anahtarı OpenAI'de geçerli (iptal denetiminin karşılaştırma noktası)", openai_gecerli(oai_kod, oai_hata))])
    if not ok:
        dur("hazırlık denetimi geçmedi; hiçbir şey değişmedi, geçici klasör oluşturulmadı.", "çıktıyı asistana gönder.")
    depo_yaz("eski_eslesme", dosya); depo_yaz("eski_openai", eski_oai)
    adim_kaydet("hazirla", {"gecti": True, "eski_eslesme_iz": iz(dosya), "eski_openai_iz": iz(eski_oai)})
    yaz(f"   eski iki anahtar, iptal denetimi için {DEPO} içine alındı (0700 klasör, 0600 dosya; 'bitir' ya da 'temizle' siler)")
    yaz("SONUÇ: hazırlık tamam. Değişiklik yapılmadı.")
    yaz("SONRAKİ ADIM: OpenAI'da yeni anahtar oluştur ve panele kaydet (eskisini henüz iptal etme); sonra 'yenile'.")


def yenile() -> None:
    d = depo_durum(); gerek(d, "hazirla", "hazirla")
    if "yenile" in d:
        dur("eşleşme anahtarı bu denemede zaten yenilendi; ikinci kez yenilenmez.", "'ara' adımını çalıştır.")
    st = ENV.stat(); satirlar = ENV.read_text(encoding="utf-8").splitlines()
    anahtarlar = [s for s in satirlar if s.startswith("PORTMAN_API_TOKEN=")]
    if len(anahtarlar) != 1:
        dur("agent.env'de PORTMAN_API_TOKEN satırı yok ya da birden çok; dosyaya dokunulmadı.")
    eski = gizli(anahtarlar[0].split("=", 1)[1].strip())
    if iz(eski) != d["hazirla"]["eski_eslesme_iz"]:
        dur("agent.env'deki anahtar hazırlıktakinden farklı; dosyaya dokunulmadı.", "asistana haber ver.")
    yedek = ENV.with_name(ENV.name + f".before-c-{time.strftime('%Y%m%d-%H%M%S')}")
    fd = os.open(yedek, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(s for s in satirlar if not s.startswith("PORTMAN_API_TOKEN=")) + "\n")
    yeni = gizli(secrets.token_hex(32))
    gecici = ENV.with_name(ENV.name + ".yeni")
    fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, st.st_mode & 0o777)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join("PORTMAN_API_TOKEN=" + yeni if s.startswith("PORTMAN_API_TOKEN=") else s for s in satirlar) + "\n")
    os.chown(gecici, st.st_uid, st.st_gid); os.chmod(gecici, st.st_mode & 0o777)
    os.replace(gecici, ENV)
    son = ENV.stat()
    adim_kaydet("yenile", {"gecti": True, "yeni_eslesme_iz": iz(yeni)})
    yaz(f"== Kapı C · eşleşme anahtarı yenilendi · {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    yaz(f"   eski {iz(eski)} → yeni {iz(yeni)} · izin {oct(son.st_mode & 0o777)} · sahip {son.st_uid}:{son.st_gid} (öncekiyle "
        f"{'aynı' if (son.st_mode & 0o777, son.st_uid, son.st_gid) == (st.st_mode & 0o777, st.st_uid, st.st_gid) else 'FARKLI'})")
    yaz(f"   anahtar satırı çıkarılmış yedek: {yedek.name} (eski anahtar yedekte YOK)")
    yaz("   servis yeniden başlatılmadı: çalışan ajan, hosting güncellenene dek eski anahtarla sürer")
    yaz("SONRAKİ ADIM: yeni anahtarı ekrana getirmeden hosting'teki api_token.txt'ye koy; sonra 'ara'.")


def ara() -> None:
    d = depo_durum(); gerek(d, "yenile", "yenile")
    e = env_oku(); yeni = e["PORTMAN_API_TOKEN"]; api = e["PORTMAN_API_URL"]
    eski = depo_oku("eski_eslesme") or ""
    k_yeni, ayar = hosting_ayar(api, yeni)
    k_eski, _ = hosting_ayar(api, eski)
    oai = ayar.get("openai_key") or ""
    oai_kod, oai_hata = openai_dene(oai) if oai else (0, "anahtar_yok")
    yaz(f"== Kapı C · ara doğrulama (yeniden başlatmadan önce) · {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    yaz(f"   hosting op=settings: yeni eşleşme anahtarıyla ({iz(yeni)}) HTTP {k_yeni} · eskisiyle ({d['hazirla']['eski_eslesme_iz']}) HTTP {k_eski}")
    yaz(f"   hosting'in verdiği OpenAI anahtarı: {iz(oai) if oai else 'YOK'} (eski: {d['hazirla']['eski_openai_iz']}) · OpenAI GET /models: HTTP {oai_kod} {oai_hata}".rstrip())
    liste = [("hosting yeni eşleşme anahtarını kabul ediyor", k_yeni == 200),
             ("hosting eski eşleşme anahtarını reddediyor (401)", bool(eski) and iz(eski) == d["hazirla"]["eski_eslesme_iz"] and k_eski == 401),
             ("panel yeni bir OpenAI anahtarı veriyor (parmak izi eskisinden farklı)", bool(oai) and iz(oai) != d["hazirla"]["eski_openai_iz"]),
             ("yeni OpenAI anahtarı OpenAI'de geçerli", openai_gecerli(oai_kod, oai_hata))]
    if not kontrol(liste):
        ipucu = []
        if k_yeni != 200: ipucu.append("hosting'teki api_token.txt yeni anahtarı içermiyor: yapıştırma adımını yinele")
        if not (bool(oai) and iz(oai) != d["hazirla"]["eski_openai_iz"]): ipucu.append("panelde OpenAI anahtarı henüz yeni değil ya da kaydedilemedi")
        if oai and not openai_gecerli(oai_kod, oai_hata): ipucu.append("yeni OpenAI anahtarı reddedildi: doğru kopyalandı mı, iptal edilmiş olabilir mi")
        dur("ara doğrulama geçmedi; servis yeniden başlatılmadı.", "; ".join(ipucu) + " — sonra 'ara'yı yinele.")
    adim_kaydet("ara", {"gecti": True, "yeni_openai_iz": iz(oai)})
    yaz("SONUÇ: yeni eşleşme çalışıyor, eskisi reddediliyor; panel yeni OpenAI anahtarını veriyor.")
    yaz("SONRAKİ ADIM: 'yeniden_baslat'.")


def yeniden_baslat() -> None:
    d = depo_durum(); gerek(d, "ara", "ara")
    once_pid = sc("show", SERVIS, "-p", "MainPID", "--value")
    bas = time.strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run([SYSTEMCTL, "restart", SERVIS], check=False, stdin=subprocess.DEVNULL)
    time.sleep(BEKLE)
    e = env_oku(); yeni = e["PORTMAN_API_TOKEN"]
    pid, surec = surec_anahtari()
    k, _ = hosting_ayar(e["PORTMAN_API_URL"], surec or "")
    gunluk = HOME / "logs" / "agent.log"
    sonra = [s for s in (gunluk.read_text(errors="replace").splitlines() if gunluk.exists() else []) if s[:19] >= bas]
    hata401 = sum(" api:" in s and "401" in s for s in sonra)
    yaz(f"== Kapı C · servis yeniden başlatıldı · {bas} · {BEKLE} sn beklendi")
    yaz(f"   servis: {sc('is-active', SERVIS)} · PID {once_pid} → {pid} · süreçteki eşleşme anahtarı {iz(surec) if surec else 'okunamadı'}")
    yaz(f"   hosting op=settings (süreçteki anahtarla): HTTP {k} · yeniden başlatmadan sonraki günlük: {len(sonra)} satır, "
        f"'başladı' {sum(' başladı ' in s for s in sonra)}, 401 hatası {hata401}")
    if not kontrol([("servis çalışıyor ve yeni bir süreç", sc("is-active", SERVIS) == "active" and pid not in ("", "0", once_pid)),
                    ("çalışan süreç yeni anahtarla (dosyayla aynı)", surec is not None and iz(surec) == iz(yeni) == d["yenile"]["yeni_eslesme_iz"]),
                    ("hosting süreçteki anahtarı kabul ediyor", k == 200),
                    ("günlükte yeniden başlatmadan sonra 'başladı' var, 401 yok", any(" başladı " in s for s in sonra) and hata401 == 0)]):
        dur("yeniden başlatma doğrulaması geçmedi.", "çıktıyı asistana gönder; eski anahtara dönülmez.")
    adim_kaydet("yeniden_baslat", {"gecti": True})
    yaz("SONUÇ: ajan yeni eşleşme anahtarıyla çalışıyor.")
    yaz("SONRAKİ ADIM: OpenAI panelinde ESKİ anahtarı iptal et (Revoke); sonra 'bitir'.")


def bitir() -> None:
    d = depo_durum(); gerek(d, "yeniden_baslat", "yeniden_baslat")
    e = env_oku(); api = e["PORTMAN_API_URL"]
    pid, surec = surec_anahtari()
    eski_e, eski_o = depo_oku("eski_eslesme") or "", depo_oku("eski_openai") or ""
    k_eski, _ = hosting_ayar(api, eski_e)
    k_yeni, ayar = hosting_ayar(api, surec or "")
    yeni_o = ayar.get("openai_key") or ""
    o_eski = openai_dene(eski_o)
    o_yeni = openai_dene(yeni_o) if yeni_o else (0, "anahtar_yok")
    yaz(f"== Kapı C · son doğrulama · {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    yaz(f"   eşleşme: eski ({d['hazirla']['eski_eslesme_iz']}) HTTP {k_eski} · yeni (süreçte {iz(surec) if surec else 'okunamadı'}) HTTP {k_yeni}")
    yaz(f"   OpenAI GET /models: eski ({d['hazirla']['eski_openai_iz']}) HTTP {o_eski[0]} {o_eski[1]} · "
        f"yeni ({iz(yeni_o) if yeni_o else 'YOK'}) HTTP {o_yeni[0]} {o_yeni[1]}".rstrip())
    ok = kontrol([("eski eşleşme anahtarı hosting'te geçersiz (401)", bool(eski_e) and iz(eski_e) == d["hazirla"]["eski_eslesme_iz"] and k_eski == 401),
                  ("yeni eşleşme anahtarı çalışıyor ve süreçteki anahtar dosyayla aynı", k_yeni == 200 and surec is not None and iz(surec) == iz(e["PORTMAN_API_TOKEN"])),
                  ("eski OpenAI anahtarı OpenAI'de geçersiz (401)", bool(eski_o) and iz(eski_o) == d["hazirla"]["eski_openai_iz"] and o_eski[0] == 401),
                  ("yeni OpenAI anahtarı geçerli ve hosting'in verdiği anahtar o", openai_gecerli(*o_yeni) and iz(yeni_o) == d["ara"]["yeni_openai_iz"])])
    if not ok:
        dur("son doğrulama geçmedi; geçici klasör silinmedi (denetim yinelenebilsin).",
            "eski OpenAI anahtarı hâlâ geçerliyse panelde iptal et ve birkaç dakika sonra 'bitir'i yinele; başka bir ✗ varsa çıktıyı asistana gönder.")
    silindi = depo_sil()
    yaz(f"   geçici klasör (eski anahtarlar) silindi: {'evet' if silindi else 'HAYIR'}")
    if not silindi:
        dur("geçici klasör silinemedi.", "'temizle'yi çalıştır.")
    yaz("SONUÇ: Kapı C tamam. Yeni eşleşme ve yeni OpenAI anahtarı çalışıyor; eski ikisi geçersiz; eski anahtarların kopyası kalmadı.")


def temizle() -> None:
    yaz(f"== Kapı C · temizle: geçici klasör {'silindi' if depo_sil() else 'SİLİNEMEDİ'} ({DEPO} artık {'yok' if not DEPO.exists() else 'VAR'})")


def durum() -> None:
    d = depo_durum()
    yaz(f"== Kapı C · durum · geçici klasör {'var' if DEPO.exists() else 'yok'}")
    for ad in ("hazirla", "yenile", "ara", "yeniden_baslat"):
        yaz(f"   {ad}: {'geçti · ' + time.strftime('%H:%M:%S', time.localtime(d[ad]['zaman'])) if ad in d else 'yapılmadı'}")


ADIMLAR = {"hazirla": hazirla, "yenile": yenile, "ara": ara, "yeniden_baslat": yeniden_baslat, "bitir": bitir, "temizle": temizle, "durum": durum}

if __name__ == "__main__":
    adim = sys.argv[1] if len(sys.argv) > 1 else ""
    if adim not in ADIMLAR:
        sys.exit("kullanım: python3 - <" + "|".join(ADIMLAR) + ">")
    if os.geteuid() != 0 and "PM_KAPI_C_DIR" not in os.environ:
        sys.exit("root olarak çalıştırılmalı")
    ADIMLAR[adim]()
