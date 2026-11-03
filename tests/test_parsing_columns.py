import pytest
from openpyxl import Workbook

from balidaf.columns import find_columns
from balidaf.parsing import to_float


@pytest.mark.parametrize("value, expected", [
    (None, 0.0), ("", 0.0), ("   ", 0.0), (5, 5.0), (2.5, 2.5),
    ("1.234,56", 1234.56), ("12,5", 12.5), ("1234.5", 1234.5),
    ("1 000", 1000.0), ("abc", 0.0),
])
def test_to_float(value, expected):
    assert to_float(value) == pytest.approx(expected)


def _ws(headers):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    return ws


def test_find_columns_crea_salidas_faltantes():
    ws = _ws(["CONCATENAR", "IMPORTE_SUBSIDIADO", "RETENCION_GANANCIAS",
              "RETENCION_IIBB", "OTRAS_RETENCIONES", "IMPORTE_SOLICITADO"])
    m = find_columns(ws)
    assert m["key"] == 1 and m["solicitado"] == 6
    assert (m["apli_sss"], m["transferido"], m["fdo_ppio"]) == (7, 8, 9)
    assert ws.cell(row=1, column=7).value == "impor_apli_sss"


def test_find_columns_alias_y_normalizacion():
    ws = _ws(["Socio", "importe subsidiado", "ret-ganancias", "ret_iibb", "otras ret", "Imp Solicitado"])
    m = find_columns(ws)
    assert [m[k] for k in ("key", "subsidiado", "ret_gcias", "ret_iibb", "ret_otras", "solicitado")] == [1, 2, 3, 4, 5, 6]


def test_find_columns_falta_requerida():
    ws = _ws(["CONCATENAR", "IMPORTE_SUBSIDIADO"])
    with pytest.raises(ValueError, match="Faltan columnas requeridas"):
        find_columns(ws)
