"""Pestaña «1 · Balancear»: Paso 1 (Analizar) y Paso 2 (revisar y aplicar correcciones)."""

import tkinter as tk
from typing import TYPE_CHECKING, Dict, List, Optional

from ..balanceo import APLICADA, PENDIENTE, TIPOS, Grupo, tipo_correccion
from ..montos import fmt
from ..schema import COL
from ..validacion import ERROR
from .componentes import (Aviso, BarraFina, Boton, Buscador, Caja, Circulo, Combo, EstadoVacio, Indicador, Lbl, Linea,
                          Segmentado, Tabla, fmt_n)
from .tema import F, P, al_cambiar_tema

if TYPE_CHECKING:
    from .app import BalidafApp

RET = ("ret_gan", "ret_iibb", "ret_otras")


def cambio(o: int, n: int) -> str:
    return fmt(o) if o == n else f"{fmt(o)}  →  {fmt(n)}"


def errores_sss(r, g: Grupo) -> str:
    filas = {ln.fila for ln in g.lineas}
    cods = sorted({h.codigo for h in r.antes if h.fila in filas and h.nivel == ERROR})
    return ", ".join(cods) if cods else "—"


class CampoRuta(tk.Frame):
    """Campo de ruta del Excel (fondo surface2, monoespaciada, con texto de ayuda si está vacío)."""

    AYUDA = "Ningún archivo elegido · usá «Examinar…» para elegir el Excel original de Presmed"

    def __init__(self, master, al_cambiar):
        super().__init__(master, highlightthickness=1)
        self.var = tk.StringVar()
        self.e = tk.Entry(self, textvariable=self.var, relief="flat", bd=0, font=F(12.5, mono=True))
        self.e.pack(fill="x", padx=10, ipady=6)
        self._vacio = True
        self.e.bind("<FocusIn>", lambda e: self._entrar())
        self.e.bind("<FocusOut>", lambda e: self._salir())
        self.var.trace_add("write", lambda *a: al_cambiar())
        al_cambiar_tema(self._tema)
        self._salir()

    def get(self) -> str:
        return "" if self._vacio else self.var.get().strip().strip('"')

    def set(self, ruta: str) -> None:
        self._vacio = not ruta
        self.var.set(ruta or self.AYUDA)
        self._tema()

    def _entrar(self):
        if self._vacio:
            self._vacio = False
            self.var.set("")
            self._tema()

    def _salir(self):
        if not self.var.get().strip():
            self._vacio = True
            self.var.set(self.AYUDA)
        self._tema()

    def _tema(self):
        self.config(bg=P["surface2"], highlightbackground=P["line"], highlightcolor=P["accent"])
        self.e.config(bg=P["surface2"], fg=P["ink3"] if self._vacio else P["ink"], insertbackground=P["ink"],
                      font=F(12.5, mono=not self._vacio))


class PagBalancear(tk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padx=20, pady=12)
        self.app = app
        self.f_estado, self.f_tipo, self.q = PENDIENTE, "Todos", ""
        self._por_iid: Dict[str, Grupo] = {}
        self._foco: Optional[Grupo] = None
        al_cambiar_tema(lambda: self.config(bg=P["bg"]))

        # ---------------- Paso 1
        p1 = Caja(self, padx=14, pady=10)
        p1.pack(fill="x")
        self.c1 = Circulo(p1, "1", "actual")
        self.c1.pack(side="left", padx=(0, 10))
        Lbl(p1, "Excel original de Presmed", 13, "semibold").pack(side="left", padx=(0, 12))
        self.btn_analizar = Boton(p1, "Analizar", app.on_analizar, "primario")
        self.btn_analizar.pack(side="right")
        self.btn_examinar = Boton(p1, "Examinar…", app.on_examinar)
        self.btn_examinar.pack(side="right", padx=(8, 8))
        self.ruta = CampoRuta(p1, lambda: self.app.actualizar_botones())
        self.ruta.pack(side="left", fill="x", expand=True)

        # ---------------- Aviso + indicadores
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(10, 0))
        ind = tk.Frame(self)
        ind.pack(fill="x", pady=(10, 0))
        al_cambiar_tema(lambda: ind.config(bg=P["bg"]))
        self.k_err = Indicador(ind, "Errores en el Excel (ahora)", "err", lambda: app.ver_excel("err"))
        self.k_pend = Indicador(ind, "Correcciones pendientes", "pend", lambda: self._estado(PENDIENTE))
        self.k_apl = Indicador(ind, "Correcciones aplicadas", "ok", lambda: self._estado(APLICADA))
        self.k_man = Indicador(ind, "Errores que NO se corrigen solos", "warn", lambda: app.ver_excel("err"))
        for i, k in enumerate((self.k_err, self.k_pend, self.k_apl, self.k_man)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            ind.columnconfigure(i, weight=1, uniform="k")

        # ---------------- Paso 2
        self.p2 = Caja(self)
        self.p2.pack(fill="both", expand=True, pady=(10, 0))
        cab = tk.Frame(self.p2, padx=14, pady=9)
        cab.pack(fill="x")
        self.c2 = Circulo(cab, "2", "pendiente")
        self.c2.pack(side="left", padx=(0, 10))
        Lbl(cab, "Revisá y aplicá las correcciones", 13.5, "semibold").pack(side="left")
        Lbl(cab, "Nada cambia hasta que lo apliques. Podés deshacer hasta guardar.", 12.5, color="ink3").pack(
            side="left", padx=(10, 0))
        self.mini = BarraFina(cab, 6, "ok_fg", "line", ancho=140)
        self.mini.pack(side="right", padx=(8, 0))
        self.lbl_corr = Lbl(cab, "", 12.5, color="ink2")
        self.lbl_corr.pack(side="right")
        al_cambiar_tema(lambda: cab.config(bg=P["surface"]))
        Linea(self.p2).pack(fill="x")

        barra = tk.Frame(self.p2, padx=14, pady=8)
        barra.pack(fill="x")
        al_cambiar_tema(lambda: barra.config(bg=P["surface2"]))
        self.btn_todas = Boton(barra, "✓ Aplicar todas las de la lista", self.aplicar_lista, "primario")
        self.btn_todas.pack(side="right")
        self.btn_sel = Boton(barra, "✓ Aplicar seleccionadas", self.aplicar_sel)
        self.btn_sel.pack(side="right", padx=(6, 6))
        self.btn_undo = Boton(barra, "↶ Deshacer", self.deshacer_sel)
        self.btn_undo.pack(side="right")
        self.seg = Segmentado(barra, [(PENDIENTE, "Pendientes"), (APLICADA, "Aplicadas"), ("Todas", "Todas")],
                              self._estado, PENDIENTE)
        self.seg.pack(side="left")
        self.cb_tipo = Combo(barra, 19, self._tipo)
        self.cb_tipo.pack(side="left", padx=(10, 0))
        self.buscador = Buscador(barra, self._buscar, ancho=17)
        self.buscador.pack(side="left", padx=(10, 0))

        res = tk.Frame(self.p2, padx=14, pady=5)
        res.pack(fill="x")
        al_cambiar_tema(lambda: res.config(bg=P["surface"]))
        self.lbl_res = Lbl(res, "", 12, color="ink2")
        self.lbl_res.pack(side="left")
        self.lbl_selres = Lbl(res, "", 12, "semibold", color="accent")
        self.lbl_selres.pack(side="left", padx=(12, 0))
        self.lnk_quitar = Lbl(res, "quitar selección", 12, color="ink3", cursor="hand2")
        self.lnk_quitar.bind("<Button-1>", lambda e: self.tabla.marcar_todos(False))
        Lbl(res, "Clic en encabezado = ordenar · clic en fila = detalle · doble clic = detalle completo", 12, color="ink3").pack(side="right")

        self.pan = tk.PanedWindow(self.p2, orient="vertical", sashwidth=5, bd=0, sashrelief="flat")
        self.pan.pack(fill="both", expand=True)
        al_cambiar_tema(lambda: self.pan.config(bg=P["line_strong"]))
        self.tabla = Tabla(self.pan, [
            ("estado", "Estado", 95), ("tipo", "Tipo de corrección", 210), ("cuil", "CUIL", 115),
            ("cod", "Práctica", 70), ("pres", "Prestación", 85), ("n", "Líneas", 60, "e"),
            ("sub", "Subsidio", 120, "e"), ("ao", "Aplicado original", 135, "e"),
            ("an", "Aplicado corregido", 140, "e"), ("dif", "Diferencia", 115, "e"),
            ("err", "Errores SSS", 110, "w", True)],
            checks=True, altura=8, al_enfocar=self._enfocar, al_doble=self._doble_grupo, al_marcar=self._marcado)
        self.pan.add(self.tabla, stretch="always", minsize=120)

        det = tk.Frame(self.pan)
        al_cambiar_tema(lambda: det.config(bg=P["surface2"]))
        dcab = tk.Frame(det, padx=14, pady=7)
        dcab.pack(fill="x")
        al_cambiar_tema(lambda: dcab.config(bg=P["surface2"]))
        self.chip = Lbl(dcab, "", 11.5, "semibold", fondo="pend_bg", color="pend_fg", padx=8)
        self.lbl_g1 = Lbl(dcab, "Seleccioná un grupo para ver el detalle línea por línea (original → corregido).",
                          12.5, color="ink3", fondo="surface2")
        self.lbl_g1.pack(side="left")
        self.lbl_g2 = Lbl(dcab, "", 12.5, color="ink2", fondo="surface2")
        self.btn_grupo = Boton(dcab, "", self._accion_grupo, "chico")
        self.t_det = Tabla(det, [
            ("fila", "Fila", 55, "e"), ("clave", "Clave", 120), ("sol", "Solicitado", 120, "e"),
            ("ret", "Retenciones", 180, "e"), ("apli", "Aplicado (impor_apli_sss)", 230, "e"),
            ("tr", "Transferido (importe_transferido)", 240, "e"),
            ("fdo", "Fondos propios (fdo_ppio_ingre_cta_disca)", 270, "e", True)],
            altura=3, al_doble=lambda iid: app.abrir_detalle(int(iid)))
        self.t_det.pack(fill="both", expand=True)
        self.pan.add(det, minsize=150, height=190)

        self.vacio = EstadoVacio(self.p2)

    # ------------------------------------------------------------------ eventos de filtros
    def _estado(self, v: str) -> None:
        self.f_estado = v
        self.seg.set(v)
        self.refrescar_lista()

    def _tipo(self, v: str) -> None:
        self.f_tipo = v
        self.refrescar_lista()

    def _buscar(self, q: str) -> None:
        self.q = q
        self.refrescar_lista()

    # ------------------------------------------------------------------ pintado general
    def mostrar(self) -> None:
        r = self.app.resultado
        ocupado = self.app.ocupado
        self.btn_analizar.config(text="Volver a analizar" if r else "Analizar")
        if r is None:
            self.c1.set(estado="actual")
            self.c2.set(estado="pendiente")
            for k in (self.k_err, self.k_pend, self.k_apl, self.k_man):
                k.set("–", "")
            if ocupado:
                self.aviso.mostrar("Analizando el Excel… esto puede tardar unos segundos.", "neutro")
                self.vacio.mostrar(self.tabla, "Calculando las correcciones…",
                                   "Leyendo el Excel, revisando las reglas de la SSS y calculando la corrección de "
                                   "cada grupo.")
            else:
                self.aviso.mostrar("Todavía no se analizó ningún Excel. Elegí el archivo original de Presmed y "
                                   "presioná «Analizar».", "neutro")
                self.vacio.mostrar(self.tabla, "Todavía no hay correcciones para revisar",
                                   "Analizá el Excel original de Presmed (Paso 1). Balidaf calcula la corrección de "
                                   "cada grupo y la muestra acá para que decidas qué aplicar.")
            self.tabla.limpiar()
            self._pintar_detalle(None)
            self.lbl_corr.config(text="")
            self.mini.set(0)
            return
        self.vacio.ocultar()
        self.c1.set(estado="hecho")
        self.c2.set(estado="actual")
        pend, apl = r.grupos_con(PENDIENTE), r.grupos_con(APLICADA)
        lpend, lapl = sum(len(g.lineas) for g in pend), sum(len(g.lineas) for g in apl)
        self.k_err.set(r.errores_actuales, f"de {fmt_n(r.errores_antes)} en el original")
        self.k_pend.set(len(pend), f"grupos · {fmt_n(lpend)} líneas")
        self.k_apl.set(len(apl), f"grupos · {fmt_n(lapl)} líneas")
        self.k_man.set(r.errores_propuesta, "corregir a mano en el Excel")
        total = len(pend) + len(apl)
        self.lbl_corr.config(text=f"{fmt_n(len(apl))} de {fmt_n(total)} grupos corregidos")
        self.mini.set(100 * len(apl) / total if total else 100)
        self._pintar_aviso(r, len(pend))
        self.refrescar_lista()

    def _pintar_aviso(self, r, pend: int) -> None:
        man = r.errores_propuesta
        ver = (f"Ver los {fmt_n(man)} errores", lambda: self.app.ver_excel("err")) if man else None
        if r.lote.faltantes:
            self.aviso.mostrar("Al Excel le faltan columnas obligatorias: "
                               + ", ".join(COL[k].encabezado for k in r.lote.faltantes), "error")
        elif self.app.guardado_como and not self.app.cambios_sin_guardar:
            self.aviso.mostrar(f"Excel guardado a las {self.app.guardado_hora} como {self.app.guardado_como}. "
                               "Ya podés cargarlo en Presmed.", "ok")
        elif pend and r.errores_actuales:
            extra = f" Además hay {fmt_n(man)} errores para corregir a mano." if man else ""
            self.aviso.mostrar(f"El Excel tiene {fmt_n(r.errores_actuales)} errores. Balidaf propone "
                               f"{fmt_n(pend)} correcciones: revisalas y aplicalas.{extra}", "info", ver)
        elif pend:
            self.aviso.mostrar(f"Sin errores. Quedan {fmt_n(pend)} correcciones opcionales sin aplicar. "
                               "Podés guardar el Excel (Paso 3).", "info")
        elif r.errores_actuales:
            self.aviso.mostrar(f"Quedan {fmt_n(r.errores_actuales)} errores que el balanceo no puede corregir: hay que "
                               "corregirlos en el Excel original y volver a analizar.", "error", ver)
        else:
            self.aviso.mostrar("Sin errores. Guardá el Excel para Presmed (Paso 3).", "ok")

    # ------------------------------------------------------------------ lista de grupos
    def refrescar_lista(self) -> None:
        r = self.app.resultado
        if r is None:
            return
        grupos = list(r.grupos.values())
        self._por_iid = {f"g{i}": g for i, g in enumerate(grupos)}
        con = [(iid, g) for iid, g in self._por_iid.items() if g.estado in (PENDIENTE, APLICADA)]
        n_est = {PENDIENTE: 0, APLICADA: 0}
        for _, g in con:
            n_est[g.estado] += 1
        self.seg.set_textos({PENDIENTE: f"Pendientes {fmt_n(n_est[PENDIENTE])}",
                             APLICADA: f"Aplicadas {fmt_n(n_est[APLICADA])}", "Todas": f"Todas {fmt_n(len(con))}"})
        en_estado = [(iid, g) for iid, g in con if self.f_estado == "Todas" or g.estado == self.f_estado]
        por_tipo = {t: 0 for t in TIPOS}
        for _, g in en_estado:
            por_tipo[tipo_correccion(g)] += 1
        self.cb_tipo.cargar([("Todos", "Todos los tipos", len(en_estado))]
                            + [(t, t, por_tipo[t]) for t in TIPOS if por_tipo[t] or t == self.f_tipo], self.f_tipo)
        q = self.q
        vista = [(iid, g) for iid, g in en_estado
                 if (self.f_tipo == "Todos" or tipo_correccion(g) == self.f_tipo)
                 and (not q or q in g.clave[0] or any(q in ln.clave for ln in g.lineas))]
        filas, dif, nlin = [], 0, 0
        for iid, g in vista:
            cuil, _, pres, cod = g.clave
            ao = sum(ln.original["apli"] for ln in g.lineas)
            an = sum(ln.propuesta["apli"] for ln in g.lineas)
            dif += an - ao
            nlin += len(g.lineas)
            filas.append((iid, (g.estado, tipo_correccion(g), cuil, cod, pres, len(g.lineas), fmt(g.subsidio),
                                fmt(ao), fmt(an), fmt(an - ao), errores_sss(r, g)),
                          "pend" if g.estado == PENDIENTE else "ok"))
        self._vista = [g for _, g in vista]
        self.lbl_res.config(text=f"{fmt_n(len(filas))} grupos · {fmt_n(nlin)} líneas · diferencia en aplicado: "
                                 f"{fmt(dif)}")
        self.tabla.cargar(filas)
        if self._foco is not None and self._foco not in self._vista:
            self._pintar_detalle(None)
        elif self._foco is not None:
            self._pintar_detalle(self._foco)
        self._marcado()

    def _sel(self) -> List[Grupo]:
        return [self._por_iid[i] for i in self.tabla.marcados if i in self._por_iid]

    def _marcado(self) -> None:
        sel = self._sel()
        pend = [g for g in sel if g.estado == PENDIENTE]
        apl = [g for g in sel if g.estado == APLICADA]
        pend_lista = sum(1 for g in getattr(self, "_vista", []) if g.estado == PENDIENTE)
        self.btn_sel.config(text=f"✓ Aplicar seleccionadas ({fmt_n(len(pend))})")
        self.btn_undo.config(text=f"↶ Deshacer ({fmt_n(len(apl))})")
        self.btn_todas.config(text=f"✓ Aplicar todas las de la lista ({fmt_n(pend_lista)})")
        if sel:
            self.lbl_selres.config(text=f"Seleccionados: {fmt_n(len(sel))} grupos · "
                                        f"{fmt_n(sum(len(g.lineas) for g in sel))} líneas")
            self.lnk_quitar.pack(side="left", padx=(8, 0))
        else:
            self.lbl_selres.config(text="")
            self.lnk_quitar.pack_forget()
        libre = not self.app.ocupado and self.app.resultado is not None
        self.btn_sel.habilitar(libre and bool(pend))
        self.btn_undo.habilitar(libre and bool(apl))
        self.btn_todas.habilitar(libre and bool(pend_lista))

    # ------------------------------------------------------------------ detalle del grupo
    def _enfocar(self, iid: str) -> None:
        g = self._por_iid.get(iid)
        if g:
            self._foco = g
            self._pintar_detalle(g)

    def _doble_grupo(self, iid: str) -> None:
        g = self._por_iid.get(iid)
        if g:
            self.app.abrir_detalle(g.lineas[0].fila)

    def _pintar_detalle(self, g: Optional[Grupo]) -> None:
        self.t_det.limpiar()
        for w in (self.chip, self.lbl_g2, self.btn_grupo):
            w.pack_forget()
        if g is None:
            self._foco = None
            self.lbl_g1.config(text="Seleccioná un grupo para ver el detalle línea por línea (original → corregido).",
                               font=F(12.5))
            self.lbl_g1.set_color("ink3")
            return
        fam = "pend" if g.estado == PENDIENTE else "ok"
        self.chip.config(text=g.estado)
        self.chip._fondo, self.chip._color = f"{fam}_bg", f"{fam}_fg"
        self.chip._tema()
        self.chip.pack(side="left", padx=(0, 10), before=self.lbl_g1)
        cuil, _, pres, cod = g.clave
        self.lbl_g1.config(text=f"CUIL {cuil} · práctica {cod} · prestación {pres}", font=F(12.5, "semibold"))
        self.lbl_g1.set_color("ink")
        ao = sum(ln.original["apli"] for ln in g.lineas)
        an = sum(ln.propuesta["apli"] for ln in g.lineas)
        self.lbl_g2.config(text=f"Subsidio {fmt(g.subsidio)} · aplicado {fmt(ao)} → {fmt(an)} · {tipo_correccion(g)}")
        self.lbl_g2.pack(side="left", padx=(12, 0))
        self.btn_grupo.config(text="✓ Aplicar este grupo" if g.estado == PENDIENTE else "↶ Deshacer este grupo")
        self.btn_grupo.habilitar(not self.app.ocupado)
        self.btn_grupo.pack(side="right")
        filas = []
        for ln in g.lineas:
            o, n = ln.original, ln.propuesta
            filas.append((str(ln.fila), (ln.fila, ln.clave, fmt(o["solicitado"]),
                                         cambio(sum(o[k] for k in RET), sum(n[k] for k in RET)),
                                         cambio(o["apli"], n["apli"]), cambio(o["transferido"], n["transferido"]),
                                         cambio(o["fdo_ppio"], n["fdo_ppio"])),
                          "vio" if ln.fila in g.retenciones_reducidas else ""))
        self.t_det.cargar(filas)

    def _accion_grupo(self) -> None:
        g = self._foco
        if g is None:
            return
        if g.estado == PENDIENTE:
            self.app.aplicar([g])
        else:
            self.app.deshacer([g])

    # ------------------------------------------------------------------ acciones
    def aplicar_sel(self) -> None:
        self.app.aplicar([g for g in self._sel() if g.estado == PENDIENTE])

    def aplicar_lista(self) -> None:
        self.app.aplicar([g for g in self._vista if g.estado == PENDIENTE])

    def deshacer_sel(self) -> None:
        self.app.deshacer([g for g in self._sel() if g.estado == APLICADA])

    def habilitar(self, ocupado: bool) -> None:
        tiene_ruta = bool(self.ruta.get())
        self.btn_analizar.habilitar(not ocupado and tiene_ruta)
        self.btn_examinar.habilitar(not ocupado)
        self._marcado()
        if self._foco is not None:
            self.btn_grupo.habilitar(not ocupado)
