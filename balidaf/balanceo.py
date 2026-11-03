"""
Balanceo de subsidios por grupo.

Grupo (regla 624 de la SSS): igual CUIL + PERÍODO PRESENTACIÓN + PERÍODO PRESTACIÓN + CÓDIGO PRÁCTICA.
La clave se arma automáticamente: ya no hace falta la columna CONCATENAR.

Para cada grupo:
  1. Subsidio a aplicar = Σ subsidiado − Σ (trasladado + devuelto + saldo no aplicado + recupero).
  2. Se reparte entre las líneas, sin superar en cada una lo que se puede aplicar:
         tope = solicitado − (fdo. otras ctas + trasladado + devuelto + saldo no aplicado + recupero)
     Primero las líneas CON retenciones (para que el subsidio las cubra y el transferido no quede
     negativo) y luego el resto, respetando el orden del Excel.
  3. Si en una línea el aplicado no alcanza para cubrir las retenciones, se reducen las retenciones
     (ganancias → IIBB → otras se conservan en ese orden) y el transferido queda en 0.
  4. transferido = aplicado − retenciones                                   (regla 622)
     fondos propios cta. discapacidad = solicitado − aplicado − otros       (regla 623)

Sólo se modifican: impor_apli_sss, importe_transferido, fdo_ppio_ingre_cta_disca y, cuando el
subsidio no alcanza, las retenciones. Nunca se tocan los campos 2 a 9 (regla 602).
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Tuple

from .excel_io import Linea
from .schema import OTROS_DESTINOS_SOLICITADO, OTROS_DESTINOS_SUBSIDIO, RETENCIONES

ProgFn = Callable[[str, int, int], None]

# Estado de la corrección propuesta para un grupo
SIN_CAMBIOS = "Sin cambios"
PENDIENTE = "Pendiente"
APLICADA = "Aplicada"


@dataclass
class Grupo:
    clave: Tuple[str, str, str, str]
    lineas: List[Linea]
    subsidio: int = 0              # Σ subsidiado (centavos)
    a_aplicar: int = 0             # subsidio − otros destinos
    aplicado: int = 0              # Σ aplicado luego del balanceo
    sobrante: int = 0              # subsidio que no se pudo aplicar (> 0 ⇒ no balancea)
    retenciones_reducidas: List[int] = field(default_factory=list)   # filas
    estado: str = SIN_CAMBIOS      # SIN_CAMBIOS | PENDIENTE | APLICADA

    @property
    def tiene_propuesta(self) -> bool:
        return self.estado in (PENDIENTE, APLICADA)

    @property
    def nombre(self) -> str:
        cuil, pp, pr, cod = self.clave
        return f"CUIL {cuil} · práctica {cod} · prestación {pr}"


def agrupar(lineas: List[Linea]) -> "OrderedDict[Tuple[str, str, str, str], Grupo]":
    grupos: "OrderedDict[Tuple, Grupo]" = OrderedDict()
    for ln in lineas:
        g = grupos.get(ln.grupo)
        if g is None:
            g = grupos[ln.grupo] = Grupo(ln.grupo, [])
        g.lineas.append(ln)
    return grupos


def _reducir_retenciones(ln: Linea, disponible: int) -> bool:
    """Ajusta las retenciones para que no superen ``disponible``. Devuelve True si cambió algo."""
    if ln.retenciones() <= disponible:
        return False
    resto = disponible
    for k in RETENCIONES:
        nuevo = min(ln.monto[k], max(resto, 0))
        ln.monto[k] = nuevo
        resto -= nuevo
    return True


def grupo_ya_balanceado(g: Grupo) -> bool:
    """True si el grupo ya cumple exactamente 622, 623 y 624 sin importes negativos."""
    for ln in g.lineas:
        m = ln.monto
        otros = sum(m[k] for k in OTROS_DESTINOS_SOLICITADO)
        if m["apli"] != m["transferido"] + ln.retenciones():
            return False
        if m["solicitado"] != m["fdo_ppio"] + otros + m["apli"]:
            return False
        if min(m["apli"], m["transferido"], m["fdo_ppio"]) < 0:
            return False
    return sum(ln.monto["apli"] for ln in g.lineas) == g.a_aplicar


def balancear_grupo(g: Grupo) -> None:
    g.subsidio = sum(ln.monto["subsidiado"] for ln in g.lineas)
    otros_grupo = sum(ln.monto[k] for ln in g.lineas for k in OTROS_DESTINOS_SUBSIDIO)
    g.a_aplicar = g.subsidio - otros_grupo

    if grupo_ya_balanceado(g):
        # Ya cumple las reglas: no se toca (evita cambios innecesarios en líneas correctas)
        g.aplicado = g.a_aplicar
        g.sobrante = 0
        return

    # Orden: primero líneas con retenciones, después el resto (estable = orden del Excel)
    orden = sorted(g.lineas, key=lambda ln: 0 if ln.retenciones() > 0 else 1)

    resto = max(g.a_aplicar, 0)
    for ln in orden:
        otros = sum(ln.monto[k] for k in OTROS_DESTINOS_SOLICITADO)
        tope = max(ln.monto["solicitado"] - otros, 0)
        aplicado = min(tope, resto)
        resto -= aplicado

        if _reducir_retenciones(ln, aplicado):
            g.retenciones_reducidas.append(ln.fila)
        ln.monto["apli"] = aplicado
        ln.monto["transferido"] = aplicado - ln.retenciones()
        ln.monto["fdo_ppio"] = ln.monto["solicitado"] - aplicado - otros

    g.aplicado = sum(ln.monto["apli"] for ln in g.lineas)
    g.sobrante = resto


def balancear(lineas: List[Linea], progreso: Optional[ProgFn] = None) -> "OrderedDict[Tuple, Grupo]":
    progreso = progreso or (lambda *a: None)
    grupos = agrupar(lineas)
    total = len(grupos)
    for i, g in enumerate(grupos.values(), start=1):
        balancear_grupo(g)
        if i % 500 == 0 or i == total:
            progreso("Balanceando grupos…", i, total)
    return grupos


# ----------------------------------------------------------------------------------------------
# Propuesta → el usuario decide → aplicar / deshacer
# ----------------------------------------------------------------------------------------------
def proponer(lineas: List[Linea], progreso: Optional[ProgFn] = None) -> "OrderedDict[Tuple, Grupo]":
    """Calcula el balanceo SIN aplicarlo.

    Cada línea guarda la corrección en ``ln.propuesta``; ``ln.monto`` queda con los valores
    originales hasta que el usuario decide aplicar (``aplicar``).
    """
    for ln in lineas:
        ln.monto = dict(ln.original)
    grupos = balancear(lineas, progreso)
    for g in grupos.values():
        for ln in g.lineas:
            ln.propuesta = dict(ln.monto)
            ln.monto = dict(ln.original)
        g.estado = PENDIENTE if any(ln.propuesta != ln.original for ln in g.lineas) else SIN_CAMBIOS
    return grupos


def aplicar(grupos: Iterable[Grupo]) -> int:
    """Aplica la corrección propuesta. Devuelve cuántos grupos se aplicaron."""
    n = 0
    for g in grupos:
        if g.estado == PENDIENTE:
            for ln in g.lineas:
                ln.monto = dict(ln.propuesta)
            g.estado = APLICADA
            n += 1
    return n


def deshacer(grupos: Iterable[Grupo]) -> int:
    """Vuelve los grupos a sus valores originales. Devuelve cuántos se deshicieron."""
    n = 0
    for g in grupos:
        if g.estado == APLICADA:
            for ln in g.lineas:
                ln.monto = dict(ln.original)
            g.estado = PENDIENTE
            n += 1
    return n
