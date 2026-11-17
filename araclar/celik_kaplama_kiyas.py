"""D-113 (BK-48) · havuzdaki çelik evlerin standart kaplamayla önce/sonra yükleme listesi kıyası (yalnız okur, LLM yok).

Lokman, kart 16 Kasım 2026 08:27:26 UTC "Standart: tek kat panel" (seçenek metni: "Havuzdaki her çelik ev tek kat panelle çizilir, bayi
kaplamayı formda seçer. Bugün sandviç panelli 10 çelik ev değişir."). Araç depodaki her çelik tanımı (`modeller/*.json`,
`modeller/havuz/*.json`, `modeller/banka/*/tanim.json`) tarar; `varyant.standart_kaplama_islemi` işlem veren her evi genel motorla iki kez
üretir (worker'ın çağrısı gibi: yöntem panel, güncel kural kitabı, perspektifsiz): asıl tanım (önce) ve standart işlemli tanım (sonra).
Yükleme listelerinin satır farkı yazılır. Tanım dosyaları değişmez (asıl proje, D-103).

Komut: python -m araclar.celik_kaplama_kiyas <çıktı klasörü> [--json yol] [--md yol]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from beyin import varyant  # noqa: E402


def celik_tanimlari() -> list[Path]:
    """Depodaki çelik tanım dosyaları (genel motorun okuduğu Yapı Tanımı; pafta sayımı ve altın kayıt dosyaları değil)."""
    yollar = sorted((KOK / "modeller").glob("*.json")) + sorted((KOK / "modeller" / "havuz").glob("*.json")) + \
        sorted((KOK / "modeller" / "banka").glob("*/tanim.json"))
    out = []
    for y in yollar:
        try:
            t = json.loads(y.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(t, dict) and isinstance(t.get("cati"), dict) and t.get("duvarlar") is not None:
            out.append(y)
    return out


def kod(t: dict, yol: Path) -> str:
    """Bayinin gördüğü kod ("KT-04"; banka tanımı "KT04" yazar)."""
    k = str(t.get("kod") or (yol.parent.name if yol.name == "tanim.json" else yol.stem))
    return re.sub(r"^KT(\d{2})$", r"KT-\1", k)


def _uret(t: dict, hedef: Path) -> dict:
    from motor.genel import uret as U
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "tanim.json").write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        U.uret(hedef / "tanim.json", hedef, is_emri_no="D113-KIYAS", revizyon=1, set_yolu=None, yontem="panel", perspektif=False,
               bayi=False, kaynak="D-113 kıyası")
    [yol] = list(hedef.glob("*_yukleme.json"))
    return json.loads(yol.read_text(encoding="utf-8"))


def _anahtar(s: dict) -> tuple:
    return (s.get("grup"), s.get("kalem"), s.get("boyut"))


def liste_farki(once: dict, sonra: dict) -> list[dict]:
    """Satır satır fark: çıkan, giren ve adedi ya da ölçüsü değişen satırlar (grup, kalem, boyut anahtarıyla)."""
    a = {_anahtar(s): s for s in once.get("satirlar") or []}
    b = {_anahtar(s): s for s in sonra.get("satirlar") or []}
    fark = []
    for k in list(a) + [k for k in b if k not in a]:
        x, y = a.get(k), b.get(k)
        if x and y and (x.get("adet"), x.get("olcu"), x.get("birim")) == (y.get("adet"), y.get("olcu"), y.get("birim")):
            continue
        fark.append({"grup": k[0], "kalem": k[1], "boyut": k[2],
                     "once": None if x is None else {"adet": x.get("adet"), "olcu": x.get("olcu"), "birim": x.get("birim")},
                     "sonra": None if y is None else {"adet": y.get("adet"), "olcu": y.get("olcu"), "birim": y.get("birim")}})
    return fark


def kiyas(cikti: Path) -> list[dict]:
    sonuc = []
    for yol in celik_tanimlari():
        t = json.loads(yol.read_text(encoding="utf-8"))
        ops = varyant.standart_kaplama_islemi(t)
        k = kod(t, yol)
        if not ops:
            sonuc.append({"kod": k, "tanim": str(yol.relative_to(KOK)), "degisir": False, "kaplama": varyant.kaplama_oku(t)})
            continue
        t2 = varyant.tanim_uygula(t, ops[0])
        once = _uret(t, cikti / k.replace("-", "") / "once")
        sonra = _uret(t2, cikti / k.replace("-", "") / "sonra")
        sonuc.append({"kod": k, "tanim": str(yol.relative_to(KOK)), "degisir": True, "ad": t.get("ad"),
                      "once_kaplama": once.get("cati_kaplamasi"), "sonra_kaplama": sonra.get("cati_kaplamasi"),
                      "once_satir": len(once.get("satirlar") or []), "sonra_satir": len(sonra.get("satirlar") or []),
                      "fark": liste_farki(once, sonra)})
    return sonuc


def _sayi(v) -> str:
    if v is None:
        return "—"
    x = v.get("adet") if v.get("adet") is not None else v.get("olcu")
    if isinstance(x, float):
        x = f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{x}{(' ' + v['birim']) if v.get('birim') and v.get('adet') is None else ''}"


def md(sonuc: list[dict]) -> str:
    deg = [r for r in sonuc if r["degisir"]]
    satirlar = ["# D-113 · çelik havuz evleri standart kaplamayla: yükleme listesi önce/sonra", "",
                f"{len(sonuc)} çelik tanım tarandı; {len(deg)} ev değişir, {len(sonuc) - len(deg)} ev zaten standart.", "",
                "| Ev | Kaplama önce → sonra | Satır önce → sonra | Değişen satır |", "|---|---|---|---|"]
    for r in deg:
        satirlar.append(f"| {r['kod']} | {r['once_kaplama']} → {r['sonra_kaplama']} | {r['once_satir']} → {r['sonra_satir']} | {len(r['fark'])} |")
    satirlar += ["", "Değişmeyenler: " + ", ".join(f"{r['kod']} ({r['kaplama']})" for r in sonuc if not r["degisir"]), ""]
    for r in deg:
        satirlar += [f"## {r['kod']}", "", "| Grup | Kalem | Boyut | Önce | Sonra |", "|---|---|---|---|---|"]
        for f in r["fark"]:
            satirlar.append(f"| {f['grup']} | {f['kalem']} | {f['boyut'] or ''} | {_sayi(f['once'])} | {_sayi(f['sonra'])} |")
        satirlar.append("")
    return "\n".join(satirlar)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    sonuc = kiyas(a.cikti)
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    metin = md(sonuc)
    if a.md:
        a.md.write_text(metin + "\n", encoding="utf-8")
    print(metin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
