"""BK-20 (D-42) · Mühürlü konuların kilit testi ve mühür freninin kendi testleri.

Lokman, 1 Kasım 2026 20:16: "bir daha değişmemek üzere bu konuyu mühürle taki ben yeni bir değişiklik verene kadar sen yorumlama";
20:25: "hook diye bir şey varmış yapay zeka'nın sağa sola sapmaması için bunu uygula emeklerimiz boşa gitmesin".

Her mühürlü konu için bir kilit testi (`test_muhur[M-NN]`): kuralı sabitleyen her yer (kural kitabının anahtarı, hedef örnek, testin
kendisi) `KARARLAR/muhurlu.json`'daki izle aynı olmalı. Fark varsa CI kırmızıdır ve iş `main`'e girmez. Mühür yalnız Lokman'ın açık sözüyle
açılır (`muhur_koruma.py ac`) ve yeni kararla kapanır (`kapat`); ikisi de kaydın `gecmis`'ine yazılır. Bu testi geçirmek için kayıttaki iz
elle değiştirilmez.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
HOOK = KOK / ".claude" / "hooks" / "muhur_koruma.py"
_spec = importlib.util.spec_from_file_location("muhur_koruma", HOOK)
mk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mk)
KAYIT = json.loads((KOK / mk.KAYIT).read_text(encoding="utf-8"))
MUHURLER = KAYIT["muhurler"]


def _karar_dosyasi(karar: str) -> Path:
    if karar.startswith("İE-"):
        return KOK / "docs" / "is_emirleri" / f"IE-{karar[3:]}.md"
    return KOK / "KARARLAR" / f"{karar}.md"


def test_kayit_bicimi():
    assert KAYIT["sema"] == "portman.muhurlu_konular/1"
    kodlar = [m["kod"] for m in MUHURLER]
    assert kodlar == [f"M-{i:02d}" for i in range(1, len(kodlar) + 1)], "kodlar sıralı ve boşluksuz (M-01, M-02 …); mühür silinmez"
    for m in MUHURLER:
        assert m["konu"] and m["kural"] and m["kilitler"], m["kod"]
        assert m["durum"] in (mk.MUHURLU, mk.ACIK)
        assert m["lokman"] and all(s.get("tarih") and s.get("soz") for s in m["lokman"]), f"{m['kod']}: Lokman'ın sözü ve saati"
        for k in m["kararlar"]:
            assert _karar_dosyasi(k).is_file(), f"{m['kod']}: {k} kaydı yok"
        assert any(ayir[0].startswith("testler/") and ayir[0].endswith(".py") for ayir in (mk.ayir(k["yer"], KOK) for k in m["kilitler"])), \
            f"{m['kod']}: davranışı sabitleyen en az bir test kilitli olmalı"
        assert len({k["yer"] for k in m["kilitler"]}) == len(m["kilitler"]), f"{m['kod']}: aynı yer iki kez"
    for c in KAYIT["cekirdek"]:
        assert (KOK / c).is_file(), c


@pytest.mark.parametrize("m", MUHURLER, ids=[m["kod"] for m in MUHURLER])
def test_muhur(m):
    """Mühürlü konunun kilitleri kayıttaki izle aynı; konu açık bırakılmamış."""
    assert m["durum"] == mk.MUHURLU, (f"{m['kod']} açık kaldı (açılış: {m.get('acilis')}). İş bitince yeni kararla kapatın: "
                                      f"`{mk.KOMUT} kapat {m['kod']} --karar D-NN`")
    bozuk = []
    for k in m["kilitler"]:
        icerik = mk.deger(k["yer"], KOK)
        if icerik is mk.YOK:
            bozuk.append(f"{k['yer']}: bulunamadı")
        elif mk.iz(icerik) != k["iz"]:
            bozuk.append(f"{k['yer']}: kayıt {k['iz']}, şimdi {mk.iz(icerik)}")
    assert not bozuk, (f"MÜHÜRLÜ KONU {mk.ozet(m)} değişti; Lokman yeni bir değişiklik vermedikçe değiştirilmez "
                       f"(AGENTS.md › Mühürlü konular):\n  " + "\n  ".join(bozuk))


def test_main_ile_kiyas():
    """`main`'deki mühürler kalkmaz; kilidi değişen mühürün geçmişinde Lokman'ın sözü ve yeni kararı vardır."""
    r = subprocess.run(["git", "show", f"origin/main:{mk.KAYIT}"], cwd=KOK, capture_output=True, text=True)
    if r.returncode:
        pytest.skip("origin/main'de mühür kaydı yok (ilk PR) ya da origin/main alınmamış")
    ana = {m["kod"]: m for m in json.loads(r.stdout)["muhurler"]}
    simdi = {m["kod"]: m for m in MUHURLER}
    for kod, m in ana.items():
        assert kod in simdi, f"{kod} kayıttan kaldırılmış (mühür silinmez)"
        n = simdi[kod]
        if {(k["yer"], k["iz"]) for k in m["kilitler"]} - {(k["yer"], k["iz"]) for k in n["kilitler"]}:
            assert len(n.get("gecmis", [])) > len(m.get("gecmis", [])), f"{kod}: kilit değişmiş ama mühür açılıp kapanmamış (`ac`, `kapat`)"
            son = n["gecmis"][-1]
            assert son.get("soz") and _karar_dosyasi(son.get("karar", "")).is_file(), f"{kod}: açılışta Lokman'ın sözü ve yeni karar"


def test_agents_tablosu():
    """AGENTS.md › Mühürlü konular tablosu kayıtla aynı konuları sayar."""
    metin = (KOK / "AGENTS.md").read_text(encoding="utf-8")
    bolum = metin.split("## Mühürlü konular", 1)[1].split("\n## ", 1)[0]
    satirlar = re.findall(r"^\| (M-\d\d) \| ([^|]+) \|", bolum, flags=re.M)
    assert [(k, a.strip()) for k, a in satirlar] == [(m["kod"], m["konu"]) for m in MUHURLER]


def test_hooklar_bagli():
    h = json.loads((KOK / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]

    def kipler(olay, matcher):
        return {c["command"].rsplit(" ", 1)[-1] for g in h.get(olay, []) if g.get("matcher") == matcher
                for c in g["hooks"] if "muhur_koruma.py" in c["command"]}
    assert kipler("PreToolUse", "Edit|Write|MultiEdit") == {"duzenleme"}
    assert kipler("PreToolUse", "Bash") == {"komut"}
    assert kipler("PostToolUse", "Bash") == {"komut_sonu"}
    assert kipler("SessionStart", None) == {"oturum"}


# ---------------------------------------------------------------- frenin kendisi (geçici depoda)

@pytest.fixture()
def depo(tmp_path):
    (tmp_path / "KARARLAR").mkdir()
    (tmp_path / "KARARLAR" / "D-99.md").write_text("# D-99\n", encoding="utf-8")
    (tmp_path / "testler").mkdir()
    (tmp_path / "testler" / "test_x.py").write_text("def test_kilitli():\n    assert 6 == 6\n\n\ndef test_serbest():\n    assert 1\n", encoding="utf-8")
    (tmp_path / "kural.json").write_text(json.dumps({"a": {"b": 516}, "c": 1}), encoding="utf-8")
    kayit = {"sema": "portman.muhurlu_konular/1", "cekirdek": [".claude/hooks/muhur_koruma.py", mk.KAYIT],
             "muhurler": [{"kod": "M-01", "konu": "Deneme", "kural": "516", "kararlar": [], "lokman": [{"tarih": "t", "soz": "s"}],
                           "durum": mk.MUHURLU, "gecmis": [],
                           "kilitler": [{"yer": "testler/test_x.py::test_kilitli"}, {"yer": "kural.json#a.b"}]}]}
    mk.kayit_yaz(tmp_path, kayit)
    assert _cli(tmp_path, "kilitle").returncode == 0
    return tmp_path


def _hook(kok: Path, kip: str, veri: dict) -> dict:
    r = subprocess.run([sys.executable, str(HOOK), kip], input=json.dumps(veri), capture_output=True, text=True,
                       env={**os.environ, "CLAUDE_PROJECT_DIR": str(kok)}, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else {}


def _cli(kok: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HOOK), "--kok", str(kok), *a], capture_output=True, text=True, timeout=60)


def _karari(c: dict) -> str | None:
    return (c.get("hookSpecificOutput") or {}).get("permissionDecision")


def test_fren_duzenleme(depo):
    yol = str(depo / "testler" / "test_x.py")
    kilitli = {"tool_name": "Edit", "tool_input": {"file_path": yol, "old_string": "6 == 6", "new_string": "6 == 5"}}
    c = _hook(depo, "duzenleme", kilitli)
    assert _karari(c) == "deny" and "Patron onayı gerekir" in c["hookSpecificOutput"]["permissionDecisionReason"]
    assert _hook(depo, "duzenleme", {"tool_name": "Edit", "tool_input": {"file_path": yol, "old_string": "assert 1", "new_string": "assert 2"}}) == {}
    json_yaz = {"tool_name": "Write", "tool_input": {"file_path": "kural.json", "content": json.dumps({"a": {"b": 600}, "c": 1})}}
    assert _karari(_hook(depo, "duzenleme", json_yaz)) == "deny"
    json_serbest = {"tool_name": "Write", "tool_input": {"file_path": "kural.json", "content": json.dumps({"a": {"b": 516}, "c": 2})}}
    assert _hook(depo, "duzenleme", json_serbest) == {}
    cekirdek = {"tool_name": "Edit", "tool_input": {"file_path": ".claude/hooks/muhur_koruma.py", "old_string": "x", "new_string": "y"}}
    assert _karari(_hook(depo, "duzenleme", cekirdek)) == "ask"


def test_fren_kayit_gevsemez(depo):
    kayit = json.loads((depo / mk.KAYIT).read_text(encoding="utf-8"))
    yaz = lambda k: {"tool_name": "Write", "tool_input": {"file_path": mk.KAYIT, "content": json.dumps(k, ensure_ascii=False)}}
    sil = {**kayit, "muhurler": []}
    acik = json.loads(json.dumps(kayit)); acik["muhurler"][0]["durum"] = mk.ACIK
    iz = json.loads(json.dumps(kayit)); iz["muhurler"][0]["kilitler"][1]["iz"] = "0" * 16
    for k in (sil, acik, iz):
        assert _karari(_hook(depo, "duzenleme", yaz(k))) == "deny"
    yeni = json.loads(json.dumps(kayit))
    yeni["muhurler"].append({**kayit["muhurler"][0], "kod": "M-02"})
    yeni["muhurler"][0]["kilitler"].append({"yer": "kural.json#c"})
    assert _hook(depo, "duzenleme", yaz(yeni)) == {}


def test_fren_komut(depo):
    k = lambda s: _karari(_hook(depo, "komut", {"tool_input": {"command": s}}))
    assert k("sed -i s/516/600/ kural.json") == "deny"
    assert k("echo '{}' > kural.json") == "deny"
    assert k("python3 - <<'E'\nopen('testler/test_x.py','w').write('')\nE") == "deny"
    assert k("cat kural.json && grep -n b kural.json 2>&1 | head") is None
    assert k("pytest -q testler/test_x.py") is None
    assert k(f"python3 {mk.KOMUT.split()[-1]} ac M-01 --soz 'yeni söz'") == "ask"


def test_fren_komut_sonu_ve_oturum(depo):
    assert _hook(depo, "komut_sonu", {}) == {}
    o = _hook(depo, "oturum", {})["hookSpecificOutput"]
    assert o["hookEventName"] == "SessionStart" and "M-01 Deneme" in o["additionalContext"]
    (depo / "kural.json").write_text(json.dumps({"a": {"b": 600}, "c": 1}), encoding="utf-8")   # betik mühürlü yere yazdı
    c = _hook(depo, "komut_sonu", {})
    assert c["decision"] == "block" and "kural.json#a.b" in c["reason"]
    assert _cli(depo, "denetle").returncode == 1


def test_ac_kapat(depo):
    (depo / "kural.json").write_text(json.dumps({"a": {"b": 600}, "c": 1}), encoding="utf-8")
    assert _cli(depo, "kapat", "M-01", "--karar", "D-99").returncode != 0, "açılmamış mühür kapatılamaz"
    assert _cli(depo, "ac", "M-01", "--soz", "516 değil 600", "--mesaj", "cmsg_x").returncode == 0
    assert _hook(depo, "komut_sonu", {}) == {}, "açık mühür denetlenmez"
    assert _cli(depo, "denetle").returncode == 1, "açık mühür CI'da kırmızı"
    assert _cli(depo, "kapat", "M-01", "--karar", "D-98").returncode != 0, "karar dosyası olmadan kapanmaz"
    assert _cli(depo, "kapat", "M-01", "--karar", "D-99").returncode == 0
    m = json.loads((depo / mk.KAYIT).read_text(encoding="utf-8"))["muhurler"][0]
    assert m["durum"] == mk.MUHURLU and m["gecmis"][-1]["soz"] == "516 değil 600" and m["gecmis"][-1]["karar"] == "D-99"
    assert "D-99" in m["kararlar"] and _cli(depo, "denetle").returncode == 0


def test_yer_bicimleri(tmp_path):
    (tmp_path / "a.py").write_text("import x\n\n@d(1)\ndef f():\n    return 1\n\n\nclass K:\n    def u(self):\n        pass\n\n\n"
                                   "B = {\n    'p': (1, 2),\n    'q': 3,\n}\n", encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"l": [{"k": "x", "v": 1}, {"k": "y", "v": 2}, {"k": "x", "v": 3}]}), encoding="utf-8")
    (tmp_path / "c.txt").write_text("1 a.png\n2 a.json\n3 b.pdf\n", encoding="utf-8")
    d = lambda y: mk.deger(y, tmp_path)
    assert d("a.py::f") == "@d(1)\ndef f():\n    return 1"
    assert d("a.py::K.u") == "    def u(self):\n        pass" and d("a.py::B[p]") == "(1, 2)" and d("a.py::yok") is mk.YOK
    assert json.loads(d("b.json#l[k=y].v")) == 2 and json.loads(d("b.json#l[k=x].v")) == [1, 3] and d("b.json#l[k=z]") is mk.YOK
    assert d("c.txt@\\.(png|pdf)$") == "1 a.png\n3 b.pdf"
    assert mk.ayir("{son_referans}/x.txt", KOK)[0].startswith("testler/referans/20")
