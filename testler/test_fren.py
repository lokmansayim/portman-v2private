"""BK-21 · Korunan dosyalar freni (`araclar/fren.py`) ve CI işi (`.github/workflows/korunan.yml`).

Project thread'lerinde hook ve izinler yüklenmez (4 Kasım 2026 denetimi); aynı liste CI'da denetlenir. Bu testler: hook'un ve
izinlerin koruduğu her yerin frende de korunduğunu, sınıfların, yeniden adlandırmanın, Lokman'ın etiket onayının ve oturumdaki
kipin davranışını sınar. Ağ yok.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fren", KOK / "araclar" / "fren.py")
fren = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fren)


def _hook_korunan() -> list[str]:
    """`sir_koruma.py › KORUNAN` desenleri (hook içe aktarılırken stdin okur; metinden okunur)."""
    agac = ast.parse((KOK / ".claude" / "hooks" / "sir_koruma.py").read_text(encoding="utf-8"))
    for dugum in agac.body:
        if isinstance(dugum, ast.Assign) and any(getattr(h, "id", None) == "KORUNAN" for h in dugum.targets):
            return [ast.literal_eval(e.elts[0]) for e in dugum.value.elts]
    raise AssertionError("KORUNAN bulunamadı")


def test_hook_listesi_frende():
    """Hook'un engellediği her dosya deseni frende aynen var (yasak ya da dondurulmuş)."""
    frendeki = {d for d, _ in fren.YASAK + fren.DONDURULMUS}
    eksik = [d for d in _hook_korunan() if d not in frendeki]
    assert not eksik, f"hook'ta olup frende olmayan desenler: {eksik}"


def _ornek(izin: str) -> str:
    yol = izin[len("Edit(./"):-1]
    return yol.replace("**/", "x/").replace("/**", "/x.md").replace("2026-*", "2026-01-01").replace("*", "y")


def test_izin_listesi_frende():
    """settings.json'da düzenlemesi "sor" ya da "engelle" olan her yer frende de durdurulur ya da görünür."""
    izinler = json.loads((KOK / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]
    yerler = [i for i in izinler["ask"] + izinler["deny"] if i.startswith("Edit(./")]
    assert len(yerler) >= 15
    for izin in yerler:
        yol = _ornek(izin)
        s = fren.sinifla("M", yol)
        assert s, f"{izin} ({yol}) frende serbest"
        if izin == "Edit(./KARARLAR/**)":
            assert s[0] == "bilgi"  # yeni karar ve README serbest; var olan karar dosyası PR'da görünür (BK-21)
        else:
            assert s[0] in ("yasak", "onay"), (izin, s)


@pytest.mark.parametrize("durum, yol, beklenen", [
    ("A", "kanal/settings.json", "yasak"),
    ("M", "vps/agent.env", "yasak"),
    ("A", "x/deploy_key", "yasak"),
    ("D", "kanal/settings.json", None),
    ("M", "SHA256SUMS", "onay"),
    ("M", "KARARLAR.md", "onay"),
    ("A", "testler/referans/2026-11-04/pdf_parmak_izleri.txt", "onay"),
    ("M", "testler/referans/2026-10-14b/sonuc.json", "onay"),
    ("M", "testler/referans/dogrula.py", None),
    ("A", "hosting/x.php", "onay"),
    ("A", "is_emri/yeni.json", None),
    ("M", "is_emri/p6001.json", "onay"),
    ("D", "beyin/veri/adaylar.json", "onay"),
    ("M", "beyin/testler/mesajlar.json", "onay"),
    ("M", "ref_prefabrik/README.md", "onay"),
    ("A", "modeller/YENI.json", None),
    ("M", "modeller/altin.json", "onay"),
    ("M", "modeller/banka/KT04/tanim.json", None),
    ("M", "kurallar/liste/setler/0.19.json", "onay"),
    ("M", "kurallar/liste/kurallar.json", None),
    ("M", ".claude/settings.json", "onay"),
    ("M", ".claude/hooks/komut_koruma.py", "onay"),
    ("A", ".github/workflows/yeni.yml", "onay"),
    ("M", "araclar/fren.py", "onay"),
    ("M", "testler/test_muhurlu_konular.py", "onay"),
    ("M", ".claude/rules/frenler.md", "onay"),
    ("M", ".claude/rules/motor-cizim.md", None),
    ("M", "KARARLAR/D-28.md", "bilgi"),
    ("M", "KARARLAR/README.md", None),
    ("A", "KARARLAR/D-48.md", None),
    ("M", "AGENTS.md", "bilgi"),
    ("M", "motor/dxf_out.py", None),
    ("M", "./SHA256SUMS", "onay"),
])
def test_sinif(durum, yol, beklenen):
    s = fren.sinifla(durum, yol)
    assert (s[0] if s else None) == beklenen


def test_yeniden_adlandirma():
    """Referans girdiden dışarı taşınan dosya silinmiş sayılır (onay); yeni adı serbest."""
    d = fren.pr_degisiklikleri([
        {"status": "renamed", "filename": "deneme/x.json", "previous_filename": "is_emri/p6001.json"},
        {"status": "added", "filename": "docs/yeni.md"},
        {"status": "removed", "filename": "SHA256SUMS"},
        {"status": "modified", "filename": "motor/dxf_out.py"},
    ])
    assert d == [("D", "is_emri/p6001.json"), ("A", "deneme/x.json"), ("A", "docs/yeni.md"), ("D", "SHA256SUMS"),
                 ("M", "motor/dxf_out.py")]
    assert [b["yol"] for b in fren.siniflandir(d)] == ["is_emri/p6001.json", "SHA256SUMS"]


def _olay(kim, zaman, uygulama=None, ad=fren.ONAY_ETIKETI, olay="labeled"):
    return {"event": olay, "label": {"name": ad}, "actor": {"login": kim}, "created_at": zaman,
            "performed_via_github_app": uygulama}


CLAUDE = {"slug": "claude", "name": "Claude"}


@pytest.mark.parametrize("etiketler, olaylar, beklenen", [
    ([fren.ONAY_ETIKETI], [_olay("lokmansayim", "2026-11-04T06:00:00Z")], True),
    ([fren.ONAY_ETIKETI], [_olay("lokmansayim", "2026-11-04T06:00:00Z", CLAUDE)], False),
    ([fren.ONAY_ETIKETI], [_olay("baskasi", "2026-11-04T06:00:00Z")], False),
    ([], [_olay("lokmansayim", "2026-11-04T06:00:00Z")], False),
    ([fren.ONAY_ETIKETI], [], False),
    # en son ekleme sayılır
    ([fren.ONAY_ETIKETI], [_olay("lokmansayim", "2026-11-04T06:00:00Z", CLAUDE), _olay("lokmansayim", "2026-11-04T07:00:00Z")], True),
    ([fren.ONAY_ETIKETI], [_olay("lokmansayim", "2026-11-04T07:00:00Z", CLAUDE), _olay("lokmansayim", "2026-11-04T06:00:00Z")], False),
    # başka etiket onay değildir
    (["baska"], [_olay("lokmansayim", "2026-11-04T06:00:00Z", ad="baska")], False),
])
def test_onay(etiketler, olaylar, beklenen):
    assert fren.onay_durumu(etiketler, olaylar, "lokmansayim")[0] is beklenen


def _git(kok, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=kok, check=True, capture_output=True)


def test_yerel_kip(tmp_path):
    """Oturum kipi: dalın farkı (commit'lenmemiş ve izlenmeyen dahil), sözdizimi; çıkış 0 / 3 / 1."""
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "SHA256SUMS").write_text("a\n")
    (tmp_path / "motor.py").write_text("x = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "ilk")
    _git(tmp_path, "checkout", "-q", "-b", "is")

    def kos():
        r = subprocess.run([sys.executable, str(KOK / "araclar" / "fren.py"), "--taban", "main"], cwd=tmp_path, capture_output=True,
                           text=True)
        return r.returncode, r.stdout

    (tmp_path / "motor.py").write_text("x = 2\n")
    assert kos()[0] == 0
    (tmp_path / "SHA256SUMS").write_text("b\n")  # commit'lenmemiş değişiklik de görülür
    kod, cikti = kos()
    assert kod == 3 and "SHA256SUMS" in cikti
    (tmp_path / "bozuk.json").write_text("{")  # izlenmeyen dosya da görülür
    kod, cikti = kos()
    assert kod == 1 and "bozuk.json" in cikti
    (tmp_path / "bozuk.json").write_text("{}")
    (tmp_path / "kanal").mkdir()
    (tmp_path / "kanal" / "settings.json").write_text("{}")
    kod, cikti = kos()
    assert kod == 1 and "YASAK" in cikti


def test_ci_isi_taban_kodunu_kosar():
    """CI işi PR'ın kodunu çekmez: pull_request_target, yalnız okuma izni, iş adı dal korumasındakiyle aynı."""
    metin = (KOK / ".github" / "workflows" / "korunan.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" in metin and "\n  pull_request:" not in metin
    assert "ref:" not in metin, "PR'ın dalı çekilmez"
    assert "write" not in metin.split("permissions:", 1)[1].split("jobs:", 1)[0]
    assert "name: Korunan dosya onayı" in metin
    assert "python3 araclar/fren.py ci" in metin
