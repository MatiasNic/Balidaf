import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from openpyxl import Workbook  # noqa: E402

from generar_ejemplo import ENCABEZADOS  # noqa: E402


def fila(**kw):
    """Fila del Excel con valores por defecto válidos (formato Presmed)."""
    base = {
        "cuit_CBU": "30526018156", "cbu": "9083016761318609139094", "opg_1": "2700000001",
        "fecha_transfer_1": "28/08/2026", "importe_transferido": 0, "retencion_ganancias": 0,
        "retencion_IIBB": 0, "otras_retnciones": 0, "impor_apli_sss": 0, "compro_tipo": "00",
        "compro_nro": "00000000", "clave_rendicion": "84600000001", "perio_prestac": "01/04/2026",
        "cuil": "20960308248", "cod_prestac": "090", "cuit_sss": "30694407044",
        "cbu_sss": "0110599520000002713698", "tipo_archi": "DS", "ofi": "Oficina Central", "expe": 1,
        "rnos": "999999", "periodo_presentacion": "202606", "importe_subsidiado": 0,
        "importe_solicitado": 0, "cuit_prestador": "30526018156", "punto_venta": "00000",
        "numero_envio_afip": "0116", "compro_total": 0,
    }
    base.update(kw)
    return [base.get(h) for h in ENCABEZADOS]


@pytest.fixture
def excel(tmp_path):
    """Crea un Excel con las filas indicadas y devuelve su ruta."""
    def _crear(filas, nombre="lote.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "Lote"
        ws.append(ENCABEZADOS)
        for i, f in enumerate(filas, start=1):
            if isinstance(f, dict):
                f.setdefault("clave_rendicion", f"846{i:08d}")
                f = fila(**f)
            ws.append(f)
        ruta = str(tmp_path / nombre)
        wb.save(ruta)
        return ruta
    return _crear
