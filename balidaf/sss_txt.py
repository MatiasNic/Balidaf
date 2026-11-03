"""
Lectura de los TXT del circuito de rendición:

- ``######-AAAAMM_DR.DEVOLUCION.txt``      (generado por Presmed y enviado a la SSS)
- ``######-AAAAMM_DR.DEVOLUCION_OK.txt``   (devolución SSS: registros aceptados)
- ``######-AAAAMM_DR.DEVOLUCION_ERR.txt``  (devolución SSS: registros rechazados + código de error)

Campos separados por "|" según el Anexo I (30 campos; el ERR agrega el 31: código de error).
Acepta los dos formatos de importe que aparecen: "1234.56    " (Presmed) y " 000001234,56" (SSS).
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .montos import a_centavos

CAMPOS = ["clave", "rnos", "tipo", "per_pres", "per_prest", "cuil", "cod", "subsidiado", "solicitado",
          "nro_envio", "cuit_cbu", "cbu", "opg_1", "opg_2", "fecha_1", "fecha_2", "cheque", "transferido",
          "ret_gan", "ret_iibb", "ret_otras", "apli", "fdo_ppio", "fdo_otras", "recibo", "revers",
          "devuelto", "saldo", "recup", "obs"]
CAMPOS_IMPORTE = {"subsidiado", "solicitado", "transferido", "ret_gan", "ret_iibb", "ret_otras", "apli",
                  "fdo_ppio", "fdo_otras", "revers", "devuelto", "saldo", "recup"}


@dataclass
class RegistroTxt:
    nro_linea: int
    texto: Dict[str, str] = field(default_factory=dict)
    monto: Dict[str, int] = field(default_factory=dict)
    errores: List[str] = field(default_factory=list)      # códigos ("623", "624", …)
    error_crudo: str = ""
    campos_leidos: int = 0

    @property
    def clave(self) -> str:
        return self.texto.get("clave", "")


@dataclass
class ArchivoTxt:
    ruta: str
    tipo: str                     # "ERR", "OK" o "ENVIO"
    registros: List[RegistroTxt]

    @property
    def nombre(self) -> str:
        return os.path.basename(self.ruta)

    def por_clave(self) -> Dict[str, RegistroTxt]:
        return {r.clave: r for r in self.registros if r.clave}


def tipo_por_nombre(ruta: str) -> str:
    n = os.path.basename(ruta).upper()
    if "_ERR" in n:
        return "ERR"
    if "_OK" in n:
        return "OK"
    return "ENVIO"


def _codigos(s: str) -> List[str]:
    return re.findall(r"\d{3}", s or "")


def leer_txt(ruta: str, tipo: Optional[str] = None) -> ArchivoTxt:
    tipo = tipo or tipo_por_nombre(ruta)
    registros: List[RegistroTxt] = []
    # Se separa sólo por "\n": un "\r" suelto dentro de un registro no debe partirlo en dos
    # (pasa en registros con error 699 "diseño de registro").
    with open(ruta, "rb") as f:
        contenido = f.read().decode("latin-1")
    for n, linea in enumerate(contenido.split("\n"), start=1):
        linea = linea.replace("\r", "")
        if not linea.strip():
            continue
        partes = linea.split("|")
        r = RegistroTxt(nro_linea=n, campos_leidos=len(partes))
        for nombre, valor in zip(CAMPOS, partes):
            if nombre in CAMPOS_IMPORTE:
                r.monto[nombre] = a_centavos(valor)[0]
            r.texto[nombre] = valor.strip()
        if tipo == "ERR":
            # el código está en el último campo no vacío después del 30
            extra = [p for p in partes[len(CAMPOS):] if p.strip()]
            r.error_crudo = extra[-1].strip() if extra else ""
            r.errores = _codigos(r.error_crudo)
        registros.append(r)
    return ArchivoTxt(ruta=ruta, tipo=tipo, registros=registros)
