"""
Cruce de la devolución de la SSS (TXT _ERR y _OK) con el Excel analizado.

NO corrige nada por sí solo: para cada registro rechazado muestra
  - los errores que informó la SSS y qué significan (Anexo IV),
  - la corrección que propone Balidaf (antes → después) para que el usuario decida aplicarla,
  - o si requiere corrección manual / de Sistemas.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .balanceo import APLICADA, PENDIENTE, Grupo
from .montos import fmt
from .schema import CODIGOS, COL, MANUAL, SISTEMAS
from .sss_txt import ArchivoTxt
from .validacion import ERROR

PROPUESTA = "Corrección propuesta (sin aplicar)"
APLICADA_TXT = "Corrección aplicada"
YA_CUMPLE = "Ya cumple las reglas en el Excel"
PENDIENTE_MANUAL = "Requiere corrección manual"
PENDIENTE_SISTEMAS = "Lo resuelve Sistemas / Presmed"
NO_ENCONTRADO = "No está en el Excel"

ESTADOS = [PROPUESTA, APLICADA_TXT, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS, YA_CUMPLE, NO_ENCONTRADO]
CAMPOS_RESUMEN = ["apli", "transferido", "fdo_ppio", "ret_gan", "ret_iibb", "ret_otras"]


@dataclass
class CruceLinea:
    clave: str
    cuil: str
    fila: int                       # fila en el Excel (0 si no está)
    codigos_sss: List[str]
    estado: str
    correccion: str = ""            # texto antes → después
    pendientes: List[str] = field(default_factory=list)   # errores que la corrección NO resuelve
    grupo: Optional[Grupo] = None


@dataclass
class ResultadoCruce:
    lineas: List[CruceLinea]
    por_codigo: Counter
    por_estado: Counter
    aceptadas_que_cambian: int = 0  # líneas aceptadas cuyo grupo tiene corrección
    total_ok: int = 0
    total_err: int = 0

    def grupos(self, estados=(PROPUESTA,)) -> List[Grupo]:
        vistos, res = set(), []
        for l in self.lineas:
            if l.grupo is not None and l.estado in estados and id(l.grupo) not in vistos:
                vistos.add(id(l.grupo))
                res.append(l.grupo)
        return res


def texto_correccion(ln) -> str:
    partes = []
    for k in CAMPOS_RESUMEN:
        o, n = ln.original[k], ln.propuesta.get(k, ln.original[k])
        if o != n:
            partes.append(f"{COL[k].titulo}: {fmt(o)} → {fmt(n)}")
    return " · ".join(partes)


def cruzar(resultado, err: Optional[ArchivoTxt], ok: Optional[ArchivoTxt] = None) -> ResultadoCruce:
    lote = resultado.lote
    por_clave = {ln.clave: ln for ln in lote.lineas}
    grupo_de: Dict[int, Grupo] = {ln.fila: g for g in resultado.grupos.values() for ln in g.lineas}
    err_propuesta: Dict[int, List[str]] = defaultdict(list)
    for h in resultado.propuesta:
        if h.nivel == ERROR and h.fila:
            err_propuesta[h.fila].append(h.codigo)
    err_actual = {h.fila for h in resultado.actual if h.nivel == ERROR and h.fila}

    lineas: List[CruceLinea] = []
    cnt_cod: Counter = Counter()
    for r in (err.registros if err else []):
        if not r.clave:
            continue
        cnt_cod.update(r.errores)
        ln = por_clave.get(r.clave)
        if ln is None:
            lineas.append(CruceLinea(r.clave, r.texto.get("cuil", ""), 0, r.errores, NO_ENCONTRADO))
            continue
        g = grupo_de.get(ln.fila)
        quien = {CODIGOS[c].resuelve if c in CODIGOS else MANUAL for c in r.errores}
        pendientes = sorted(set(err_propuesta.get(ln.fila, [])))
        if SISTEMAS in quien:
            estado = PENDIENTE_SISTEMAS
        elif pendientes:
            estado = PENDIENTE_MANUAL
        elif g is not None and g.estado == PENDIENTE:
            estado = PROPUESTA
        elif g is not None and g.estado == APLICADA:
            estado = APLICADA_TXT
        else:
            estado = YA_CUMPLE if ln.fila not in err_actual else PENDIENTE_MANUAL
        correccion = texto_correccion(ln) if g is not None and g.tiene_propuesta else ""
        if g is not None and g.tiene_propuesta and len(g.lineas) > 1:
            if correccion:
                correccion += f" · (grupo de {len(g.lineas)} líneas)"
            else:
                correccion = (f"Esta línea queda igual: se corrige otra línea de su grupo "
                              f"({len(g.lineas)} líneas). Doble clic para ver el grupo.")
        lineas.append(CruceLinea(r.clave, r.texto.get("cuil", ""), ln.fila, r.errores, estado,
                                 correccion, pendientes, g))

    aceptadas = 0
    if ok:
        for r in ok.registros:
            ln = por_clave.get(r.clave)
            g = grupo_de.get(ln.fila) if ln else None
            if g is not None and g.tiene_propuesta:
                aceptadas += 1

    return ResultadoCruce(lineas=lineas, por_codigo=cnt_cod, por_estado=Counter(l.estado for l in lineas),
                          aceptadas_que_cambian=aceptadas, total_ok=len(ok.registros) if ok else 0,
                          total_err=len(lineas))
