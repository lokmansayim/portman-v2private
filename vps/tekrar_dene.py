"""Canlı kabul gösterimi, adım 7: aynı kanal mesajını Postgres'e yeniden verir; ikinci iş açılmadığını gösterir.
Mesajın kuyruk satırı (ham) Postgres'ten okunur ve mesaj_kaydet'e aynen verilir. Hosting'e ve WhatsApp'a dokunmaz.
  sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/tekrar_dene.py <mesaj kimliğinin başı>
"""
import sys
from pathlib import Path

_BURASI = Path(__file__).resolve().parent
for _yol in (_BURASI, _BURASI.parent / "kanal"):         # pakette depo.py yanında; depoda kanal/ altında
    if (_yol / "depo.py").is_file():
        sys.path.insert(0, str(_yol)); break
from depo import Depo  # noqa: E402

if len(sys.argv) != 2 or len(sys.argv[1]) < 12:
    raise SystemExit("kullanım: tekrar_dene.py <mesaj kimliğinin en az 12 karakteri> (kanit_sorgulari.sql 1. tablo)")
d = Depo()
with d.baglan() as c:
    satirlar = c.execute("SELECT id, ham FROM mesajlar WHERE id LIKE %s", (sys.argv[1] + "%",)).fetchall()
if len(satirlar) != 1:
    raise SystemExit(f"{len(satirlar)} mesaj eşleşti; kimliğin daha uzun bir başını verin")
mid, ham = satirlar[0]["id"], satirlar[0]["ham"]
once = d.mesaj_durumu(mid)
yeni = d.mesaj_kaydet(ham)
with d.baglan() as c:
    n = c.execute("SELECT count(*) AS n FROM isler WHERE mesaj_id = %s", (mid,)).fetchone()["n"]
print(f"mesaj {mid[:24]}…: yeniden verildi → yeni iş açıldı mı: {'EVET' if yeni else 'hayır'}; bu mesajın iş sayısı: {n} "
      f"(önce: iş {once['is_id']}, {once['is_durum']})")
sys.exit(1 if yeni or n != 1 else 0)
