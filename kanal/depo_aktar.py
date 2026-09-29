"""İE-02 · geçiş ve geri dönüş: dosya düzeni (durum/*.json, state.json) ↔ Postgres.

  içe aktar  : durum/<numara>.json → konusmalar (bekleyen B1/B2 soruları durumun içinde olduğu için onlar da gelir; askıdaki
               soru sorular tablosuna da yazılır, doğuran mesaj bilinmediği için kaynağı boş); state.json inbound →
               mesajlar + isler. Bitmiş satırlar yalnız tekilleştirme için kaydedilir (aynı mesaj yeniden gelirse yeniden
               işlenmez). 'queued' satırlar canlı geçişte ATLANIR (varsayılan): hosting kuyruğunda kalır, ajan claim ile
               alır; böylece hosting'teki satır 'processing' olmadan Postgres'te işlenip sonucu reddedilmez. Yalnız hosting'siz
               (çevrimdışı) kullanımda --sirada is ile iş olarak sıraya girer. Kuyrukta 'processing' satır varsa aktarma yapılmaz: eski
               işleyici durdurulup kuyruk boşalmadan geçilmez (yarım işin sonucu bilinmez).
  dışa aktar : konusmalar → durum/<numara>.json (geri dönüşte hosting ya da eski ajan kaldığı yerden sürer).
Var olan kayıtların üzerine yazılmaz; atlananlar sayılır. Komut satırı yalnız boş veritabanına aktarır. Anahtar ya da
sır okumaz, yazmaz.

  python kanal/depo_aktar.py ice  --kanal KLASOR
  python kanal/depo_aktar.py disa --hedef KLASOR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from depo import Depo, soru_ayrintisi  # noqa: E402

_IS_DURUMU = {"queued": "sirada", "done": "bitti", "failed": "basarisiz"}


def ice_aktar(depo: Depo, kanal: Path, sirada_olanlar: str = "atla", bos_olmali: bool = False) -> dict:
    """bos_olmali: hedef veritabanında konuşma ya da mesaj varsa aktarılmaz. Komut satırı bunu her zaman ister: geri
    dönüşten sonra yeniden girişte eski veritabanı üzerine aktarılırsa, dosya modunda ilerlemiş konuşmalar "zaten var"
    diye atlanır ve Postgres'teki eski durum sessizce kullanılırdı (kapı H: eski veritabanı adı değiştirilip saklanır)."""
    assert sirada_olanlar in ("atla", "is")
    if bos_olmali:
        with depo.baglan() as c:
            dolu = c.execute("SELECT (SELECT count(*) FROM konusmalar) + (SELECT count(*) FROM mesajlar) AS n").fetchone()["n"]
        if dolu:
            raise ValueError(f"hedef veritabanı boş değil ({dolu} konuşma/mesaj); yeniden girişte eski veritabanının adı "
                             "değiştirilir ve boş bir veritabanına aktarılır (IE-02-canli.md, kapı H)")
    kanal = Path(kanal)
    say = {"konusma": 0, "konusma_atlandi": 0, "soru": 0, "mesaj": 0, "mesaj_atlandi": 0, "sirada": 0, "kuyrukta_birakildi": 0}
    st = kanal / "state.json"
    inbound = (json.loads(st.read_text(encoding="utf-8")).get("inbound") or {}) if st.exists() else {}
    yarim = [m for m, g in inbound.items() if g.get("state") == "processing"]
    if yarim:
        raise ValueError(f"kuyrukta işlenmekte olan {len(yarim)} mesaj var; eski işleyici durdurulup kuyruk boşalmadan aktarılmaz")
    with depo.baglan() as c, c.transaction():
        for p in sorted((kanal / "durum").glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            r = c.execute("INSERT INTO konusmalar (gonderen, durum) VALUES (%s, %s) ON CONFLICT (gonderen) DO NOTHING RETURNING surum",
                          (p.stem, Jsonb(d))).fetchone()
            say["konusma" if r else "konusma_atlandi"] += 1
            alan = d.get("son_soru_alani")
            if r and alan:
                zaman = float(d.get("bekleyen_zamani") or d.get("guncellendi") or 0)
                c.execute("INSERT INTO sorular (gonderen, alan, kaynak_mesaj_id, bekletilen_talep, bekletilen_metin, pencere_satiri, deneme, "
                          "soruldu, son_soruldu, gecerlilik_sonu) VALUES (%s, %s, NULL, %s, %s, %s, %s, to_timestamp(%s), to_timestamp(%s), %s)",
                          (p.stem, alan, *soru_ayrintisi(d, alan), zaman, zaman, Depo._gecerlilik(d, alan)))
                say["soru"] += 1
        for mid, g in sorted(inbound.items(), key=lambda x: (x[1].get("timestamp", 0), x[1].get("received_at", 0))):
            if not str(mid).startswith("wamid.") or g.get("self_test"):
                continue
            if g.get("state") == "queued" and sirada_olanlar == "atla":
                say["kuyrukta_birakildi"] += 1          # ajan hosting kuyruğundan claim ile alacak
                continue
            g = {**g, "id": mid}
            bayi = g.get("bayi") if isinstance(g.get("bayi"), dict) else None
            if bayi:
                c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES (%s, %s, %s, %s) ON CONFLICT (numara) DO NOTHING",
                          (str(g["sender"]), bayi.get("kod"), bayi.get("ad") or "", "patron" if bayi.get("rol") == "patron" else "bayi"))
            r = c.execute("INSERT INTO mesajlar (id, gonderen, bayi_kod, tur, metin, alinti_id, wa_zamani, ham) "
                          "VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), %s) ON CONFLICT (id) DO NOTHING RETURNING id",
                          (mid, str(g["sender"]), (bayi or {}).get("kod"), g.get("type") or "text", g.get("text") or "",
                           g.get("context_id"), float(g.get("timestamp") or 0), Jsonb(g))).fetchone()
            if r is None:
                say["mesaj_atlandi"] += 1
                continue
            durum = _IS_DURUMU.get(g.get("state"), "basarisiz")      # bilinmeyen durum: yeniden işlenmez
            c.execute("INSERT INTO isler (mesaj_id, gonderen, durum, sonuc, hata, bitti) VALUES (%s, %s, %s, %s, %s, "
                      "CASE WHEN %s = 'sirada' THEN NULL ELSE now() END)",
                      (mid, str(g["sender"]), durum, Jsonb(g.get("result")) if g.get("result") is not None else None,
                       None if durum != "basarisiz" else (g.get("error") or f"geçişte '{g.get('state')}' durumundaydı"),
                       durum))
            say["mesaj"] += 1; say["sirada"] += durum == "sirada"
    return say


def disa_aktar(depo: Depo, hedef: Path) -> dict:
    hedef = Path(hedef) / "durum"; hedef.mkdir(parents=True, exist_ok=True)
    n = 0
    with depo.baglan() as c:
        for r in c.execute("SELECT gonderen, durum FROM konusmalar ORDER BY gonderen"):
            d = dict(r["durum"]); d.pop("proje_id", None)          # proje kimliği yalnız Postgres düzeninde anlamlı
            (hedef / f"{r['gonderen']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            n += 1
    return {"konusma": n}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    ice = alt.add_parser("ice")
    ice.add_argument("--kanal", required=True)
    ice.add_argument("--sirada", choices=["atla", "is"], default="atla", help="kuyruktaki mesajlar: atla (canlı geçiş) | is")
    alt.add_parser("disa").add_argument("--hedef", required=True)
    ns = ap.parse_args(argv)
    depo = Depo()
    print(json.dumps(ice_aktar(depo, Path(ns.kanal), ns.sirada, bos_olmali=True) if ns.komut == "ice" else disa_aktar(depo, Path(ns.hedef)),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
