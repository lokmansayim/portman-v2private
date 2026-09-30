"""VPS teslimatını üretir: build/current.zip (+ .sha256, SURUM.txt) ve build/bootstrap_vps.sh (ajan gömülü).
Paket düzeni kanal paketiyle aynı (kökte worker.py; beyin/, motor/, is_emri/, referans dosyalar)."""
from __future__ import annotations
import hashlib, io, sys, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VPS = ROOT / "vps"
BUILD = VPS / "build"
SURUM = "kanal-v1.3-" + time.strftime("%Y%m%d-%H%M")

ATLA_DIZIN = {"__pycache__", "durum", "checks", "projects", "install", "tests", "package"}
# adaylar_test.json ve TEST* şablonları yalnız yerel testlerde (settings.test_adaylari) yüklenir; pakete girmez (canlıda test adayı yok)
ATLA_DOSYA = {"settings.json", "state.json", "state.lock", "worker.lock", "tick.lock", "api_token.txt", "lib.snapshot.php", "adaylar_test.json"}


def ekle_dizin(z: zipfile.ZipFile, kaynak: Path, hedef: str) -> int:
    n = 0
    for p in sorted(kaynak.rglob("*")):
        if p.is_dir(): continue
        if any(part in ATLA_DIZIN for part in p.relative_to(kaynak).parts): continue
        if p.name in ATLA_DOSYA or p.suffix in (".pyc", ".log"): continue
        if p.name.upper().startswith("TEST") and "adaylar" in p.parts: continue      # test aday şablonu ve görseli
        z.write(p, f"{hedef}/{p.relative_to(kaynak).as_posix()}"); n += 1
    return n


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / "kanal" / "worker.py", "worker.py")
        # İE-02 kalıcı mod: Postgres deposu, kalıcı işleyici, aktarma ve göçler (ajan yalnız PORTMAN_PG_DSN varken kullanır)
        for ad in ("depo.py", "kalici.py", "depo_aktar.py", "etkilesim.py"):        # etkilesim.py: İE-04 buton/liste cevabı çözümü
            z.write(ROOT / "kanal" / ad, ad)
        z.write(VPS / "kanit_sorgulari.sql", "kanit_sorgulari.sql")     # salt okunur kanıt sorguları (canlı kabul gösterimi)
        z.write(VPS / "tekrar_dene.py", "tekrar_dene.py")               # kabul gösterimi adım 7 (aynı kanal mesajı yeniden)
        for g in sorted((ROOT / "kanal" / "goc").glob("[0-9][0-9][0-9]_*.sql")):
            z.write(g, f"goc/{g.name}")
        for ad in ("self-test-request.json", "ref_h-connector.json", "ref_source-6x8.dxf", "DejaVuSans.ttf"):
            z.write(ROOT / "kanal" / ad, ad)
        n = ekle_dizin(z, ROOT / "beyin", "beyin") + ekle_dizin(z, ROOT / "motor", "motor") + ekle_dizin(z, ROOT / "is_emri", "is_emri")
        z.write(VPS / "agent.py", "agent.py")
        z.writestr("SURUM.txt", SURUM + "\n")
    raw = buf.getvalue(); sha = hashlib.sha256(raw).hexdigest()
    (BUILD / "current.zip").write_bytes(raw)
    (BUILD / "current.sha256").write_text(sha + "\n")
    (BUILD / "SURUM.txt").write_text(SURUM + "\n")
    sablon = (VPS / "bootstrap_template.sh").read_text(encoding="utf-8")
    ajan = (VPS / "agent.py").read_text(encoding="utf-8")
    assert "PYAGENT" not in ajan
    (BUILD / "bootstrap_vps.sh").write_text(sablon.replace("__AGENT_PY__", ajan.rstrip("\n")), encoding="utf-8")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        uye = len(z.namelist())                     # gerçek ZIP üye sayısı (denetim bulgusu F05: eski 'n+6' bir eksik sayıyordu)
    print(f"paket {SURUM}: {len(raw)} B, sha256 {sha[:16]}…, {uye} dosya; bootstrap {len((BUILD / 'bootstrap_vps.sh').read_bytes())} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
