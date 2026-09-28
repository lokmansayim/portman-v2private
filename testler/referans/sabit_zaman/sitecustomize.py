"""Yalnız referans koşularında (dogrula.py) üretim zamanını sabitler; canlı koda ve canlı çıktılara dokunmaz.

Motor her çizime üretim zamanını yazar ("Üretim: … UTC", PORTMAN_INFO katmanı). PDF'te bu yazı çizgi olarak basılır;
zaman değişince PDF'in yalnız o çizimi değişir. dogrula.py kos.py'yi TEST_SABIT_ZAMAN ortam değişkeniyle ve bu klasör
PYTHONPATH'te olacak biçimde koşar: Python her süreçte bu dosyayı kendiliğinden yükler ve argümansız time.gmtime()
sabit anı döner. Böylece PDF içeriği koşudan koşuya birebir karşılaştırılabilir. Değişken yoksa hiçbir şey yapmaz.
"""
import os
import time

_ZAMAN = os.environ.get("TEST_SABIT_ZAMAN")
if _ZAMAN:
    _sabit = time.gmtime(int(_ZAMAN))
    _asil_gmtime = time.gmtime

    def gmtime(saniye=None):
        return _sabit if saniye is None else _asil_gmtime(saniye)

    time.gmtime = gmtime
