"""D-71 · vps/kurulum_on_bakis.sh (sürüm kurulumundan önce salt okunur bakış) sahte psql ve yerel çıplak git deposuyla.
Postgres, ağ, canlı, LLM ve WhatsApp yok. Betik hiçbir şeyi değiştirmez: settings.json ve sürüm dizinleri koşudan sonra bayt bayt aynı."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
BETIK = KOK / "vps" / "kurulum_on_bakis.sh"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@ornek.invalid", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@ornek.invalid"}

# Sahte psql: sorgunun içindeki ilk eşleşen anahtarın sayısını yazar (sayılar ortamdan).
SAHTE_PSQL = """#!/usr/bin/env bash
q="$2"
case "$q" in
  *"interval '24 hours'"*) echo "${PM_S_MK24:-0}" ;;
  *"FROM muhendis_kontrolleri WHERE durum = 'bekliyor'"*) echo "${PM_S_MK:-0}" ;;
  *"patron_durum = 'bekliyor'"*) echo "${PM_S_PATRON:-0}" ;;
  *"FROM revizyonlar"*) echo "${PM_S_REV:-0}" ;;
  *"FROM isler"*) echo "${PM_S_IS:-0}" ;;
  *"FROM giden"*) echo "${PM_S_GIDEN:-0}" ;;
  *"sema_surumu"*) echo 8 ;;
  *) echo "?" ;;
esac
"""


def _git(calisma: Path, *a):
    return subprocess.run(["git", "-C", str(calisma), *a], check=True, capture_output=True, text=True, env={**os.environ, **GIT_ENV})


def _ortam(tmp_path: Path, ayar: dict, oz_test: bool = True) -> dict:
    bare = tmp_path / "kaynak.git"; calisma = tmp_path / "calisma"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(calisma)], check=True, capture_output=True)
    (calisma / "x").write_text("x\n")
    _git(calisma, "add", "-A"); _git(calisma, "commit", "-q", "-m", "x")
    _git(calisma, "tag", "-a", "v2026.11.08", "-m", "açıklamalı"); _git(calisma, "tag", "v2026.11.09")       # ikincisi hafif
    _git(calisma, "push", "-q", "origin", "main", "--tags")
    kok = tmp_path / "opt"
    for s in ("v2026.10.15", "v2026.10.16"):
        (kok / "surumler" / s).mkdir(parents=True); (kok / "surumler" / s / "SURUM").write_text(s + "\n")
    os.symlink(kok / "surumler" / "v2026.10.16", kok / "guncel"); os.symlink(kok / "surumler" / "v2026.10.15", kok / "onceki")
    (kok / "data" / "nabiz").mkdir(parents=True)
    (kok / "data" / "settings.json").write_text(json.dumps(ayar, ensure_ascii=False))
    (kok / "data" / "nabiz" / "yedek.json").write_text(json.dumps({"zaman": 1_762_562_511}))
    if oz_test:
        (kok / "data" / "self-test-result.json").write_text(json.dumps({"state": "done", "surum": "v2026.10.15"}))
    psql = tmp_path / "psql"; psql.write_text(SAHTE_PSQL); psql.chmod(0o755)
    return {"PM_KOK": str(kok), "PM_ETC": str(tmp_path / "etc"), "PM_PSQL": str(psql), "PM_GIT_URL": str(bare), "PM_TEST": "1",
            "PM_EN_AZ_MB": "1", "PM_SIMDI": str(1_762_562_511 + 13 * 3600)}


def _kos(env: dict, etiket: str, **sayi) -> subprocess.CompletedProcess:
    ek = {f"PM_S_{k.upper().rstrip('_')}": str(v) for k, v in sayi.items()}
    return subprocess.run(["bash", str(BETIK), etiket], env={**os.environ, **env, **ek}, capture_output=True, text=True, timeout=120,
                          stdin=subprocess.DEVNULL)


def _iz(kok: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(kok.rglob("*")):
        h.update(str(p.relative_to(kok)).encode())
        if p.is_file() and not p.is_symlink():
            h.update(p.read_bytes())
        elif p.is_symlink():
            h.update(os.readlink(p).encode())
    return h.hexdigest()


def test_temiz_sunucu_kurulabilir_ve_yeni_ozellikler_kapali(tmp_path):
    canli = {"enabled": True, "dry_run": False, "mesaj_katmani": True, "ucb_taban_url": None,
             "plan_uretimi": {"acik": False}, "llm_once_revizyon": {"acik": False}}           # v2026.10.16 ayarı: dört yeni anahtar yok
    env = _ortam(tmp_path, canli)
    once = _iz(Path(env["PM_KOK"]))
    r = _kos(env, "v2026.11.08")
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "guncel: v2026.10.16 · onceki: v2026.10.15" in out
    assert "var: v2026.11.08 →" in out and "(açıklamalı)" in out
    assert "açık iş 0 · bekleyen giden 0 · şema 8" in out
    assert "kararı bekleyen mühendis kontrolü: 0 (24 saati geçmiş: 0)" in out and "NOT:" not in out
    assert "kanal (enabled): açık · dry_run: hayır · mesaj katmanı: açık · 3D adresi (ucb_taban_url): boş" in out
    assert "plan üretimi (İE-14): kapalı · LLM-önce revizyon: kapalı" in out
    for k in ("banka_germe", "gorsel_okuma", "talep_formu", "bayi_kaydi", "yarim_pano"):
        assert f"{k} (" in out
    assert out.count("ayarda yok → kapalı") == 5 and "yeni özelliklerin hepsi kapalı" in out     # İE-39 PR-2: yarim_pano eklendi
    assert "son yedek: 13 saat önce" in out
    assert "öz-test sonucu var (sürüm v2026.10.15, done): kurulumda öz-test yeniden koşmaz, LLM çağrısı yok" in out
    assert out.rstrip().endswith("== sonuç: KURULABİLİR (hiçbir şey değişmedi)")
    assert _iz(Path(env["PM_KOK"])) == once                                                      # salt okunur


def test_engeller_beklet_der_ve_d19_bildirimini_soyler(tmp_path):
    env = _ortam(tmp_path, {"enabled": True, "bayi_kaydi": {"acik": True}, "talep_formu": {"acik": False}}, oz_test=False)
    r = _kos(env, "v2026.11.09", is_=0, giden=2, mk=3, mk24=2, patron=1, rev=4)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "var ama açıklamalı değil: v2026.11.09" in out
    assert "bekleyen giden 2" in out
    assert "kararı bekleyen mühendis kontrolü: 3 (24 saati geçmiş: 2) · fiyat hatırlatması bekleyen: 1 · onay bekleyen revizyon: 4" in out
    assert "NOT: 24 saati geçmiş 2 kontrol" in out and "ücretli şablon" in out
    assert "bayi_kaydi (WhatsApp'tan bayi kaydı, İE-22, satır 111): açık" in out and "DİKKAT: açık yeni özellik: bayi_kaydi" in out
    assert "DİKKAT: öz-test sonucu yok" in out and "1 ücretli çağrı (~0,03 $)" in out
    assert "bekle: etiket açıklamalı değil" in out and "bekle: bekleyen giden 0 değil" in out
    assert out.rstrip().endswith("== sonuç: BEKLE (2 madde; hiçbir şey değişmedi)")


def test_etiket_yoksa_ve_guncelse_bekle(tmp_path):
    env = _ortam(tmp_path, {})
    r = _kos(env, "v2026.11.10")
    assert "yok: v2026.11.10 GitHub'da değil" in r.stdout and "== sonuç: BEKLE" in r.stdout
    r = _kos(env, "v2026.10.16")
    assert "bekle: v2026.10.16 zaten guncel" in r.stdout
    r = _kos(env, "2026.11.08")
    assert "bekle: etiket biçimi" in r.stdout


def test_stdin_ile_bash_s_betigin_tamami_kosar(tmp_path):
    """Sunucuda kopyası olmadığı için Mac'ten `… | ssh portman-vps 'bash -s -- <etiket>'` ile koşar: psql, git ve ssh betiğin kalanını
    stdin'den yutmamalı (gövde işlevde, komutların stdin'i /dev/null)."""
    env = _ortam(tmp_path, {})
    yutan = Path(env["PM_PSQL"]); yutan.write_text(SAHTE_PSQL.replace('q="$2"', 'q="$2"; cat > /dev/null'))   # stdin'i sonuna kadar okur
    r = subprocess.run(["bash", "-s", "--", "v2026.11.08"], input=BETIK.read_text(encoding="utf-8"), env={**os.environ, **env},
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "-- [6/6] son yedek ve öz-test" in r.stdout and r.stdout.rstrip().endswith("== sonuç: KURULABİLİR (hiçbir şey değişmedi)")
