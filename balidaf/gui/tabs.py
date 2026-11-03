"""Pestañas de la ventana principal."""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict, List, Optional

from ..balanceo import APLICADA, PENDIENTE, SIN_CAMBIOS, Grupo
from ..devolucion import (APLICADA_TXT, ESTADOS, NO_ENCONTRADO, PENDIENTE_MANUAL,
                          PENDIENTE_SISTEMAS, PROPUESTA, YA_CUMPLE, ResultadoCruce)
from ..excel_io import Linea, texto_celda
from ..montos import fmt
from ..schema import CODIGOS, COL, IMPORTES
from ..validacion import ADVERTENCIA, ERROR, INFO
from .widgets import AZUL, FUENTE, NARANJA, ROJO, VERDE, Aviso, Tabla, Tarjeta, fila

if TYPE_CHECKING:
    from .app import BalidafApp

NIVEL_TAG = {ERROR: "error", ADVERTENCIA: "warn", INFO: "info"}
ESTADO_TAG = {PENDIENTE: "prop", APLICADA: "mod", SIN_CAMBIOS: ""}


def _cambio(o: int, n: int) -> str:
    return fmt(o) if o == n else f"{fmt(o)} → {fmt(n)}"


def _motivo(r, g: Grupo) -> str:
    filas = {ln.fila for ln in g.lineas}
    cods = sorted({h.codigo for h in r.antes if h.fila in filas and h.nivel == ERROR})
    return ", ".join(cods) if cods else "—"


# =====================================================================================
class TabBalancear(ttk.Frame):
    """Paso 1: elegir Excel → Analizar → revisar la corrección → aplicar → guardar."""

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        self.app = app

        # ---- Paso 1
        ttk.Label(self, text="Paso 1 · Elegí el Excel ORIGINAL de Presmed y presioná «Analizar»",
                  style="Paso.TLabel").pack(anchor="w")
        f = fila(self, pady=(4, 8))
        self.var_ruta = tk.StringVar()
        ttk.Entry(f, textvariable=self.var_ruta).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="Examinar…", command=app.on_examinar).pack(side="left", padx=6)
        self.btn_analizar = ttk.Button(f, text="Analizar", style="Accent.TButton", command=app.on_analizar)
        self.btn_analizar.pack(side="left")

        self.aviso = Aviso(self, "Todavía no se analizó ningún Excel.")
        self.aviso.pack(fill="x", pady=(0, 8))

        cont = ttk.Frame(self)
        cont.pack(fill="x", pady=(0, 8))
        self.tarjetas: Dict[str, Tarjeta] = {}
        for i, (k, t, c) in enumerate([
                ("errores", "Errores en el Excel (ahora)", ROJO),
                ("pendientes", "Correcciones pendientes (grupos)", AZUL),
                ("aplicadas", "Correcciones aplicadas (grupos)", VERDE),
                ("manual", "Errores que NO se corrigen solos", NARANJA)]):
            tj = Tarjeta(cont, t, c)
            tj.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            cont.columnconfigure(i, weight=1)
            self.tarjetas[k] = tj

        # ---- Paso 2
        cab = fila(self, pady=(2, 4))
        ttk.Label(cab, text="Paso 2 · Revisá las correcciones propuestas y aplicalas", style="Paso.TLabel").pack(side="left")
        ttk.Label(cab, text="   Mostrar:").pack(side="left")
        self.var_filtro = tk.StringVar(value="Pendientes")
        cb = ttk.Combobox(cab, textvariable=self.var_filtro, state="readonly", width=12,
                          values=["Pendientes", "Aplicadas", "Todas"])
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refrescar_grupos())
        self.lbl_cant = ttk.Label(cab, text="", style="Sub.TLabel")
        self.lbl_cant.pack(side="left", padx=8)

        acc = fila(self, pady=(0, 4))
        self.btn_aplicar_sel = ttk.Button(acc, text="✔ Aplicar seleccionadas", command=self.aplicar_sel)
        self.btn_aplicar_sel.pack(side="left")
        self.btn_aplicar_todo = ttk.Button(acc, text="✔ Aplicar todas", command=self.aplicar_todo)
        self.btn_aplicar_todo.pack(side="left", padx=6)
        self.btn_deshacer = ttk.Button(acc, text="↶ Deshacer seleccionadas", command=self.deshacer_sel)
        self.btn_deshacer.pack(side="left")
        ttk.Label(acc, text="Seleccioná varias con Ctrl o Shift. Cada fila es un grupo (CUIL + períodos + práctica).",
                  style="Sub.TLabel").pack(side="left", padx=10)

        pan = ttk.PanedWindow(self, orient="vertical")
        pan.pack(fill="both", expand=True)
        self.t_grupos = Tabla(pan, [("estado", "Estado", 90), ("cuil", "CUIL", 105), ("cod", "Práctica", 65),
                                    ("pres", "Prestación", 80), ("n", "Líneas", 55), ("sub", "Subsidio", 110),
                                    ("apli_o", "Aplicado original", 130), ("apli_n", "Aplicado corregido", 130),
                                    ("motivo", "Errores SSS", 90), ("nota", "Nota", 260)],
                              altura=8, seleccion="extended")
        self.t_grupos.tree.bind("<<TreeviewSelect>>", lambda e: self.mostrar_detalle())
        pan.add(self.t_grupos, weight=3)
        lf = ttk.LabelFrame(pan, text="Detalle del grupo seleccionado (original → corregido)", padding=4)
        self.t_det = Tabla(lf, [("fila", "Fila", 55), ("clave", "Clave", 105), ("sol", "Solicitado", 105),
                                ("ret", "Retenciones", 170), ("apli", "Aplicado (impor_apli_sss)", 210),
                                ("tr", "Transferido (importe_transferido)", 230),
                                ("fdo", "Fondos propios (fdo_ppio_ingre_cta_disca)", 250)], altura=4,
                           on_doble_click=lambda iid: app.abrir_detalle(int(iid)))
        self.t_det.pack(fill="both", expand=True)
        pan.add(lf, weight=2)

        # ---- Paso 3
        f3 = fila(self, pady=(8, 0))
        ttk.Label(f3, text="Paso 3 · ", style="Paso.TLabel").pack(side="left")
        self.btn_guardar = ttk.Button(f3, text="💾 Guardar Excel para Presmed", style="Ok.TButton",
                                      command=app.on_guardar)
        self.btn_guardar.pack(side="left")
        self.btn_informe = ttk.Button(f3, text="Exportar informe (opcional)…", command=app.on_informe)
        self.btn_informe.pack(side="left", padx=8)
        ttk.Label(f3, text="El Excel se guarda limpio (sin colores ni hojas nuevas) con las correcciones APLICADAS.",
                  style="Sub.TLabel").pack(side="left", padx=6)
        self._grupos_vista: List[Grupo] = []

    # ------------------------------------------------------------------
    def mostrar(self) -> None:
        r = self.app.resultado
        if r is None:
            return
        pend, apl = len(r.grupos_con(PENDIENTE)), len(r.grupos_con(APLICADA))
        self.tarjetas["errores"].set(r.errores_actuales, VERDE if r.errores_actuales == 0 else ROJO)
        self.tarjetas["pendientes"].set(pend)
        self.tarjetas["aplicadas"].set(apl)
        self.tarjetas["manual"].set(r.errores_propuesta, VERDE if r.errores_propuesta == 0 else NARANJA)

        if r.lote.faltantes:
            self.aviso.mostrar("✖ Al Excel le faltan columnas obligatorias: "
                               + ", ".join(COL[k].encabezado for k in r.lote.faltantes), "error")
        elif r.listo_para_presmed and pend == 0:
            self.aviso.mostrar("✔ Sin errores. Ya podés guardar el Excel para Presmed (Paso 3).", "ok")
        elif r.listo_para_presmed:
            self.aviso.mostrar(f"✔ Sin errores. Quedan {pend} correcciones opcionales sin aplicar. "
                               "Podés guardar el Excel (Paso 3).", "ok")
        elif pend:
            extra = (f" Además hay {r.errores_propuesta} errores que hay que corregir a mano (ver pestaña «Ver Excel», "
                     "filtro «Con errores»).") if r.errores_propuesta else ""
            self.aviso.mostrar(f"El Excel tiene {r.errores_actuales} errores. Balidaf propone corregir {pend} grupos: "
                               f"revisalos abajo y presioná «Aplicar todas» o elegí cuáles aplicar.{extra}", "info")
        else:
            self.aviso.mostrar(f"Quedan {r.errores_actuales} errores que el balanceo no puede corregir: hay que "
                               "corregirlos en el Excel original (ver pestaña «Ver Excel», filtro «Con errores»).",
                               "error")
        self.refrescar_grupos()

    def refrescar_grupos(self) -> None:
        r = self.app.resultado
        if r is None:
            return
        filtro = self.var_filtro.get()
        estados = {"Pendientes": (PENDIENTE,), "Aplicadas": (APLICADA,), "Todas": (PENDIENTE, APLICADA)}[filtro]
        self._grupos_vista = [g for g in r.grupos.values() if g.estado in estados]
        filas = []
        for i, g in enumerate(self._grupos_vista):
            cuil, _, pres, cod = g.clave
            apli_o = sum(ln.original["apli"] for ln in g.lineas)
            apli_n = sum(ln.propuesta["apli"] for ln in g.lineas)
            nota = "Reduce retenciones (subsidio insuficiente)" if g.retenciones_reducidas else ""
            if g.sobrante:
                nota = f"No se puede balancear: sobran {fmt(g.sobrante)}"
            filas.append((str(i), (g.estado, cuil, cod, pres, len(g.lineas), fmt(g.subsidio), fmt(apli_o), fmt(apli_n),
                                   _motivo(r, g), nota), (ESTADO_TAG.get(g.estado, ""),)))
        self.lbl_cant.config(text=f"{len(filas):,} grupos".replace(",", "."))
        self.t_grupos.cargar(filas)
        self.t_det.limpiar()

    def _sel(self) -> List[Grupo]:
        return [self._grupos_vista[int(i)] for i in self.t_grupos.seleccionados()]

    def mostrar_detalle(self) -> None:
        sel = self._sel()
        self.t_det.limpiar()
        if not sel:
            return
        g = sel[0]
        filas = []
        for ln in g.lineas:
            o, n = ln.original, ln.propuesta
            ret_o = sum(o[k] for k in ("ret_gan", "ret_iibb", "ret_otras"))
            ret_n = sum(n[k] for k in ("ret_gan", "ret_iibb", "ret_otras"))
            filas.append((str(ln.fila), (ln.fila, ln.clave, fmt(o["solicitado"]), _cambio(ret_o, ret_n),
                                         _cambio(o["apli"], n["apli"]), _cambio(o["transferido"], n["transferido"]),
                                         _cambio(o["fdo_ppio"], n["fdo_ppio"])),
                          ("ret",) if ln.fila in g.retenciones_reducidas else ()))
        self.t_det.cargar(filas)

    def aplicar_sel(self) -> None:
        self.app.aplicar([g for g in self._sel() if g.estado == PENDIENTE], "seleccionadas")

    def aplicar_todo(self) -> None:
        r = self.app.resultado
        if r:
            self.app.aplicar(r.grupos_con(PENDIENTE), "todas")

    def deshacer_sel(self) -> None:
        self.app.deshacer([g for g in self._sel() if g.estado == APLICADA])

    def habilitar(self, ocupado: bool) -> None:
        r = self.app.resultado
        hay = r is not None and not r.lote.faltantes
        self.btn_analizar.config(state="disabled" if ocupado else "normal")
        for b in (self.btn_aplicar_sel, self.btn_aplicar_todo, self.btn_deshacer, self.btn_guardar):
            b.config(state="normal" if hay and not ocupado else "disabled")
        self.btn_informe.config(state="normal" if r and not ocupado else "disabled")


# =====================================================================================
class TabDevolucion(ttk.Frame):
    """Paso opcional: cruzar la devolución de la SSS, ver la corrección propuesta y decidir aplicarla."""

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        self.app = app
        self.cruce: Optional[ResultadoCruce] = None

        ttk.Label(self, text="1 · Analizá el Excel original en la pestaña «1 · Balancear»   "
                             "2 · Cargá el TXT de errores de la SSS   3 · Revisá y decidí qué corregir",
                  style="Paso.TLabel").pack(anchor="w")
        f = fila(self, pady=(6, 6))
        self.btn_err = ttk.Button(f, text="Cargar TXT de errores (_ERR)…", style="Accent.TButton",
                                  command=lambda: app.on_cargar_txt("ERR"))
        self.btn_err.pack(side="left")
        self.btn_ok = ttk.Button(f, text="Cargar TXT aceptados (_OK) (opcional)…", command=lambda: app.on_cargar_txt("OK"))
        self.btn_ok.pack(side="left", padx=6)
        self.lbl_archivos = ttk.Label(f, text="Ningún TXT cargado.", style="Sub.TLabel")
        self.lbl_archivos.pack(side="left", padx=8)

        self.aviso = Aviso(self, "Cargá el TXT de errores para ver qué rechazó la SSS y qué corrección propone Balidaf. "
                                 "Nada se corrige hasta que vos lo apliques.")
        self.aviso.pack(fill="x", pady=(0, 8))

        cont = ttk.Frame(self)
        cont.pack(fill="x", pady=(0, 8))
        self.tarjetas = {}
        for i, (k, t, c) in enumerate([("total", "Líneas rechazadas", AZUL), (PROPUESTA, "Con corrección propuesta", AZUL),
                                       (APLICADA_TXT, "Corrección aplicada", VERDE),
                                       (PENDIENTE_MANUAL, "Requieren corrección manual", ROJO),
                                       (PENDIENTE_SISTEMAS, "Las resuelve Sistemas", NARANJA)]):
            tj = Tarjeta(cont, t, c)
            tj.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            cont.columnconfigure(i, weight=1)
            self.tarjetas[k] = tj

        lf1 = ttk.LabelFrame(self, text="Errores informados por la SSS (doble clic para filtrar)", padding=4)
        lf1.pack(fill="x")
        self.t_cod = Tabla(lf1, [("cod", "Código", 65), ("n", "Líneas", 65), ("res", "Lo resuelve", 100),
                                 ("desc", "Descripción (instructivo SSS, Anexo IV)", 900)], altura=4,
                           on_doble_click=self._filtrar_cod)
        self.t_cod.pack(fill="x")

        cab = fila(self, pady=(8, 4))
        ttk.Label(cab, text="Detalle por línea", style="Paso.TLabel").pack(side="left")
        ttk.Label(cab, text="   Estado:").pack(side="left")
        self.var_estado = tk.StringVar(value="Todos")
        cb = ttk.Combobox(cab, textvariable=self.var_estado, width=32, state="readonly", values=["Todos"] + ESTADOS)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.mostrar_detalle())
        ttk.Label(cab, text="  Código:").pack(side="left")
        self.var_cod = tk.StringVar(value="Todos")
        self.cb_cod = ttk.Combobox(cab, textvariable=self.var_cod, width=7, state="readonly", values=["Todos"])
        self.cb_cod.pack(side="left", padx=4)
        self.cb_cod.bind("<<ComboboxSelected>>", lambda e: self.mostrar_detalle())

        acc = fila(self, pady=(0, 4))
        self.btn_aplicar_sel = ttk.Button(acc, text="✔ Corregir seleccionadas en el Excel", command=self.aplicar_sel)
        self.btn_aplicar_sel.pack(side="left")
        self.btn_aplicar_todo = ttk.Button(acc, text="✔ Corregir todas las que tienen propuesta", command=self.aplicar_todo)
        self.btn_aplicar_todo.pack(side="left", padx=6)
        self.btn_deshacer = ttk.Button(acc, text="↶ Deshacer seleccionadas", command=self.deshacer_sel)
        self.btn_deshacer.pack(side="left")
        ttk.Label(acc, text="La corrección se aplica a todo el grupo de la línea (CUIL + períodos + práctica).",
                  style="Sub.TLabel").pack(side="left", padx=10)

        self.t_det = Tabla(self, [("clave", "Clave", 100), ("cuil", "CUIL", 100), ("fila", "Fila", 50),
                                  ("err", "Error SSS", 85), ("estado", "Estado", 210),
                                  ("corr", "Corrección propuesta (original → corregido)", 640),
                                  ("pend", "Qué falta", 110)], altura=9, seleccion="extended",
                           on_doble_click=self._abrir)
        self.t_det.pack(fill="both", expand=True)
        self._lineas = []

    def actualizar_archivos(self) -> None:
        partes = []
        if self.app.txt_err:
            partes.append(f"ERR: {self.app.txt_err.nombre} ({len(self.app.txt_err.registros):,} líneas)".replace(",", "."))
        if self.app.txt_ok:
            partes.append(f"OK: {self.app.txt_ok.nombre} ({len(self.app.txt_ok.registros):,} líneas)".replace(",", "."))
        self.lbl_archivos.config(text="   ·   ".join(partes) or "Ningún TXT cargado.")

    def mostrar(self, cruce: Optional[ResultadoCruce]) -> None:
        self.actualizar_archivos()
        self.cruce = cruce
        if cruce is None:
            for t in self.tarjetas.values():
                t.set("–")
            self.t_cod.limpiar()
            self.t_det.limpiar()
            if self.app.txt_err and self.app.resultado is None:
                self.aviso.mostrar("TXT cargado. Ahora analizá el Excel ORIGINAL en la pestaña «1 · Balancear» "
                                   "para cruzar la información.", "warn")
            return
        self.tarjetas["total"].set(cruce.total_err)
        for k in (PROPUESTA, APLICADA_TXT, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS):
            self.tarjetas[k].set(cruce.por_estado.get(k, 0))
        n_prop = cruce.por_estado.get(PROPUESTA, 0)
        if n_prop:
            extra = (f" Ojo: además {cruce.aceptadas_que_cambian} líneas ACEPTADAS por la SSS pertenecen a esos grupos y "
                     "también cambian." if cruce.aceptadas_que_cambian else "")
            self.aviso.mostrar(f"{n_prop} líneas rechazadas tienen una corrección propuesta. Revisala en «Corrección "
                               f"propuesta» y presioná «Corregir…» para aplicarla.{extra}", "info")
        elif cruce.por_estado.get(PENDIENTE_MANUAL, 0):
            self.aviso.mostrar("Quedan líneas que requieren corrección manual en el Excel original (columna «Qué falta»).",
                               "error")
        else:
            self.aviso.mostrar("No quedan correcciones pendientes para las líneas rechazadas. "
                               "Guardá el Excel en la pestaña «1 · Balancear» (Paso 3).", "ok")
        filas = []
        for cod, n in sorted(cruce.por_codigo.items()):
            c = CODIGOS.get(cod)
            filas.append((cod, (cod, n, c.resuelve if c else "", c.descripcion if c else "No figura en el instructivo"), ()))
        self.t_cod.cargar(filas)
        self.cb_cod.config(values=["Todos"] + sorted(cruce.por_codigo))
        self.mostrar_detalle()

    def _filtrar_cod(self, cod: str) -> None:
        self.var_cod.set(cod)
        self.mostrar_detalle()

    def mostrar_detalle(self) -> None:
        cr = self.cruce
        if not cr:
            return
        est, cod = self.var_estado.get(), self.var_cod.get()
        tags = {PROPUESTA: "prop", APLICADA_TXT: "ok", YA_CUMPLE: "ok", PENDIENTE_MANUAL: "error",
                PENDIENTE_SISTEMAS: "warn", NO_ENCONTRADO: "gris"}
        self._lineas = [l for l in cr.lineas if (est == "Todos" or l.estado == est)
                        and (cod == "Todos" or cod in l.codigos_sss)]
        filas = [(str(i), (l.clave, l.cuil, l.fila or "", " ".join(l.codigos_sss), l.estado, l.correccion or "—",
                           " ".join(l.pendientes)), (tags.get(l.estado, ""),))
                 for i, l in enumerate(self._lineas)]
        self.t_det.cargar(filas)

    def _grupos_sel(self, estado_grupo: str) -> List[Grupo]:
        vistos, res = set(), []
        for iid in self.t_det.seleccionados():
            g = self._lineas[int(iid)].grupo
            if g is not None and g.estado == estado_grupo and id(g) not in vistos:
                vistos.add(id(g))
                res.append(g)
        return res

    def aplicar_sel(self) -> None:
        self.app.aplicar(self._grupos_sel(PENDIENTE), "seleccionadas")

    def aplicar_todo(self) -> None:
        if self.cruce:
            self.app.aplicar(self.cruce.grupos((PROPUESTA,)), "de las líneas rechazadas")

    def deshacer_sel(self) -> None:
        self.app.deshacer(self._grupos_sel(APLICADA))

    def _abrir(self, iid: str) -> None:
        l = self._lineas[int(iid)]
        if l.fila:
            self.app.abrir_detalle(l.fila)

    def habilitar(self, ocupado: bool) -> None:
        hay = self.cruce is not None
        for b in (self.btn_err, self.btn_ok):
            b.config(state="disabled" if ocupado else "normal")
        for b in (self.btn_aplicar_sel, self.btn_aplicar_todo, self.btn_deshacer):
            b.config(state="normal" if hay and not ocupado else "disabled")


# =====================================================================================
class TabExcel(ttk.Frame):
    """El Excel completo con los valores actuales (los colores son sólo de la pantalla)."""

    FILTROS = ["Todas", "Con corrección pendiente", "Corregidas (aplicadas)", "Con errores", "Con advertencias",
               "Con retenciones reducidas"]

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        self.app = app
        self.sucio = True
        f = fila(self)
        ttk.Label(f, text="Mostrar:").pack(side="left")
        self.var_filtro = tk.StringVar(value="Todas")
        cb = ttk.Combobox(f, textvariable=self.var_filtro, width=26, state="readonly", values=self.FILTROS)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        ttk.Label(f, text="  Buscar CUIL / clave:").pack(side="left")
        self.var_buscar = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.var_buscar, width=16)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refrescar())
        ttk.Button(f, text="Buscar", command=self.refrescar).pack(side="left")
        self.lbl = ttk.Label(f, text="", style="Sub.TLabel")
        self.lbl.pack(side="right")

        ley = fila(self, pady=(0, 4))
        for txt, bg in [("Corrección pendiente", "#e3f2fd"), ("Corregida", "#fff9c4"), ("Retenciones reducidas", "#ede1f7"),
                        ("Error", "#fde2e1"), ("Advertencia", "#fff1d6")]:
            tk.Label(ley, text=f"  {txt}  ", bg=bg, font=(FUENTE, 8)).pack(side="left", padx=(0, 6))
        ttk.Label(ley, text="Valores actuales (lo que se va a guardar). Colores sólo en pantalla. Doble clic = detalle.",
                  style="Sub.TLabel").pack(side="left", padx=8)
        self.cont = ttk.Frame(self)
        self.cont.pack(fill="both", expand=True)
        self.tabla: Optional[Tabla] = None
        self.msg = ttk.Label(self.cont, text="Analizá un Excel en la pestaña «1 · Balancear».", style="Sub.TLabel")
        self.msg.pack(pady=40)

    def filtrar(self, filtro: str) -> None:
        self.var_filtro.set(filtro)
        self.sucio = True

    def _armar_tabla(self, encabezados: List[str], muestra: List[List]) -> None:
        if self.tabla:
            self.tabla.destroy()
        self.msg.pack_forget()
        cols = [("_fila", "Fila", 55), ("_estado", "Estado", 130)]
        for i, h in enumerate(encabezados):
            largo = max([len(h or "")] + [len(texto_celda(f[i])) for f in muestra if i < len(f)])
            cols.append((f"c{i}", h or f"Col {i + 1}", max(70, min(220, largo * 8 + 24))))
        self.tabla = Tabla(self.cont, cols, altura=22, on_doble_click=lambda iid: self.app.abrir_detalle(int(iid)))
        self.tabla.pack(fill="both", expand=True)

    def refrescar(self) -> None:
        self.sucio = False
        r = self.app.resultado
        if r is None:
            return
        lote = r.lote
        if self.tabla is None or len(self.tabla.ids) != len(lote.encabezados) + 2:
            self._armar_tabla(lote.encabezados, lote.filas[:300])
        col_a_clave = {v: k for k, v in lote.columnas.items()}
        errores, advs = r.filas_con(ERROR), r.filas_con(ADVERTENCIA)
        estado_grupo = {ln.fila: g.estado for g in r.grupos.values() for ln in g.lineas}
        ret = {f for g in r.grupos.values() for f in g.retenciones_reducidas}
        filtro, q = self.var_filtro.get(), self.var_buscar.get().strip()

        filas = []
        for ln, crudo in zip(lote.lineas, lote.filas):
            eg = estado_grupo.get(ln.fila, SIN_CAMBIOS)
            if filtro == "Con corrección pendiente" and eg != PENDIENTE:
                continue
            if filtro == "Corregidas (aplicadas)" and eg != APLICADA:
                continue
            if filtro == "Con errores" and ln.fila not in errores:
                continue
            if filtro == "Con advertencias" and ln.fila not in advs:
                continue
            if filtro == "Con retenciones reducidas" and ln.fila not in ret:
                continue
            if q and q not in ln.cuil and q not in ln.clave:
                continue
            if ln.fila in errores:
                estado, tag = ("Error (corrección pendiente)" if eg == PENDIENTE else "Error"), "error"
            elif eg == APLICADA and ln.fila in ret:
                estado, tag = "Corregida (ret. reducidas)", "ret"
            elif eg == APLICADA:
                estado, tag = "Corregida", "mod"
            elif eg == PENDIENTE:
                estado, tag = "Corrección pendiente", "prop"
            elif ln.fila in advs:
                estado, tag = "Advertencia", "warn"
            else:
                estado, tag = "OK", ""
            vals = [ln.fila, estado]
            for j, v in enumerate(crudo, start=1):
                k = col_a_clave.get(j)
                vals.append(fmt(ln.monto[k]) if k in ln.monto else texto_celda(v))
            filas.append((str(ln.fila), vals, (tag,) if tag else ()))
        self.lbl.config(text=f"{len(filas):,} de {len(lote.lineas):,} líneas".replace(",", "."))
        self.tabla.cargar(filas)


# =====================================================================================
REGLAS_TEXTO = [
    ("h1", "Cómo balancea Balidaf"),
    ("p", "Balidaf trabaja sobre la PRIMERA hoja del Excel de Presmed. Primero PROPONE la corrección y "
          "sólo la aplica cuando vos lo decidís (botones «Aplicar…» / «Corregir…»)."),
    ("h2", "1. Columnas"),
    ("b", "Lee:"),
    ("code", "clave_rendicion, cuil, cod_prestac, periodo_presentacion, perio_prestac, importe_subsidiado,\n"
             "importe_solicitado, retencion_ganancias, retencion_IIBB, otras_retnciones, fdo_ppio_otras_ctas,\n"
             "reversion_import_trasl, import_devuelto_cta_sss, saldo_no_apli, recup_fdos_ppios"),
    ("b", "Puede modificar:"),
    ("code", "impor_apli_sss            (importe aplicado SSS)\n"
             "importe_transferido       (importe transferido)\n"
             "fdo_ppio_ingre_cta_disca  (fondos propios cuenta discapacidad)\n"
             "retencion_ganancias / retencion_IIBB / otras_retnciones   → SÓLO si el subsidio no alcanza a cubrirlas"),
    ("b", "Nunca modifica:"),
    ("code", "Campos 2 a 9 de la SSS (rnos, tipo_archi, periodo_presentacion, perio_prestac, cuil, cod_prestac,\n"
             "importe_subsidiado, importe_solicitado), CUIT, CBU, órdenes de pago, fechas, cheque, recibo, obs."),
    ("h2", "2. Grupos"),
    ("p", "Las líneas se agrupan como lo controla la SSS en la regla 624:"),
    ("code", "GRUPO = cuil + periodo_presentacion + perio_prestac + cod_prestac"),
    ("p", "El subsidio se informa en una línea del grupo y se reparte entre todas sus líneas."),
    ("h2", "3. Cálculo de cada grupo"),
    ("code", "SUBSIDIO        = Σ importe_subsidiado del grupo\n"
             "A_APLICAR       = SUBSIDIO − Σ (reversion_import_trasl + import_devuelto_cta_sss\n"
             "                               + saldo_no_apli + recup_fdos_ppios)\n\n"
             "Para cada línea:\n"
             "  OTROS         = fdo_ppio_otras_ctas + reversion_import_trasl + import_devuelto_cta_sss\n"
             "                  + saldo_no_apli + recup_fdos_ppios\n"
             "  TOPE          = importe_solicitado − OTROS\n"
             "  RETENCIONES   = retencion_ganancias + retencion_IIBB + otras_retnciones"),
    ("p", "Orden de reparto: primero las líneas CON retenciones (así el subsidio las cubre y el transferido "
          "nunca queda negativo), después el resto, en el orden del Excel."),
    ("code", "  impor_apli_sss            = el menor entre TOPE y lo que queda de A_APLICAR\n"
             "  si RETENCIONES > impor_apli_sss:\n"
             "      se reducen retencion_ganancias → retencion_IIBB → otras_retnciones\n"
             "      hasta que sumen impor_apli_sss   (el transferido queda en 0)\n"
             "  importe_transferido       = impor_apli_sss − RETENCIONES\n"
             "  fdo_ppio_ingre_cta_disca  = importe_solicitado − impor_apli_sss − OTROS"),
    ("h2", "4. Casos especiales"),
    ("li", "Si el grupo YA cumple las reglas 622, 623 y 624 sin importes negativos, no se toca."),
    ("li", "Si el subsidio supera lo que se puede aplicar (Σ TOPE), el grupo no se puede balancear: "
           "se informa como error B02 para revisarlo a mano."),
    ("li", "Todos los importes se calculan en centavos exactos (sin diferencias de redondeo)."),
    ("h2", "5. Reglas de la SSS que debe cumplir el resultado"),
    ("code", "622  impor_apli_sss = importe_transferido + retencion_ganancias + retencion_IIBB + otras_retnciones\n"
             "623  importe_solicitado = fdo_ppio_ingre_cta_disca + fdo_ppio_otras_ctas + impor_apli_sss\n"
             "                          + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli\n"
             "                          + recup_fdos_ppios                         (no se exige si tipo_archi = DB)\n"
             "624  Por GRUPO: Σ importe_subsidiado = Σ (impor_apli_sss + reversion_import_trasl\n"
             "                          + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)"),
    ("h2", "6. Ejemplo (caso real de la rendición 202606)"),
    ("code", "Subsidio 1.010.735,49 · Solicitado 1.364.492,91 · Retenciones 27.289,86 + 27.289,86\n"
             "Original:  aplicado 1.364.492,91  transferido 1.309.913,19  fdo. propios 0          → error 624\n"
             "Corregido: aplicado 1.010.735,49  transferido   956.155,77  fdo. propios 353.757,42 → OK"),
    ("h2", "7. Todos los controles (instructivo SSS – Anexos III y IV)"),
]


class TabReglas(ttk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        pan = ttk.Frame(self)
        pan.pack(fill="both", expand=True)
        txt = tk.Text(pan, wrap="word", relief="flat", bg="white", padx=12, pady=8, height=24)
        sb = ttk.Scrollbar(pan, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.tag_configure("h1", font=(FUENTE, 15, "bold"), foreground=AZUL, spacing3=6)
        txt.tag_configure("h2", font=(FUENTE, 12, "bold"), foreground=AZUL, spacing1=12, spacing3=4)
        txt.tag_configure("p", font=(FUENTE, 10), spacing3=4)
        txt.tag_configure("b", font=(FUENTE, 10, "bold"), spacing1=4)
        txt.tag_configure("li", font=(FUENTE, 10), lmargin1=12, lmargin2=24, spacing3=2)
        txt.tag_configure("code", font=("Consolas", 10), background="#f5f7fa", lmargin1=12, lmargin2=12,
                          spacing1=2, spacing3=6)
        for tag, contenido in REGLAS_TEXTO:
            txt.insert("end", ("•  " if tag == "li" else "") + contenido + "\n", (tag,))
        for c in CODIGOS.values():
            ctrl = "se controla con el Excel" if c.validable else "se ve con la devolución de la SSS"
            txt.insert("end", f"{c.codigo:>4}  {c.campo}: {c.descripcion}  [{c.resuelve} · {ctrl}]\n", ("li",))
        txt.configure(state="disabled")


# =====================================================================================
class DetalleLinea(tk.Toplevel):
    """Ventana con todo lo que pasa en una línea: original, corrección propuesta, valor actual y validaciones."""

    def __init__(self, app: "BalidafApp", ln: Linea):
        super().__init__(app)
        r = app.resultado
        self.title(f"Fila {ln.fila} · clave {ln.clave} · CUIL {ln.cuil}")
        self.geometry("1020x660")
        self.transient(app)
        cont = ttk.Frame(self, padding=12)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text=f"CUIL {ln.cuil}  ·  práctica {ln.texto.get('cod', '')}  ·  prestación "
                             f"{ln.grupo[2]}  ·  clave {ln.clave}", style="Paso.TLabel").pack(anchor="w")

        lf = ttk.LabelFrame(cont, text="Importes de la línea", padding=6)
        lf.pack(fill="x", pady=(8, 4))
        t = Tabla(lf, [("campo", "Campo", 240), ("col", "Columna Excel", 190), ("orig", "Original", 120),
                       ("prop", "Corrección propuesta", 150), ("act", "Actual (se guarda)", 140)], altura=9)
        t.pack(fill="x")
        filas = []
        for k in IMPORTES:
            o, p, a = ln.original[k], ln.propuesta.get(k, ln.original[k]), ln.monto[k]
            tag = ("mod",) if a != o else (("prop",) if p != o else ())
            filas.append((k, (COL[k].titulo, COL[k].encabezado, fmt(o), fmt(p) if p != o else "", fmt(a)), tag))
        t.cargar(filas)

        g = r.grupo_de_fila(ln.fila) if r else None
        if g:
            lf2 = ttk.LabelFrame(cont, text=f"Grupo regla 624 ({len(g.lineas)} línea/s) · subsidio {fmt(g.subsidio)} · "
                                            f"corrección: {g.estado}", padding=6)
            lf2.pack(fill="x", pady=4)
            t2 = Tabla(lf2, [("fila", "Fila", 60), ("clave", "Clave", 110), ("sub", "Subsidiado", 110),
                             ("sol", "Solicitado", 110), ("apli_o", "Aplicado original", 130),
                             ("apli_p", "Aplicado propuesto", 140), ("fdo", "Fdo. propios propuesto", 160)],
                       altura=min(6, len(g.lineas) + 1))
            t2.pack(fill="x")
            t2.cargar([(str(x.fila), (x.fila, x.clave, fmt(x.original["subsidiado"]), fmt(x.original["solicitado"]),
                                      fmt(x.original["apli"]), fmt(x.propuesta.get("apli", 0)),
                                      fmt(x.propuesta.get("fdo_ppio", 0))), ("info",) if x.fila == ln.fila else ())
                       for x in g.lineas])

        hs = [h for h in (r.actual if r else []) if h.fila == ln.fila]
        lf3 = ttk.LabelFrame(cont, text=f"Validaciones actuales de la línea ({len(hs)})", padding=6)
        lf3.pack(fill="both", expand=True, pady=4)
        if hs:
            t3 = Tabla(lf3, [("cod", "Código", 70), ("nivel", "Nivel", 90), ("det", "Detalle", 800)], altura=5)
            t3.pack(fill="both", expand=True)
            t3.cargar([(str(i), (h.codigo, h.nivel, h.detalle), (NIVEL_TAG.get(h.nivel, ""),)) for i, h in enumerate(hs)])
        else:
            tk.Label(lf3, text="✔ La línea cumple todas las reglas de la SSS.", fg=VERDE, bg="white").pack(anchor="w")
        ttk.Button(cont, text="Cerrar", command=self.destroy).pack(anchor="e", pady=(6, 0))
