"""
Núcleo del balanceo (sin dependencias de interfaz gráfica).

- Trabaja sobre la PRIMERA hoja del Excel.
- Solo escribe en 3 columnas objetivo: impor_apli_sss, importe_transferido, fdo_ppio_ingre_cta_disca.
- Agrega una hoja LOG con detalle por línea.
- Lee valores desde un workbook data_only=True (para tomar el valor real de CONCATENAR si es fórmula)
  y escribe en otro workbook (para preservar formatos y crear columnas faltantes sin afectar lectura).
"""

import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .columns import find_columns
from .parsing import to_float

LogFn = Callable[[str], None]
ProgFn = Callable[[int, int], None]

OUTPUT_SUFFIX = "_balidaf.xlsx"
LOG_SHEET_NAME = "LOG"


def _noop_log(_msg: str) -> None:
    pass


def _noop_prog(_cur: int, _tot: int) -> None:
    pass


# ====== Núcleo: lee de ws_read (data_only) y escribe en ws_write ======
def balancear_y_log(ws_read, ws_write, mapping_write: Dict[str, int], log: LogFn, prog: ProgFn) -> List[List[Any]]:
    r1, rN = 2, ws_write.max_row  # asumimos mismas filas
    # Construir orden y grupos leyendo la clave desde ws_read (valor calculado si era fórmula)
    order_keys: List[Tuple[int, str]] = []
    for r in range(r1, rN + 1):
        key_val = ws_read.cell(row=r, column=mapping_write["key"]).value
        key_str = "" if key_val is None else str(key_val)
        order_keys.append((r, key_str))

    groups = OrderedDict()
    for r, k in order_keys:
        groups.setdefault(k, []).append(r)

    total_groups = len(groups)
    gi = 0

    # Subsidio total por grupo (leer de ws_read)
    subsidio_por_grupo: Dict[str, float] = {}
    subs_col = mapping_write["subsidiado"]
    for k, rows in groups.items():
        s_total = 0.0
        for r in rows:
            s_total += to_float(ws_read.cell(row=r, column=subs_col).value)
        subsidio_por_grupo[k] = round(s_total, 2)

    # Columnas de escritura (ws_write)
    apli_c = mapping_write["apli_sss"]; apli_letter = get_column_letter(apli_c)
    tran_c = mapping_write["transferido"]; tran_letter = get_column_letter(tran_c)
    fdo_c = mapping_write["fdo_ppio"]; fdo_letter = get_column_letter(fdo_c)

    # LOG rows (en memoria)
    log_rows: List[List[Any]] = []
    log_rows.append([
        "socio", "subsidio_total_grupo", "subsidio_rest_antes", "subsidio_rest_despues",
        "solicitado", "ret_ganancias", "ret_iibb", "ret_otras", "ret_total",
        f"{apli_letter} (impor_apli_sss)",
        f"{tran_letter} (importe_transferido)",
        f"{fdo_letter} (fdo_ppio_ingre_cta_disca)"
    ])

    for k, rows in groups.items():
        gi += 1
        subsidio_rest = subsidio_por_grupo.get(k, 0.0)
        aplicado_total = 0.0

        # Log de grupo: mostrar valor real de la clave (no fórmula)
        log(f"[SOCIO {k}] Subsidio total: {subsidio_rest:.2f} | filas: {len(rows)}")

        for r in rows:
            rg = to_float(ws_read.cell(row=r, column=mapping_write["ret_gcias"]).value)
            ri = to_float(ws_read.cell(row=r, column=mapping_write["ret_iibb"]).value)
            ro = to_float(ws_read.cell(row=r, column=mapping_write["ret_otras"]).value)
            solicitado = round(to_float(ws_read.cell(row=r, column=mapping_write["solicitado"]).value), 2)

            ret_total = round(rg + ri + ro, 2)
            imp_apli_bruto = solicitado
            subsidio_rest_antes = subsidio_rest

            if subsidio_rest <= 0:
                imp_apli_final = 0.0
            else:
                imp_apli_final = imp_apli_bruto if imp_apli_bruto <= subsidio_rest else subsidio_rest

            imp_trans_final = round(imp_apli_final - ret_total, 2)
            diff = round((imp_trans_final + ret_total) - solicitado, 2)
            fdo_val = abs(diff)

            # Escribir solo en ws_write (preservando el resto)
            ws_write.cell(row=r, column=apli_c).value = round(imp_apli_final, 2)
            ws_write.cell(row=r, column=tran_c).value = round(imp_trans_final, 2)
            ws_write.cell(row=r, column=fdo_c).value = round(fdo_val, 2)

            subsidio_rest = round(subsidio_rest - imp_apli_final, 2)
            aplicado_total = round(aplicado_total + imp_apli_final, 2)

            log_rows.append([
                k, subsidio_por_grupo[k], subsidio_rest_antes, subsidio_rest,
                solicitado, rg, ri, ro, ret_total,
                round(imp_apli_final, 2),
                round(imp_trans_final, 2),
                round(fdo_val, 2)
            ])

        log(f"  → Aplicado: {aplicado_total:.2f} | Remanente: {round(subsidio_rest, 2):.2f}")
        prog(gi, total_groups)

    return log_rows


def write_log_sheet(wb, log_rows: List[List[Any]], sheet_name: str = LOG_SHEET_NAME) -> None:
    if sheet_name in wb.sheetnames:
        wb.remove(wb[sheet_name])
    ws = wb.create_sheet(title=sheet_name)
    for ri, row in enumerate(log_rows, start=1):
        for ci, val in enumerate(row, start=1):
            ws.cell(row=ri, column=ci, value=val)


def output_path_for(input_path: str) -> str:
    """Ruta de salida: mismo nombre con sufijo ``_balidaf.xlsx``."""
    return os.path.splitext(input_path)[0] + OUTPUT_SUFFIX


@dataclass
class ProcessResult:
    sheet_used: str
    out_path: str


def process_file(path: str, log: Optional[LogFn] = None, prog: Optional[ProgFn] = None,
                 out_path: Optional[str] = None) -> ProcessResult:
    """Procesa un Excel completo y guarda el resultado. Usado por la GUI y por la línea de comandos."""
    log = log or _noop_log
    prog = prog or _noop_prog

    # Workbook para LECTURA de valores (incluye resultados de fórmula si existen)
    wb_read = load_workbook(path, data_only=True)
    ws_read = wb_read.worksheets[0]
    sheet_used = ws_read.title

    # Workbook para ESCRITURA (preserva formatos y permite crear columnas)
    wb_write = load_workbook(path, data_only=False)
    ws_write = wb_write.worksheets[0]

    # Detectar/crear columnas en el workbook de ESCRITURA
    mapping_write = find_columns(ws_write)

    # Proceso con lectura desde ws_read y escritura en ws_write
    log_rows = balancear_y_log(ws_read, ws_write, mapping_write, log, prog)

    # Crear hoja LOG en wb_write
    write_log_sheet(wb_write, log_rows, sheet_name=LOG_SHEET_NAME)

    out_path = out_path or output_path_for(path)
    wb_write.save(out_path)
    return ProcessResult(sheet_used=sheet_used, out_path=out_path)
