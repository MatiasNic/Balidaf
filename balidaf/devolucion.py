"""
Cruce de la devolución de la SSS (TXT _ERR y _OK) con el Excel.

Para cada registro rechazado indica:
  - qué errores informó la SSS y qué significan (Anexo IV),
  - si el balanceo de Balidaf lo deja corregido (se vuelve a validar la línea y su grupo),
  - o si requiere corrección manual / de Sistemas.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .excel_io import Lote
from .schema import CODIGOS, MANUAL, SISTEMAS
from .sss_txt import ArchivoTxt
from .validacion import ERROR, Hallazgo

CORREGIDO = "Corregido (ya cumple las reglas)"
PENDIENTE_MANUAL = "Requiere corrección manual"
PENDIENTE_SISTEMAS = "Lo resuelve Sistemas / Presmed"
NO_ENCONTRADO = "No está en el Excel"


@dataclass
class CruceLinea:
    clave: str
    cuil: str
    fila: int                       # fila en el Excel (0 si no está)
    codigos_sss: List[str]
    error_crudo: str
    estado: str
    errores_actuales: List[str] = field(default_factory=list)


@dataclass
class ResultadoCruce:
    lineas: List[CruceLinea]
    por_codigo: Counter
    por_estado: Counter
    aceptadas_modificadas: int = 0  # líneas que estaban OK y el balanceo modificó
    total_ok: int = 0
    total_err: int = 0


def cruzar(lote: Lote, hallazgos: List[Hallazgo], err: Optional[ArchivoTxt],
           ok: Optional[ArchivoTxt] = None) -> ResultadoCruce:
    por_clave = {ln.clave: ln for ln in lote.lineas}
    errores_por_fila: Dict[int, List[str]] = defaultdict(list)
    for h in hallazgos:
        if h.nivel == ERROR and h.fila:
            errores_por_fila[h.fila].append(h.codigo)

    lineas: List[CruceLinea] = []
    cnt_cod: Counter = Counter()
    for r in (err.registros if err else []):
        if not r.clave:
            continue
        cnt_cod.update(r.errores)
        ln = por_clave.get(r.clave)
        if ln is None:
            estado, actuales, fila = NO_ENCONTRADO, [], 0
        else:
            fila = ln.fila
            actuales = sorted(set(errores_por_fila.get(ln.fila, [])))
            quien = {CODIGOS[c].resuelve if c in CODIGOS else MANUAL for c in r.errores}
            if SISTEMAS in quien:
                estado = PENDIENTE_SISTEMAS
            elif actuales:
                estado = PENDIENTE_MANUAL
            else:
                estado = CORREGIDO
        lineas.append(CruceLinea(r.clave, r.texto.get("cuil", ""), fila, r.errores, r.error_crudo, estado, actuales))

    aceptadas_mod = 0
    if ok:
        for r in ok.registros:
            ln = por_clave.get(r.clave)
            if ln and ln.modificados():
                aceptadas_mod += 1

    return ResultadoCruce(lineas=lineas, por_codigo=cnt_cod, por_estado=Counter(l.estado for l in lineas),
                          aceptadas_modificadas=aceptadas_mod,
                          total_ok=len(ok.registros) if ok else 0,
                          total_err=len(lineas))
