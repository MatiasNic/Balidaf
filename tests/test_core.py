"""Pruebas del balanceo y de paridad con el programa original (legacy/Balidaf.py)."""

import importlib.util
import os

import pytest
from openpyxl import Workbook, load_workbook

from balidaf.core import output_path_for, process_file
from generar_ejemplo import HEADERS, build_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_legacy():
    spec = importlib.util.spec_from_file_location("balidaf_legacy", os.path.join(ROOT, "legacy", "Balidaf.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_legacy(path):
    """Replica exactamente el flujo de worker() del programa original."""
    legacy = _load_legacy()
    wb_read = load_workbook(path, data_only=True)
    wb_write = load_workbook(path, data_only=False)
    ws_write = wb_write.worksheets[0]
    mapping = legacy.find_columns(ws_write)
    rows = legacy.balancear_y_log(wb_read.worksheets[0], ws_write, mapping, lambda s: None, lambda c, t: None)
    legacy.write_log_sheet(wb_write, rows, sheet_name="LOG")
    out = os.path.splitext(path)[0] + "_legacy.xlsx"
    wb_write.save(out)
    return out


def _values(path):
    wb = load_workbook(path)
    return {name: [list(r) for r in wb[name].iter_rows(values_only=True)] for name in wb.sheetnames}


def test_caso_simple(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(HEADERS)
    # Socio A: subsidio total 1000, dos líneas de 700 → la 2da solo recibe 300
    ws.append(["A", 600, 10, 5, 0, 700, None, None, None])
    ws.append(["A", 400, 0, 0, 0, 700, None, None, None])
    # Socio B: subsidio 0 → no se aplica nada
    ws.append(["B", 0, 1, 1, 1, 100, None, None, None])
    src = tmp_path / "in.xlsx"
    wb.save(src)

    res = process_file(str(src))
    assert res.out_path == output_path_for(str(src))
    out = load_workbook(res.out_path)
    data = [list(r) for r in out.worksheets[0].iter_rows(min_row=2, values_only=True)]
    # (apli, transferido, fdo)
    assert [r[6:9] for r in data] == [
        [700, 685, 0],
        [300, 300, 400],
        [0, -3, 100],
    ]
    assert "LOG" in out.sheetnames
    assert out["LOG"].max_row == 4


@pytest.mark.parametrize("socios,seed", [(5, 1), (50, 2), (200, 3)])
def test_paridad_con_original(tmp_path, socios, seed):
    src = str(tmp_path / f"ej_{seed}.xlsx")
    build_workbook(socios, seed).save(src)

    nuevo = process_file(src).out_path
    original = _run_legacy(src)

    assert _values(nuevo) == _values(original)
