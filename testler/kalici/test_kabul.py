"""T10: kabul gösterimini (kabul_gosterimi.py) test olarak koşar. Simülasyondur; ayrıntı betiğin başında."""
import kabul_gosterimi


def test_t10_kabul_gosterimi(sablon, tmp_path):
    assert kabul_gosterimi.main(["--rapor", str(tmp_path / "kabul.md")]) == 0
