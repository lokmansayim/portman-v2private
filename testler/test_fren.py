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
    # inceleme bulguları (BK-21): sır taraması, gerileme kapısı, hakem ve kapanış da frendir
    ("M", "testler/referans/dogrula.py", "onay"),
    ("M", "testler/test_sir_taramasi.py", "onay"),
    ("M", "denetim/kos.py", "onay"),
    ("D", ".claude/agents/geometri-hakemi.md", "onay"),
    ("M", ".claude/skills/kapanis/SKILL.md", "onay"),
    ("M", ".claude/skills/atolye/SKILL.md", None),
    # karar ve ortak kural silinmez; değişikliği görünür
    ("D", "KARARLAR/D-28.md", "onay"),
    ("D", "AGENTS.md", "onay"),
    ("D", "KARARLAR/README.md", None),
    # birden çok liste uyarsa en sıkısı: referans girdideki sır dosyası yasak, yeni dosya olsa da
    ("A", "beyin/veri/agent.env", "yasak"),
    ("M", "is_emri/x.key", "yasak"),
    ("D", "is_emri/x.key", "onay"),
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
    onayli, _, zaman = fren.onay_durumu(etiketler, olaylar, "lokmansayim")
    assert onayli is beklenen and (zaman is not None) is beklenen


def _kayit(*muhurler, cekirdek=("a", "b")):
    return json.dumps({"sema": "s/1", "cekirdek": list(cekirdek), "muhurler": list(muhurler)}, ensure_ascii=False)


M1 = {"kod": "M-01", "kural": "k", "durum": "mühürlü", "kilitler": [{"yer": "x.json#a", "iz": "1"}], "gecmis": []}
M2 = {"kod": "M-02", "kural": "k2", "durum": "mühürlü", "kilitler": [], "gecmis": []}


@pytest.mark.parametrize("durum, eski, yeni, beklenen", [
    ("M", _kayit(M1), _kayit(M1, M2), None),                                    # yeni mühür serbest
    ("M", _kayit(M1), _kayit(dict(M1, kural="gevşek")), "M-01"),                 # kural değişti
    ("M", _kayit(M1), _kayit(dict(M1, durum="açık")), "M-01"),                   # açma da Lokman'ın onayıyla
    ("M", _kayit(M1), _kayit(dict(M1, gecmis=[{"soz": "uydurma"}])), "M-01"),    # kapama (geçmiş) da
    ("M", _kayit(M1, M2), _kayit(M2), "M-01"),                                   # mühür silinmez
    ("M", _kayit(M1), _kayit(M1, cekirdek=("a",)), "çekirdek"),
    ("M", _kayit(M1), "{", "JSON"),
    ("D", _kayit(M1), None, "siliniyor"),
    ("A", None, _kayit(M1), None),                                               # ilk kayıt
])
def test_muhur_kaydi(durum, eski, yeni, beklenen):
    b = fren.muhur_kaydi_bulgusu(durum, eski, yeni)
    if beklenen is None:
        assert b is None
    else:
        assert b["sinif"] == "onay" and b["yol"] == fren.MUHUR_KAYDI and beklenen in b["neden"]


def _commit(sha, tarih, ebeveyn=1):
    return {"sha": sha, "parents": [{"sha": "p"}] * ebeveyn, "commit": {"committer": {"date": tarih}}}


def test_onaydan_sonraki_commitler():
    """Etiketten sonraki tek ebeveynli commit'ler; birleştirme commit'i sayılmaz; zamanı okunamayan sayılır."""
    commitler = [_commit("a" * 40, "2026-11-04T05:00:00Z"), _commit("b" * 40, "2026-11-04T07:00:00Z"),
                 _commit("c" * 40, "2026-11-04T08:00:00Z", ebeveyn=2), _commit("d" * 40, None)]
    assert fren.onaydan_sonraki(commitler, "2026-11-04T06:00:00Z") == ["b" * 40, "d" * 40]


def test_eskiyen_onay():
    """Onaydan sonra korunan dosyaya dokunan commit onayı düşürür; serbest dosyaya dokunan düşürmez."""
    korunan = {"KARARLAR/muhurlu.json", "SHA256SUMS"}
    assert fren.eskiyen_onay([("b" * 40, [("M", "motor/dxf_out.py"), ("A", "docs/x.md")])], korunan) == []
    assert fren.eskiyen_onay([("b" * 40, [("M", "KARARLAR/muhurlu.json")])], korunan) == ["bbbbbbb KARARLAR/muhurlu.json"]
    assert fren.eskiyen_onay([("c" * 40, [("M", ".claude/hooks/sir_koruma.py")])], korunan) == ["ccccccc .claude/hooks/sir_koruma.py"]


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


def test_yerel_kip_muhur_kaydi(tmp_path):
    """Oturum kipi mühür kaydını dalın ayrıldığı yerle kıyaslar: yeni mühür temiz, var olan mühürün değişmesi onay (3)."""
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "KARARLAR").mkdir()
    kayit = tmp_path / "KARARLAR" / "muhurlu.json"
    kayit.write_text(_kayit(M1), encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "ilk")
    _git(tmp_path, "checkout", "-q", "-b", "is")

    def kos():
        r = subprocess.run([sys.executable, str(KOK / "araclar" / "fren.py"), "--taban", "main"], cwd=tmp_path, capture_output=True,
                           text=True)
        return r.returncode, r.stdout

    kayit.write_text(_kayit(M1, M2), encoding="utf-8")
    assert kos()[0] == 0
    kayit.write_text(_kayit(dict(M1, kural="gevşek"), M2), encoding="utf-8")
    kod, cikti = kos()
    assert kod == 3 and "M-01" in cikti


def test_ci_isi_taban_kodunu_kosar():
    """CI işi PR'ın kodunu çekmez: pull_request_target, yalnız okuma izni, iş adı dal korumasındakiyle aynı."""
    metin = (KOK / ".github" / "workflows" / "korunan.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" in metin and "\n  pull_request:" not in metin
    assert "ref:" not in metin, "PR'ın dalı çekilmez"
    assert "write" not in metin.split("permissions:", 1)[1].split("jobs:", 1)[0]
    assert "name: Korunan dosya onayı" in metin
    assert "python3 araclar/fren.py ci" in metin
