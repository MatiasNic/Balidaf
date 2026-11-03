"""Validaciones del Anexo III del instructivo de la SSS."""

import datetime as dt

import pytest

from balidaf.excel_io import leer_excel
from balidaf.validacion import ERROR, cbu_digitos_ok, cuit_valido, validar


def _codigos(excel, filas, nivel=ERROR):
    lote = leer_excel(excel(filas))
    return {h.codigo for h in validar(lote.lineas, lote.faltantes) if nivel is None or h.nivel == nivel}


OK = dict(importe_subsidiado=100, importe_solicitado=100, impor_apli_sss=100, importe_transferido=100,
          fdo_ppio_ingre_cta_disca=0)


def test_linea_correcta(excel):
    assert _codigos(excel, [dict(OK)]) == set()


def test_cuit_y_cbu():
    assert cuit_valido("30694407044")
    assert not cuit_valido("30694407045")
    assert cbu_digitos_ok("0110599520000002713698")


@pytest.mark.parametrize("cambios, codigo", [
    (dict(clave_rendicion="123"), "605"),
    (dict(rnos="12"), "600"),
    (dict(periodo_presentacion="202613"), "601"),
    (dict(tipo_archi="XX"), "609"),
    (dict(importe_solicitado="abc"), "610"),
    (dict(cuit_CBU=""), "611"),
    (dict(cuit_CBU="00020010500"), "612"),            # con transferencia
    (dict(cuit_CBU="30694407045"), "613"),
    (dict(cbu="123"), "614"),
    (dict(opg_1="X" * 21), "615"),
    (dict(fecha_transfer_1="31/02/2026"), "616"),
    (dict(fecha_transfer_1="25/05/2026"), "617"),
    (dict(cheque="ABC"), "618"),
    (dict(nro_recibo="123456789"), "619"),
    (dict(obs="x" * 151), "625"),
    (dict(importe_transferido=90), "622"),
    (dict(fdo_ppio_ingre_cta_disca=5), "623"),
    (dict(importe_subsidiado=120), "624"),
])
def test_cada_regla(excel, cambios, codigo):
    f = dict(OK)
    f.update(cambios)
    assert codigo in _codigos(excel, [f])


def test_clave_duplicada(excel):
    a, b = dict(OK, clave_rendicion="84600000001"), dict(OK, clave_rendicion="84600000001")
    assert "606" in _codigos(excel, [a, b])


def test_linea_sin_pago_no_exige_cuit_valido(excel):
    # Caso real aceptado por la SSS: todo en 0, CUIT 00020010500 y CBU "0"
    f = dict(cuit_CBU="00020010500", cbu="0", opg_1=0, fecha_transfer_1=0)
    assert _codigos(excel, [f]) == set()


def test_fecha_como_fecha_de_excel(excel):
    assert _codigos(excel, [dict(OK, fecha_transfer_1=dt.datetime(2026, 6, 25))]) == set()


def test_devuelto_exige_cuenta_sss(excel):
    f = dict(OK, importe_solicitado=150, import_devuelto_cta_sss=50, importe_subsidiado=150)
    assert "621" in _codigos(excel, [f])
    f.update(cuit_CBU="30694407044", cbu="0110599520000002713698")
    assert "621" not in _codigos(excel, [f])


def test_tipo_db_no_valida_623(excel):
    assert "623" not in _codigos(excel, [dict(OK, tipo_archi="DB", fdo_ppio_ingre_cta_disca=5)])


def test_cbu_con_digito_incorrecto_es_advertencia(excel):
    assert "B04" in _codigos(excel, [dict(OK, cbu="0110599520000002713699")], nivel=None)


def test_falta_columna(excel, tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["cuil", "importe_subsidiado"])
    ruta = str(tmp_path / "x.xlsx")
    wb.save(ruta)
    lote = leer_excel(ruta)
    assert "clave" in lote.faltantes
    assert "B01" in {h.codigo for h in validar(lote.lineas, lote.faltantes)}
