"""İE-04 · worker.bagimliliklar_hazir: isteğe bağlı paketler (matplotlib, pillow, ifcopenshell) üretimi ve öz-testi durdurmaz;
kurulum başarılıysa aynı süreçte yeniden denetlenir. Gerçek pip çağrılmaz (subprocess.run sahtesi)."""
from __future__ import annotations

import json
import types

import worker as W


class _Pip:
    def __init__(self, kurar: set[str], rc: int = 0):
        self.kurar, self.rc, self.cagri = kurar, rc, []

    def __call__(self, cmd, **k):
        self.cagri.append(cmd)
        for p in self.kurar:
            W.__dict__["_sahte_kurulu"].add(p)
        return types.SimpleNamespace(returncode=self.rc, stdout="ok", stderr="")


def _sahte_ortam(monkeypatch, kurulu: set[str]):
    W.__dict__["_sahte_kurulu"] = set(kurulu)

    def import_module(ad):
        if ad in W.__dict__["_sahte_kurulu"]:
            return types.SimpleNamespace()
        raise ImportError(ad)
    monkeypatch.setattr(W.importlib, "import_module", import_module)
    monkeypatch.setattr(W.importlib, "invalidate_caches", lambda: None)


def test_hepsi_varsa_pip_cagrilmaz(monkeypatch, kanal_dizini):
    _sahte_ortam(monkeypatch, set(W.GEREKLI) | set(W.ISTEGE_BAGLI))
    pip = _Pip(set()); monkeypatch.setattr(W.subprocess, "run", pip)
    assert W.bagimliliklar_hazir() is True and pip.cagri == [] and not (kanal_dizini / "install-report.json").exists()


def test_istege_bagli_kurulunca_ayni_tikte_hazir(monkeypatch, kanal_dizini):
    """Canlı v1.2 → v1.3 geçişi: zorunlular var, üç isteğe bağlı paket yok; pip kurar; öz-test bu tikte koşabilmeli."""
    _sahte_ortam(monkeypatch, set(W.GEREKLI))
    pip = _Pip({"matplotlib", "PIL", "ifcopenshell"}); monkeypatch.setattr(W.subprocess, "run", pip)
    assert W.bagimliliklar_hazir() is True
    assert len(pip.cagri) == 1 and pip.cagri[0][-3:] == ["matplotlib==3.11.2", "pillow", "ifcopenshell==0.8.5"]
    r = json.loads((kanal_dizini / "install-report.json").read_text())
    assert r["attempts"] == 1 and r["kalan_zorunlu"] == [] and r["kalan_istege_bagli"] == [] and r["returncode"] == 0


def test_istege_bagli_kurulamazsa_uretim_surer_uc_denemeden_sonra_susar(monkeypatch, kanal_dizini):
    _sahte_ortam(monkeypatch, set(W.GEREKLI))
    pip = _Pip(set(), rc=1); monkeypatch.setattr(W.subprocess, "run", pip)
    for i in range(1, 4):
        assert W.bagimliliklar_hazir() is True                  # ekler üretilmez ama akış durmaz
        assert json.loads((kanal_dizini / "install-report.json").read_text())["attempts"] == i
    assert W.bagimliliklar_hazir() is True and len(pip.cagri) == 3     # 4. çağrı: pip yok, yine True
    r = json.loads((kanal_dizini / "install-report.json").read_text())
    assert r["attempts"] == 3 and r["bildirildi"] is True and r["kalan_istege_bagli"] == ["matplotlib", "PIL", "ifcopenshell"]


def test_zorunlu_eksikse_eskisi_gibi_durur(monkeypatch, kanal_dizini):
    _sahte_ortam(monkeypatch, (set(W.GEREKLI) | set(W.ISTEGE_BAGLI)) - {"ezdxf"})
    pip = _Pip(set(), rc=1); monkeypatch.setattr(W.subprocess, "run", pip)
    for _ in range(4):
        assert W.bagimliliklar_hazir() is False
    assert len(pip.cagri) == 3 and pip.cagri[0][-1:] == ["ezdxf"]


def test_zorunlu_kurulunca_ayni_tikte_hazir(monkeypatch, kanal_dizini):
    _sahte_ortam(monkeypatch, (set(W.GEREKLI) | set(W.ISTEGE_BAGLI)) - {"fitz"})
    pip = _Pip({"fitz"}); monkeypatch.setattr(W.subprocess, "run", pip)
    assert W.bagimliliklar_hazir() is True and pip.cagri[0][-1:] == ["pymupdf"]
