"""Proceso completo, Excel de salida limpio, TXT de la SSS y cruce con la devolución."""

from openpyxl import load_workbook

from balidaf.devolucion import CORREGIDO, PENDIENTE_SISTEMAS, cruzar
from balidaf.informe import exportar
from balidaf.proceso import guardar, procesar
from balidaf.sss_txt import leer_txt
from generar_ejemplo import ENCABEZADOS, construir

EDITABLES = {"importe_transferido", "retencion_ganancias", "retencion_IIBB", "otras_retnciones",
             "impor_apli_sss", "fdo_ppio_ingre_cta_disca"}


def test_proceso_completo_y_excel_limpio(tmp_path):
    ruta = str(tmp_path / "lote.xlsx")
    construir(60, 9).save(ruta)
    r = procesar(ruta)
    assert r.errores_antes > 0
    assert r.listo_para_presmed
    destino = guardar(r)
    assert destino.endswith("_balidaf.xlsx")

    a = load_workbook(ruta)
    b = load_workbook(destino)
    assert b.sheetnames == a.sheetnames                 # no agrega hojas
    wa, wb = a.worksheets[0], b.worksheets[0]
    assert (wa.max_row, wa.max_column) == (wb.max_row, wb.max_column)
    for ra, rb in zip(wa.iter_rows(), wb.iter_rows()):
        for ca, cb in zip(ra, rb):
            h = ENCABEZADOS[ca.column - 1]
            if h not in EDITABLES:
                assert ca.value == cb.value, f"Se modificó {h} fila {ca.row}"   # campos 2–9 intactos
            assert cb.number_format == ca.number_format
            assert cb.fill.fgColor.rgb == ca.fill.fgColor.rgb
            assert not (isinstance(cb.value, str) and cb.value.startswith("="))

    # al releer la salida, cumple todas las reglas
    r2 = procesar(destino)
    assert r2.errores_antes == 0
    assert r2.lineas_modificadas == 0

    inf = exportar(r, str(tmp_path / "informe.xlsx"))
    assert {"Resumen", "Cambios", "Validación"} <= set(load_workbook(inf).sheetnames)


def _linea_txt(clave, cuil, cod, sub, sol, errores="", formato_sss=True):
    if formato_sss:
        imp = lambda v: f" {v:013.2f}".replace(".", ",")
    else:
        imp = lambda v: f"{v:.2f}".ljust(13)
    campos = [clave, "999999", "DS", "202606", "202604", cuil, cod, imp(sub), imp(sol), "0116",
              "30526018156", "9083016761318609139094", "2700000001", "", "28/08/2026", "", "", imp(sol),
              imp(0), imp(0), imp(0), imp(sol), imp(0)] + [""] * 6 + ["."]
    return "|".join(campos) + ("|" + errores if errores else "")


def test_leer_txt_ambos_formatos(tmp_path):
    p = tmp_path / "999999-202606_DR.DEVOLUCION_ERR.txt"
    p.write_bytes((_linea_txt("84600000001", "20960308248", "090", 1234.5, 99.99, "-623-624") + "\n" +
                   _linea_txt("84600000002", "20960308248", "090", 0, 10, "", False) + "\r|-699{}\r\n").encode())
    a = leer_txt(str(p))
    assert a.tipo == "ERR"
    assert a.registros[0].monto["subsidiado"] == 123450
    assert a.registros[0].errores == ["623", "624"]
    assert a.registros[1].monto["solicitado"] == 1000
    assert a.registros[1].errores == ["699"]          # "\r" dentro del registro no lo parte


def test_cruce_con_devolucion(tmp_path, excel):
    ruta = excel([
        dict(clave_rendicion="84600000001", importe_subsidiado=100, importe_solicitado=150,
             impor_apli_sss=150, importe_transferido=150),
        dict(clave_rendicion="84600000002", cod_prestac="096", importe_subsidiado=50, importe_solicitado=50,
             impor_apli_sss=50, importe_transferido=50, fdo_ppio_ingre_cta_disca=0),
    ])
    r = procesar(ruta)
    p = tmp_path / "999999-202606_DR.DEVOLUCION_ERR.txt"
    p.write_text(_linea_txt("84600000001", "20960308248", "090", 100, 150, "-623-624") + "\n" +
                 _linea_txt("84600000002", "20960308248", "096", 50, 50, "-699{}") + "\n")
    c = cruzar(r.lote, r.despues, leer_txt(str(p)))
    estados = {l.clave: l.estado for l in c.lineas}
    assert estados == {"84600000001": CORREGIDO, "84600000002": PENDIENTE_SISTEMAS}
    assert c.por_codigo == {"623": 1, "624": 1, "699": 1}
