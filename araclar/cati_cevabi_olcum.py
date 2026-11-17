"""İE-42 · çatı cevabı ölçümü: havuzun ölçüm satırları gerçek LLM'le okunur, kod karar verir, sonuç hakemin beklediğiyle kıyaslanır.

DİKKAT: `--ucretli` ile her satır bir LLM çağrısıdır (ücretli deneme; Lokman'ın onayıyla, AGENTS.md › Ayrı onay gerekenler). Anahtar
`ANTHROPIC_API_KEY` ortam değişkeninden okunur; hiçbir yere yazılmaz. `--ucretli` olmadan kuru koşu: bağlamı ve satır sayısını yazar.

    python3 araclar/cati_cevabi_olcum.py <çıktı klasörü> [--ucretli] [--sinir N]

Sınıflar: yuksek (yanlış çatı ya da beklenmeyen onay), orta (kararsız söze çizim ya da açık seçime soru), dusuk (öteki fark)."""
from __future__ import annotations

import argparse
import copy
import io
import json
import contextlib
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "testler"))

from beyin import cati_cevabi as CC, llm  # noqa: E402
from beyin import karar as K  # noqa: E402
from test_celik_revizyon_karar import BAYI  # noqa: E402


def _setler(tmp: Path) -> dict:
    import test_prefabrik_cati_seti as TP
    from test_celik_revizyon_karar import Sohbet, onayla
    s, k = TP._cati_seti(tmp / "p")
    assert k.eylem == "secenek", k.mesaj
    c = Sohbet(tmp / "c")
    assert c.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik").eylem == "is_emri"
    assert onayla(c).eylem == "secenek"
    return {"prefabrik": s, "celik": c}


def _sinif(s, k) -> str:
    d = s.k.d
    ie = d.get("son_is_emri") or {}
    y = ie.get("yapi") or {}
    kod = y.get("kod") if y.get("sistem") == "celik" else (ie.get("talep") or {}).get("kaynak")
    if k.gerekce == K.PLAN_ONAYI:
        return "ONAY"
    if k.eylem == "sor" and (k.mesaj or "").startswith("Hangi çatı olsun?"):
        return "SORU"
    if k.eylem == "is_emri":
        return f"R{k.revizyon}:{kod}"
    return f"{k.eylem}"


def _beklenen(x: dict, st: dict) -> str:
    if x["durum"] != "secti":
        return "SORMALI"
    return "ONAY" if x["secilen"] == 1 else f"R2:{st['adaylar'][x['secilen'] - 1]['kod']}"


def _derece(bek: str, c: str) -> str | None:
    if bek == c:
        return None
    if bek == "SORMALI":
        if c == "SORU" or not (c == "ONAY" or c.startswith("R")):
            return None
        return "orta" if c.startswith("R") else "yuksek"           # kararsız söze onay yüksek, çizim orta (r02 onaylanabilir)
    if c == "ONAY" or c.startswith("R"):
        return "yuksek"                                             # başka çatı ya da yanlış onay
    return "orta"                                                   # açık seçim soruya döndü


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cikti")
    ap.add_argument("--ucretli", action="store_true")
    ap.add_argument("--sinir", type=int, default=0)
    ap.add_argument("--model", default="claude-opus-5-5")
    a = ap.parse_args()
    out = Path(a.cikti); out.mkdir(parents=True, exist_ok=True)
    satirlar = list(CC.havuz()[1])
    if a.sinir:
        satirlar = satirlar[:a.sinir]
    setler = _setler(Path(tempfile.mkdtemp()))
    on = "aşama: ön onay planı gönderildi, bayinin onay/revizyon cevabı bekleniyor"
    if not a.ucretli:
        print(f"kuru koşu: {len(satirlar)} satır; örnek bağlam:\n{on}; {CC.baglam(setler['prefabrik'].k, satirlar[0]['m'])}")
        return 0
    sonuc, sayac = [], {"yuksek": 0, "orta": 0, "dusuk": 0, "dogru": 0, "hata": 0}
    girdi = cikti = 0
    for i, x in enumerate(satirlar, 1):
        s = copy.deepcopy(setler[x["yapi"]])
        st = s.k.d["secenek_seti"]
        bag = f"{on}; {CC.baglam(s.k, x['m'])}"
        try:
            t, meta = llm.cikar_guvenli(x["m"], bag, backend="anthropic", model=a.model, timeout=120)
            girdi += meta.get("girdi_token") or 0
            cikti += meta.get("cikti_token") or 0
            with contextlib.redirect_stdout(io.StringIO()):
                k = K.karar_ver(t, s.k, BAYI, s.kat, x["m"])
            c = _sinif(s, k)
            bek = _beklenen(x, st)
            d = _derece(bek, c)
            sayac[d or "dogru"] += 1
            sonuc.append({"m": x["m"], "yapi": x["yapi"], "beklenen": bek, "sonuc": c, "derece": d,
                          "okuma": t.cati_cevabi.model_dump() if t.cati_cevabi else None, "niyet": t.niyet})
        except Exception as e:                                       # noqa: BLE001
            sayac["hata"] += 1
            sonuc.append({"m": x["m"], "hata": f"{type(e).__name__}: {str(e)[:200]}"})
        if i % 25 == 0:
            print(f"{i}/{len(satirlar)} {sayac} token {girdi}+{cikti}", flush=True)
        time.sleep(0.2)
    ozet = {"satir": len(satirlar), **sayac, "girdi_token": girdi, "cikti_token": cikti, "model": a.model}
    (out / "olcum.json").write_text(json.dumps({"ozet": ozet, "satirlar": sonuc}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(ozet, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
