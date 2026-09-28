"""D-02: PDF içerik parmak izi sayfa ölçüsü aynı kalsa da yanlış revizyonu, yanlış proje kodunu, değişen ölçüyü ve silinen
plan çizgilerini yakalar. Motor gerçekten koşulur (her üretim ~15 sn); üretim zamanı referans koşularındaki gibi sabit.

Koşum: python -m pytest testler/referans/test_pdf_izi.py -q
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REF = Path(__file__).resolve().parent
KOK = REF.parents[1]

BETIK = r'''
import copy, json, sys, tempfile
from pathlib import Path
KOK = Path(sys.argv[1]); sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "testler" / "referans"))
from motor import dxf_out
from parmak_izi import ozet
import fitz
ie = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
tmp = Path(tempfile.mkdtemp())
def pdf(ie, ad):
    m = dxf_out.uret(copy.deepcopy(ie), tmp / ad)
    return tmp / ad / m["pdf"]
def boyut(p):
    with fitz.open(p) as d:
        return [(round(s.rect.width), round(s.rect.height)) for s in d]
def cizim(p):
    with fitz.open(p) as d:
        return sum(len(s.get_drawings()) for s in d)
a = pdf(ie, "a"); b = pdf(ie, "b")
ie_r = copy.deepcopy(ie); ie_r["revizyon"] = int(ie.get("revizyon") or 1) + 1
ie_p = copy.deepcopy(ie); ie_p["is_emri_no"] = ie["is_emri_no"] + "9"
ie_o = copy.deepcopy(ie)
pencere = next(x for x in ie_o["acikliklar"] if x.get("tur") == "pencere"); pencere["olcu"] = "60x40"
r, p, o = pdf(ie_r, "r"), pdf(ie_p, "p"), pdf(ie_o, "o")
d = fitz.open(a); s = d[0]; R = s.rect
s.add_redact_annot(fitz.Rect(R.x0 + R.width * 0.3, R.y0 + R.height * 0.3, R.x0 + R.width * 0.6, R.y0 + R.height * 0.6))
s.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED, text=fitz.PDF_REDACT_TEXT_NONE)
k = tmp / "kirpik.pdf"; d.save(k); d.close()
print(json.dumps({ad: {"ozet": ozet(x), "boyut": boyut(x), "cizim": cizim(x)} for ad, x in
                  {"a": a, "b": b, "rev": r, "proje": p, "olcu": o, "silik": k}.items()}))
'''


def test_pdf_izi_icerigi_yakalar():
    env = {k: v for k, v in os.environ.items() if not k.startswith("PORTMAN_")}
    env.update(TEST_SABIT_ZAMAN="1767225600", PYTHONPATH=str(REF / "sabit_zaman"))
    r = subprocess.run([sys.executable, "-c", BETIK, str(KOK)], capture_output=True, text=True, env=env, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    s = json.loads(r.stdout.strip().splitlines()[-1])
    a = s["a"]
    assert s["b"]["ozet"] == a["ozet"], "aynı İş Emri iki kez aynı özeti vermeli"
    for ad in ("rev", "proje", "olcu", "silik"):
        assert s[ad]["boyut"] == a["boyut"], f"{ad}: sayfa ölçüsü aynı kalmalı (sınanan durum bu)"
        assert s[ad]["ozet"] != a["ozet"], f"{ad}: içerik farkı yakalanmadı"
    assert s["silik"]["cizim"] < a["cizim"]
