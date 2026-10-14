"""İE-14 r3 · P1: çok durumlu doğrulama raporu (`dogrulama.json`).

"Dosya üretildi" ile "teknik olarak doğrulandı" ayrıdır. Her kalemin durumu ayrı yazılır:
- GECTI: denetim koştu, bulgu yok.
- KALDI: denetim koştu, bulgu var (bulgular yanında).
- DOGRULANMADI: denetlenebilir ama bu üretimde denetlenmedi ya da kıyas yok (ör. yükleme listesi gerçek listeyle kıyaslanmadı).
- YAPILMADI: sistemde bu denetim yok (ör. yapısal hesap; mühendis kabulü 8b'de).

Kalemler: sözleşme, geometri, ölçü ve program, çatı (denetçiden: `plan_denetim.denetle` → `kalemler`, `kosan`), çizim çıktıları
(genel motorun `manifest.json`), yazı çakışması (verilirse), yükleme listesi (kör test kıyası verilirse ölçüm; hedef yok), yapısal,
mühendis kabulü. Rapor `uret`'in dışında yazılır (altın ve referans izleri değişmez); bayiye gitmez.
"""
from __future__ import annotations

import json
from pathlib import Path

SEMA = "portman.dogrulama/0.1"
GECTI, KALDI, DOGRULANMADI, YAPILMADI = "GECTI", "KALDI", "DOGRULANMADI", "YAPILMADI"
AD = {"sozlesme": "Sözleşme", "geometri": "Geometri", "olcu_program": "Ölçü ve program", "cati": "Çatı", "cizim": "Çizim çıktıları",
      "yazi_cakismasi": "Yazı çakışması", "yukleme_listesi": "Yükleme listesi", "yapisal": "Yapısal", "muhendis_kabulu": "Mühendis kabulü"}
DURUM_ADI = {GECTI: "geçti", KALDI: "kaldı", DOGRULANMADI: "doğrulanmadı", YAPILMADI: "yapılmadı"}


def _kalem(durum: str, gerekce: str, bulgular: list | None = None, **ek) -> dict:
    return {"durum": durum, "gerekce": gerekce, **({"bulgular": bulgular} if bulgular else {}), **ek}


def _cizim(cikti: Path | None) -> dict:
    if cikti is None:
        return _kalem(DOGRULANMADI, "çizim bu denetimde üretilmedi")
    man = Path(cikti) / "manifest.json"
    if not man.exists():
        return _kalem(KALDI, "manifest yok (genel motor çıktı üretmedi)")
    m = json.loads(man.read_text(encoding="utf-8"))
    eksik = [ad for ad in ("pdf", "ifc", "plan_bayi", "yukleme_json") if not m.get(ad) or not (Path(cikti) / m[ad]).exists()]
    if not m.get("passed") or m.get("hatali_pdf"):
        return _kalem(KALDI, "genel motorun kendi doğrulaması geçmedi (K23; teslim PDF'i yok)", list(m.get("errors") or m.get("hatalar") or [])[:6])
    if not m.get("duzenlenebilir_dxf"):
        eksik.append("düzenlenebilir DXF (yeniden açılış denetimi geçmedi ya da üretilmedi)")
    if eksik:
        return _kalem(KALDI, "beklenen çıktı eksik", eksik[:6])
    return _kalem(GECTI, "genel motor doğrulaması geçti: pafta PDF, IFC, DXF yeniden açılış", uyarilar=list(m.get("warnings") or [])[:6])


def rapor(denetim: dict, tanim: dict | None = None, cikti: Path | None = None, yazi_bulgulari: list | None = None,
          liste_kiyasi: dict | None = None, muhendis_kabulu: bool = False) -> dict:
    """`denetim`: `plan_denetim.denetle`'nin dönüşü. Dönüş: {sema, kalemler: {ad: {durum, gerekce, bulgular?}}, ozet}."""
    kal = denetim.get("kalemler") or {}
    kosan = set(denetim.get("kosan") or [])
    k: dict[str, dict] = {}
    for ad, gerekce in (("sozlesme", "plan şeması"), ("geometri", "döşeme, derleme, yapi.kur, açıklık, duvar örtüşmesi, 15 cm, kapı yayları"),
                        ("olcu_program", "alan ±%10, oda programı, oda en küçükleri, erişim, zorunlu pencere"),
                        ("cati", "çatı kuralları ve cati_kur")):
        b = kal.get(ad) or []
        if b:
            k[ad] = _kalem(KALDI, gerekce, b)
        elif ad not in kosan or (ad in ("olcu_program", "cati") and f"{ad}_tam" not in kosan):
            k[ad] = _kalem(DOGRULANMADI, f"{gerekce}: önceki kalem kaldığı için koşmadı ya da yarım koştu")
        else:
            k[ad] = _kalem(GECTI, gerekce)
    k["cizim"] = _cizim(cikti)
    if yazi_bulgulari is None:
        k["yazi_cakismasi"] = _kalem(DOGRULANMADI, "bu üretimde koşmadı (testler/genel/test_yazi_cakismasi.py düzeneği)")
    else:
        k["yazi_cakismasi"] = _kalem(KALDI if yazi_bulgulari else GECTI, "bayiye giden çıktılarda mürekkep kutusu", yazi_bulgulari)
    if liste_kiyasi:
        k["yukleme_listesi"] = _kalem(DOGRULANMADI, "gerçek listeyle kıyas ölçüldü; kabul eşiği henüz yok (önce ölçüm, Lokman 14.10)",
                                      olcum=liste_kiyasi)
    else:
        k["yukleme_listesi"] = _kalem(DOGRULANMADI, "kural kitabından üretildi; bu plan için gerçek liste yok")
    if tanim and tanim.get("celik_modeli"):
        k["yapisal"] = _kalem(DOGRULANMADI, "çelik modeli var; yapısal hesap mühendiste")
    else:
        k["yapisal"] = _kalem(YAPILMADI, "yapısal hesap yok (çelik modeli yok)")
    k["muhendis_kabulu"] = _kalem(GECTI if muhendis_kabulu else YAPILMADI,
                                  "8b mühendis kontrolü" + ("" if muhendis_kabulu else ": bekliyor (TASLAK, D-18)"))
    return {"sema": SEMA, "kalemler": k, "ozet": ozet(k)}


def ozet(kalemler: dict) -> str:
    """Tek satır: 'Geometri: geçti · … · Yapısal: yapılmadı'."""
    return " · ".join(f"{AD[a]}: {DURUM_ADI[v['durum']]}" for a, v in kalemler.items())


def yaz(r: dict, hedef: Path) -> Path:
    hedef = Path(hedef)
    hedef.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return hedef
