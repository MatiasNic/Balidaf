import pytest

from balidaf.montos import a_centavos, a_excel, fmt


@pytest.mark.parametrize("valor, cent, prob", [
    (None, 0, None), ("", 0, None), (0, 0, None), (5, 500, None), (2.5, 250, None),
    (150848.96000000002, 15084896, None),      # resto de float (caso real)
    (14387.789999999999, 1438779, None),
    ("1.234,56", 123456, None), ("12,5", 1250, None), (" 000301697,92", 30169792, None),
    ("301697.92    ", 30169792, None), ("abc", 0, "invalido"), (1.234, 123, "redondeo"),
])
def test_a_centavos(valor, cent, prob):
    assert a_centavos(valor) == (cent, prob)


def test_a_excel_y_formato():
    assert a_excel(30169792) == 301697.92
    assert a_excel(100) == 1
    assert fmt(123456789) == "1.234.567,89"
    assert fmt(-1001) == "-10,01"
