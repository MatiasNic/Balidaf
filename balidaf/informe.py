"""
Informe de detalle en un Excel APARTE (no es el que se carga en Presmed).

Hojas: Resumen, Cambios (antes/después por línea), Validación (hallazgos) y, si se cargó,
Devolución SSS.
"""

import os
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from .balanceo import APLICADA, PENDIENTE
from .devolucion import ResultadoCruce
from .proceso import Resultado
from .schema import CODIGOS, COL

NEGRITA = Font(bold=True)
RELLENO = PatternFill("solid", fgColor="DDEBF7")


def _encabezado(ws, columnas):
    ws.append(columnas)
    for c in ws[1]:
        c.font = NEGRITA
        c.fill = RELLENO
    ws.freeze_panes = "A2"


def ruta_informe(ruta_excel: str) -> str:
    return os.path.splitext(ruta_excel)[0] + "_informe_balidaf.xlsx"


def exportar(r: Resultado, destino: str, cruce: Optional[ResultadoCruce] = None) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Balidaf – Informe de balanceo"]); ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    for k, v in [("Archivo", os.path.basename(r.lote.ruta)), ("Líneas", len(r.lote.lineas)),
                 ("Grupos", len(r.grupos)), ("Grupos corregidos (aplicados)", len(r.grupos_con(APLICADA))),
                 ("Grupos con corrección pendiente", len(r.grupos_con(PENDIENTE))),
                 ("Líneas modificadas", r.lineas_modificadas),
                 ("Líneas con retenciones reducidas", r.lineas_ret_reducidas),
                 ("Errores antes", r.errores_antes), ("Errores actuales", r.errores_actuales),
                 ("Advertencias", r.advertencias),
                 ("Listo para Presmed", "SÍ" if r.listo_para_presmed else "NO")]:
        ws.append([k, v])
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 40

    ws = wb.create_sheet("Cambios")
    campos = ["apli", "transferido", "fdo_ppio", "ret_gan", "ret_iibb", "ret_otras"]
    cols = ["Fila", "Clave", "CUIL", "Práctica", "Subsidiado", "Solicitado"]
    for k in campos:
        cols += [f"{COL[k].encabezado} antes", f"{COL[k].encabezado} después"]
    _encabezado(ws, cols)
    for ln in r.lote.lineas:
        if not ln.modificados():
            continue
        fila = [ln.fila, ln.clave, ln.cuil, ln.texto.get("cod", ""),
                ln.monto["subsidiado"] / 100, ln.monto["solicitado"] / 100]
        for k in campos:
            fila += [ln.original[k] / 100, ln.monto[k] / 100]
        ws.append(fila)

    ws = wb.create_sheet("Validación")
    _encabezado(ws, ["Fila", "Clave", "CUIL", "Código", "Nivel", "Campo", "Descripción", "Detalle"])
    for h in r.actual:
        ws.append([h.fila, h.clave, h.cuil, h.codigo, h.nivel, h.campo, h.descripcion, h.detalle])

    ws = wb.create_sheet("Validación original")
    _encabezado(ws, ["Fila", "Clave", "CUIL", "Código", "Nivel", "Campo", "Descripción", "Detalle"])
    for h in r.antes:
        ws.append([h.fila, h.clave, h.cuil, h.codigo, h.nivel, h.campo, h.descripcion, h.detalle])

    if cruce:
        ws = wb.create_sheet("Devolución SSS")
        _encabezado(ws, ["Clave", "CUIL", "Fila Excel", "Errores SSS", "Descripción", "Estado",
                         "Corrección", "Errores que quedan"])
        for c in cruce.lineas:
            ws.append([c.clave, c.cuil, c.fila or "", " ".join(c.codigos_sss),
                       " | ".join(CODIGOS[x].descripcion for x in c.codigos_sss if x in CODIGOS),
                       c.estado, c.correccion, " ".join(c.pendientes)])

    wb.save(destino)
    return destino
