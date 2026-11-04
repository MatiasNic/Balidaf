"""Ventana modal «Detalle de línea»: importes, grupo de la regla 624 y validaciones actuales."""

import tkinter as tk
from typing import TYPE_CHECKING

from ..balanceo import APLICADA, PENDIENTE, tipo_correccion
from ..excel_io import Linea
from ..montos import fmt
from ..schema import COL, IMPORTES
from ..validacion import ADVERTENCIA, ERROR, INFO
from .componentes import Boton, Lbl, Linea as Divisor, Tabla, _Velo
from .tema import P

if TYPE_CHECKING:
    from .app import BalidafApp

NIVEL = {ERROR: "err", ADVERTENCIA: "warn", INFO: "pend"}


class DetalleLinea(tk.Toplevel):
    def __init__(self, app: "BalidafApp", ln: Linea):
        super().__init__(app)
        self.app = app
        r = app.resultado
        g = r.grupo_de_fila(ln.fila) if r else None
        self.velo = _Velo(app)
        self.title(f"Detalle de línea · fila {ln.fila}")
        self.transient(app)
        self.configure(bg=P["surface"])
        self.bind("<Escape>", lambda e: self.cerrar())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        cab = tk.Frame(self, bg=P["surface"], padx=20, pady=12)
        cab.pack(fill="x")
        der = tk.Frame(cab, bg=P["surface"])
        der.pack(side="right", anchor="n")
        izq = tk.Frame(cab, bg=P["surface"])
        izq.pack(side="left", fill="x", expand=True)
        sup = tk.Frame(izq, bg=P["surface"])
        sup.pack(anchor="w")
        Lbl(sup, f"Detalle de línea · fila {ln.fila}", 12, color="ink3").pack(side="left")
        if g is not None and g.estado in (PENDIENTE, APLICADA):
            fam = "pend" if g.estado == PENDIENTE else "ok"
            texto = "Corrección pendiente" if g.estado == PENDIENTE else "Corregida"
            Lbl(sup, texto, 11.5, "semibold", fondo=f"{fam}_bg", color=f"{fam}_fg", padx=8).pack(side="left", padx=10)
        Lbl(izq, f"CUIL {ln.cuil} · práctica {ln.texto.get('cod', '')} · prestación {ln.grupo[2]} · clave {ln.clave}",
            15, "semibold").pack(anchor="w", pady=(2, 0))
        cerrar = Lbl(der, "×", 18, color="ink2", cursor="hand2", padx=6)
        cerrar.pack(side="right")
        cerrar.bind("<Button-1>", lambda e: self.cerrar())
        if g is not None and g.estado == PENDIENTE:
            Boton(der, "✓ Aplicar corrección del grupo", lambda: self._accion("aplicar", g), "chico_primario").pack(
                side="right", padx=(0, 10))
        elif g is not None and g.estado == APLICADA:
            Boton(der, "↶ Deshacer corrección del grupo", lambda: self._accion("deshacer", g), "chico").pack(
                side="right", padx=(0, 10))
        Divisor(self).pack(fill="x")

        cuerpo = tk.Frame(self, bg=P["surface"], padx=20, pady=10)
        cuerpo.pack(fill="both", expand=True)
        Lbl(cuerpo, "Importes de la línea", 13, "semibold").pack(anchor="w", pady=(0, 6))
        t = Tabla(cuerpo, [("campo", "Campo", 240), ("col", "Columna Excel", 220), ("o", "Original", 140, "e"),
                           ("p", "Corrección propuesta", 170, "e"), ("a", "Actual (se guarda)", 160, "e", True)],
                  altura=len(IMPORTES))
        t.pack(fill="x")
        filas = []
        for k in IMPORTES:
            o, p, a = ln.original[k], ln.propuesta.get(k, ln.original[k]), ln.monto[k]
            fam = "ok" if a != o else ("pend" if p != o else "")
            filas.append((k, (COL[k].titulo, COL[k].encabezado, fmt(o), fmt(p) if p != o else "", fmt(a)), fam))
        t.cargar(filas)

        if g is not None:
            Lbl(cuerpo, f"Grupo regla 624 · {len(g.lineas)} línea(s) · subsidio {fmt(g.subsidio)} · corrección: "
                        f"{tipo_correccion(g) if g.tiene_propuesta else 'sin cambios'}", 13, "semibold").pack(
                anchor="w", pady=(12, 6))
            t2 = Tabla(cuerpo, [("fila", "Fila", 60, "e"), ("clave", "Clave", 120), ("sub", "Subsidiado", 130, "e"),
                                ("sol", "Solicitado", 130, "e"), ("ao", "Aplicado original", 140, "e"),
                                ("ap", "Aplicado propuesto", 150, "e"), ("fdo", "Fdo. propios propuesto", 160, "e", True)],
                       altura=min(5, len(g.lineas)))
            t2.pack(fill="x")
            t2.cargar([(str(x.fila), (x.fila, x.clave, fmt(x.original["subsidiado"]), fmt(x.original["solicitado"]),
                                      fmt(x.original["apli"]), fmt(x.propuesta.get("apli", 0)),
                                      fmt(x.propuesta.get("fdo_ppio", 0))), "pend" if x.fila == ln.fila else "")
                       for x in g.lineas])

        hs = [h for h in (r.actual if r else []) if h.fila == ln.fila]
        Lbl(cuerpo, f"Validaciones actuales de la línea ({len(hs)})", 13, "semibold").pack(anchor="w", pady=(12, 6))
        if hs:
            t3 = Tabla(cuerpo, [("c", "Código", 80), ("n", "Nivel", 110), ("d", "Detalle", 600, "w", True)],
                       altura=min(4, len(hs)))
            t3.pack(fill="x")
            t3.cargar([(str(i), (h.codigo, h.nivel, h.detalle), NIVEL.get(h.nivel, "")) for i, h in enumerate(hs)])
        else:
            Lbl(cuerpo, "✓ La línea cumple todas las reglas de la SSS.", 13, "semibold", color="ok_fg").pack(anchor="w")

        self.update_idletasks()
        w, h = 1000, min(self.winfo_reqheight(), app.winfo_height() - 40)
        x = app.winfo_rootx() + (app.winfo_width() - w) // 2
        y = app.winfo_rooty() + 20
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.focus_set()

    def _accion(self, que: str, g) -> None:
        self.cerrar()
        (self.app.aplicar if que == "aplicar" else self.app.deshacer)([g])

    def cerrar(self) -> None:
        self.velo.cerrar()
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
