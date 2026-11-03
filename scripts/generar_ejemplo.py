#!/usr/bin/env python3
"""Genera un Excel de ejemplo con el formato de Presmed y DATOS FICTICIOS, sin balancear.

    python scripts/generar_ejemplo.py                       → data/ejemplo.xlsx
    python scripts/generar_ejemplo.py ruta.xlsx --beneficiarios 500

Reproduce las situaciones reales encontradas en la rendición 202606:
  - aplicado = solicitado aunque el subsidio no alcance (error 624)
  - fondos propios vacíos (error 623)
  - líneas sin pago (todo en 0, CBU "0")
  - beneficiarios con varias líneas por práctica y retenciones altas
"""

import argparse
import os
import random

from openpyxl import Workbook

ENCABEZADOS = [
    "cuit_CBU", "cbu", "opg_1", "opg_2", "fecha_transfer_1", "fecha_transfer_2", "cheque",
    "importe_transferido", "retencion_ganancias", "retencion_IIBB", "otras_retnciones", "impor_apli_sss",
    "fdo_ppio_ingre_cta_disca", "fdo_ppio_otras_ctas", "nro_recibo", "reversion_import_trasl",
    "import_devuelto_cta_sss", "saldo_no_apli", "recup_fdos_ppios", "obs", "compro_tipo", "compro_nro",
    "clave_rendicion", "perio_prestac", "cuil", "cod_prestac", "cuit_sss", "cbu_sss", "tipo_archi", "ofi",
    "expe", "rnos", "periodo_presentacion", "importe_subsidiado", "importe_solicitado", "cuit_prestador",
    "punto_venta", "numero_envio_afip", "compro_total",
]


def cuit(rnd: random.Random, prefijo: str) -> str:
    while True:
        base = prefijo + "".join(str(rnd.randint(0, 9)) for _ in range(8))
        r = 11 - sum(int(a) * b for a, b in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
        if r == 10:
            continue
        return base + str(0 if r == 11 else r)


def cbu(rnd: random.Random) -> str:
    b1 = "".join(str(rnd.randint(0, 9)) for _ in range(7))
    d1 = (10 - sum(int(a) * b for a, b in zip(b1, (7, 1, 3, 9, 7, 1, 3))) % 10) % 10
    b2 = "".join(str(rnd.randint(0, 9)) for _ in range(13))
    d2 = (10 - sum(int(a) * b for a, b in zip(b2, (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3))) % 10) % 10
    return f"{b1}{d1}{b2}{d2}"


def construir(beneficiarios: int = 30, seed: int = 42) -> Workbook:
    rnd = random.Random(seed)
    wb = Workbook()
    ws = wb.active
    ws.title = "Lote"
    ws.append(ENCABEZADOS)
    clave = 84600000000
    for _ in range(beneficiarios):
        cuil_b = cuit(rnd, rnd.choice(["20", "27", "23"]))
        for cod in rnd.sample(["090", "096", "086", "001"], rnd.randint(1, 2)):
            n = rnd.choice([1, 1, 1, 2, 2, 3])
            sols = [round(rnd.uniform(50_000, 900_000), 2) for _ in range(n)]
            caso = rnd.random()
            if caso < 0.45:
                subsidio = round(sum(sols), 2)                       # ya cierra
            elif caso < 0.85:
                subsidio = round(sum(sols) * rnd.uniform(0.3, 0.95), 2)  # subsidio menor → hay que balancear
            else:
                subsidio = 0.0 if n == 1 else round(sols[0] * 0.2, 2)    # subsidio muy chico
            sin_pago = rnd.random() < 0.05
            if sin_pago:
                subsidio = 0.0
            prest = cuit(rnd, rnd.choice(["30", "27", "20"]))
            for i, sol in enumerate(sols):
                clave += 1
                if sin_pago:
                    sol = 0.0
                gan = round(sol * rnd.choice([0, 0, 0.02, 0.33]), 2)
                iibb = round(sol * rnd.choice([0, 0, 0.0125]), 2)
                transf = round(sol - gan - iibb, 2)
                ws.append([
                    "00020010500" if sin_pago else prest, "0" if sin_pago else cbu(rnd),
                    0 if sin_pago else str(2700000000 + clave % 1000000), None,
                    0 if sin_pago else "28/08/2026", None, None,
                    transf, gan, iibb, 0, sol,
                    None, None, None, None, None, None, None, None, "00", "00000000",
                    str(clave), f"01/{rnd.choice(['04', '05', '06'])}/2026" if i == 0 else None, cuil_b, cod,
                    "30694407044", "0110599520000002713698", "DS", "Oficina Central", rnd.randint(5_900_000, 5_999_999),
                    "999999", "202606", subsidio if i == 0 else 0, sol, prest, "00000", "0116", sol,
                ])
    # el período de prestación es el mismo para todas las líneas del grupo
    ultimo = None
    for row in ws.iter_rows(min_row=2):
        c = row[ENCABEZADOS.index("perio_prestac")]
        if c.value is None:
            c.value = ultimo
        ultimo = c.value
    return wb


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida", nargs="?", default=os.path.join("data", "ejemplo.xlsx"))
    p.add_argument("--beneficiarios", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    construir(a.beneficiarios, a.seed).save(a.salida)
    print(f"Generado: {a.salida}")


if __name__ == "__main__":
    main()
