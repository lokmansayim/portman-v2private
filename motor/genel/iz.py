"""İçerik izleri (İE-08 GM3): IFC ve JSON çıktılarının, başlık zamanı, rastgele kimlikler ve kayıt numaralarından bağımsız özeti.

IFC dosyası hiçbir zaman bayt bayt aynı değildir: FILE_NAME başlığı üretim zamanını ve yazan sürümü taşır, her IfcRoot'un
GlobalId'si rastgeledir; ifcopenshell kayıtları (#n) ve ilişki kayıtlarındaki eleman listelerini her koşuda başka sırada yazabilir.
`ifc_izi` içerik adreslidir: her kayıt, başvurduğu kayıtların (özyineli) içeriğiyle anılır, GlobalId maskelenir, ondalıklar 1e-4'e
yuvarlanır, ilişki listeleri sıralanır; sıralı kayıt çoklu kümesinin sha256'sı izdir. Aynı geometri ve aynı nitelikler aynı izi verir;
bir duvar, pencere, çatı düzlemi ya da pset değişince iz değişir (testler/genel/test_iz.py).

    python -m motor.genel.iz <dosya.ifc|dosya.json> [...]   # her dosya için iz yazar
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

_SAYI = re.compile(r"(?<![A-Za-z_#\w])-?\d+\.\d*(?:[Ee][-+]?\d+)?")
_KAYIT = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9]+)\((.*)\);?$")
_GUID = re.compile(r"^'[0-9A-Za-z_$]{22}'")
_REF = re.compile(r"#(\d+)")
_HASH_LISTESI = re.compile(r"\((<[0-9a-f]{10}>(?:,<[0-9a-f]{10}>)+)\)")
_BASLIK = ("FILE_NAME(", "FILE_DESCRIPTION(")
# Eleman listesi IFC şemasında küme olan kayıtlar: sıra anlam taşımaz, ifcopenshell her koşuda başka yazabilir → sıralanır.
# (IfcRel*: RelatedElements/RelatedObjects; IfcUnitAssignment.Units; IfcPropertySet.HasProperties; IfcElementQuantity.Quantities)
_SIRASIZ = ("IFCREL", "IFCUNITASSIGNMENT", "IFCPROPERTYSET", "IFCELEMENTQUANTITY")


def _sayi_yuvarla(m: re.Match) -> str:
    try:
        v = round(float(m.group(0)), 4)
    except ValueError:
        return m.group(0)
    if v == 0:
        v = 0.0                                     # -0.0 → 0.0
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def _kayitlar(metin: str) -> dict[int, tuple[str, str]]:
    kayit = {}
    for ham in metin.splitlines():
        s = ham.strip()
        m = _KAYIT.match(s)
        if m:
            kayit[int(m.group(1))] = (m.group(2), m.group(3))
    return kayit


def ifc_kanonik(metin: str) -> list[str]:
    """Kayıt numarasından bağımsız, sıralanmış kanonik kayıtlar (iz bunlardan hesaplanır; fark ayıklamada okunur)."""
    kayit = _kayitlar(metin)
    bellek: dict[int, str] = {}
    yol: set[int] = set()

    def coz(n: int) -> str:
        if n in bellek:
            return bellek[n]
        if n not in kayit:
            return f"<yok:{n}>"
        if n in yol:
            return "<dongu>"
        yol.add(n)
        tip, govde = kayit[n]
        govde = _SAYI.sub(_sayi_yuvarla, govde)
        if tip.startswith("IFC") and _GUID.match(govde):
            govde = "'<guid>'" + govde[24:]
        govde = _REF.sub(lambda m: "<" + hashlib.sha1(coz(int(m.group(1))).encode("utf-8")).hexdigest()[:10] + ">", govde)
        if tip.startswith(_SIRASIZ):
            govde = _HASH_LISTESI.sub(lambda m: "(" + ",".join(sorted(m.group(1).split(","))) + ")", govde)
        yol.discard(n)
        bellek[n] = f"{tip}({govde})"
        return bellek[n]

    return sorted(coz(n) for n in kayit)


def ifc_izi(yol: Path) -> str:
    kanonik = ifc_kanonik(Path(yol).read_text(encoding="utf-8", errors="replace"))
    return hashlib.sha256("\n".join(kanonik).encode("utf-8")).hexdigest()


def json_izi(yol: Path) -> str:
    """Anahtar sırası ve boşluktan bağımsız JSON izi."""
    veri = json.loads(Path(yol).read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def dosya_izi(yol: Path) -> str:
    """Uzantıya göre iz: .ifc kanonik, .json kanonik, gerisi ham sha256."""
    yol = Path(yol); u = yol.suffix.lower()
    if u == ".ifc":
        return ifc_izi(yol)
    if u == ".json":
        return json_izi(yol)
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__); return 2
    for a in argv:
        print(f"{dosya_izi(Path(a))}  {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
