"""BK-35 · Havuz hakeminin silme hâli kaleminde veranda duvarı aksa (kesilen ek akstaki duvar ızgara aksına oturur) ve tam + yarım pano
(dış yüzdeki silme kısa parçasız, dış yüze ulaşan duvar tam ve yarım panoya döner): 60 m² 2+1'in 647,5 × 951,25 cm hâli, yalnız
Lokman'ın o evdeki sözleri ve kartlarıyla. LLM'siz, Postgres'siz.

Lokman, 15 Kasım 2026 UTC (standart pano sohbeti, 60 m² 2+1'in eskizi üstüne):
- 06:07:17: "yani sonuç değişmiyor yine 2 tane özel pano çıkıyor özel pano çıkmaması için en doğrusu 125,5 ve 62,75 çıkması öncesinde
  dikkat edersen mühendis aksı korumuş şöyle yapabilirsin dışdaki 37 cm mi ve içteki 32'şer santimleri kaldır veranda duvarını aksa oturt
  sonra mutfak çıkıntısını tam ve yarım pano olarak güncelle ara ölçü çıkmamış olur"
- kart 07:15:45 "60 m2 evin veranda duvarı aksta eskizi doğru mu?" → "Doğru, yanına eklensin"
- 07:17:23: "buna ek olarak bir doğrulama daha yapmanı istiyorum dış pano 78 cm olan panoyuda tam pano yap selondaki pencereyi ortala ortaya
  125,5 tam pano pencere koy yanlara kalanı eşit dağıt"
- kart 07:24:23 "60 m2 evin 647,5 × 951,25 cm eskizi doğru mu?" → "Doğru, yanına eklensin" ("Bugünkü 60 m² kalır; 647,5 × 951,25 cm hâli
  (61,6 m²) yeni numarayla girer. 57 m² ara hâli girmez.")
CIO, 15 Kasım 2026 07:16: kalem yalnız bu evin sözüyle, BK-31/BK-34 gibi. Silme, büyüme ve kesim hattı kalemleri aynen.
Girdi: `testler/havuz/is_emirleri/PA18_GENIS.json` (standart pano sohbetinin İş Emri'si; PF Havuz_Standart_Pano/2026-11-15_kalan_evler/
60m2_genis_is_emri.json, eskiz 60m2_genis_eskiz.png).
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402

SOZ_0607 = ("Lokman 15 Kasım 2026 06:07:17 UTC: \"yani sonuç değişmiyor yine 2 tane özel pano çıkıyor özel pano çıkmaması için en doğrusu "
            "125,5 ve 62,75 çıkması öncesinde dikkat edersen mühendis aksı korumuş şöyle yapabilirsin dışdaki 37 cm mi ve içteki 32'şer "
            "santimleri kaldır veranda duvarını aksa oturt sonra mutfak çıkıntısını tam ve yarım pano olarak güncelle ara ölçü çıkmamış olur\"")
KART_0715 = "kart 07:15:45 \"60 m2 evin veranda duvarı aksta eskizi doğru mu?\" → \"Doğru, yanına eklensin\""
SOZ_0717 = ("Lokman 15 Kasım 2026 07:17:23 UTC: \"buna ek olarak bir doğrulama daha yapmanı istiyorum dış pano 78 cm olan panoyuda tam pano "
            "yap selondaki pencereyi ortala ortaya 125,5 tam pano pencere koy yanlara kalanı eşit dağıt\"")
KART_0724 = ("kart 07:24:23 \"60 m2 evin 647,5 × 951,25 cm eskizi doğru mu?\" → \"Doğru, yanına eklensin\" (\"Bugünkü 60 m² kalır; "
             "647,5 × 951,25 cm hâli (61,6 m²) yeni numarayla girer. 57 m² ara hâli girmez.\")")
GENIS = "testler/havuz/is_emirleri/PA18_GENIS.json"
KAYNAK = "is_emri/adaylar/PA18.json"
KART = "AP-19"
KESIM = "on:37:795"
SOZLER = {"kesim_hatti": KESIM, "kesim_sozu": f"{SOZ_0607}; {KART_0715}", "aks_sozu": SOZ_0607, "tam_yarim_sozu": SOZ_0607,
          "buyume_sozu": f"{SOZ_0717}; {KART_0724}", "veranda_sozu": KART_0724, "aciklik_sozu": f"{SOZ_0717}; {KART_0724}"}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _denetle(ie: dict | None = None, **degis) -> tuple[list[str], dict]:
    return HH.denetle_silme(ie or _ie(GENIS), HH.kartlar()[KART], _ie(KAYNAK), **{**SOZLER, **degis})


def test_60m2_genis_gecer():
    """Eskizin hâli bütün sözlerle geçer: veranda duvarı ek aks 795'ten 758 aksına oturur (37 ve iki 32 cm'lik parça düşer, ek aks kalkar);
    ön yüz ayrıca 11,75 cm içeri, mutfak çıkıntısı ve sol duvar tam + yarım panoya döner; sağ 47,5 cm dışarı (78'ler 125,5); salonun
    penceresi veranda duvarında salonun ortasına kayar (125,5'lik pencereli pano, yanlarda 62,75)."""
    bulgular, o = _denetle()
    assert bulgular == []
    assert (o["kaynak_dis_olcu_cm"], o["dis_olcu_cm"]) == ([600.0, 1000.0], [647.5, 951.25])
    assert (o["silinen_cm"], o["buyuyen_cm"]) == ([0.0, 48.75], [47.5, 0.0])
    assert o["kesim_hatti"] == {"yazi": KESIM, "eksen": "y", "hat_cm": 795.0, "cm": 37.0}
    assert o["aksa_oturan"] == {"eksen": "y", "ek_aks_cm": 795.0, "aks_cm": 758.0}
    assert {(p["duvar"], p["boy"]) for p in o["silinen"]} == {("dis y 595", 37.0), ("ic y 261", 32.0), ("ic y 386.5", 32.0)}
    assert {(p["duvar"], p["once"], p["sonra"]) for p in o["tamamlanan"]} == {("dis x 5", 78.0, 125.5), ("ic x 381.5", 78.0, 125.5)}
    assert {p["duvar"]: p["sonra"] for p in o["tam_yarim"]} == {"dis y 261": [120.5, 62.75], "dis y 5": [125.5] * 7 + [62.75]}
    assert o["veranda_kisalan"] == ["VERANDA"]
    assert o["kayan_aciklik"] == [{"aciklik": "pencere 120x180", "duvar": "dis x 758", "once_cm": [427.0, 552.5],
                                   "sonra_cm": [449.25, 574.75]}]
    a0, a1 = o["kayan_aciklik"][0]["sonra_cm"]
    assert (a0 + a1) / 2 == (386.5 + 637.5) / 2                                    # salonun ortası (SALON x 386,5–637,5)
    assert {d["duvar"]: d["sonra"] for d in o["yeniden_dizilen"]}["dis x 795"] == [125.5, 62.75, 125.5, 62.75]


@pytest.mark.parametrize("eksik,beklenen", [
    ("kesim_sozu", "--kesim-sozu"),
    ("aks_sozu", "--aks-sozu"),
    ("tam_yarim_sozu", "--tam-yarim-sozu"),
    ("buyume_sozu", "--buyume-sozu"),
    ("veranda_sozu", "--veranda-sozu"),
    ("aciklik_sozu", "--aciklik-sozu"),
])
def test_her_degisiklik_yalniz_sozuyle(eksik, beklenen):
    """Her değişiklik kendi sözüyle: biri eksikse hâl kalır ve bulgu eksik seçeneği adıyla söyler."""
    bulgular, _ = _denetle(**{eksik: None})
    assert bulgular and any(beklenen in b for b in bulgular), bulgular


def test_kesim_parcasi_dis_yuzu_karsilamaz():
    """Kesimli eksende dış yüzdeki 11,75 cm'lik silme kesim hattının kısa parçalarıyla (37, 32, 32) gerekçelenmez: tam + yarım pano sözü
    yoksa hâl kalır (BK-34'te kesimli eksende dış yüz büyüyordu; silme ayrı denetlenir)."""
    bulgular, _ = _denetle(tam_yarim_sozu=None)
    assert bulgular == [b for b in bulgular if b.startswith("silinen: 11.75 cm hiçbir y duvarında")] and len(bulgular) == 1, bulgular


@pytest.mark.parametrize("yazi,beklenen", [
    ("on:30:795", "765 cm ızgara aksı değil"),            # duvar ızgara aksına oturmaz
    ("on:63:795", "kısa parça kesilir"),                  # yarım panodan uzun: en yakın aks değil
    ("on:37:758", "ek aksı değil"),                       # 758 ızgara aksı; kesilen hat ek aks olmalı
])
def test_aksa_oturmayan_kesim(yazi, beklenen):
    bulgular, _ = _denetle(kesim_hatti=yazi)
    assert bulgular and any(beklenen in b for b in bulgular), (yazi, bulgular)


def test_kapinin_duvar_ucu():
    """HOL–SALON kapısına yazılan duvar ucu (arka) kapıyı kaynaktaki yerinde tutar ve kabul edilir; yazılmazsa Motor kapıyı yeniden dizilen
    duvarın öteki ucuna koyar ve açıklık yeri kalemi bulur."""
    ie = _ie(GENIS)
    assert [a["arasi"] for a in ie["acikliklar"] if a.get("duvar_ucu") == "arka"] == [["HOL", "SALON"]]
    for a in ie["acikliklar"]:
        a.pop("duvar_ucu", None)
    bulgular, _ = _denetle(ie)
    assert any(b.startswith("açıklık yeri:") and "ic_kapi 82" in b for b in bulgular), bulgular


def test_komut_satiri():
    """Hakemin komut satırı: bütün sözlerle GEÇTİ ve sözler satırda; aks sözü kesim hattısız DUR."""
    komut = [sys.executable, "araclar/havuz_hakemi.py", GENIS, "--kart", KART, "--silme-hali", KAYNAK]
    sozlu = komut + sum(([f"--{k.replace('_', '-')}", v] for k, v in SOZLER.items()), [])
    r = subprocess.run(sozlu, cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    son = r.stdout.strip().splitlines()[-1]
    assert son.startswith("GEÇTİ: silme hâli") and f"aksa oturan duvar (ek aks 795 → aks 758): {SOZ_0607}" in son
    assert "tam ve yarım pano (" in son and f"kesim hattı {KESIM}:" in son
    r = subprocess.run(komut + ["--aks-sozu", SOZ_0607], cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 2 and "--aks-sozu yalnız --kesim-hatti ile" in r.stdout


def test_aday_kaydi_ayni_secenekler():
    """Aday kaydı hakemle aynı seçenekleri alır (sözler kayda yazılır); aks sözü kesim hattısız DUR, kayıt yazılmaz."""
    r = subprocess.run([sys.executable, "araclar/aday_kaydet.py", "--help"], cwd=KOK, capture_output=True, text=True)
    assert "--aks-sozu" in r.stdout and "--tam-yarim-sozu" in r.stdout
    komut = [sys.executable, "araclar/aday_kaydet.py", GENIS, "--kod", "PA-99", "--durum", "test", "--katalog-m2", "61", "--kart", KART,
             "--silme-hali", KAYNAK, "--aks-sozu", SOZ_0607]
    r = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 2 and "--aks-sozu yalnız --kesim-hatti ile" in r.stdout, r.stdout + r.stderr
