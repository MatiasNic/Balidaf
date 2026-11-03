"""
Orquestación: leer → validar (antes) → balancear → validar (después) → guardar.

Lo usan la interfaz gráfica y la línea de comandos.
"""

import os
from dataclasses import dataclass
from typing import Callable, List, Optional

from .balanceo import balancear
from .excel_io import Lote, leer_excel
from .montos import fmt
from .validacion import ADVERTENCIA, ERROR, INFO, Hallazgo, contar, validar

LogFn = Callable[[str, str], None]          # (nivel, mensaje)  nivel: info|ok|warn|error|titulo
ProgFn = Callable[[str, int, int], None]    # (etapa, actual, total)

SUFIJO_SALIDA = "_balidaf.xlsx"


def ruta_salida(ruta_excel: str) -> str:
    return os.path.splitext(ruta_excel)[0] + SUFIJO_SALIDA


@dataclass
class Resultado:
    lote: Lote
    grupos: dict
    antes: List[Hallazgo]
    despues: List[Hallazgo]
    lineas_modificadas: int = 0
    grupos_modificados: int = 0
    lineas_ret_reducidas: int = 0
    grupos_sin_balance: int = 0

    @property
    def errores_antes(self) -> int:
        return sum(1 for h in self.antes if h.nivel == ERROR)

    @property
    def errores_despues(self) -> int:
        return sum(1 for h in self.despues if h.nivel == ERROR)

    @property
    def advertencias(self) -> int:
        return sum(1 for h in self.despues if h.nivel == ADVERTENCIA)

    @property
    def listo_para_presmed(self) -> bool:
        return self.errores_despues == 0

    def filas_con(self, nivel: str) -> set:
        return {h.fila for h in self.despues if h.nivel == nivel and h.fila}


def procesar(ruta: str, log: Optional[LogFn] = None, progreso: Optional[ProgFn] = None) -> Resultado:
    log = log or (lambda n, m: None)
    progreso = progreso or (lambda *a: None)

    log("titulo", f"Archivo: {os.path.basename(ruta)}")
    lote = leer_excel(ruta, progreso)
    log("info", f"Hoja '{lote.hoja}': {len(lote.lineas)} líneas, {len(lote.encabezados)} columnas")
    for k in lote.faltantes:
        log("error", f"Falta la columna obligatoria: {k}")

    antes = validar(lote.lineas, lote.faltantes, progreso)
    _log_conteo(log, "Validación del Excel ORIGINAL", antes)

    if lote.faltantes:
        log("error", "No se puede balancear: faltan columnas obligatorias.")
        return Resultado(lote, {}, antes, antes)

    grupos = balancear(lote.lineas, progreso)
    res_grupos = list(grupos.values())

    # Hallazgos propios del balanceo
    extra: List[Hallazgo] = []
    for g in res_grupos:
        if g.sobrante > 0:
            for ln in g.lineas:
                extra.append(Hallazgo("B02", ERROR, ln.fila, ln.clave, ln.cuil, "importe_subsidiado",
                                      f"Sobran {fmt(g.sobrante)} de subsidio sin poder aplicar en el grupo"))
        for fila in g.retenciones_reducidas:
            ln = next(l for l in g.lineas if l.fila == fila)
            cambios = ", ".join(f"{k}: {fmt(ln.original[k])} → {fmt(ln.monto[k])}"
                                for k in ("ret_gan", "ret_iibb", "ret_otras") if ln.monto[k] != ln.original[k])
            extra.append(Hallazgo("B03", INFO, ln.fila, ln.clave, ln.cuil, "retenciones", cambios))

    despues = validar(lote.lineas, lote.faltantes, progreso)
    # Evitar duplicar el 624 donde ya está el B02 (misma causa)
    filas_b02 = {h.fila for h in extra if h.codigo == "B02"}
    despues = [h for h in despues if not (h.codigo == "624" and h.fila in filas_b02)] + extra

    r = Resultado(lote, grupos, antes, despues)
    r.lineas_modificadas = sum(1 for ln in lote.lineas if ln.modificados())
    r.grupos_modificados = sum(1 for g in res_grupos if any(ln.modificados() for ln in g.lineas))
    r.lineas_ret_reducidas = sum(len(g.retenciones_reducidas) for g in res_grupos)
    r.grupos_sin_balance = sum(1 for g in res_grupos if g.sobrante > 0)

    log("titulo", "Balanceo")
    log("info", f"Grupos (CUIL + períodos + práctica): {len(res_grupos)}")
    log("ok" if r.grupos_modificados else "info",
        f"Grupos balanceados: {r.grupos_modificados} · líneas modificadas: {r.lineas_modificadas}")
    if r.lineas_ret_reducidas:
        log("warn", f"Líneas con retenciones reducidas (subsidio insuficiente): {r.lineas_ret_reducidas}")
    if r.grupos_sin_balance:
        log("error", f"Grupos que NO se pueden balancear (subsidio mayor a lo solicitado): {r.grupos_sin_balance}")
    _log_conteo(log, "Validación DESPUÉS del balanceo", despues)
    if r.listo_para_presmed:
        log("ok", "✔ Sin errores: el Excel queda listo para cargar en Presmed.")
    else:
        log("error", f"✖ Quedan {r.errores_despues} errores que requieren revisión (ver pestaña Validación SSS).")
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
        log("ok", "Sin errores ni advertencias.")
    for cod, n in sorted(errs.items()):
        log("error", f"  Error {cod}: {n} línea/s")
    for cod, n in sorted(advs.items()):
        log("warn", f"  Advertencia {cod}: {n} línea/s")
