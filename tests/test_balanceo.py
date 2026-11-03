"""Reglas de balanceo (622 / 623 / 624) y criterios aprendidos de la corrección manual."""

from balidaf.balanceo import balancear
from balidaf.excel_io import leer_excel
from balidaf.validacion import ERROR, validar


def _lineas(excel, filas):
    return leer_excel(excel(filas)).lineas


def _errores(lineas):
    return [h for h in validar(lineas) if h.nivel == ERROR]


def test_subsidio_menor_al_solicitado(excel):
    # Caso real: subsidio 1.010.735,49 y se había aplicado todo lo solicitado (1.364.492,91)
    ls = _lineas(excel, [dict(importe_subsidiado=1010735.49, importe_solicitado=1364492.91,
                              retencion_ganancias=27289.86, retencion_IIBB=27289.86,
                              importe_transferido=1309913.19, impor_apli_sss=1364492.91)])
    assert {h.codigo for h in _errores(ls)} == {"624"}
    balancear(ls)
    ln = ls[0]
    assert ln.monto["apli"] == 101073549
    assert ln.monto["transferido"] == 101073549 - 2728986 * 2
    assert ln.monto["fdo_ppio"] == 136449291 - 101073549
    assert _errores(ls) == []


def test_grupo_es_cuil_periodos_y_practica(excel):
    # Mismo CUIL pero distinta práctica → grupos distintos (cada uno con su subsidio)
    ls = _lineas(excel, [
        dict(cod_prestac="090", importe_subsidiado=100, importe_solicitado=150),
        dict(cod_prestac="096", importe_subsidiado=0, importe_solicitado=80),
    ])
    balancear(ls)
    assert [l.monto["apli"] for l in ls] == [10000, 0]
    assert [l.monto["fdo_ppio"] for l in ls] == [5000, 8000]
    assert _errores(ls) == []


def test_prioriza_lineas_con_retenciones(excel):
    # El subsidio sólo cubre una línea: se aplica primero a la que tiene retenciones
    ls = _lineas(excel, [
        dict(importe_subsidiado=1000, importe_solicitado=1000),
        dict(importe_subsidiado=0, importe_solicitado=1000, retencion_ganancias=200),
    ])
    balancear(ls)
    assert [l.monto["apli"] for l in ls] == [0, 100000]
    assert [l.monto["transferido"] for l in ls] == [0, 80000]
    assert min(l.monto["transferido"] for l in ls) >= 0
    assert _errores(ls) == []


def test_reduce_retenciones_si_el_subsidio_no_alcanza(excel):
    # Opción (a): se baja la retención y el transferido queda en 0
    ls = _lineas(excel, [dict(importe_subsidiado=225.21, importe_solicitado=1508.48,
                              retencion_ganancias=467.63)])
    grupos = balancear(ls)
    ln = ls[0]
    assert ln.monto["apli"] == 22521
    assert ln.monto["ret_gan"] == 22521
    assert ln.monto["transferido"] == 0
    assert list(grupos.values())[0].retenciones_reducidas == [ln.fila]
    assert _errores(ls) == []


def test_reduce_en_orden_ganancias_iibb_otras(excel):
    ls = _lineas(excel, [dict(importe_subsidiado=50, importe_solicitado=100,
                              retencion_ganancias=30, retencion_IIBB=30, otras_retnciones=30)])
    balancear(ls)
    m = ls[0].monto
    assert (m["ret_gan"], m["ret_iibb"], m["ret_otras"], m["transferido"]) == (3000, 2000, 0, 0)


def test_grupo_correcto_no_se_toca(excel):
    ls = _lineas(excel, [
        dict(importe_subsidiado=300, importe_solicitado=200, impor_apli_sss=150, importe_transferido=150,
             fdo_ppio_ingre_cta_disca=50),
        dict(importe_subsidiado=0, importe_solicitado=150, impor_apli_sss=150, importe_transferido=150,
             fdo_ppio_ingre_cta_disca=0),
    ])
    balancear(ls)
    assert all(not l.modificados() for l in ls)


def test_subsidio_mayor_a_lo_solicitado_no_balancea(excel):
    ls = _lineas(excel, [dict(importe_subsidiado=500, importe_solicitado=300)])
    g = list(balancear(ls).values())[0]
    assert g.sobrante == 20000
    assert "624" in {h.codigo for h in _errores(ls)}


def test_considera_otros_destinos(excel):
    # Saldo no aplicado y fondos de otra cuenta entran en las fórmulas 623 / 624
    ls = _lineas(excel, [dict(importe_subsidiado=1000, importe_solicitado=1200, saldo_no_apli=100,
                              fdo_ppio_otras_ctas=50)])
    balancear(ls)
    m = ls[0].monto
    assert m["apli"] == 90000          # 1000 − 100 de saldo no aplicado
    assert m["fdo_ppio"] == 120000 - 90000 - 10000 - 5000
    assert _errores(ls) == []


def test_ejemplo_completo_queda_sin_errores(tmp_path):
    from generar_ejemplo import construir
    ruta = str(tmp_path / "ej.xlsx")
    construir(80, 3).save(ruta)
    ls = leer_excel(ruta).lineas
    assert _errores(ls)                 # el ejemplo viene sin balancear
    balancear(ls)
    assert _errores(ls) == []
    assert all(l.monto["transferido"] >= 0 and l.monto["fdo_ppio"] >= 0 for l in ls)


def test_tipo_de_correccion(excel):
    from balidaf.balanceo import (TIPO_CENTAVOS, TIPO_DE_MAS, TIPO_DE_MENOS, TIPO_NO_BALANCEA,
                                  TIPO_RETENCIONES, proponer, tipo_correccion)
    ls = _lineas(excel, [
        dict(cuil="20960308248", importe_subsidiado=100, importe_solicitado=150, impor_apli_sss=150, importe_transferido=150),
        dict(cuil="27628194829", importe_subsidiado=100, importe_solicitado=100, impor_apli_sss=99.5, importe_transferido=99.5),
        dict(cuil="20000000019", importe_subsidiado=100, importe_solicitado=150, impor_apli_sss=50, importe_transferido=50,
             fdo_ppio_ingre_cta_disca=100),
        dict(cuil="20000000027", importe_subsidiado=10, importe_solicitado=150, retencion_ganancias=50),
        dict(cuil="20000000035", importe_subsidiado=500, importe_solicitado=100),
    ])
    tipos = [tipo_correccion(g) for g in proponer(ls).values()]
    assert tipos == [TIPO_DE_MAS, TIPO_CENTAVOS, TIPO_DE_MENOS, TIPO_RETENCIONES, TIPO_NO_BALANCEA]
