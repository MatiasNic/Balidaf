"""Pestaña «2 · Devolución SSS»: cruzar los rechazos de la SSS, ver la corrección y decidir aplicarla."""

import tkinter as tk
from typing import TYPE_CHECKING, Dict, List, Optional

from ..balanceo import APLICADA, PENDIENTE, Grupo
from ..devolucion import (APLICADA_TXT, ESTADOS, NO_ENCONTRADO, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS,
                          PROPUESTA, YA_CUMPLE, CruceLinea)
from ..schema import CODIGOS
from .componentes import (Aviso, Boton, Buscador, Caja, Circulo, Combo, EstadoVacio, Indicador, Lbl, Linea,
                          Tabla, fmt_n)
from .tema import F, P, al_cambiar_tema

if TYPE_CHECKING:
    from .app import BalidafApp

FAMILIA = {PROPUESTA: "pend", APLICADA_TXT: "ok", PENDIENTE_MANUAL: "err", PENDIENTE_SISTEMAS: "warn",
           YA_CUMPLE: "ok", NO_ENCONTRADO: "neu"}


class PagDevolucion(tk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padx=20, pady=12)
        self.app = app
        self.f_estado, self.f_cod, self.q = "Todos", "Todos", ""
        self._lineas: Dict[str, CruceLinea] = {}
        self._vista: List[str] = []
        self._foco: Optional[str] = None
        al_cambiar_tema(lambda: self.config(bg=P["bg"]))

        # ---------------- guía
        guia = Caja(self, padx=14, pady=10)
        guia.pack(fill="x")
        self.circ = []
        for i, txt in enumerate(("Analizá el Excel original", "Cargá el TXT de errores de la SSS",
                                 "Revisá y decidí qué corregir")):
            if i:
                Lbl(guia, "›", 13, color="ink3").pack(side="left", padx=10)
            c = Circulo(guia, str(i + 1), "pendiente")
            c.pack(side="left", padx=(0, 8))
            lb = Lbl(guia, txt, 13, "semibold" if i == 2 else "normal", color="ink2")
            lb.pack(side="left")
            self.circ.append((c, lb))
        self.btn_err = Boton(guia, "Cargar TXT de errores (_ERR)…", lambda: app.on_cargar_txt("ERR"), "primario")
        self.btn_err.pack(side="right")
        self.btn_ok = Boton(guia, "Cargar TXT aceptados (_OK)…", lambda: app.on_cargar_txt("OK"))
        self.btn_ok.pack(side="right", padx=(8, 8))
        self.lbl_txt = Lbl(guia, "", 12, color="ink2", mono=True)
        self.lbl_txt.pack(side="right", padx=(12, 0))

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(10, 0))

        ind = tk.Frame(self)
        ind.pack(fill="x", pady=(10, 0))
        al_cambiar_tema(lambda: ind.config(bg=P["bg"]))
        self.kpis = {}
        for i, (k, t, fam) in enumerate([("Todos", "Líneas rechazadas", "accent"),
                                         (PROPUESTA, "Con corrección propuesta", "pend"),
                                         (APLICADA_TXT, "Corrección aplicada", "ok"),
                                         (PENDIENTE_MANUAL, "Requieren corrección manual", "err"),
                                         (PENDIENTE_SISTEMAS, "Las resuelve Sistemas", "warn")]):
            w = Indicador(ind, t, fam, lambda k=k: self._estado(k))
            w.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            ind.columnconfigure(i, weight=1, uniform="k")
            self.kpis[k] = w

        # ---------------- tabla
        self.card = Caja(self)
        self.card.pack(fill="both", expand=True, pady=(10, 0))
        barra = tk.Frame(self.card, padx=14, pady=8)
        barra.pack(fill="x")
        al_cambiar_tema(lambda: barra.config(bg=P["surface2"]))
        self.btn_todas = Boton(barra, "✓ Corregir todas las de la lista", self.aplicar_lista, "primario")
        self.btn_todas.pack(side="right")
        self.btn_sel = Boton(barra, "✓ Corregir seleccionadas", self.aplicar_sel)
        self.btn_sel.pack(side="right", padx=(6, 6))
        self.btn_undo = Boton(barra, "↶ Deshacer", self.deshacer_sel)
        self.btn_undo.pack(side="right")
        self.cb_estado = Combo(barra, 30, self._estado)
        self.cb_estado.pack(side="left")
        self.cb_cod = Combo(barra, 22, self._cod)
        self.cb_cod.pack(side="left", padx=(10, 0))
        self.buscador = Buscador(barra, self._buscar, ancho=17)
        self.buscador.pack(side="left", padx=(10, 0))
        Linea(self.card).pack(fill="x")
        res = tk.Frame(self.card, padx=14, pady=5)
        res.pack(fill="x")
        al_cambiar_tema(lambda: res.config(bg=P["surface"]))
        self.lbl_res = Lbl(res, "", 12, color="ink2")
        self.lbl_res.pack(side="left")
        self.lbl_selres = Lbl(res, "", 12, "semibold", color="accent")
        self.lbl_selres.pack(side="left", padx=(12, 0))
        Lbl(res, "Clic = explicación abajo · doble clic = detalle de la línea", 12, color="ink3").pack(side="right")

        self.pan = tk.PanedWindow(self.card, orient="vertical", sashwidth=5, bd=0, sashrelief="flat")
        self.pan.pack(fill="both", expand=True)
        al_cambiar_tema(lambda: self.pan.config(bg=P["line_strong"]))
        self.tabla = Tabla(self.pan, [
            ("clave", "Clave", 115), ("cuil", "CUIL", 115), ("fila", "Fila", 60, "e"), ("err", "Error SSS", 95),
            ("estado", "Estado", 230), ("corr", "Corrección propuesta (original → corregido)", 640, "w", True),
            ("falta", "Qué falta", 110)],
            checks=True, altura=8, al_enfocar=self._enfocar, al_doble=self._doble, al_marcar=self._marcado)
        self.pan.add(self.tabla, stretch="always", minsize=120)

        det = tk.Frame(self.pan, padx=14, pady=8)
        al_cambiar_tema(lambda: det.config(bg=P["surface2"]))
        dcab = tk.Frame(det)
        dcab.pack(fill="x")
        al_cambiar_tema(lambda: dcab.config(bg=P["surface2"]))
        self.chip = Lbl(dcab, "", 11.5, "semibold", fondo="pend_bg", color="pend_fg", padx=8)
        self.lbl_d1 = Lbl(dcab, "Seleccioná una línea para ver la explicación completa del error y de la corrección.",
                          12.5, color="ink3", fondo="surface2")
        self.lbl_d1.pack(side="left")
        self.btn_linea = Boton(dcab, "", self._accion_linea, "chico_primario")
        self.btn_ver = Boton(dcab, "Ver detalle de la línea", lambda: self._doble(self._foco), "chico")
        self.grilla = tk.Frame(det)
        self.grilla.pack(fill="both", expand=True, pady=(8, 0))
        al_cambiar_tema(lambda: self.grilla.config(bg=P["surface2"]))
        self.grilla.columnconfigure(1, weight=1)
        self.pan.add(det, minsize=130, height=165)

        self.vacio = EstadoVacio(self.card)

    # ------------------------------------------------------------------ filtros
    def _estado(self, v: str) -> None:
        self.f_estado = v
        self.refrescar_lista()

    def _cod(self, v: str) -> None:
        self.f_cod = v
        self.refrescar_lista()

    def _buscar(self, q: str) -> None:
        self.q = q
        self.refrescar_lista()

    # ------------------------------------------------------------------ pintado
    def mostrar(self) -> None:
        app, r, cr = self.app, self.app.resultado, self.app.cruce
        pasos = ["hecho" if r else "actual",
                 "hecho" if app.txt_err else ("actual" if r else "pendiente"),
                 "actual" if cr else "pendiente"]
        for (c, lb), est in zip(self.circ, pasos):
            c.set(estado=est)
            lb.set_color("ink" if est == "actual" else "ink2")
        nombres = [a.nombre for a in (app.txt_err, app.txt_ok) if a]
        self.lbl_txt.config(text="  ·  ".join(nombres))
        self.btn_err.config(text="Cargar otro TXT (_ERR)…" if app.txt_err else "Cargar TXT de errores (_ERR)…")
        if cr is None:
            for k in self.kpis.values():
                k.set("–", "", activo=False)
            self.tabla.limpiar()
            self._pintar_detalle(None)
            if r is None:
                self.aviso.mostrar("Primero analizá el Excel original en «1 · Balancear». Después cargá el TXT de "
                                   "errores que devolvió la SSS.", "neutro")
                self.vacio.mostrar(self.tabla, "Falta analizar el Excel original",
                                   "Para cruzar los rechazos de la SSS, primero analizá el mismo Excel que se envió.",
                                   ("Ir a «1 · Balancear»", lambda: app.ir("balancear")))
            else:
                self.aviso.mostrar("Cargá el TXT de errores (_ERR) que devolvió la SSS: Balidaf muestra qué rechazó y "
                                   "qué corrección propone. Nada se corrige hasta que vos lo apliques.", "neutro")
                self.vacio.mostrar(self.tabla, "Esperando el TXT de errores de la SSS",
                                   "Archivo ######-AAAAMM_DR.DEVOLUCION_ERR.txt. Opcionalmente, también el _OK.")
            return
        self.vacio.ocultar()
        n = cr.por_estado
        self.kpis["Todos"].set(cr.total_err, "", activo=self.f_estado == "Todos")
        for k in (PROPUESTA, APLICADA_TXT, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS):
            self.kpis[k].set(n.get(k, 0), "", activo=self.f_estado == k)
        prop, man = n.get(PROPUESTA, 0), n.get(PENDIENTE_MANUAL, 0)
        if prop:
            extra = (f" Ojo: {fmt_n(cr.aceptadas_que_cambian)} líneas ACEPTADAS por la SSS están en esos grupos y "
                     "también cambian." if cr.aceptadas_que_cambian else "")
            self.aviso.mostrar(f"{fmt_n(prop)} líneas rechazadas tienen una corrección propuesta. Revisala y "
                               f"presioná «Corregir…» para aplicarla.{extra}", "info")
        elif man:
            self.aviso.mostrar(f"{fmt_n(man)} líneas requieren corrección manual en el Excel original (ver «Qué falta»).",
                               "error", (f"Ver las {fmt_n(man)}", lambda: self._estado(PENDIENTE_MANUAL)))
        else:
            self.aviso.mostrar("No quedan correcciones pendientes para las líneas rechazadas. Guardá el Excel para "
                               "Presmed (Paso 3).", "ok")
        self.refrescar_lista()

    def refrescar_lista(self) -> None:
        cr = self.app.cruce
        if cr is None:
            return
        for k, w in self.kpis.items():
            w.set(cr.total_err if k == "Todos" else cr.por_estado.get(k, 0), "", activo=self.f_estado == k)
        self._lineas = {str(i): l for i, l in enumerate(cr.lineas)}
        en_estado = [(i, l) for i, l in self._lineas.items() if self.f_estado == "Todos" or l.estado == self.f_estado]
        cods: Dict[str, int] = {}
        for _, l in en_estado:
            for c in l.codigos_sss:
                cods[c] = cods.get(c, 0) + 1
        self.cb_estado.cargar([("Todos", "Todos los estados", len(cr.lineas))]
                              + [(e, e, cr.por_estado.get(e, 0)) for e in ESTADOS if cr.por_estado.get(e, 0)],
                              self.f_estado)
        self.cb_cod.cargar([("Todos", "Todos los errores", len(en_estado))]
                           + [(c, f"Error {c}", n) for c, n in sorted(cods.items())], self.f_cod)
        q = self.q
        vista = [(i, l) for i, l in en_estado if (self.f_cod == "Todos" or self.f_cod in l.codigos_sss)
                 and (not q or q in l.cuil or q in l.clave)]
        self._vista = [i for i, _ in vista]
        filas = [(i, (l.clave, l.cuil, l.fila or "", " ".join(l.codigos_sss), l.estado, l.correccion or "—",
                      " ".join(l.pendientes)), FAMILIA.get(l.estado, "")) for i, l in vista]
        prop = sum(1 for _, l in vista if l.estado == PROPUESTA)
        self.lbl_res.config(text=f"{fmt_n(len(filas))} líneas · {fmt_n(prop)} con corrección propuesta")
        self.tabla.cargar(filas)
        self._pintar_detalle(self._foco if self._foco in self._lineas else None)
        self._marcado()

    # ------------------------------------------------------------------ selección
    def _grupos(self, iids, estado: str) -> List[Grupo]:
        vistos, res = set(), []
        for i in iids:
            l = self._lineas.get(i)
            g = l.grupo if l else None
            if g is not None and g.estado == estado and id(g) not in vistos:
                vistos.add(id(g))
                res.append(g)
        return res

    def _marcado(self) -> None:
        sel = list(self.tabla.marcados)
        prop = [i for i in sel if self._lineas.get(i) and self._lineas[i].estado == PROPUESTA]
        apl = [i for i in sel if self._lineas.get(i) and self._lineas[i].estado == APLICADA_TXT]
        lista = [i for i in self._vista if self._lineas[i].estado == PROPUESTA]
        self.btn_sel.config(text=f"✓ Corregir seleccionadas ({fmt_n(len(prop))})")
        self.btn_undo.config(text=f"↶ Deshacer ({fmt_n(len(apl))})")
        self.btn_todas.config(text=f"✓ Corregir todas las de la lista ({fmt_n(len(lista))})")
        self.lbl_selres.config(text=f"Seleccionadas: {fmt_n(len(sel))} líneas" if sel else "")
        libre = not self.app.ocupado and self.app.cruce is not None
        self.btn_sel.habilitar(libre and bool(prop))
        self.btn_undo.habilitar(libre and bool(apl))
        self.btn_todas.habilitar(libre and bool(lista))

    # ------------------------------------------------------------------ detalle
    def _enfocar(self, iid: str) -> None:
        self._foco = iid
        self._pintar_detalle(iid)

    def _doble(self, iid: Optional[str]) -> None:
        l = self._lineas.get(iid) if iid else None
        if l and l.fila:
            self.app.abrir_detalle(l.fila)

    def _fila_grilla(self, fila: int, etiqueta: str, color: str, texto: str, color_txt: str = "ink") -> None:
        Lbl(self.grilla, etiqueta, 12.5, "semibold", color=color, fondo="surface2", anchor="nw").grid(
            row=fila, column=0, sticky="nw", padx=(0, 16), pady=2)
        lb = Lbl(self.grilla, texto, 12.5, color=color_txt, fondo="surface2", anchor="w", justify="left",
                 wraplength=1000)
        lb.grid(row=fila, column=1, sticky="w", pady=2)

    def _pintar_detalle(self, iid: Optional[str]) -> None:
        for w in self.grilla.winfo_children():
            w.destroy()
        for w in (self.chip, self.btn_linea, self.btn_ver):
            w.pack_forget()
        l = self._lineas.get(iid) if iid else None
        if l is None:
            self._foco = None
            self.lbl_d1.config(text="Seleccioná una línea para ver la explicación completa del error y de la corrección.",
                               font=F(12.5))
            self.lbl_d1.set_color("ink3")
            return
        fam = FAMILIA.get(l.estado, "neu")
        self.chip.config(text=l.estado)
        self.chip._fondo, self.chip._color = f"{fam}_bg", f"{fam}_fg"
        self.chip._tema()
        self.chip.pack(side="left", padx=(0, 10), before=self.lbl_d1)
        self.lbl_d1.config(text=f"Clave {l.clave} · CUIL {l.cuil} · fila {l.fila or '—'}", font=F(12.5, "semibold"))
        self.lbl_d1.set_color("ink")
        if l.estado == PROPUESTA:
            self.btn_linea.config(text="✓ Corregir esta línea")
            self.btn_linea.pack(side="right")
        elif l.estado == APLICADA_TXT:
            self.btn_linea.config(text="↶ Deshacer")
            self.btn_linea.pack(side="right")
        self.btn_linea.habilitar(not self.app.ocupado)
        if l.fila:
            self.btn_ver.pack(side="right", padx=(0, 8))
        f = 0
        for c in l.codigos_sss:
            d = CODIGOS.get(c)
            texto = f"{d.descripcion}  →  {d.accion} (lo resuelve: {d.resuelve})" if d else "No figura en el instructivo"
            self._fila_grilla(f, f"Error {c}", "err_fg", texto)
            f += 1
        if l.correccion:
            self._fila_grilla(f, "Corrección aplicada" if l.estado == APLICADA_TXT else "Corrección propuesta",
                              "accent", l.correccion)
            f += 1
        if l.pendientes:
            self._fila_grilla(f, "Qué falta", "err_fg",
                              " | ".join(f"{c}: {CODIGOS[c].descripcion}" for c in l.pendientes if c in CODIGOS),
                              "err_fg")
            f += 1
        quien = {PENDIENTE_SISTEMAS: "Sistemas / Presmed (formato del archivo o del envío).",
                 PENDIENTE_MANUAL: "A mano: corregir el dato en el Excel original y volver a analizar.",
                 NO_ENCONTRADO: "La clave no está en el Excel analizado: verificar que sea el mismo archivo enviado."}
        if l.estado in quien:
            self._fila_grilla(f, "Quién lo resuelve", "ink2", quien[l.estado])

    def _accion_linea(self) -> None:
        l = self._lineas.get(self._foco) if self._foco else None
        if not l or l.grupo is None:
            return
        if l.estado == PROPUESTA:
            self.app.aplicar([l.grupo])
        elif l.estado == APLICADA_TXT:
            self.app.deshacer([l.grupo])

    # ------------------------------------------------------------------ acciones
    def aplicar_sel(self) -> None:
        self.app.aplicar(self._grupos(self.tabla.marcados, PENDIENTE))

    def aplicar_lista(self) -> None:
        self.app.aplicar(self._grupos([i for i in self._vista if self._lineas[i].estado == PROPUESTA], PENDIENTE))

    def deshacer_sel(self) -> None:
        self.app.deshacer(self._grupos(self.tabla.marcados, APLICADA))

    def habilitar(self, ocupado: bool) -> None:
        self.btn_err.habilitar(not ocupado)
        self.btn_ok.habilitar(not ocupado)
        self._marcado()
