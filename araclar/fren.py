#!/usr/bin/env python3
"""Korunan dosyalar freni (BK-21, 4 Kasım 2026).

Project thread'lerinde (claude.ai proje sohbeti) `.claude/settings.json` okunmaz: `sir_koruma.py`, `komut_koruma.py` ve
`hizli_kontrol.py` hook'ları ile izinlerin "engelle / sor" kuralları orada çalışmaz (4 Kasım 2026 denetimi). Bu betik hook'ların
ve izinlerin koruduğu dosya listesini iki yerde denetler:

  python3 araclar/fren.py [--taban origin/main]   oturumda, commit'ten ve PR'dan önce: dalın `main`'den farkı (commit'lenmemiş ve
                                                  izlenmeyen dosyalar dahil), değişen .py/.sh/.json'un sözdizimi, mühür denetimi
  python3 araclar/fren.py ci                      GitHub'da (`.github/workflows/korunan.yml`, pull_request_target): PR'ın dosyaları
                                                  ve Lokman'ın `patron-onayi` etiketi

Sınıflar (bir dosya birden çok listeye uyarsa en sıkısı geçer):
  yasak   sır ya da canlı durum dosyası depoya giriyor. Etiket kurtarmaz: dosya depodan çıkar, sır değiştirilir.
  onay    dondurulmuş kayıt, referans girdinin var olan dosyası, fren dosyası, mühür kaydında var olan bir mühür, karar dosyası
          silme: Lokman'ın onayı gerekir.
  bilgi   var olan bir karar dosyası, AGENTS.md ya da CLAUDE.md değişiyor: durdurmaz, PR'da görünür.

Onay: PR'da `patron-onayi` etiketi var, o etiketi en son depo sahibi (Lokman) GitHub'da kendisi eklemiş (bir uygulama üzerinden,
Claude dahil, eklenen sayılmaz) ve etiketten sonra yazılmış bir commit korunan bir dosyaya dokunmuyor. Etiketi oturum eklemez
(AGENTS.md: Lokman'ın yerine onay verilmez). Onaydan sonra korunan dosya yeniden değişirse Lokman etiketi kaldırıp yeniden ekler.

Çıkış: 0 temiz · 1 yasak, sözdizimi ya da mühür hatası, CI'da onaysız korunan dosya · 3 (yalnız oturumda) Lokman'ın onayı gerekir.
Yalnız standart kütüphane.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ONAY_ETIKETI = "patron-onayi"
MUHUR_KAYDI = "KARARLAR/muhurlu.json"

# Sır ve canlı durum dosyaları: `.claude/hooks/sir_koruma.py › KORUNAN` ile aynı desenler (testler/test_fren.py denetler).
YASAK = [
    (r"(^|/)[^/]*\.env$", "ortam/sır dosyası"),
    (r"(^|/)agent\.env$", "VPS ajan sırları"),
    (r"(^|/)claude_api\.json$", "hosting LLM anahtarı"),
    (r"(^|/)kanal/settings\.json$", "canlı kanal ayarı"),
    (r"(^|/)kanal/api_token\.txt$", "eşleşme anahtarı"),
    (r"(^|/)kanal/state\.json$", "canlı kuyruk durumu"),
    (r"(^|/)kanal/durum/", "canlı durum dizini"),
    (r"(^|/)kanal/lib\.snapshot\.php$", "hosting lib kopyası"),
    (r"\.(pem|key|p12|pfx)$", "anahtar dosyası"),
    (r"(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$", "SSH anahtarı"),
    (r"(^|/)deploy_key(\.pub)?$", "VPS dağıtım anahtarı"),
    (r"(^|/)rclone\.conf$", "Drive bağlantısı (rclone)"),
    (r"(^|/)yedek\.(pub|key)$", "yedek şifre anahtarı (age)"),
]
# Dondurulmuş kayıtlar: eklenen, değişen ya da silinen her dosya onay ister (hook ve izinlerde "engelle").
DONDURULMUS = [
    (r"^SHA256SUMS$", "v1.1.1 özet kaydı (dondurulmuş)"),
    (r"^KARARLAR\.md$", "karar günlüğü (dondurulmuş; yeni karar KARARLAR/ altına yeni dosya)"),
    (r"^testler/referans/20\d\d-\d\d-\d\d[a-z]?/", "dondurulmuş referans (yeniden dondurma D-02: kararla ve Lokman'ın onayıyla)"),
    (r"^hosting/", "hosting kayıt kopyası (düzenlenmez)"),
]
# Referans girdiler: yeni dosya eklenebilir; var olan dosya değişirse ya da silinirse onay ister (izinlerde "sor").
REFERANS_GIRDI = [
    (r"^is_emri/", "dondurulmuş İş Emri girdisi"),
    (r"^ref_katalog/", "dondurulmuş katalog girdisi"),
    (r"^ref_yan/", "dondurulmuş referans girdisi"),
    (r"^ref_prefabrik/", "dondurulmuş prefabrik kaynağı (D-12)"),
    (r"^beyin/veri/", "Beyin verisi (referans girdi)"),
    (r"^beyin/testler/", "harness vakaları (22 vaka değişmez; harness'i durum_dir ile koş)"),
    (r"^modeller/[^/]+\.json$", "model tanımı (D-07: var olan tanım değişmez, yeni dosya ya da sürüm)"),
    (r"^kurallar/liste/setler/", "dondurulmuş kural seti (eski set eski çıktıyı bayt bayt verir)"),
]
# Frenlerin kendisi ve onları sınayan yerler: her değişiklik onay ister (CLAUDE.md › Frenler: Lokman'ın onayıyla).
FREN = [
    (r"^\.claude/settings\.json$", "izinler ve hook ayarı"),
    (r"^\.claude/hooks/", "hook (fren kodu)"),
    (r"^\.claude/agents/", "hakem ajan (kapanış incelemesi)"),
    (r"^\.claude/skills/kapanis/", "kapanış adımları (doğrulama, kanıt)"),
    (r"^\.github/workflows/", "CI iş akışı (son kapı)"),
    (r"^araclar/fren\.py$", "bu fren"),
    (r"^testler/test_fren\.py$", "bu frenin testi"),
    (r"^testler/test_muhurlu_konular\.py$", "mühür kilit testi"),
    (r"^testler/referans/dogrula\.py$", "gerileme ve sır taraması kapısı (CI'da koşar)"),
    (r"^testler/test_sir_taramasi\.py$", "sır taramasının testi"),
    (r"^denetim/", "sır taraması (dogrula.py üzerinden CI'da)"),
    (r"^\.claude/rules/frenler\.md$", "frenlerin metni"),
]
# Kararlar ve ortak kurallar: değişiklik PR'da görünür; silme onay ister.
KARAR = [(r"^KARARLAR/(?!README\.md$)[^/]+\.md$", "karar dosyası (var olan kararın metni Lokman'ın sözü olmadan değişmez)")]
ORTAK = [(r"^(AGENTS|CLAUDE)\.md$", "ortak kural dosyası")]

# (liste, {durum: sınıf}); durum A eklendi, M değişti, D silindi. Listede olup durumu tabloda olmayan serbesttir.
SINIFLAR = [
    (YASAK, {"A": "yasak", "M": "yasak"}),
    (DONDURULMUS, {"A": "onay", "M": "onay", "D": "onay"}),
    (REFERANS_GIRDI, {"M": "onay", "D": "onay"}),
    (FREN, {"A": "onay", "M": "onay", "D": "onay"}),
    (KARAR, {"M": "bilgi", "D": "onay"}),
    (ORTAK, {"M": "bilgi", "D": "onay"}),
]
SIRA = {"bilgi": 1, "onay": 2, "yasak": 3}
SINIF_ADI = {"yasak": "YASAK", "onay": "ONAY GEREKİR", "bilgi": "bilgi"}


def _eslesen(yol: str, liste: list[tuple[str, str]]) -> str | None:
    for desen, neden in liste:
        if re.search(desen, yol):
            return neden
    return None


def _yol(yol: str) -> str:
    yol = yol.replace("\\", "/")
    return yol[2:] if yol.startswith("./") else yol


def sinifla(durum: str, yol: str) -> tuple[str, str] | None:
    """(durum, yol) → (sınıf, neden) ya da None (serbest). Birden çok liste uyarsa en sıkı sınıf."""
    yol = _yol(yol)
    en: tuple[str, str] | None = None
    for liste, kipler in SINIFLAR:
        neden = _eslesen(yol, liste)
        sinif = kipler.get(durum) if neden else None
        if sinif and (en is None or SIRA[sinif] > SIRA[en[0]]):
            en = (sinif, neden)
    return en


def siniflandir(degisiklikler: list[tuple[str, str]]) -> list[dict]:
    bulgular = []
    for durum, yol in degisiklikler:
        s = sinifla(durum, yol)
        if s:
            bulgular.append({"sinif": s[0], "durum": durum, "yol": _yol(yol), "neden": s[1]})
    return bulgular


def muhur_kaydi_bulgusu(durum: str, eski: str | None, yeni: str | None) -> dict | None:
    """Mühür kaydında var olan bir mühürü değiştiren ya da kaldıran, çekirdek listesini daraltan değişiklik onay ister (açma ve
    kapama dahil: Lokman'ın sözü kayda oturumun elinden girer, onayı etiketle Lokman verir). Yeni mühür eklemek serbest."""
    if eski is None:
        return None
    try:
        e = json.loads(eski)
    except ValueError:
        return None
    y = None
    if durum == "D" or yeni is None:
        degisen = ["kayıt siliniyor"]
    else:
        try:
            y = json.loads(yeni)
            degisen = [] if isinstance(y, dict) else ["kayıt biçimi bozuk"]
        except ValueError:
            degisen = ["kayıt JSON olarak okunmuyor"]
    if isinstance(y, dict):
        yk = {m.get("kod"): m for m in y.get("muhurler", [])}
        degisen = [str(m.get("kod")) for m in e.get("muhurler", []) if yk.get(m.get("kod")) != m]
        if set(e.get("cekirdek", [])) - set(y.get("cekirdek", [])):
            degisen.append("çekirdek listesi")
        if e.get("sema") != y.get("sema"):
            degisen.append("şema")
    if not degisen:
        return None
    return {"sinif": "onay", "durum": durum, "yol": MUHUR_KAYDI,
            "neden": f"mühür kaydında var olan mühür değişiyor ({', '.join(degisen)}); yeni mühür eklemek serbest"}


def pr_degisiklikleri(dosyalar: list[dict]) -> list[tuple[str, str]]:
    """GitHub'ın PR ya da commit dosya listesi → (durum, yol). Yeniden adlandırma: eski yol silindi, yeni yol eklendi."""
    sonuc = []
    for d in dosyalar:
        s, yol = d.get("status"), d["filename"]
        if s == "renamed":
            sonuc += [("D", d.get("previous_filename") or yol), ("A", yol)]
        elif s == "removed":
            sonuc.append(("D", yol))
        elif s in ("added", "copied"):
            sonuc.append(("A", yol))
        elif s != "unchanged":
            sonuc.append(("M", yol))
    return sonuc


def _zaman(metin: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(metin.replace("Z", "+00:00"))


def onay_durumu(etiketler: list[str], olaylar: list[dict], sahip: str, etiket: str = ONAY_ETIKETI) -> tuple[bool, str, str | None]:
    """Etiket var mı ve en son ekleyen, uygulama aracılığı olmadan depo sahibi mi. → (onaylı, metin, etiketin zamanı)."""
    if etiket not in etiketler:
        return False, f"`{etiket}` etiketi yok", None
    eklemeler = sorted((o for o in olaylar if o.get("event") == "labeled" and (o.get("label") or {}).get("name") == etiket),
                       key=lambda o: o.get("created_at") or "")
    if not eklemeler:
        return False, f"`{etiket}` etiketini kimin eklediği okunamadı", None
    son = eklemeler[-1]
    kim = (son.get("actor") or {}).get("login") or "?"
    uygulama = son.get("performed_via_github_app")
    if kim != sahip:
        return False, f"`{etiket}` etiketini {kim} ekledi; onay yalnız {sahip}'ın", None
    if uygulama:
        ad = uygulama.get("slug") or uygulama.get("name") or "uygulama"
        return False, f"`{etiket}` etiketi bir uygulama üzerinden ({ad}) eklendi; Lokman GitHub'da kendisi ekler", None
    return True, f"`{etiket}`: {kim}, {son.get('created_at')}", son.get("created_at")


def onaydan_sonraki(commitler: list[dict], zaman: str) -> list[str]:
    """Etiketten sonra yazılmış tek ebeveynli commit'ler (zamanı okunamayan da sayılır). Birleştirme commit'i sayılmaz: `main`'i
    dala getirir, `main`'de olan değişiklik PR'ın farkında görünmez."""
    t = _zaman(zaman)
    sonra = []
    for c in commitler:
        if len(c.get("parents") or []) != 1:
            continue
        tarih = ((c.get("commit") or {}).get("committer") or {}).get("date")
        if not tarih or _zaman(tarih) > t:
            sonra.append(c["sha"])
    return sonra


def eskiyen_onay(sonraki: list[tuple[str, list[tuple[str, str]]]], korunan: set[str]) -> list[str]:
    """Etiketten sonraki commit'lerden korunan bir dosyaya dokunanlar: `<sha> <yol>`."""
    out = []
    for sha, degisiklikler in sonraki:
        for durum, yol in degisiklikler:
            yol = _yol(yol)
            s = sinifla(durum, yol)
            if yol in korunan or (s and s[0] in ("onay", "yasak")):
                out.append(f"{sha[:7]} {yol}")
    return out


def rapor(bulgular: list[dict]) -> list[str]:
    satirlar = []
    for sinif in ("yasak", "onay", "bilgi"):
        for b in (b for b in bulgular if b["sinif"] == sinif):
            satirlar.append(f"- {SINIF_ADI[sinif]} · {b['durum']} `{b['yol']}` · {b['neden']}")
    return satirlar


# ---------------------------------------------------------------- oturumda

def _git(*args: str, kok: Path) -> str:
    return subprocess.run(["git", *args], cwd=kok, capture_output=True, text=True, check=True).stdout


def _temel(taban: str, kok: Path) -> str:
    return _git("merge-base", taban, "HEAD", kok=kok).strip()


def yerel_degisiklikler(taban: str, kok: Path) -> list[tuple[str, str]]:
    temel = _temel(taban, kok)
    sonuc = []
    for satir in _git("diff", "--name-status", "-M", temel, kok=kok).splitlines():
        parca = satir.split("\t")
        d = parca[0][:1]
        if d == "R":
            sonuc += [("D", parca[1]), ("A", parca[2])]
        elif d == "C":
            sonuc.append(("A", parca[2]))
        elif d in "AMD":
            sonuc.append((d, parca[1]))
        else:
            sonuc.append(("M", parca[-1]))
    for yol in _git("ls-files", "--others", "--exclude-standard", kok=kok).splitlines():
        if yol:
            sonuc.append(("A", yol))
    return sonuc


def yerel_muhur_kaydi(degisiklikler: list[tuple[str, str]], taban: str, kok: Path) -> dict | None:
    durumlar = [d for d, y in degisiklikler if _yol(y) == MUHUR_KAYDI]
    if not durumlar:
        return None
    try:
        eski = _git("show", f"{_temel(taban, kok)}:{MUHUR_KAYDI}", kok=kok)
    except subprocess.CalledProcessError:
        eski = None
    p = kok / MUHUR_KAYDI
    yeni = p.read_text(encoding="utf-8") if p.is_file() else None
    return muhur_kaydi_bulgusu(durumlar[-1], eski, yeni)


def sozdizimi(degisiklikler: list[tuple[str, str]], kok: Path) -> list[str]:
    """hizli_kontrol.py'nin işi: değişen .py / .sh / .json dosyası açılıyor mu."""
    hatalar = []
    for durum, yol in degisiklikler:
        p = kok / yol
        if durum == "D" or not p.is_file():
            continue
        uzanti = p.suffix.lower()
        try:
            if uzanti == ".py":
                compile(p.read_bytes(), yol, "exec", dont_inherit=True)
            elif uzanti == ".json":
                json.loads(p.read_text(encoding="utf-8"))
            elif uzanti == ".sh":
                r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
                if r.returncode:
                    raise SyntaxError(r.stderr.strip())
        except (SyntaxError, ValueError, UnicodeDecodeError) as e:
            hatalar.append(f"- sözdizimi · `{yol}` · {str(e).splitlines()[0] if str(e) else type(e).__name__}")
    return hatalar


def muhur(kok: Path) -> tuple[bool, str]:
    hook = kok / ".claude" / "hooks" / "muhur_koruma.py"
    if not hook.is_file():
        return True, "mühür denetimi atlandı (fren dosyası yok)"
    r = subprocess.run([sys.executable, str(hook), "--kok", str(kok), "denetle"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _tabani_guncelle(taban: str, kok: Path) -> str | None:
    """`origin/main` ile kıyaslanıyorsa önce alınır (eski origin/main, main'e girmiş işi dalın farkı sanar). → uyarı ya da None."""
    if taban != "origin/main":
        return None
    try:
        r = subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=kok, capture_output=True, text=True, timeout=90)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "uyarı: origin/main alınamadı (zaman aşımı); yereldeki origin/main ile kıyaslanıyor"
    if r.returncode:
        return f"uyarı: origin/main alınamadı ({(r.stderr or '').strip().splitlines()[-1:] or ['?']}); yereldeki origin/main ile kıyaslanıyor"
    return None


def yerel(taban: str, kok: Path = KOK) -> int:
    uyari = _tabani_guncelle(taban, kok)
    try:
        degisiklikler = yerel_degisiklikler(taban, kok)
        kayit = yerel_muhur_kaydi(degisiklikler, taban, kok)
    except subprocess.CalledProcessError as e:
        print(f"DUR: git farkı okunamadı ({taban}): {e.stderr.strip()}")
        return 1
    bulgular = siniflandir(degisiklikler) + ([kayit] if kayit else [])
    hatalar = sozdizimi(degisiklikler, kok)
    muhur_tamam, muhur_metni = muhur(kok)
    print(f"Fren denetimi · {len(degisiklikler)} dosya, taban {taban}")
    if uyari:
        print(f"- {uyari}")
    for s in rapor(bulgular) + hatalar:
        print(s)
    print(f"- mühür · {muhur_metni}")
    yasak = any(b["sinif"] == "yasak" for b in bulgular)
    onay = any(b["sinif"] == "onay" for b in bulgular)
    if yasak or hatalar or not muhur_tamam:
        print("SONUÇ: DUR. Yasak dosya, sözdizimi ya da mühür hatası düzeltilmeden commit ve PR yok.")
        return 1
    if onay:
        print(f"SONUÇ: Lokman'ın onayı gerekir. PR'da `{ONAY_ETIKETI}` etiketini Lokman ekler; "
              "onay yoksa iş main'e girmez. Oturum etiketi eklemez.")
        return 3
    print("SONUÇ: temiz.")
    return 0


# ---------------------------------------------------------------- GitHub'da

def _api(yol: str, token: str) -> list | dict:
    istek = urllib.request.Request("https://api.github.com" + yol, headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "portman-fren"})
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        return json.load(yanit)


def _sayfalar(yol: str, token: str, en_cok: int = 30) -> list:
    hepsi = []
    ayrac = "&" if "?" in yol else "?"
    for sayfa in range(1, en_cok + 1):
        parca = _api(f"{yol}{ayrac}per_page=100&page={sayfa}", token)
        if isinstance(parca, dict):  # commit: dosyalar `files` altında
            parca = parca.get("files") or []
        hepsi += parca
        if len(parca) < 100:
            return hepsi
    raise RuntimeError(f"{yol}: {en_cok} sayfadan uzun; denetim eksik kalırdı")


def _icerik(depo: str, yol: str, ref: str, token: str) -> str | None:
    try:
        veri = _api(f"/repos/{depo}/contents/{yol}?ref={ref}", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not isinstance(veri, dict) or veri.get("encoding") != "base64":
        raise RuntimeError(f"{yol}@{ref[:7]} okunamadı")
    return base64.b64decode(veri["content"]).decode("utf-8")


def ci() -> int:
    depo, no = os.environ["DEPO"], os.environ["PR_NO"]
    token = os.environ.get("GH_TOKEN", "")
    sahip = os.environ.get("SAHIP") or depo.split("/")[0]
    try:
        degisiklikler = pr_degisiklikleri(_sayfalar(f"/repos/{depo}/pulls/{no}/files", token))
        bulgular = siniflandir(degisiklikler)
        kayit_durum = [d for d, y in degisiklikler if y == MUHUR_KAYDI]
        if kayit_durum:  # mühür kaydı: var olan mühürler dalın ayrıldığı yerle kıyaslanır
            pr = _api(f"/repos/{depo}/pulls/{no}", token)  # PR'ın commit'leri taban depoda da okunur (refs/pull/N/head)
            bas = pr["head"]["sha"]
            temel = _api(f"/repos/{depo}/compare/{pr['base']['sha']}...{bas}", token)["merge_base_commit"]["sha"]
            yeni = None if kayit_durum[-1] == "D" else _icerik(depo, MUHUR_KAYDI, bas, token)
            kayit = muhur_kaydi_bulgusu(kayit_durum[-1], _icerik(depo, MUHUR_KAYDI, temel, token), yeni)
            if kayit:
                bulgular.append(kayit)
        onay_gerekli = any(b["sinif"] == "onay" for b in bulgular)
        onayli, onay_metni = True, ""
        if onay_gerekli:
            etiketler = [e["name"] for e in _sayfalar(f"/repos/{depo}/issues/{no}/labels", token)]
            onayli, onay_metni, zaman = onay_durumu(etiketler, _sayfalar(f"/repos/{depo}/issues/{no}/events", token), sahip)
            if onayli:
                commitler = _sayfalar(f"/repos/{depo}/pulls/{no}/commits", token, en_cok=3)
                if len(commitler) >= 250:  # GitHub PR'ın ilk 250 commit'ini verir; sonrası görülmez
                    raise RuntimeError("PR'da 250'den çok commit var; onaydan sonraki değişiklik denetlenemez")
                sonraki = [(sha, pr_degisiklikleri(_sayfalar(f"/repos/{depo}/commits/{sha}", token, en_cok=10)))
                           for sha in onaydan_sonraki(commitler, zaman)]
                eski = eskiyen_onay(sonraki, {b["yol"] for b in bulgular if b["sinif"] in ("onay", "yasak")})
                if eski:
                    onayli = False
                    onay_metni = (f"etiketten sonra korunan dosya yeniden değişti ({'; '.join(eski[:5])}); Lokman etiketi kaldırıp "
                                  "yeniden ekler")
    except Exception as e:  # noqa: BLE001 — okunamayan PR'da kapı kapalı kalır
        print(f"::error::Korunan dosya denetimi koşamadı: {e}")
        return 1
    yasak = any(b["sinif"] == "yasak" for b in bulgular)
    if yasak:
        sonuc = "KIRMIZI: sır ya da canlı durum dosyası PR'da. Dosya depodan çıkar, sır değiştirilir; etiket kurtarmaz."
    elif onay_gerekli and not onayli:
        sonuc = (f"KIRMIZI: korunan dosya değişiyor, Lokman'ın onayı yok ({onay_metni}). Lokman PR'a `{ONAY_ETIKETI}` etiketini "
                 "GitHub'da kendisi ekler; oturum eklemez.")
    elif onay_gerekli:
        sonuc = f"YEŞİL: korunan dosyalar Lokman'ın onayıyla ({onay_metni})."
    else:
        sonuc = "YEŞİL: korunan dosya yok."
    metin = [f"## Korunan dosyalar · PR #{no}", "", f"{len(degisiklikler)} dosya.", ""] + (rapor(bulgular) or ["- korunan dosya yok"]) \
        + ["", f"**{sonuc}**"]
    print("\n".join(metin))
    for b in bulgular:
        seviye = "error" if b["sinif"] == "yasak" or (b["sinif"] == "onay" and not onayli) else "notice"
        print(f"::{seviye} file={b['yol']}::{SINIF_ADI[b['sinif']]}: {b['neden']}")
    ozet = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet:
        with open(ozet, "a", encoding="utf-8") as f:
            f.write("\n".join(metin) + "\n")
    return 1 if yasak or (onay_gerekli and not onayli) else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Korunan dosyalar freni (BK-21)")
    ap.add_argument("kip", nargs="?", choices=["yerel", "ci"], default="yerel")
    ap.add_argument("--taban", default="origin/main", help="dalın karşılaştırıldığı yer (yerel kip)")
    o = ap.parse_args(argv)
    if o.kip == "ci":
        return ci()
    try:  # çalışılan klasörün deposu (betik başka bir kopyadan da koşturulabilir)
        kok = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        kok = KOK
    return yerel(o.taban, kok)


if __name__ == "__main__":
    sys.exit(main())
