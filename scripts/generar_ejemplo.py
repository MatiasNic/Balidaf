#!/usr/bin/env python3
"""Genera un Excel de ejemplo con datos ficticios para probar Balidaf.

    python scripts/generar_ejemplo.py                 → data/ejemplo.xlsx
    python scripts/generar_ejemplo.py ruta.xlsx --socios 500
"""

import argparse
import os
import random

from openpyxl import Workbook

HEADERS = [
    "CONCATENAR", "IMPORTE_SUBSIDIADO", "RETENCION_GANANCIAS", "RETENCION_IIBB",
    "OTRAS_RETENCIONES", "IMPORTE_SOLICITADO",
    "impor_apli_sss", "importe_transferido", "fdo_ppio_ingre_cta_disca",
]


def build_workbook(socios: int = 20, seed: int = 42) -> Workbook:
    rnd = random.Random(seed)
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(HEADERS)
    for s in range(1, socios + 1):
        key = f"SOC{s:05d}"
        for _ in range(rnd.randint(1, 4)):
            solicitado = round(rnd.uniform(1_000, 50_000), 2)
            subsidiado = round(solicitado * rnd.uniform(0.3, 1.2), 2)
            ws.append([
                key, subsidiado,
                round(solicitado * 0.02, 2), round(solicitado * 0.01, 2), round(rnd.choice([0, 0, 150.5]), 2),
                solicitado, None, None, None,
            ])
    return wb


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("salida", nargs="?", default=os.path.join("data", "ejemplo.xlsx"))
    p.add_argument("--socios", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    build_workbook(a.socios, a.seed).save(a.salida)
    print(f"Generado: {a.salida}")


if __name__ == "__main__":
    main()
