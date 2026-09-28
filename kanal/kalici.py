"""İE-02 · kalıcı işleyici: Postgres üzerinde mesaj → iş → Beyin/Motor → giden satırları → gönderim.

Kural ve Motor kodu değişmez: işleme kanal/worker.py::isle ile yapılır; konuşma dosyadan değil Postgres'ten okunur ve işin
bütün sonuçlarıyla birlikte tek işlemde yazılır (kanal/depo.py). Ayrıntı: docs/is_emirleri/IE-02.md.

Bu dosya WhatsApp'a bağlanmaz. Gönderim, çağıranın verdiği gönderici işleviyle yapılır (canlıda hosting; testte sahte).

Komut satırı (yalnız yerel/izole ortam; PORTMAN_PG_DSN ve PORTMAN_KANAL_DIR ortam değişkenleri):
  python kanal/kalici.py goc                        göçleri uygula
  python kanal/kalici.py isle --ayar AYAR.json [--tek] [--bos-bekle SN]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import traceback
from pathlib import Path

KOD = Path(__file__).resolve().parent
for _yol in (KOD, KOD.parent):                       # paket düzeninde beyin/ kökte (KOD), depoda bir üstte
    if (_yol / "beyin").is_dir() and str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))
if str(KOD) not in sys.path:
    sys.path.insert(0, str(KOD))

import worker as W                                   # noqa: E402  (kanal/worker.py; paket düzeninde kökte)
from depo import HATA_BAYIYE, Cakisma, Depo, KiraKaybi, maske     # noqa: E402
from beyin.konusma import BellekKonusma              # noqa: E402


class Gonderilmedi(Exception):
    """Gönderici dış çağrı yapmadan vazgeçti (ör. dosya doğrulaması): satır kesin olarak gönderilmedi."""


def isleyici_adi() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _kopya(d):
    return json.loads(json.dumps(d)) if d is not None else None


# ───────────────────────── revizyon onayı ─────────────────────────
def onay_denetimi(depo: Depo, gelen: dict, d: dict | None, talep: dict) -> dict | None:
    """Onay, bayinin mesajı yazdığı anda kendisine iletilmiş son revizyona bağlanır. Bağlanamıyorsa
    {"neden", "mesaj", "patrona"} döner ve onay kaydedilmez; bağlanıyorsa (ya da denetlenecek bir şey yoksa) None."""
    if (talep or {}).get("niyet") != "onay" or not d or d.get("asama") != "onay_bekliyor" or d.get("son_soru_alani") \
            or not d.get("son_is_emri"):
        return None
    ie = d["son_is_emri"]; no = ie.get("is_emri_no"); rev = int(ie.get("revizyon") or 1)
    r = depo.revizyon_iletimi(gelen["sender"], no, rev)
    if r is None:
        return None                     # geçişten önceki plan: revizyon kaydı yok, bugünkü davranış
    etiket = f"{no} r{rev:02d}"
    tekrar = f"{etiket} planını onaylıyorsanız lütfen yeniden \"onaylıyorum\" yazın."
    if gelen.get("context_id"):
        ar = depo.alintinin_revizyonu(gelen["sender"], gelen["context_id"])
        if ar and (ar["is_emri_no"], ar["rev"]) != (no, rev):
            return {"neden": "alıntı başka revizyona ait", "patrona": False,
                    "mesaj": f"Alıntıladığınız mesaj {ar['is_emri_no']} r{ar['rev']:02d} planına ait; güncel plan {etiket}. {tekrar}"}
    if r["pdf_durum"] in ("belirsiz", "gonderilmedi"):
        return {"neden": f"PDF iletimi teyitsiz ({r['pdf_durum']})", "patrona": True,
                "mesaj": f"{etiket} planının size ulaştığını teyit edemedim; onayınızı kaydetmedim. Lokman Bey'e iletiyorum."}
    yazildi = float(gelen.get("timestamp") or 0)
    if r["iletildi"] is None or yazildi < float(r["iletildi"]):
        return {"neden": "onay, plan iletilmeden yazılmış", "patrona": False,
                "mesaj": f"Onay mesajınız {etiket} planı size ulaşmadan yazılmış görünüyor; onayınızı kaydetmedim. "
                         f"Planı inceledikten sonra {tekrar[0].lower()}{tekrar[1:]}"}
    return None


def _red_ciktisi(gelen: dict, k: BellekKonusma, talep: dict, red: dict) -> dict:
    satirlar = [W.giden_metin(gelen, red["mesaj"], 1)]
    if red["patrona"] and (gelen.get("role") or "bayi") != "patron":
        satirlar.append(W.giden_metin(gelen, f"Portman: {maske(gelen['sender'])} onay yazdı ama kaydedilmedi: {red['neden']}.", 2, "PATRON", "bildirim"))
    k.not_dus("gelen", talep.get("ozet") or "", {"niyet": talep.get("niyet"), "guven": talep.get("guven")})
    k.not_dus("kural", f"onay revizyona bağlanmadı: {red['neden']}")
    k.not_dus("giden", red["mesaj"], {"eylem": "cevapla", "gerekce": "onay bağlanmadı"})
    k.kaydet()
    return {"satirlar": satirlar, "sonuc": {"eylem": "cevapla", "gerekce": f"onay bağlanmadı: {red['neden']}", "niyet": "onay",
                                             "asama": k.d.get("asama")}}


def _karar_ozeti(d_eski: dict | None, d_yeni: dict, cikti: dict, t0: float) -> dict:
    """Soru ve revizyon kayıtları için bu işte ne olduğunu konuşma notlarından okur (kural koduna dokunmadan)."""
    eski = (d_eski or {}).get("gecmis") or []
    yeni = [g for g in d_yeni.get("gecmis") or [] if int(g.get("t") or 0) >= int(t0) and g not in eski]
    kural = [str(g.get("metin") or "") for g in yeni if g.get("yon") == "kural"]
    onay = (cikti.get("sonuc") or {}).get("gerekce") == "plan onaylandı"
    ie = (d_eski or {}).get("son_is_emri") or {}
    return {"d01_cevap": any(n.startswith("eski taslak sorusunun cevabı") for n in kural),
            "pencere_cevap": any(n.startswith("pencere_islem cevabı") for n in kural),
            "onaylanan_is_emri_no": ie.get("is_emri_no") if onay else None,
            "onaylanan_rev": int(ie.get("revizyon") or 1) if onay else None}


# ───────────────────────── işleme ─────────────────────────
def bir_is(depo: Depo, settings: dict, sahip: str | None = None) -> dict | None:
    """Bir işi alır ve bitirir. None: sırada iş yok. Dönen sözlükte 'durum': bitti | basarisiz | cakisma | atildi."""
    sahip = sahip or isleyici_adi()
    alinan = depo.is_al(sahip, kira_sn=int(settings.get("kira_sn") or 600), en_cok=int(settings.get("en_cok_deneme") or 3))
    if not alinan:
        return None
    j, gelen = alinan["is"], alinan["gelen"]
    t0 = time.time()
    d, surum = depo.konusma_oku(gelen["sender"])
    k = BellekKonusma(gelen["sender"], d)
    d_eski = _kopya(d)
    yazili = gelen.get("type") in W.GELEN_YAZILI and bool((gelen.get("text") or "").strip())
    cikarim = j.get("cikarim")
    if yazili and cikarim is None:
        try:
            talep, meta = W.cikar(gelen, settings, k)
            cikarim = {"talep": talep.model_dump(mode="json"), "meta": meta}
        except Exception as e:                       # hata da kaydedilir: yeniden alınan iş LLM'i yeniden çağırmaz
            cikarim = {"hata": f"{type(e).__name__}: {str(e)[:300]}"}
        if not depo.cikarim_kaydet(j["id"], sahip, cikarim):
            return {"durum": "atildi", "is_id": j["id"], "neden": "kira kaybedildi (çıkarım kaydı)"}
    try:
        red = onay_denetimi(depo, gelen, d, cikarim["talep"]) if yazili and not cikarim.get("hata") else None
        cikti = _red_ciktisi(gelen, k, cikarim["talep"], red) if red else \
            W.isle(gelen, settings, k=k, cikarim=cikarim if yazili else None)
    except Exception:
        hata = traceback.format_exc()[-2500:]
        k = BellekKonusma(gelen["sender"], d)       # yarım kalan durum değişikliği yazılmaz
        cikti = {"satirlar": [W.giden_metin(gelen, HATA_BAYIYE, 1)]
                 + ([] if gelen.get("role") == "patron" else
                    [W.giden_metin(gelen, f"Portman: {maske(gelen['sender'])} mesajı işlenirken hata oluştu; günlüğe bakın.", 2, "PATRON", "bildirim")]),
                 "sonuc": {"eylem": "hata", "gerekce": "beklenmeyen hata"}, "hata": hata}
    cikti["sonuc"]["worker"] = "kalici"; cikti["sonuc"]["sure_s"] = round(time.time() - t0, 1)
    try:
        kayit = depo.isi_bitir(j, sahip, gelen, surum, d_eski, k.d, cikti, _karar_ozeti(d_eski, k.d, cikti, t0))
    except Cakisma as e:
        depo.is_geri_birak(j["id"], sahip, str(e))
        return {"durum": "cakisma", "is_id": j["id"], "neden": str(e)}
    except KiraKaybi as e:
        return {"durum": "atildi", "is_id": j["id"], "neden": str(e)}
    return {"durum": "basarisiz" if cikti.get("hata") else "bitti", "is_id": j["id"], "mesaj_id": gelen["id"],
            "eylem": cikti["sonuc"].get("eylem"), "gerekce": cikti["sonuc"].get("gerekce"), "giden": len(cikti["satirlar"]), **kayit}


# ───────────────────────── gönderim ─────────────────────────
def gonder(depo: Depo, gonderici, en_fazla: int = 100) -> dict:
    """Bekleyen giden satırlarını sırayla gönderir. gonderici(satir) WhatsApp kimliğini döner; Gonderilmedi → kesin
    gönderilmedi; başka her hata → belirsiz (otomatik yeniden gönderilmez)."""
    say = {"iletildi": 0, "belirsiz": 0, "gonderilmedi": 0, "yarim_belirsiz": depo.yarim_gonderimleri_belirsiz_say()}
    for _ in range(en_fazla):
        r = depo.gonderime_al()
        if r is None:
            break
        try:
            dis_id = gonderici(r)
            depo.gonderim_sonucu(r["id"], "iletildi", dis_id=dis_id); say["iletildi"] += 1
        except Gonderilmedi as e:
            depo.gonderim_sonucu(r["id"], "gonderilmedi", hata=str(e)[:300]); say["gonderilmedi"] += 1
        except Exception as e:
            depo.gonderim_sonucu(r["id"], "belirsiz", hata=f"Gönderim sonucu belirsiz; otomatik tekrar yok. {type(e).__name__}: {str(e)[:200]}")
            say["belirsiz"] += 1
    return say


# ───────────────────────── komut satırı ─────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("goc")
    a = alt.add_parser("isle")
    a.add_argument("--ayar", required=True)
    a.add_argument("--tek", action="store_true", help="bir iş işle ve çık")
    a.add_argument("--bos-bekle", type=float, default=0, help="kuyruk boşsa bu kadar saniye bekleyip yeniden bak (0: çık)")
    ns = ap.parse_args(argv)
    depo = Depo()
    if ns.komut == "goc":
        print("uygulanan göçler:", depo.goc_uygula() or "yok (güncel)")
        return 0
    settings = json.loads(Path(ns.ayar).read_text(encoding="utf-8"))
    sahip = isleyici_adi()
    while True:
        r = bir_is(depo, settings, sahip)
        if r is not None:
            print(json.dumps({k: v for k, v in r.items() if k != "mesaj_id"}, ensure_ascii=False), flush=True)
            if ns.tek:
                return 0
            continue
        if ns.bos_bekle <= 0:
            return 0
        time.sleep(ns.bos_bekle)


if __name__ == "__main__":
    sys.exit(main())
