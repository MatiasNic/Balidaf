"""Detección flexible de columnas por encabezado (fila 1 de la hoja)."""

from typing import Dict, List, Tuple

# Alias aceptados para cada columna canónica.
ALIASES: Dict[str, List[str]] = {
    "key": ["CONCATENAR", "SOCIO", "ID_SOCIO", "NRO_USUARIO", "USUARIO", "AFILIADO"],
    "subsidiado": ["IMPORTE_SUBSIDIADO", "IMPORTEDESUBSIDIO", "IMPSUBSIDIADO", "SUBSIDIADO"],
    "apli_sss": ["IMPOR_APLI_SSS", "IMPORTE_APLICADO_SSS", "IMP_APLI_SSS", "APLICADOSSS"],
    "ret_gcias": ["RETENCION_GANANCIAS", "RETENCIONGCIA", "RET_GANANCIAS", "GANANCIAS"],
    "ret_iibb": ["RETENCION_IIBB", "RETENCION_INGRESOS_BRUTOS", "RET_IIBB", "INGRESOSBRUTOS"],
    "ret_otras": ["OTRAS_RETNciones", "OTRAS_RETENCIONES", "OTRAS_RET", "OTRASRET", "OTRAS"],
    "solicitado": ["IMPORTE_SOLICITADO", "IMP_SOLICITADO", "IMPORTE_SOL", "SOLICITADO"],
    "transferido": ["IMPORTE_TRANSFERIDO", "IMP_TRANSFERIDO", "IMPOR_TRANSFERIDO", "TRANSFERIDO"],
    "fdo_ppio": [
        "FDO_PPIO_INGRE_CTA_DISCA", "FDO_PPIO_INGRE_CTA_DISCA ",
        "FDO_PPIO_INGRESOS_CTA_DISCA", "FONDO_PROPIO_INGRE_CTA_DISCA",
        "FDO_PPIO", "FONDO_PROPIO"
    ],
}

# Columnas de entrada obligatorias.
REQUIRED_INPUTS: List[str] = ["key", "subsidiado", "ret_gcias", "ret_iibb", "ret_otras", "solicitado"]

# Columnas de salida: (clave canónica, encabezado a crear si falta).
OUTPUT_COLUMNS: List[Tuple[str, str]] = [
    ("apli_sss", "impor_apli_sss"),
    ("transferido", "importe_transferido"),
    ("fdo_ppio", "fdo_ppio_ingre_cta_disca"),
]

# Nombres legibles para el mensaje de error de columnas faltantes.
DISPLAY_NAMES: Dict[str, str] = {
    "key": "CONCATENAR (clave de socio)",
    "subsidiado": "IMPORTE_SUBSIDIADO",
    "ret_gcias": "RETENCION_GANANCIAS",
    "ret_iibb": "RETENCION_IIBB",
    "ret_otras": "OTRAS_RETENCIONES",
    "solicitado": "IMPORTE_SOLICITADO",
}


def _norm(s) -> str:
    if s is None:
        return ""
    return str(s).strip().upper().replace(" ", "").replace("_", "").replace("-", "")


def _lookup_flexible(cols_norm_map: Dict[str, int], alias_list: List[str]) -> int:
    # Exacta
    for a in alias_list:
        an = _norm(a)
        if an in cols_norm_map:
            return cols_norm_map[an]
    # Contiene
    candidates: List[Tuple[int, int]] = []
    for a in alias_list:
        an = _norm(a)
        for k_norm, idx in cols_norm_map.items():
            if an and (an in k_norm or k_norm in an):
                candidates.append((max(len(an), len(k_norm)), idx))
    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]
    return 0


def find_columns(ws) -> Dict[str, int]:
    """Devuelve {clave_canónica: índice_columna}. Crea en ``ws`` las columnas de salida faltantes.

    Lanza ``ValueError`` si falta alguna columna de entrada obligatoria.
    """
    cols_norm_map: Dict[str, int] = {}
    max_col = ws.max_column
    for c in range(1, max_col + 1):
        header = ws.cell(row=1, column=c).value
        cols_norm_map[_norm(header)] = c

    mapping: Dict[str, int] = {}
    missing: List[str] = []

    # Requeridas de entrada
    for canon in REQUIRED_INPUTS:
        col_idx = _lookup_flexible(cols_norm_map, ALIASES[canon])
        if col_idx:
            mapping[canon] = col_idx
        else:
            missing.append(canon)

    # Salidas (crear si faltan en el workbook de ESCRITURA)
    for out_key, header_name in OUTPUT_COLUMNS:
        col_idx = _lookup_flexible(cols_norm_map, ALIASES[out_key])
        if not col_idx:
            max_col += 1
            col_idx = max_col
            ws.cell(row=1, column=col_idx, value=header_name)
            cols_norm_map[_norm(header_name)] = col_idx
        mapping[out_key] = col_idx

    if missing:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(DISPLAY_NAMES[m] for m in missing))
    return mapping
