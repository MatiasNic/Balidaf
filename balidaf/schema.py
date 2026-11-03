"""
Definiciones fijas: columnas del Excel de Presmed y códigos de rechazo de la SSS.

Fuente: "Mecanismo Integración – Rendición – Especificaciones técnicas para envío de datos"
(Superintendencia de Servicios de Salud), Anexos I, III y IV.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------------------
# Columnas del Excel
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Columna:
    clave: str                 # nombre interno
    encabezado: str            # encabezado en el Excel de Presmed
    titulo: str                # nombre legible (instructivo SSS)
    alias: Tuple[str, ...] = ()
    obligatoria: bool = False
    importe: bool = False
    editable: bool = False     # ¿Balidaf puede modificarla?
    campo_sss: Optional[int] = None  # nº de campo en el diseño de registro DR.DEVOLUCION


COLUMNAS: List[Columna] = [
    Columna("clave", "clave_rendicion", "Clave rendición", ("CLAVE",), True, campo_sss=1),
    Columna("rnos", "rnos", "RNOS", (), False, campo_sss=2),
    Columna("tipo", "tipo_archi", "Tipo archivo", ("TIPO_ARCHIVO",), False, campo_sss=3),
    Columna("per_pres", "periodo_presentacion", "Período presentación", ("PERIODO_PRES",), True, campo_sss=4),
    Columna("per_prest", "perio_prestac", "Período prestación", ("PERIODO_PRESTACION",), True, campo_sss=5),
    Columna("cuil", "cuil", "CUIL", ("CUIL_BENEFICIARIO",), True, campo_sss=6),
    Columna("cod", "cod_prestac", "Código práctica", ("CODIGO_PRACTICA", "COD_PRACTICA"), True, campo_sss=7),
    Columna("subsidiado", "importe_subsidiado", "Importe subsidiado", ("IMPORTEDESUBSIDIO", "IMPSUBSIDIADO"), True, True, campo_sss=8),
    Columna("solicitado", "importe_solicitado", "Importe solicitado", ("IMP_SOLICITADO",), True, True, campo_sss=9),
    Columna("nro_envio", "numero_envio_afip", "Nro envío AFIP", ("NRO_ENVIO_AFIP",), False, campo_sss=10),
    Columna("cuit_cbu", "cuit_CBU", "CUIT del CBU", ("CUIT_DEL_CBU",), False, campo_sss=11),
    Columna("cbu", "cbu", "CBU", (), False, campo_sss=12),
    Columna("opg_1", "opg_1", "Orden de pago I", ("ORDEN_PAGO_1",), False, campo_sss=13),
    Columna("opg_2", "opg_2", "Orden de pago II", ("ORDEN_PAGO_2",), False, campo_sss=14),
    Columna("fecha_1", "fecha_transfer_1", "Fecha transferencia I", ("FECHA_TRANSFERENCIA_1",), False, campo_sss=15),
    Columna("fecha_2", "fecha_transfer_2", "Fecha transferencia II", ("FECHA_TRANSFERENCIA_2",), False, campo_sss=16),
    Columna("cheque", "cheque", "Cheque", (), False, campo_sss=17),
    Columna("transferido", "importe_transferido", "Importe transferido", ("IMP_TRANSFERIDO", "IMPOR_TRANSFERIDO"), True, True, True, campo_sss=18),
    Columna("ret_gan", "retencion_ganancias", "Retención ganancias", ("RET_GANANCIAS",), True, True, True, campo_sss=19),
    Columna("ret_iibb", "retencion_IIBB", "Retención IIBB", ("RET_IIBB", "RETENCION_INGRESOS_BRUTOS"), True, True, True, campo_sss=20),
    Columna("ret_otras", "otras_retnciones", "Otras retenciones", ("OTRAS_RETENCIONES", "OTRAS_RET"), True, True, True, campo_sss=21),
    Columna("apli", "impor_apli_sss", "Importe aplicado SSS", ("IMPORTE_APLICADO_SSS", "IMP_APLI_SSS"), True, True, True, campo_sss=22),
    Columna("fdo_ppio", "fdo_ppio_ingre_cta_disca", "Fondos propios cta. discapacidad", ("FDO_PPIO_INGRESOS_CTA_DISCA",), True, True, True, campo_sss=23),
    Columna("fdo_otras", "fdo_ppio_otras_ctas", "Fondos propios otra cuenta", ("FONDOS_PROPIOS_OTRA_CUENTA",), False, True, campo_sss=24),
    Columna("recibo", "nro_recibo", "Nro recibo", (), False, campo_sss=25),
    Columna("revers", "reversion_import_trasl", "Importe trasladado (reversión)", ("IMPORTE_TRASLADADO",), False, True, campo_sss=26),
    Columna("devuelto", "import_devuelto_cta_sss", "Importe devuelto cuenta SSS", ("IMPORTE_DEVUELTO_CUENTA_SSS",), False, True, campo_sss=27),
    Columna("saldo", "saldo_no_apli", "Saldo no aplicado", ("SALDO_NO_APLICADO",), False, True, campo_sss=28),
    Columna("recup", "recup_fdos_ppios", "Recupero fondos propios", ("RECUPERO_FONDOS_PROPIOS",), False, True, campo_sss=29),
    Columna("obs", "obs", "Observaciones", ("OBSERVACIONES",), False, campo_sss=30),
]

COL: Dict[str, Columna] = {c.clave: c for c in COLUMNAS}
IMPORTES: List[str] = [c.clave for c in COLUMNAS if c.importe]
EDITABLES: List[str] = [c.clave for c in COLUMNAS if c.editable]
OBLIGATORIAS: List[str] = [c.clave for c in COLUMNAS if c.obligatoria]

# Importes que, además del aplicado, "consumen" subsidio (regla 624) y solicitado (regla 623).
OTROS_DESTINOS_SUBSIDIO = ["revers", "devuelto", "saldo", "recup"]
OTROS_DESTINOS_SOLICITADO = ["fdo_otras", "revers", "devuelto", "saldo", "recup"]
RETENCIONES = ["ret_gan", "ret_iibb", "ret_otras"]

# Datos fijos de la SSS (Anexo III, regla 621)
CUIT_SSS = "30694407044"
CBU_SSS = "0110599520000002713698"
PREFIJOS_CUIT = ("20", "23", "24", "27", "30", "33", "34")
TIPOS_ARCHIVO = ("DS", "DB", "DC")
MAX_IMPORTE_CENTAVOS = 10 ** 12 - 1   # 10 enteros + 2 decimales → 9.999.999.999,99


# --------------------------------------------------------------------------------------
# Códigos de rechazo (Anexo IV) + códigos internos de Balidaf
# --------------------------------------------------------------------------------------
# Quién lo resuelve
BALANCEO = "Balanceo"       # lo corrige Balidaf automáticamente
MANUAL = "Manual"           # requiere corregir datos en el Excel
SISTEMAS = "Sistemas"       # formato del archivo / envío (Presmed / Sistemas)


@dataclass(frozen=True)
class CodigoError:
    codigo: str
    campo: str
    descripcion: str
    accion: str
    resuelve: str
    validable: bool = True     # ¿se puede validar sólo con el Excel?


CODIGOS: Dict[str, CodigoError] = {c.codigo: c for c in [
    CodigoError("600", "RNOS", "El RNOS informado no coincide con el RNOS detallado en el nombre del archivo",
                "Verificar código del RNOS informado", SISTEMAS),
    CodigoError("601", "PERIODO PRESENTACION", "El campo PERIODO PRESENTACION debe ser menor o igual al informado en el nombre del archivo",
                "Verificar el PERIODO PRESENTACION informado", SISTEMAS),
    CodigoError("602", "CAMPOS 2 a 9", "Los datos de los campos 2 al 9 deben ser iguales a los del archivo DR.ENVIO",
                "Verificar los datos enviados en los campos 2 al 9 (Balidaf nunca los modifica)", SISTEMAS, False),
    CodigoError("603", "CLAVE RENDICION", "La CLAVE RENDICION informada en DR.DEVOLUCION es inexistente en DR.ENVIO",
                "Verificar la CLAVE RENDICION enviada", SISTEMAS, False),
    CodigoError("604", "CLAVE RENDICION", "La CLAVE RENDICION existente en DR.ENVIO no fue enviada en DR.DEVOLUCION",
                "Verificar la CLAVE RENDICION faltante e informarla", SISTEMAS, False),
    CodigoError("605", "CLAVE RENDICION", "La CLAVE RENDICION debe poseer 11 dígitos",
                "Verificar la CLAVE RENDICION informada", MANUAL),
    CodigoError("606", "CLAVE RENDICION", "La CLAVE RENDICION se encuentra duplicada",
                "Verificar la CLAVE RENDICION informada", MANUAL),
    CodigoError("607", "NRO ENVIO AFIP", "El NRO ENVIO AFIP debe coincidir con el informado en DR.ENVIO.CONTROL",
                "Verificar el NRO ENVIO AFIP informado", SISTEMAS),
    CodigoError("609", "TIPO ARCHIVO", "El TIPO ARCHIVO debe ser DS, DB o DC",
                "Verificar la sigla informada en TIPO ARCHIVO", MANUAL),
    CodigoError("610", "IMPORTES", "Debe ser numérico de 10,2 posiciones",
                "Verificar el importe informado", MANUAL),
    CodigoError("611", "CUIT DEL CBU", "Debe ser numérico de 11 posiciones",
                "Verificar el CUIT DEL CBU informado", MANUAL),
    CodigoError("612", "CUIT DEL CBU", "El prefijo debe ser 20, 23, 24, 27, 30, 33 o 34",
                "Verificar el prefijo informado", MANUAL),
    CodigoError("613", "CUIT DEL CBU", "El dígito verificador es incorrecto",
                "Verificar el dígito verificador informado", MANUAL),
    CodigoError("614", "CBU", "Debe ser numérico de 22 posiciones o nulo",
                "Verificar el CBU informado", MANUAL),
    CodigoError("615", "ORDEN DE PAGO I / II", "Debe ser de hasta 20 caracteres",
                "Verificar los datos informados", MANUAL),
    CodigoError("616", "FECHA TRANSFERENCIA I / II", "Debe ser formato DATE (DD/MM/AAAA) o nulo",
                "Verificar fecha informada", MANUAL),
    CodigoError("617", "FECHA TRANSFERENCIA I / II", "Debe ser mayor o igual al PERIODO PRESENTACION",
                "Verificar fecha informada", MANUAL),
    CodigoError("618", "CHEQUE", "Debe ser numérico de hasta 10 posiciones o nulo",
                "Verificar los datos informados", MANUAL),
    CodigoError("619", "NRO RECIBO", "Debe ser numérico de hasta 8 posiciones o nulo",
                "Verificar los datos informados", MANUAL),
    CodigoError("621", "IMPORTE DEVUELTO CTA SSS", "Si el IMPORTE DEVUELTO es mayor a cero, CBU y CUIT deben ser los de la SSSALUD",
                "Verificar los datos informados", MANUAL),
    CodigoError("622", "IMPORTE APLICADO SSS", "TRANSFERIDO + RET. GANANCIAS + RET. IIBB + OTRAS RET. no coincide con el IMPORTE APLICADO",
                "Verificar los importes informados", BALANCEO),
    CodigoError("623", "IMPORTE SOLICITADO", "FDO. PROPIOS + FDO. OTRAS CTAS + APLICADO + TRASLADADO + DEVUELTO + SALDO NO APLICADO + RECUPERO no coincide con el SOLICITADO",
                "Verificar los importes informados", BALANCEO),
    CodigoError("624", "IMPORTE SUBSIDIADO", "Para igual CUIL, PER. PRESENTACION, PER. PRESTACION y PRACTICA, APLICADO + TRASLADADO + DEVUELTO + SALDO NO APLICADO + RECUPERO no coincide con el SUBSIDIADO",
                "Verificar los importes informados", BALANCEO),
    CodigoError("625", "OBSERVACIONES", "Debe ser alfanumérico de hasta 150 posiciones o nulo",
                "Verificar cantidad de caracteres informados", MANUAL),
    CodigoError("699", "DISEÑO DE REGISTRO", "El diseño de registro no corresponde al indicado en el Anexo I",
                "Verificar diseño de registro enviado", SISTEMAS, False),
    # ---- Internos de Balidaf (no son de la SSS, pero anticipan rechazos) ----
    CodigoError("B01", "ESTRUCTURA", "Falta una columna en el Excel",
                "Agregar la columna con el encabezado indicado", MANUAL),
    CodigoError("B02", "IMPORTE SUBSIDIADO", "El subsidio del grupo supera lo que se puede aplicar (suma de solicitados): no se puede balancear",
                "Revisar importes subsidiado/solicitado del grupo", MANUAL),
    CodigoError("B03", "RETENCIONES", "Se redujeron retenciones porque el subsidio no alcanzaba para cubrirlas (transferido = 0)",
                "Informativo: verificar que corresponda", BALANCEO),
    CodigoError("B04", "CBU", "El dígito verificador del CBU es incorrecto",
                "Verificar el CBU informado", MANUAL),
    CodigoError("B05", "IMPORTES", "El importe tenía más de 2 decimales y se redondeó",
                "Informativo", BALANCEO),
    CodigoError("B06", "DATOS GENERALES", "Valor distinto al del resto del archivo (RNOS / período / nro envío)",
                "Verificar que todas las líneas correspondan a la misma presentación", MANUAL),
]}

CODIGOS_SSS = [c for c in CODIGOS if c[0].isdigit()]


def descripcion(codigo: str) -> str:
    c = CODIGOS.get(codigo)
    return c.descripcion if c else f"Código {codigo} (no figura en el instructivo)"
