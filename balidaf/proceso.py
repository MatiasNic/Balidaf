"""
Orquestación en dos tiempos: el programa PROPONE y el usuario DECIDE.

    analizar(ruta)              → lee, valida el original y calcula la corrección (sin aplicarla)
    resultado.aplicar(grupos)   → aplica la corrección a los grupos elegidos
    resultado.deshacer(grupos)  → vuelve esos grupos a los valores originales
    guardar(resultado)          → guarda el Excel con lo aplicado (sin formatos agregados)

``procesar(ruta)`` = analizar + aplicar todo (lo usa la línea de comandos).
"""

import os
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

from .balanceo import APLICADA, PENDIENTE, Grupo, aplicar, deshacer, proponer
from .excel_io import Lote, leer_excel
from .montos import fmt
from .validacion import ADVERTENCIA, ERROR, INFO, Hallazgo, contar, validar

LogFn = Callable[[str, str], None]                 # (nivel, mensaje)  nivel: info|ok|warn|error|titulo
ProgFn = Callable[[str, str, int, int], None]      # (paso, texto, actual, total)  total 0 = sin porcentaje

SUFIJO_SALIDA = "_balidaf.xlsx"

# Pasos del análisis (los muestra la barra de progreso)
PASOS = [
    ("leer", "Leer el Excel"),
    ("original", "Revisar reglas de la SSS en el original"),
    ("balancear", "Calcular la corrección (balanceo)"),
    ("propuesta", "Validar la corrección propuesta"),
]


def ruta_salida(ruta_excel: str) -> str:
    return os.path.splitext(ruta_excel)[0] + SUFIJO_SALIDA


@dataclass
class Resultado:
    lote: Lote
    grupos: dict
    antes: List[Hallazgo]                                      # Excel original
    propuesta: List[Hallazgo] = field(default_factory=list)    # si se aplicara TODA la corrección
    actual: List[Hallazgo] = field(default_factory=list)       # estado actual (lo aplicado)

    # ---- grupos
    @property
    def grupos_lista(self) -> List[Grupo]:
        return list(self.grupos.values())

    def grupos_con(self, estado: str) -> List[Grupo]:
        return [g for g in self.grupos.values() if g.estado == estado]

    def grupo_de_fila(self, fila: int) -> Optional[Grupo]:
        for g in self.grupos.values():
            if any(ln.fila == fila for ln in g.lineas):
                return g
        return None

    # ---- decisiones del usuario
    def aplicar(self, grupos: Iterable[Grupo], progreso=None) -> int:
        n = aplicar(grupos)
        self.revalidar(progreso)
        return n

    def deshacer(self, grupos: Iterable[Grupo], progreso=None) -> int:
        n = deshacer(grupos)
        self.revalidar(progreso)
        return n

    def revalidar(self, progreso=None) -> None:
        self.actual = (validar(self.lote.lineas, self.lote.faltantes, progreso)
                       + _hallazgos_balanceo(self.grupos, solo_aplicados=True))
        self.actual = _sin_duplicar_624(self.actual)

    # ---- contadores
    @staticmethod
    def _errores(hs: List[Hallazgo]) -> int:
        return sum(1 for h in hs if h.nivel == ERROR)

    @property
    def errores_antes(self) -> int:
        return self._errores(self.antes)

    @property
    def errores_actuales(self) -> int:
        return self._errores(self.actual)

    @property
    def errores_propuesta(self) -> int:
        return self._errores(self.propuesta)

    @property
    def advertencias(self) -> int:
        return sum(1 for h in self.actual if h.nivel == ADVERTENCIA)

    @property
    def listo_para_presmed(self) -> bool:
        return self.errores_actuales == 0

    @property
    def lineas_modificadas(self) -> int:
        return sum(1 for ln in self.lote.lineas if ln.modificados())

    @property
    def lineas_ret_reducidas(self) -> int:
        return sum(len(g.retenciones_reducidas) for g in self.grupos.values())

    def filas_con(self, nivel: str, hallazgos: Optional[List[Hallazgo]] = None) -> set:
        return {h.fila for h in (self.actual if hallazgos is None else hallazgos) if h.nivel == nivel and h.fila}


def _hallazgos_balanceo(grupos: dict, solo_aplicados: bool) -> List[Hallazgo]:
    """B02 (subsidio que no se puede aplicar) y B03 (retenciones reducidas)."""
    extra: List[Hallazgo] = []
    for g in grupos.values():
        if g.sobrante > 0:
            for ln in g.lineas:
                extra.append(Hallazgo("B02", ERROR, ln.fila, ln.clave, ln.cuil, "importe_subsidiado",
                                      f"Sobran {fmt(g.sobrante)} de subsidio sin poder aplicar en el grupo"))
        if solo_aplicados and g.estado != APLICADA:
            continue
        for fila in g.retenciones_reducidas:
            ln = next(l for l in g.lineas if l.fila == fila)
            nuevos = ln.monto if g.estado == APLICADA else ln.propuesta
            cambios = ", ".join(f"{k}: {fmt(ln.original[k])} → {fmt(nuevos[k])}"
                                for k in ("ret_gan", "ret_iibb", "ret_otras") if nuevos[k] != ln.original[k])
            extra.append(Hallazgo("B03", INFO, ln.fila, ln.clave, ln.cuil, "retenciones", cambios))
    return extra


def _sin_duplicar_624(hs: List[Hallazgo]) -> List[Hallazgo]:
    filas_b02 = {h.fila for h in hs if h.codigo == "B02"}
    return [h for h in hs if not (h.codigo == "624" and h.fila in filas_b02)]


def analizar(ruta: str, log: Optional[LogFn] = None, progreso: Optional[ProgFn] = None) -> Resultado:
    log = log or (lambda n, m: None)
    progreso = progreso or (lambda *a: None)

    def paso(pid):
        return lambda texto, cur, tot: progreso(pid, texto, cur, tot)

    log("titulo", f"Archivo: {os.path.basename(ruta)}")
    lote = leer_excel(ruta, paso("leer"))
    progreso("leer", "Excel leído", 1, 1)
    log("info", f"Hoja '{lote.hoja}': {len(lote.lineas)} líneas")
    for k in lote.faltantes:
        log("error", f"Falta la columna obligatoria: {k}")

    antes = validar(lote.lineas, lote.faltantes, paso("original"))
    _log_conteo(log, "Excel ORIGINAL", antes)
    if lote.faltantes:
        return Resultado(lote, {}, antes, antes, antes)

    grupos = proponer(lote.lineas, paso("balancear"))

    # Validación "como si se aplicara todo": se aplica, se valida y se vuelve atrás
    progreso("propuesta", "Validando la corrección propuesta…", 0, 0)
    pendientes = [g for g in grupos.values() if g.estado == PENDIENTE]
    aplicar(pendientes)
    propuesta = _sin_duplicar_624(validar(lote.lineas, lote.faltantes, paso("propuesta"))
                                  + _hallazgos_balanceo(grupos, solo_aplicados=False))
    deshacer(pendientes)

    r = Resultado(lote, grupos, antes, propuesta, list(antes))
    r.revalidar()
    log("titulo", "Corrección propuesta (todavía NO aplicada)")
    log("info", f"Grupos a corregir: {len(pendientes)} de {len(grupos)}")
    _log_conteo(log, "Si se aplica toda la corrección", propuesta)
    progreso("propuesta", "Análisis terminado", 1, 1)
    return r


def procesar(ruta: str, log: Optional[LogFn] = None, progreso: Optional[ProgFn] = None) -> Resultado:
    """Analiza y aplica toda la corrección (uso por consola)."""
    r = analizar(ruta, log, progreso)
    if r.grupos:
        n = r.aplicar(r.grupos_con(PENDIENTE))
        (log or (lambda *a: None))("ok", f"Corrección aplicada a {n} grupos")
    return r


def guardar(r: Resultado, destino: Optional[str] = None, log: Optional[LogFn] = None) -> str:
    log = log or (lambda n, m: None)
    destino = destino or ruta_salida(r.lote.ruta)
    r.lote.guardar(destino)
    log("ok", f"Excel guardado (sin formatos agregados): {destino}")
    return destino


def _log_conteo(log: LogFn, titulo: str, hallazgos: List[Hallazgo]) -> None:
    log("titulo", titulo)
    errs = contar(hallazgos, ERROR)
    advs = contar(hallazgos, ADVERTENCIA)
    if not errs and not advs:
        log("ok", "  Sin errores ni advertencias.")
    for cod, n in sorted(errs.items()):
        log("error", f"  Error {cod}: {n} línea/s")
    for cod, n in sorted(advs.items()):
        log("warn", f"  Advertencia {cod}: {n} línea/s")
