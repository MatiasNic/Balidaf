"""Pestaña «Ver Excel»: el Excel con los valores actuales (lo que se va a guardar)."""

import tkinter as tk
from typing import TYPE_CHECKING, List, Optional

from ..balanceo import APLICADA, PENDIENTE, SIN_CAMBIOS
from ..excel_io import texto_celda
from ..montos import fmt
from ..schema import IMPORTES
from ..validacion import ADVERTENCIA, ERROR
from .componentes import Buscador, Caja, ChipFiltro, EstadoVacio, Lbl, Linea, Segmentado, Tabla, fmt_n
from .tema import P, al_cambiar_tema

if TYPE_CHECKING:
    from .app import BalidafApp

FILTROS = [("todas", "Todas", None), ("pend", "Corrección pendiente", "pend"), ("ok", "Corregidas", "ok"),
           ("vio", "Retenciones reducidas", "vio"), ("err", "Errores a corregir a mano", "err"),
           ("warn", "Advertencias", "warn")]
CLAVE = [("clave", "clave_rendicion", 125, ""), ("cuil", "cuil", 115, ""), ("cod", "cod_prestac", 95, ""),
         ("per_prest", "perio_prestac", 105, ""), ("subsidiado", "importe_subsidiado", 145, "e"),
         ("solicitado", "importe_solicitado", 145, "e"), ("apli", "impor_apli_sss", 135, "e"),
         ("transferido", "importe_transferido", 150, "e"), ("_ret", "retenciones", 120, "e"),
         ("fdo_ppio", "fdo_ppio_ingre_cta_disca", 190, "e")]


class PagExcel(tk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padx=20, pady=12)
        self.app = app
        self.filtro, self.q, self.vista_cols = "todas", "", "clave"
        self.sucio = True
        al_cambiar_tema(lambda: self.config(bg=P["bg"]))
        self.card = Caja(self)
        self.card.pack(fill="both", expand=True)

        barra = tk.Frame(self.card, padx=14, pady=9)
        barra.pack(fill="x")
        al_cambiar_tema(lambda: barra.config(bg=P["surface2"]))
        Lbl(barra, "Mostrar", 12.5, "semibold", color="ink2", fondo="surface2").pack(side="left", padx=(0, 10))
        self.chips = {}
        for v, t, fam in FILTROS:
            c = ChipFiltro(barra, t, fam, lambda v=v: self.set_filtro(v))
            c.pack(side="left", padx=(0, 6))
            self.chips[v] = c
        self.buscador = Buscador(barra, self._buscar, ancho=18)
        self.buscador.pack(side="right")
        fila2 = tk.Frame(self.card, padx=14, pady=6)
        fila2.pack(fill="x")
        al_cambiar_tema(lambda: fila2.config(bg=P["surface2"]))
        self.seg = Segmentado(fila2, [("clave", "Importes y datos clave"), ("todas", "Todas las columnas")],
                              self._vista, "clave")
        self.seg.pack(side="left")
        Linea(self.card).pack(fill="x")
        info = tk.Frame(self.card, padx=14, pady=6)
        info.pack(fill="x")
        al_cambiar_tema(lambda: info.config(bg=P["surface"]))
        self.lbl_n = Lbl(info, "", 12.5, "semibold")
        self.lbl_n.pack(side="left")
        Lbl(info, "Valores actuales (lo que se va a guardar). Las filas corregidas se ven en verde.", 12,
            color="ink2").pack(side="left", padx=(10, 0))
        Lbl(info, "Colores sólo en pantalla: el Excel se guarda sin formato · doble clic = detalle", 12,
            color="ink3").pack(side="right")
        self.cont = tk.Frame(self.card)
        self.cont.pack(fill="both", expand=True)
        self.tabla: Optional[Tabla] = None
        self._cols_actual = None
        self.vacio = EstadoVacio(self.card)
        self.vacio.mostrar(self.cont, "Todavía no hay datos",
                           "Analizá el Excel original en «1 · Balancear» para verlo acá.",
                           ("Ir a «1 · Balancear»", lambda: app.ir("balancear")))

    def set_filtro(self, v: str) -> None:
        self.filtro = v
        self.refrescar()

    def _buscar(self, q: str) -> None:
        self.q = q
        self.refrescar()

    def _vista(self, v: str) -> None:
        self.vista_cols = v
        self.refrescar()

    def _columnas(self, lote) -> List[tuple]:
        base = [("_fila", "Fila", 60, "e"), ("_estado", "Estado", 190)]
        if self.vista_cols == "clave":
            return base + [(k, t, w, a) for k, t, w, a in CLAVE]
        a_clave = {v: k for k, v in lote.columnas.items()}
        cols = []
        for i, h in enumerate(lote.encabezados):
            k = a_clave.get(i + 1)
            largo = max([len(h or "")] + [len(texto_celda(f[i])) for f in lote.filas[:200] if i < len(f)])
            cols.append((f"c{i}", h or f"Col {i + 1}", max(80, min(230, largo * 8 + 30)),
                         "e" if k in IMPORTES else ""))
        return base + cols

    def refrescar(self) -> None:
        self.sucio = False
        r = self.app.resultado
        if r is None:
            return
        self.vacio.ocultar()
        lote = r.lote
        self.seg.set_textos({"todas": f"Todas las columnas ({len(lote.encabezados)})"})
        cols = self._columnas(lote)
        if self.tabla is None or self._cols_actual != [c[0] for c in cols]:
            if self.tabla:
                self.tabla.destroy()
            self.tabla = Tabla(self.cont, cols, altura=18, al_doble=lambda iid: self.app.abrir_detalle(int(iid)))
            self.tabla.pack(fill="both", expand=True)
            self._cols_actual = [c[0] for c in cols]

        manual = r.filas_con(ERROR, r.propuesta)
        advs = r.filas_con(ADVERTENCIA)
        est = {ln.fila: g.estado for g in r.grupos.values() for ln in g.lineas}
        ret = {f for g in r.grupos.values() if g.estado == APLICADA for f in g.retenciones_reducidas}
        a_clave = {v: k for k, v in lote.columnas.items()}

        def clasificar(fila: int):
            e = est.get(fila, SIN_CAMBIOS)
            if fila in manual:
                return "err", "Error a corregir a mano"
            if e == PENDIENTE:
                return "pend", "Corrección pendiente"
            if fila in ret:
                return "vio", "Retenciones reducidas"
            if e == APLICADA:
                return "ok", "Corregida"
            if fila in advs:
                return "warn", "Advertencia"
            return "", "OK"

        cant = {v: 0 for v, _, _ in FILTROS}
        filas, q = [], self.q
        for ln, crudo in zip(lote.lineas, lote.filas):
            fam, estado = clasificar(ln.fila)
            cant["todas"] += 1
            if fam:
                cant[fam] += 1
            if self.filtro != "todas" and fam != self.filtro:
                continue
            if q and q not in ln.cuil and q not in ln.clave:
                continue
            vals = [ln.fila, estado]
            if self.vista_cols == "clave":
                for k, _, _, _ in CLAVE:
                    if k == "_ret":
                        vals.append(fmt(sum(ln.monto[x] for x in ("ret_gan", "ret_iibb", "ret_otras"))))
                    elif k in ln.monto:
                        vals.append(fmt(ln.monto[k]))
                    else:
                        vals.append(texto_celda(ln.crudo.get(k)))
            else:
                for i, v in enumerate(crudo):
                    k = a_clave.get(i + 1)
                    vals.append(fmt(ln.monto[k]) if k in ln.monto else texto_celda(v))
            filas.append((str(ln.fila), vals, fam))
        for v, c in self.chips.items():
            c.set(cant[v], activo=v == self.filtro)
        self.lbl_n.config(text=f"{fmt_n(len(filas))} de {fmt_n(len(lote.lineas))} líneas")
        self.tabla.cargar(filas)
