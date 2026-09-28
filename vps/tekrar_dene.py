"""Canlı kabul gösterimi, adım 7: aynı kanal mesajını Postgres'e yeniden verir; ikinci iş açılmadığını gösterir.
Mesajın kuyruk satırı (ham) Postgres'ten okunur ve mesaj_kaydet'e aynen verilir. Hosting'e ve WhatsApp'a dokunmaz.
  sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/tekrar_dene.py <mesaj izi>
Mesaj izi: kanit_sorgulari.sql 1. tablodaki mesaj_izi (left(md5(kimlik), 10)). WhatsApp kimliği numarayı içerdiği için
kimliğin kendisi yazdırılmaz. Kimliğin en az 12 karakterlik başı da verilebilir (yalnız yerel test).
"""
import hashlib
import sys
from pathlib import Path

_BURASI = Path(__file__).resolve().parent
for _yol in (_BURASI, _BURASI.parent / "kanal"):         # pakette depo.py yanında; depoda kanal/ altında
    if (_yol / "depo.py").is_file():
        sys.path.insert(0, str(_yol)); break
from depo import Depo  # noqa: E402

a = sys.argv[1] if len(sys.argv) == 2 else ""
iz = len(a) == 10 and all(ch in "0123456789abcdef" for ch in a)
if not iz and len(a) < 12:
    raise SystemExit("kullanım: tekrar_dene.py <mesaj izi> (kanit_sorgulari.sql 1. tablo, mesaj_izi)")
d = Depo()
with d.baglan() as c:
    satirlar = (c.execute("SELECT id, ham FROM mesajlar WHERE left(md5(id), 10) = %s", (a,)) if iz else
                c.execute("SELECT id, ham FROM mesajlar WHERE id LIKE %s", (a + "%",))).fetchall()
if len(satirlar) != 1:
    raise SystemExit(f"{len(satirlar)} mesaj eşleşti")
mid, ham = satirlar[0]["id"], satirlar[0]["ham"]
once = d.mesaj_durumu(mid)
yeni = d.mesaj_kaydet(ham)
with d.baglan() as c:
    n = c.execute("SELECT count(*) AS n FROM isler WHERE mesaj_id = %s", (mid,)).fetchone()["n"]
print(f"mesaj izi {hashlib.md5(mid.encode()).hexdigest()[:10]}: yeniden verildi → yeni iş açıldı mı: {'EVET' if yeni else 'hayır'}; bu mesajın iş sayısı: {n} "
      f"(önce: iş {once['is_id']}, {once['is_durum']})")
sys.exit(1 if yeni or n != 1 else 0)
