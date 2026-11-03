"""Pestañas de la ventana principal."""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict, List, Optional

from ..balanceo import APLICADA, PENDIENTE, SIN_CAMBIOS, TIPOS, Grupo, tipo_correccion
from ..devolucion import (APLICADA_TXT, ESTADOS, NO_ENCONTRADO, PENDIENTE_MANUAL,
                          PENDIENTE_SISTEMAS, PROPUESTA, YA_CUMPLE, ResultadoCruce)
from ..excel_io import Linea, texto_celda
from ..montos import fmt
from ..schema import CODIGOS, COL, IMPORTES
from ..validacion import ADVERTENCIA, ERROR, INFO
from .widgets import (AZUL, FUENTE, NARANJA, ROJO, VERDE, Aviso, Ayuda, ComboFiltro, Tabla, Tarjeta,
                      fila)

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
def _texto_ln(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class TabBalancear(ttk.Frame):
    """Paso 1: elegir Excel → Analizar → revisar la corrección (filtrada por tipo) → aplicar → guardar."""

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        self.app = app
        self.f_estado = PENDIENTE
        self.f_tipo = "Todos"

        # ---- Paso 1
        ttk.Label(self, text="Paso 1 · Elegí el Excel ORIGINAL de Presmed y presioná «Analizar»",
                  style="Paso.TLabel").pack(anchor="w")
        f = fila(self, pady=(4, 8))
        self.var_ruta = tk.StringVar()
        ttk.Entry(f, textvariable=self.var_ruta).pack(side="left", fill="x", expand=True)
        b = ttk.Button(f, text="Examinar…", command=app.on_examinar)
        b.pack(side="left", padx=6)
        Ayuda(b, "Elegí el Excel tal como lo da Presmed, SIN balancear.")
        self.btn_analizar = ttk.Button(f, text="Analizar", style="Accent.TButton", command=app.on_analizar)
        self.btn_analizar.pack(side="left")
        Ayuda(self.btn_analizar, "Lee el Excel, revisa las reglas de la SSS y calcula la corrección.\n"
                                 "No modifica nada: sólo propone.")

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
        ttk.Label(self, text="Paso 2 · Revisá las correcciones propuestas y aplicalas", style="Paso.TLabel").pack(anchor="w")
        der = cuerpo = ttk.Frame(self)
        der.pack(fill="both", expand=True, pady=(4, 0))
        bus = fila(der, pady=(0, 4))
        self.cb_estado = ComboFiltro(bus, "Estado:", 24, lambda v: self._elegir_filtro("estado", v))
        self.cb_estado.pack(side="left")
        self.cb_tipo = ComboFiltro(bus, "   Tipo de corrección:", 32, lambda v: self._elegir_filtro("tipo", v))
        self.cb_tipo.pack(side="left")
        ttk.Label(bus, text="   Buscar CUIL o clave:").pack(side="left")
        self.var_buscar = tk.StringVar()
        e = ttk.Entry(bus, textvariable=self.var_buscar, width=16)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refrescar_grupos())
        ttk.Button(bus, text="Buscar", command=self.refrescar_grupos).pack(side="left")
        ttk.Button(bus, text="Limpiar", command=lambda: (self.var_buscar.set(""), self.refrescar_grupos())).pack(side="left", padx=4)

        acc = fila(der, pady=(0, 4))
        self.btn_aplicar_sel = ttk.Button(acc, text="✔ Aplicar seleccionadas", command=self.aplicar_sel)
        self.btn_aplicar_sel.pack(side="left")
        Ayuda(self.btn_aplicar_sel, "Aplica la corrección sólo a los grupos marcados (Ctrl o Shift para marcar varios).")
        self.btn_aplicar_lista = ttk.Button(acc, text="✔ Aplicar todas las de la lista", command=self.aplicar_lista)
        self.btn_aplicar_lista.pack(side="left", padx=6)
        Ayuda(self.btn_aplicar_lista, "Aplica todas las correcciones PENDIENTES que se ven ahora en la lista\n"
                                      "(respeta el filtro y la búsqueda).")
        self.btn_deshacer = ttk.Button(acc, text="↶ Deshacer seleccionadas", command=self.deshacer_sel)
        self.btn_deshacer.pack(side="left")
        Ayuda(self.btn_deshacer, "Vuelve los grupos marcados a sus valores originales.")
        self.lbl_sel = ttk.Label(acc, text="", style="Sub.TLabel")
        self.lbl_sel.pack(side="left", padx=10)
        self.lbl_resumen = ttk.Label(acc, text="", style="Sub.TLabel")
        self.lbl_resumen.pack(side="right")

        pan = ttk.PanedWindow(der, orient="vertical")
        pan.pack(fill="both", expand=True)
        self.t_grupos = Tabla(pan, [("estado", "Estado", 80), ("tipo", "Tipo de corrección", 210),
                                    ("cuil", "CUIL", 100), ("cod", "Práctica", 62), ("pres", "Prestación", 76),
                                    ("n", "Líneas", 52), ("sub", "Subsidio", 105), ("apli_o", "Aplicado original", 120),
                                    ("apli_n", "Aplicado corregido", 125), ("dif", "Diferencia", 105),
                                    ("motivo", "Errores SSS", 85)], altura=8, seleccion="extended")
        self.t_grupos.tree.bind("<<TreeviewSelect>>", lambda e: self.mostrar_detalle())
        pan.add(self.t_grupos, weight=3)
        det = ttk.Frame(pan)
        self.lbl_det = ttk.Label(det, text="Seleccioná un grupo para ver el detalle línea por línea (original → corregido).",
                                 style="Paso.TLabel")
        self.lbl_det.pack(anchor="w", pady=(4, 2))
        self.t_det = Tabla(det, [("fila", "Fila", 55), ("clave", "Clave", 105), ("sol", "Solicitado", 105),
                                 ("ret", "Retenciones", 170), ("apli", "Aplicado (impor_apli_sss)", 210),
                                 ("tr", "Transferido (importe_transferido)", 230),
                                 ("fdo", "Fondos propios (fdo_ppio_ingre_cta_disca)", 250)], altura=4,
                           on_doble_click=lambda iid: app.abrir_detalle(int(iid)))
        self.t_det.pack(fill="both", expand=True)
        pan.add(det, weight=2)

        # ---- Paso 3 (siempre visible abajo, aunque la ventana sea chica)
        f3 = ttk.Frame(self)
        f3.pack(side="bottom", fill="x", pady=(8, 0), before=cuerpo)
        ttk.Label(f3, text="Paso 3 · ", style="Paso.TLabel").pack(side="left")
        self.btn_guardar = ttk.Button(f3, text="💾 Guardar Excel para Presmed", style="Ok.TButton",
                                      command=app.on_guardar)
        self.btn_guardar.pack(side="left")
        Ayuda(self.btn_guardar, "Guarda <archivo>_balidaf.xlsx con las correcciones APLICADAS.\n"
                                "Sin colores ni hojas nuevas. El Excel original no se modifica.")
        self.btn_informe = ttk.Button(f3, text="Exportar informe (opcional)…", command=app.on_informe)
        self.btn_informe.pack(side="left", padx=8)
        Ayuda(self.btn_informe, "Excel APARTE con el detalle de cambios y validaciones. No se carga en Presmed.")
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
            extra = (f" Además hay {r.errores_propuesta} errores para corregir a mano (pestaña «Ver Excel», "
                     "filtro «Con errores»).") if r.errores_propuesta else " Si aplicás todas, quedan 0 errores."
            self.aviso.mostrar(f"El Excel tiene {_texto_ln(r.errores_actuales)} errores. Balidaf propone "
                               f"{_texto_ln(pend)} correcciones: revisalas (podés filtrar por tipo y ordenar por "
                               f"cualquier columna) y aplicalas.{extra}", "info")
        else:
            self.aviso.mostrar(f"Quedan {r.errores_actuales} errores que el balanceo no puede corregir: hay que "
                               "corregirlos en el Excel original (pestaña «Ver Excel», filtro «Con errores»).", "error")
        self.refrescar_grupos()

    def _elegir_filtro(self, seccion: str, valor: str) -> None:
        if seccion == "estado":
            self.f_estado = valor
        else:
            self.f_tipo = valor
        self.refrescar_grupos()

    def _cargar_filtros(self) -> None:
        r = self.app.resultado
        grupos = [g for g in r.grupos.values() if g.estado in (PENDIENTE, APLICADA)]
        por_estado = {PENDIENTE: 0, APLICADA: 0}
        for g in grupos:
            por_estado[g.estado] += 1
        en_estado = [g for g in grupos if self.f_estado == "Todas" or g.estado == self.f_estado]
        por_tipo = {t: 0 for t in TIPOS}
        for g in en_estado:
            por_tipo[tipo_correccion(g)] += 1
        self.cb_estado.cargar([(PENDIENTE, "Pendientes de aplicar", por_estado[PENDIENTE]),
                               (APLICADA, "Aplicadas", por_estado[APLICADA]), ("Todas", "Todas", len(grupos))],
                              self.f_estado)
        self.cb_tipo.cargar([("Todos", "Todos los tipos", len(en_estado))]
                            + [(t, t, por_tipo[t]) for t in TIPOS if por_tipo[t] or t == self.f_tipo], self.f_tipo)

    def refrescar_grupos(self) -> None:
        r = self.app.resultado
        if r is None:
            return
        self._cargar_filtros()
        q = self.var_buscar.get().strip()
        estados = (PENDIENTE, APLICADA) if self.f_estado == "Todas" else (self.f_estado,)
        self._grupos_vista = [g for g in r.grupos.values() if g.estado in estados
                              and (self.f_tipo == "Todos" or tipo_correccion(g) == self.f_tipo)
                              and (not q or q in g.clave[0] or any(q in ln.clave for ln in g.lineas))]
        filas, dif_total, n_lineas = [], 0, 0
        for i, g in enumerate(self._grupos_vista):
            cuil, _, pres, cod = g.clave
            apli_o = sum(ln.original["apli"] for ln in g.lineas)
            apli_n = sum(ln.propuesta["apli"] for ln in g.lineas)
            dif_total += apli_n - apli_o
            n_lineas += len(g.lineas)
            filas.append((str(i), (g.estado, tipo_correccion(g), cuil, cod, pres, len(g.lineas), fmt(g.subsidio),
                                   fmt(apli_o), fmt(apli_n), fmt(apli_n - apli_o), _motivo(r, g)),
                          (ESTADO_TAG.get(g.estado, ""),)))
        self.lbl_resumen.config(text=f"{_texto_ln(len(filas))} grupos · {_texto_ln(n_lineas)} líneas · "
                                     f"diferencia en aplicado: {fmt(dif_total)}")
        pend_vista = sum(1 for g in self._grupos_vista if g.estado == PENDIENTE)
        self.btn_aplicar_lista.config(text=f"✔ Aplicar todas las de la lista ({_texto_ln(pend_vista)})")
        self.lbl_sel.config(text="")
        self.t_grupos.cargar(filas)
        self.t_det.limpiar()
        self.lbl_det.config(text="Seleccioná un grupo para ver el detalle línea por línea (original → corregido).")

    def _sel(self) -> List[Grupo]:
        return [self._grupos_vista[int(i)] for i in self.t_grupos.seleccionados()]

    def mostrar_detalle(self) -> None:
        sel = self._sel()
        self.t_det.limpiar()
        if not sel:
            self.lbl_sel.config(text="")
            return
        self.lbl_sel.config(text=f"Seleccionados: {len(sel)} grupos · {sum(len(g.lineas) for g in sel)} líneas")
        g = sel[0]
        apli_o = sum(ln.original["apli"] for ln in g.lineas)
        self.lbl_det.config(text=f"CUIL {g.clave[0]} · práctica {g.clave[3]} · prestación {g.clave[2]}   │   "
                                 f"Subsidio {fmt(g.subsidio)} · aplicado original {fmt(apli_o)} · "
                                 f"{tipo_correccion(g)}")
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
        self.app.aplicar([g for g in self._sel() if g.estado == PENDIENTE], "a los grupos seleccionados")

    def aplicar_lista(self) -> None:
        tipo = "" if self.f_tipo == "Todos" else f" de tipo «{self.f_tipo}»"
        self.app.aplicar([g for g in self._grupos_vista if g.estado == PENDIENTE], f"a todos los grupos de la lista{tipo}")

    def deshacer_sel(self) -> None:
        self.app.deshacer([g for g in self._sel() if g.estado == APLICADA])

    def habilitar(self, ocupado: bool) -> None:
        r = self.app.resultado
        hay = r is not None and not r.lote.faltantes
        self.btn_analizar.config(state="disabled" if ocupado else "normal")
        for b in (self.btn_aplicar_sel, self.btn_aplicar_lista, self.btn_deshacer, self.btn_guardar):
            b.config(state="normal" if hay and not ocupado else "disabled")
        self.btn_informe.config(state="normal" if r and not ocupado else "disabled")


# =====================================================================================
class TabDevolucion(ttk.Frame):
    """Cruzar la devolución de la SSS, ver la corrección propuesta de cada rechazo y decidir aplicarla."""

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=(14, 10))
        self.app = app
        self.cruce: Optional[ResultadoCruce] = None
        self.f_estado = "Todos"
        self.f_cod = "Todos"

        ttk.Label(self, text="1 · Analizá el Excel original en «1 · Balancear»   ›   2 · Cargá el TXT de errores de la SSS"
                             "   ›   3 · Revisá y decidí qué corregir", style="Paso.TLabel").pack(anchor="w")
        f = fila(self, pady=(6, 6))
        self.btn_err = ttk.Button(f, text="Cargar TXT de errores (_ERR)…", style="Accent.TButton",
                                  command=lambda: app.on_cargar_txt("ERR"))
        self.btn_err.pack(side="left")
        Ayuda(self.btn_err, "Archivo ######-AAAAMM_DR.DEVOLUCION_ERR.txt que devuelve la SSS.")
        self.btn_ok = ttk.Button(f, text="Cargar TXT aceptados (_OK) (opcional)…", command=lambda: app.on_cargar_txt("OK"))
        self.btn_ok.pack(side="left", padx=6)
        Ayuda(self.btn_ok, "Opcional: permite saber cuántas líneas ACEPTADAS también cambian al corregir.")
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

        der = ttk.Frame(self)
        der.pack(fill="both", expand=True)
        bus = fila(der, pady=(0, 4))
        self.cb_estado = ComboFiltro(bus, "Estado:", 34, lambda v: self._elegir_filtro("estado", v))
        self.cb_estado.pack(side="left")
        self.cb_cod = ComboFiltro(bus, "   Error SSS:", 26, lambda v: self._elegir_filtro("cod", v))
        self.cb_cod.pack(side="left")
        ttk.Label(bus, text="   Buscar CUIL o clave:").pack(side="left")
        self.var_buscar = tk.StringVar()
        e = ttk.Entry(bus, textvariable=self.var_buscar, width=16)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.mostrar_detalle())
        ttk.Button(bus, text="Buscar", command=self.mostrar_detalle).pack(side="left")
        ttk.Button(bus, text="Limpiar", command=lambda: (self.var_buscar.set(""), self.mostrar_detalle())).pack(side="left", padx=4)

        acc = fila(der, pady=(0, 4))
        self.btn_aplicar_sel = ttk.Button(acc, text="✔ Corregir seleccionadas en el Excel", command=self.aplicar_sel)
        self.btn_aplicar_sel.pack(side="left")
        Ayuda(self.btn_aplicar_sel, "Aplica la corrección propuesta a las líneas marcadas.\n"
                                    "Se corrige todo el grupo de la línea (CUIL + períodos + práctica).")
        self.btn_aplicar_lista = ttk.Button(acc, text="✔ Corregir todas las de la lista", command=self.aplicar_lista)
        self.btn_aplicar_lista.pack(side="left", padx=6)
        Ayuda(self.btn_aplicar_lista, "Aplica la corrección a todas las líneas con propuesta que se ven en la lista.")
        self.btn_deshacer = ttk.Button(acc, text="↶ Deshacer seleccionadas", command=self.deshacer_sel)
        self.btn_deshacer.pack(side="left")
        self.lbl_resumen = ttk.Label(acc, text="", style="Sub.TLabel")
        self.lbl_resumen.pack(side="right")

        pan = ttk.PanedWindow(der, orient="vertical")
        pan.pack(fill="both", expand=True)
        self.t_det = Tabla(pan, [("clave", "Clave", 100), ("cuil", "CUIL", 100), ("fila", "Fila", 50),
                                 ("err", "Error SSS", 80), ("estado", "Estado", 215),
                                 ("corr", "Corrección propuesta (original → corregido)", 600),
                                 ("pend", "Qué falta", 100)], altura=8, seleccion="extended",
                           on_doble_click=self._abrir)
        self.t_det.tree.bind("<<TreeviewSelect>>", lambda e: self._mostrar_linea())
        pan.add(self.t_det, weight=3)
        caja = ttk.Frame(pan)
        ttk.Label(caja, text="Detalle de la línea seleccionada", style="Paso.TLabel").pack(anchor="w", pady=(4, 2))
        self.txt = tk.Text(caja, height=6, wrap="word", relief="flat", bg="#f5f7fa", padx=10, pady=6,
                           font=(FUENTE, 10))
        self.txt.tag_configure("b", font=(FUENTE, 10, "bold"))
        self.txt.tag_configure("rojo", foreground=ROJO)
        self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")
        pan.add(caja, weight=1)
        self._lineas = []

    # ------------------------------------------------------------------
    def actualizar_archivos(self) -> None:
        partes = []
        if self.app.txt_err:
            partes.append(f"ERR: {self.app.txt_err.nombre} ({_texto_ln(len(self.app.txt_err.registros))} líneas)")
        if self.app.txt_ok:
            partes.append(f"OK: {self.app.txt_ok.nombre} ({_texto_ln(len(self.app.txt_ok.registros))} líneas)")
        self.lbl_archivos.config(text="   ·   ".join(partes) or "Ningún TXT cargado.")

    def mostrar(self, cruce: Optional[ResultadoCruce]) -> None:
        self.actualizar_archivos()
        self.cruce = cruce
        if cruce is None:
            for t in self.tarjetas.values():
                t.set("–")
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
            extra = (f" Ojo: {_texto_ln(cruce.aceptadas_que_cambian)} líneas ACEPTADAS por la SSS están en esos grupos y "
                     "también cambian." if cruce.aceptadas_que_cambian else "")
            self.aviso.mostrar(f"{_texto_ln(n_prop)} líneas rechazadas tienen una corrección propuesta. Revisala y "
                               f"presioná «Corregir…» para aplicarla.{extra}", "info")
        elif cruce.por_estado.get(PENDIENTE_MANUAL, 0):
            self.aviso.mostrar("Quedan líneas que requieren corrección manual en el Excel original (columna «Qué falta»).",
                               "error")
        else:
            self.aviso.mostrar("No quedan correcciones pendientes para las líneas rechazadas. "
                               "Guardá el Excel en la pestaña «1 · Balancear» (Paso 3).", "ok")
        self.mostrar_detalle()

    def _elegir_filtro(self, seccion: str, valor: str) -> None:
        if seccion == "estado":
            self.f_estado = valor
        else:
            self.f_cod = valor
        self.mostrar_detalle()

    def _cargar_filtros(self) -> None:
        cr = self.cruce
        en_estado = [l for l in cr.lineas if self.f_estado == "Todos" or l.estado == self.f_estado]
        cods = {}
        for l in en_estado:
            for c in l.codigos_sss:
                cods[c] = cods.get(c, 0) + 1
        self.cb_estado.cargar([("Todos", "Todos", len(cr.lineas))]
                              + [(e, e, cr.por_estado.get(e, 0)) for e in ESTADOS if cr.por_estado.get(e, 0)],
                              self.f_estado)
        self.cb_cod.cargar([("Todos", "Todos los errores", len(en_estado))]
                           + [(c, f"{c} · {CODIGOS[c].campo.title() if c in CODIGOS else ''}", n)
                              for c, n in sorted(cods.items())], self.f_cod)

    def mostrar_detalle(self) -> None:
        cr = self.cruce
        if not cr:
            return
        self._cargar_filtros()
        q = self.var_buscar.get().strip()
        tags = {PROPUESTA: "prop", APLICADA_TXT: "ok", YA_CUMPLE: "ok", PENDIENTE_MANUAL: "error",
                PENDIENTE_SISTEMAS: "warn", NO_ENCONTRADO: "gris"}
        self._lineas = [l for l in cr.lineas if (self.f_estado == "Todos" or l.estado == self.f_estado)
                        and (self.f_cod == "Todos" or self.f_cod in l.codigos_sss)
                        and (not q or q in l.cuil or q in l.clave)]
        filas = [(str(i), (l.clave, l.cuil, l.fila or "", " ".join(l.codigos_sss), l.estado, l.correccion or "—",
                           " ".join(l.pendientes)), (tags.get(l.estado, ""),))
                 for i, l in enumerate(self._lineas)]
        n_prop = sum(1 for l in self._lineas if l.estado == PROPUESTA)
        self.lbl_resumen.config(text=f"{_texto_ln(len(filas))} líneas · {_texto_ln(n_prop)} con corrección propuesta")
        self.btn_aplicar_lista.config(text=f"✔ Corregir todas las de la lista ({_texto_ln(n_prop)})")
        self.t_det.cargar(filas)
        self._escribir("Seleccioná una línea para ver la explicación completa del error y de la corrección.")

    def _escribir(self, *partes) -> None:
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for p in partes:
            if isinstance(p, tuple):
                self.txt.insert("end", p[0], p[1])
            else:
                self.txt.insert("end", p)
        self.txt.configure(state="disabled")

    def _mostrar_linea(self) -> None:
        sel = self.t_det.seleccionados()
        if not sel:
            return
        l = self._lineas[int(sel[0])]
        partes = [(f"Clave {l.clave} · CUIL {l.cuil} · fila {l.fila or '—'} · {l.estado}\n", "b")]
        for c in l.codigos_sss:
            d = CODIGOS.get(c)
            partes.append((f"Error {c}: ", "b"))
            partes.append(f"{d.descripcion if d else 'No figura en el instructivo'}"
                          + (f"  →  {d.accion} (lo resuelve: {d.resuelve})" if d else "") + "\n")
        if l.correccion:
            partes += [("Corrección propuesta: ", "b"), l.correccion + "\n"]
        if l.pendientes:
            partes.append(("Qué falta (no se corrige solo): ", ("b", "rojo")))
            partes.append(" | ".join(f"{c}: {CODIGOS[c].descripcion}" for c in l.pendientes if c in CODIGOS) + "\n")
        if len(sel) > 1:
            partes.append((f"\n({len(sel)} líneas seleccionadas)", "b"))
        self._escribir(*partes)

    def _grupos_de(self, lineas, estado_grupo: str) -> List[Grupo]:
        vistos, res = set(), []
        for l in lineas:
            g = l.grupo
            if g is not None and g.estado == estado_grupo and id(g) not in vistos:
                vistos.add(id(g))
                res.append(g)
        return res

    def aplicar_sel(self) -> None:
        lineas = [self._lineas[int(i)] for i in self.t_det.seleccionados()]
        self.app.aplicar(self._grupos_de(lineas, PENDIENTE), "a las líneas seleccionadas")

    def aplicar_lista(self) -> None:
        self.app.aplicar(self._grupos_de([l for l in self._lineas if l.estado == PROPUESTA], PENDIENTE),
                         "a todas las líneas rechazadas de la lista")

    def deshacer_sel(self) -> None:
        lineas = [self._lineas[int(i)] for i in self.t_det.seleccionados()]
        self.app.deshacer(self._grupos_de(lineas, APLICADA))

    def _abrir(self, iid: str) -> None:
        l = self._lineas[int(iid)]
        if l.fila:
            self.app.abrir_detalle(l.fila)

    def habilitar(self, ocupado: bool) -> None:
        hay = self.cruce is not None
        for b in (self.btn_err, self.btn_ok):
            b.config(state="disabled" if ocupado else "normal")
        for b in (self.btn_aplicar_sel, self.btn_aplicar_lista, self.btn_deshacer):
            b.config(state="normal" if hay and not ocupado else "disabled")


# =====================================================================================
class TabExcel(ttk.Frame):
    """El Excel completo con los valores actuales (los colores son sólo de la pantalla)."""

    VISTAS = ["Importes y datos clave", "Todas las columnas del Excel"]
    CLAVE = ["clave", "cuil", "cod", "per_prest", "cuit_cbu", "cbu", "subsidiado", "solicitado", "ret_gan",
             "ret_iibb", "ret_otras", "apli", "transferido", "fdo_ppio"]
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
        ttk.Label(f, text="   Columnas:").pack(side="left")
        self.var_cols = tk.StringVar(value=self.VISTAS[0])
        cb2 = ttk.Combobox(f, textvariable=self.var_cols, width=26, state="readonly", values=self.VISTAS)
        cb2.pack(side="left", padx=4)
        cb2.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
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

    def _indices(self, lote) -> List[int]:
        """Columnas del Excel (índice 0-based) a mostrar según la vista elegida."""
        if self.var_cols.get() == self.VISTAS[0]:
            return [lote.columnas[k] - 1 for k in self.CLAVE if k in lote.columnas]
        return list(range(len(lote.encabezados)))

    def _armar_tabla(self, encabezados: List[str], muestra: List[List], indices: List[int]) -> None:
        if self.tabla:
            self.tabla.destroy()
        self.msg.pack_forget()
        cols = [("_fila", "Fila", 55), ("_estado", "Estado", 205)]
        for i in indices:
            h = encabezados[i]
            largo = max([len(h or "")] + [len(texto_celda(f[i])) for f in muestra if i < len(f)])
            cols.append((f"c{i}", h or f"Col {i + 1}", max(70, min(220, largo * 8 + 24))))
        self.tabla = Tabla(self.cont, cols, altura=22, on_doble_click=lambda iid: self.app.abrir_detalle(int(iid)))
        self.tabla.pack(fill="both", expand=True)
        self._vista_actual = tuple(indices)

    def refrescar(self) -> None:
        self.sucio = False
        r = self.app.resultado
        if r is None:
            return
        lote = r.lote
        indices = self._indices(lote)
        if self.tabla is None or getattr(self, "_vista_actual", None) != tuple(indices):
            self._armar_tabla(lote.encabezados, lote.filas[:300], indices)
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
            for i in indices:
                k = col_a_clave.get(i + 1)
                v = crudo[i] if i < len(crudo) else None
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
