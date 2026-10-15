#!/usr/bin/env python3
"""İE-14 r3 · P6 (M6, M7): kayıtlardan ölçüm raporu — hedef yok, önce ölçülür (Lokman 14.10, 6. madde).

Kaynak tablolar: `plan_uretimleri` (göç 007: durum, yol, puan, süre, çağrı, token, adaylar, programdan değişen), `revizyonlar` (yeni planların
revizyon sayısı ve onayı), `okuma_kiyaslari` (göç 008: gölge okuma sınıfları). Çıktı Markdown; numara ve mesaj metni yazılmaz (bayi kodu
yeter). Veritabanına yalnız okur.

Sunucuda (Lokman koşar; asistan bağlanmaz): betik sürümle gelir, çıktı dosyaya yazılır ve okunur:
    ssh -n portman-vps 'timeout 120 /opt/portman/venv/bin/python /opt/portman/guncel/araclar/plan_olcum.py' > olcum.md 2>&1
Yerelde: PORTMAN_PG_DSN="host=127.0.0.1 port=55432 user=postgres dbname=…" python araclar/plan_olcum.py [--gun 7] [--rapor <dosya>]
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "kanal"))
sys.path.insert(0, str(KOK))


def topla(c, gun: int | None = None) -> dict:
    """Bağlantıdan (`psycopg`, dict_row) ölçümler. `gun`: son N gün."""
    kos = "WHERE olusturuldu > now() - make_interval(days => %s)" if gun else ""
    arg = (gun,) if gun else ()
    pu = c.execute(f"SELECT durum, yol, puan, sure_ms, cagri, girdi_token, cikti_token, bayi_kod, is_emri_no, degisen, adaylar "
                   f"FROM plan_uretimleri {kos}", arg).fetchall()
    sure = [r["sure_ms"] for r in pu if r["sure_ms"] is not None]
    bayi: dict[str, dict] = {}
    for r in pu:
        b = bayi.setdefault(r["bayi_kod"] or "?", {"uretim": 0, "cagri": 0, "token": 0, "secilen": 0})
        b["uretim"] += 1
        b["cagri"] += r["cagri"] or 0
        b["token"] += (r["girdi_token"] or 0) + (r["cikti_token"] or 0)
        b["secilen"] += 1 if r["is_emri_no"] else 0
    # her revizyon yeni İş Emri numarası alır; iş = proje (inceleme C6)
    rv = c.execute("SELECT proje_id, max(rev) AS son, bool_or(durum = 'onaylandi') AS onay FROM revizyonlar "
                   "WHERE is_emri->'yapi'->>'kod' LIKE 'YENI-%%' GROUP BY proje_id").fetchall()
    try:
        ok = c.execute(f"SELECT sinif, cagri, etiket FROM okuma_kiyaslari {kos}", arg).fetchall()
    except Exception:                                    # 008 uygulanmamış sürüm
        ok = []
    return {
        "uretim": len(pu), "durum": dict(Counter(r["durum"] for r in pu)), "yol": dict(Counter(r["yol"] or "—" for r in pu)),
        "secilen": sum(1 for r in pu if r["is_emri_no"]), "son_basamak_degisen": sum(1 for r in pu if r["degisen"]),
        "cagri": sum(r["cagri"] or 0 for r in pu), "token": sum((r["girdi_token"] or 0) + (r["cikti_token"] or 0) for r in pu),
        "sure_ms_medyan": statistics.median(sure) if sure else None, "sure_ms_en_cok": max(sure) if sure else None,
        "bayi": bayi,
        "yeni_plan_isi": len(rv), "revizyon_ortalama": round(statistics.mean(r["son"] - 1 for r in rv), 2) if rv else None,
        "onaylanan": sum(1 for r in rv if r["onay"]),
        "okuma": dict(Counter(r["sinif"] for r in ok)), "okuma_cagri": sum(r["cagri"] or 0 for r in ok),
        "okuma_etiket": dict(Counter(r["etiket"] or "etiketsiz" for r in ok)),
    }


def rapor(o: dict, gun: int | None = None) -> str:
    r = ["# İE-14 kayıtlardan ölçüm (M6, M7)" + (f" · son {gun} gün" if gun else ""), "",
         "Hedef yok: önce ölçülür, hedef sonra konur. Numara ve mesaj metni yok.", "",
         "| Ölçüm | Değer |", "|---|---|",
         f"| Yeni plan üretimi | {o['uretim']} ({', '.join(f'{k} {v}' for k, v in sorted(o['durum'].items())) or '—'}) |",
         f"| Üretim yolu | {', '.join(f'{k} {v}' for k, v in sorted(o['yol'].items())) or '—'} |",
         f"| Bayinin seçtiği yeni plan | {o['secilen']} |",
         f"| Son basamakta programı değişen | {o['son_basamak_degisen']} |",
         f"| LLM çağrısı / token (üretim) | {o['cagri']} / {o['token']} |",
         f"| Üretim süresi medyan / en çok | {o['sure_ms_medyan'] or '—'} ms / {o['sure_ms_en_cok'] or '—'} ms |",
         f"| Yeni plan işi · ortalama revizyon · onaylanan | {o['yeni_plan_isi']} · {o['revizyon_ortalama'] if o['revizyon_ortalama'] is not None else '—'} · {o['onaylanan']} |",
         f"| Gölge okuma (sınıf) | {', '.join(f'{k} {v}' for k, v in sorted(o['okuma'].items())) or '—'} |",
         f"| Gölge okuma çağrısı · etiket | {o['okuma_cagri']} · {', '.join(f'{k} {v}' for k, v in sorted(o['okuma_etiket'].items())) or '—'} |",
         "", "## Bayi başına", "", "| Bayi | Üretim | Seçilen | Çağrı | Token |", "|---|---|---|---|---|"]
    for b, v in sorted(o["bayi"].items()):
        r.append(f"| {b} | {v['uretim']} | {v['secilen']} | {v['cagri']} | {v['token']} |")
    return "\n".join(r) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="İE-14 kayıtlardan ölçüm (yalnız okur)")
    ap.add_argument("--gun", type=int)
    ap.add_argument("--rapor", type=Path)
    a = ap.parse_args(argv)
    from depo import Depo
    d = Depo(os.environ.get("PORTMAN_PG_DSN"))
    with d.baglan() as c:
        metin = rapor(topla(c, a.gun), a.gun)
    if a.rapor:
        a.rapor.write_text(metin, encoding="utf-8")
    else:
        print(metin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
