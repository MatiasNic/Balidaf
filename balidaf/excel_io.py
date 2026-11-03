"""
Lectura y escritura del Excel de rendición.

- Trabaja sobre la PRIMERA hoja.
- Identifica las columnas por encabezado exacto (normalizado) o por alias conocidos.
  No usa coincidencias parciales, para no tomar una columna equivocada.
- Al guardar sólo cambia el VALOR de las columnas editables: no agrega hojas, colores,
  formatos ni fórmulas. El archivo queda listo para cargar en Presmed.
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from openpyxl import load_workbook

from .montos import a_centavos, a_excel
from .schema import COLUMNAS, IMPORTES, OBLIGATORIAS, RETENCIONES

ProgFn = Callable[[str, int, int], None]


def _norm(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().upper().replace(" ", "").replace("_", "").replace("-", "").replace(".", "")


def texto_celda(v: Any) -> str:
    """Representación de texto de una celda no numérica (como la vería Presmed)."""
    if v is None:
        return ""
    if isinstance(v, dt.datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, dt.date):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def periodo_aaaamm(v: Any) -> str:
    """'01/04/2026', datetime o '202604' → '202604'. Si no se reconoce, devuelve el texto tal cual."""
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%Y%m")
    s = texto_celda(v)
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s[6:10] + s[3:5]
    if len(s) == 7 and s[2] == "/":          # 04/2026
        return s[3:7] + s[0:2]
    return s


@dataclass
class Linea:
    fila: int                                   # fila del Excel (1 = encabezados)
    texto: Dict[str, str] = field(default_factory=dict)
    crudo: Dict[str, Any] = field(default_factory=dict)
    original: Dict[str, int] = field(default_factory=dict)   # importes leídos (centavos)
    monto: Dict[str, int] = field(default_factory=dict)      # importes actuales (centavos)
    propuesta: Dict[str, int] = field(default_factory=dict)  # importes propuestos por el balanceo
    problemas_monto: Dict[str, str] = field(default_factory=dict)

    @property
    def clave(self) -> str:
        return self.texto.get("clave", "")

    @property
    def cuil(self) -> str:
        return self.texto.get("cuil", "")

    @property
    def grupo(self) -> Tuple[str, str, str, str]:
        """Grupo de la regla 624: CUIL + período presentación + período prestación + práctica."""
        return (self.texto.get("cuil", ""), periodo_aaaamm(self.crudo.get("per_pres")),
                periodo_aaaamm(self.crudo.get("per_prest")), self.texto.get("cod", ""))

    def retenciones(self) -> int:
        return sum(self.monto[k] for k in RETENCIONES)

    def modificados(self) -> List[str]:
        """Importes que ya cambiaron (corrección aplicada)."""
        return [k for k in IMPORTES if self.monto[k] != self.original[k]]

    def propuestos(self) -> List[str]:
        """Importes que la corrección propuesta cambiaría."""
        return [k for k in IMPORTES if self.propuesta.get(k, self.original[k]) != self.original[k]]


@dataclass
class Lote:
    ruta: str
    hoja: str
    encabezados: List[str]
    filas: List[List[Any]]                      # todas las celdas (para mostrar el Excel completo)
    columnas: Dict[str, int]                    # clave interna → índice de columna (1-based)
    faltantes: List[str]
    lineas: List[Linea]
    _wb: Any = None

    def guardar(self, destino: str) -> None:
        """Escribe los importes en el Excel original y lo guarda en ``destino``."""
        if self._wb is None:
            self._wb = load_workbook(self.ruta)
        ws = self._wb.worksheets[0]
        # Se escriben las columnas editables con 2 decimales exactos (también limpia restos
        # de float como 150848.96000000002). Ninguna otra celda se toca.
        cols = [(k, self.columnas[k]) for k in ("apli", "transferido", "fdo_ppio") + tuple(RETENCIONES)
                if k in self.columnas]
        for ln in self.lineas:
            for k, col in cols:
                ws.cell(row=ln.fila, column=col).value = a_excel(ln.monto[k])
        self._wb.save(destino)


def _mapear(encabezados: List[Any]) -> Tuple[Dict[str, int], List[str]]:
    idx = {}
    for i, h in enumerate(encabezados, start=1):
        n = _norm(h)
        if n and n not in idx:
            idx[n] = i
    columnas: Dict[str, int] = {}
    for c in COLUMNAS:
        for nombre in (c.encabezado,) + c.alias:
            n = _norm(nombre)
            if n in idx:
                columnas[c.clave] = idx[n]
                break
    faltantes = [k for k in OBLIGATORIAS if k not in columnas]
    return columnas, faltantes


def leer_excel(ruta: str, progreso: Optional[ProgFn] = None) -> Lote:
    progreso = progreso or (lambda *a: None)
    progreso("Abriendo el Excel (puede tardar unos segundos)…", 0, 0)   # 0/0 = sin porcentaje
    wb = load_workbook(ruta)          # una sola lectura: se reutiliza al guardar
    ws = wb.worksheets[0]
    filas_iter = ws.iter_rows(values_only=True)
    encabezados = list(next(filas_iter, []) or [])
    columnas, faltantes = _mapear(encabezados)

    hay_formulas = False
    filas: List[List[Any]] = []
    for r in filas_iter:
        fila = list(r)
        if not hay_formulas and any(isinstance(v, str) and v.startswith("=") for v in fila):
            hay_formulas = True
        filas.append(fila)

    if hay_formulas:
        # Se necesitan los valores calculados: leer una copia con data_only
        progreso("El Excel tiene fórmulas: leyendo valores calculados…", 0, 1)
        ws_val = load_workbook(ruta, data_only=True, read_only=True).worksheets[0]
        filas = [list(r) for i, r in enumerate(ws_val.iter_rows(values_only=True)) if i > 0]

    # quitar filas completamente vacías del final
    while filas and all(v is None or str(v).strip() == "" for v in filas[-1]):
        filas.pop()

    lineas: List[Linea] = []
    total = len(filas)
    for i, fila in enumerate(filas):
        ln = Linea(fila=i + 2)
        for c in COLUMNAS:
            col = columnas.get(c.clave)
            v = fila[col - 1] if col and col - 1 < len(fila) else None
            ln.crudo[c.clave] = v
            if c.importe:
                cent, prob = a_centavos(v)
                ln.original[c.clave] = cent
                ln.monto[c.clave] = cent
                if prob:
                    ln.problemas_monto[c.clave] = prob
            else:
                ln.texto[c.clave] = texto_celda(v)
        lineas.append(ln)
        if i % 2000 == 0:
            progreso("Leyendo Excel…", i, total)

    return Lote(ruta=ruta, hoja=ws.title, encabezados=[texto_celda(h) for h in encabezados],
                filas=filas, columnas=columnas, faltantes=faltantes, lineas=lineas, _wb=wb)
