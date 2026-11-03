"""Pestañas de la ventana principal."""

import tkinter as tk
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING, Dict, List, Optional

from ..devolucion import (CORREGIDO, NO_ENCONTRADO, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS,
                          ResultadoCruce)
from ..excel_io import Linea, texto_celda
from ..montos import fmt
from ..schema import CODIGOS, COL, IMPORTES
from ..validacion import ADVERTENCIA, ERROR, INFO, contar
from .widgets import (AZUL, GRIS, NARANJA, ROJO, ROJO_CLARO, VERDE, VERDE_CLARO, Tabla,
                      Tarjeta, fila_botones)

if TYPE_CHECKING:
    from .app import BalidafApp

NIVEL_TAG = {ERROR: "error", ADVERTENCIA: "warn", INFO: "info"}


# =====================================================================================
class TabResumen(ttk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=14)
        self.app = app

        self.banner = tk.Label(self, text="Seleccioná el Excel de rendición y presioná «Balancear y validar».",
                               font=("Segoe UI", 12, "bold"), fg=GRIS, bg="#f3f4f6", anchor="w", padx=14, pady=12)
        self.banner.pack(fill="x", pady=(0, 12))

        cont = ttk.Frame(self)
        cont.pack(fill="x")
        defs = [("lineas", "Líneas del Excel", AZUL), ("grupos", "Grupos\n(CUIL + períodos + práctica)", AZUL),
                ("grupos_mod", "Grupos balanceados", AZUL), ("lineas_mod", "Líneas modificadas", AZUL),
                ("ret", "Líneas con retenciones\nreducidas", NARANJA), ("err_antes", "Errores en el\nExcel original", ROJO),
                ("err_despues", "Errores luego\ndel balanceo", ROJO), ("adv", "Advertencias", NARANJA)]
        self.tarjetas: Dict[str, Tarjeta] = {}
        for i, (k, t, c) in enumerate(defs):
            tj = Tarjeta(cont, t, c)
            tj.grid(row=i // 4, column=i % 4, sticky="nsew", padx=4, pady=4)
            self.tarjetas[k] = tj
        for c in range(4):
            cont.columnconfigure(c, weight=1)

        lf = ttk.LabelFrame(self, text="Reglas de la Superintendencia (Anexo III / IV del instructivo)", padding=8)
        lf.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(lf, text="Doble clic en una regla para ver el detalle de las líneas.", style="Sub.TLabel").pack(anchor="w")
        self.tabla = Tabla(lf, [("cod", "Código", 70), ("campo", "Campo", 190), ("regla", "Regla", 520),
                                ("antes", "Original", 80), ("despues", "Balanceado", 90), ("resuelve", "Lo resuelve", 300)],
                           altura=14, on_doble_click=self._ir_a_codigo)
        self.tabla.pack(fill="both", expand=True, pady=(4, 0))
        self.mostrar(None)

    def _ir_a_codigo(self, iid: str) -> None:
        self.app.tab_validacion.filtrar_codigo(iid)
        self.app.nb.select(self.app.tab_validacion)

    def mostrar(self, r) -> None:
        if r is None:
            for t in self.tarjetas.values():
                t.set("–")
        else:
            vals = {"lineas": len(r.lote.lineas), "grupos": len(r.grupos), "grupos_mod": r.grupos_modificados,
                    "lineas_mod": r.lineas_modificadas, "ret": r.lineas_ret_reducidas,
                    "err_antes": r.errores_antes, "err_despues": r.errores_despues, "adv": r.advertencias}
            for k, v in vals.items():
                color = None
                if k == "err_despues":
                    color = VERDE if v == 0 else ROJO
                self.tarjetas[k].set(v, color)
            if r.listo_para_presmed:
                self.banner.config(text="✔  Sin errores: el Excel balanceado está listo para cargar en Presmed.",
                                   fg=VERDE, bg=VERDE_CLARO)
            else:
                self.banner.config(text=f"✖  Quedan {r.errores_despues} errores que requieren revisión manual "
                                        f"(ver «Validación SSS»).", fg=ROJO, bg=ROJO_CLARO)

        antes = contar(r.antes) if r else {}
        despues = contar(r.despues) if r else {}
        filas = []
        for cod, c in CODIGOS.items():
            if not c.validable:
                filas.append((cod, (cod, c.campo, c.descripcion, "—", "—", c.resuelve + " (se ve en la devolución SSS)"), ("gris",)))
                continue
            a, d = antes.get(cod, 0), despues.get(cod, 0)
            if r is None:
                tag = ()
            elif cod in ("B03", "B05"):
                tag = ("info",) if d else ()
            else:
                tag = ("error",) if d else (("ok",) if a else ())
            filas.append((cod, (cod, c.campo, c.descripcion, a if r else "", d if r else "", c.resuelve), tag))
        self.tabla.cargar(filas)


# =====================================================================================
class TabValidacion(ttk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=10)
        self.app = app
        f = fila_botones(self)
        ttk.Label(f, text="Ver:").pack(side="left")
        self.var_momento = tk.StringVar(value="despues")
        ttk.Radiobutton(f, text="Luego del balanceo", value="despues", variable=self.var_momento,
                        command=self.refrescar).pack(side="left", padx=4)
        ttk.Radiobutton(f, text="Excel original", value="antes", variable=self.var_momento,
                        command=self.refrescar).pack(side="left", padx=4)
        ttk.Label(f, text="   Código:").pack(side="left")
        self.var_codigo = tk.StringVar(value="Todos")
        self.cb_codigo = ttk.Combobox(f, textvariable=self.var_codigo, width=8, state="readonly",
                                      values=["Todos"] + list(CODIGOS))
        self.cb_codigo.pack(side="left", padx=4)
        self.cb_codigo.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        ttk.Label(f, text="  Nivel:").pack(side="left")
        self.var_nivel = tk.StringVar(value="Todos")
        cb = ttk.Combobox(f, textvariable=self.var_nivel, width=12, state="readonly",
                          values=["Todos", ERROR, ADVERTENCIA, INFO])
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

        self.tabla = Tabla(self, [("fila", "Fila", 60), ("clave", "Clave", 105), ("cuil", "CUIL", 105),
                                  ("cod", "Código", 65), ("nivel", "Nivel", 90), ("campo", "Campo", 170),
                                  ("detalle", "Detalle", 640)], altura=20, on_doble_click=self._abrir)
        self.tabla.pack(fill="both", expand=True)
        self.tabla.tree.bind("<<TreeviewSelect>>", self._seleccion)
        self.desc = tk.Label(self, text="Seleccioná una línea para ver la descripción de la regla.", anchor="w",
                             justify="left", fg=GRIS, bg="#f3f4f6", padx=10, pady=8, wraplength=1100)
        self.desc.pack(fill="x", pady=(6, 0))
        self._hallazgos = []

    def filtrar_codigo(self, cod: str) -> None:
        self.var_codigo.set(cod)
        self.var_nivel.set("Todos")
        self.refrescar()

    def refrescar(self) -> None:
        r = self.app.resultado
        if r is None:
            self.tabla.limpiar()
            self.lbl.config(text="")
            return
        hs = r.despues if self.var_momento.get() == "despues" else r.antes
        cod, niv, q = self.var_codigo.get(), self.var_nivel.get(), self.var_buscar.get().strip()
        sel = [h for h in hs if (cod == "Todos" or h.codigo == cod) and (niv == "Todos" or h.nivel == niv)
               and (not q or q in h.cuil or q in h.clave)]
        self._hallazgos = sel
        filas = [(str(i), (h.fila or "", h.clave, h.cuil, h.codigo, h.nivel, h.campo, h.detalle),
                  (NIVEL_TAG.get(h.nivel, ""),)) for i, h in enumerate(sel)]
        self.lbl.config(text=f"{len(sel):,} hallazgos".replace(",", "."))
        self.tabla.cargar(filas)

    def _seleccion(self, _e=None) -> None:
        s = self.tabla.tree.selection()
        if not s:
            return
        h = self._hallazgos[int(s[0])]
        c = CODIGOS.get(h.codigo)
        if c:
            self.desc.config(text=f"[{c.codigo}] {c.campo}: {c.descripcion}\nAcción: {c.accion}  ·  Lo resuelve: {c.resuelve}"
                                  + ("\nDoble clic para ver la línea completa." if h.fila else ""))

    def _abrir(self, iid: str) -> None:
        h = self._hallazgos[int(iid)]
        if h.fila:
            self.app.abrir_detalle(h.fila)


# =====================================================================================
class TabExcel(ttk.Frame):
    """Muestra el Excel completo tal como se va a guardar (los colores son sólo de la pantalla)."""

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=10)
        self.app = app
        f = fila_botones(self)
        ttk.Label(f, text="Mostrar:").pack(side="left")
        self.var_filtro = tk.StringVar(value="Todas")
        cb = ttk.Combobox(f, textvariable=self.var_filtro, width=24, state="readonly",
                          values=["Todas", "Modificadas por el balanceo", "Con errores", "Con advertencias",
                                  "Con retenciones reducidas"])
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

        ley = ttk.Frame(self)
        ley.pack(fill="x", pady=(0, 4))
        for txt, bg in [("Modificada", "#fff9c4"), ("Retenciones reducidas", "#ede1f7"), ("Error", "#fde2e1"),
                        ("Advertencia", "#fff1d6")]:
            tk.Label(ley, text=f"  {txt}  ", bg=bg, font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        ttk.Label(ley, text="Los colores son sólo de esta pantalla: el Excel se guarda sin formatos.  Doble clic = detalle.",
                  style="Sub.TLabel").pack(side="left", padx=8)
        self.cont = ttk.Frame(self)
        self.cont.pack(fill="both", expand=True)
        self.tabla: Optional[Tabla] = None

    def _armar_tabla(self, encabezados: List[str], muestra: List[List]) -> None:
        if self.tabla:
            self.tabla.destroy()
        cols = [("_fila", "Fila", 55), ("_estado", "Estado", 110)]
        for i, h in enumerate(encabezados):
            largo = max([len(h or "")] + [len(texto_celda(f[i])) for f in muestra if i < len(f)])
            cols.append((f"c{i}", h or f"Col {i + 1}", max(70, min(220, largo * 8 + 24))))
        self.tabla = Tabla(self.cont, cols, altura=22, on_doble_click=lambda iid: self.app.abrir_detalle(int(iid)))
        self.tabla.pack(fill="both", expand=True)

    def refrescar(self) -> None:
        r = self.app.resultado
        if r is None:
            if self.tabla:
                self.tabla.limpiar()
            return
        lote = r.lote
        if self.tabla is None or len(self.tabla.ids) != len(lote.encabezados) + 2:
            self._armar_tabla(lote.encabezados, lote.filas[:300])
        col_a_clave = {v: k for k, v in lote.columnas.items()}
        errores, advs = r.filas_con(ERROR), r.filas_con(ADVERTENCIA)
        ret = {f for g in r.grupos.values() for f in g.retenciones_reducidas}
        filtro, q = self.var_filtro.get(), self.var_buscar.get().strip()

        filas = []
        for ln, crudo in zip(lote.lineas, lote.filas):
            mod = bool(ln.modificados())
            if filtro.startswith("Modificadas") and not mod:
                continue
            if filtro == "Con errores" and ln.fila not in errores:
                continue
            if filtro == "Con advertencias" and ln.fila not in advs:
                continue
            if filtro.startswith("Con retenciones") and ln.fila not in ret:
                continue
            if q and q not in ln.cuil and q not in ln.clave:
                continue
            if ln.fila in errores:
                estado, tag = "Error", "error"
            elif ln.fila in ret:
                estado, tag = "Ret. reducida", "ret"
            elif ln.fila in advs:
                estado, tag = "Advertencia", "warn"
            elif mod:
                estado, tag = "Modificada", "mod"
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
class TabDevolucion(ttk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=10)
        self.app = app
        f = fila_botones(self)
        ttk.Button(f, text="Cargar TXT de errores (_ERR)…", command=lambda: self.cargar("ERR")).pack(side="left")
        ttk.Button(f, text="Cargar TXT aceptados (_OK)…", command=lambda: self.cargar("OK")).pack(side="left", padx=6)
        self.lbl_archivos = ttk.Label(f, text="Ningún archivo cargado.", style="Sub.TLabel")
        self.lbl_archivos.pack(side="left", padx=10)

        ttk.Label(self, text="Cargá la devolución de la SSS para cruzarla con el Excel: se muestra cada rechazo con su "
                             "descripción y si el balanceo actual lo corrige.", style="Sub.TLabel").pack(anchor="w")

        cont = ttk.Frame(self)
        cont.pack(fill="x", pady=8)
        self.tarjetas = {}
        for i, (k, t, c) in enumerate([("total", "Líneas rechazadas", AZUL), (CORREGIDO, "Corregidas\n(ya cumplen las reglas)", VERDE),
                                       (PENDIENTE_MANUAL, "Requieren\ncorrección manual", ROJO),
                                       (PENDIENTE_SISTEMAS, "Las resuelve\nSistemas / Presmed", NARANJA),
                                       ("ok_mod", "Aceptadas que el\nbalanceo modifica", GRIS)]):
            tj = Tarjeta(cont, t, c)
            tj.grid(row=0, column=i, sticky="nsew", padx=4)
            cont.columnconfigure(i, weight=1)
            self.tarjetas[k] = tj

        pan = ttk.PanedWindow(self, orient="vertical")
        pan.pack(fill="both", expand=True)
        lf1 = ttk.LabelFrame(pan, text="Errores informados por la SSS", padding=6)
        self.t_cod = Tabla(lf1, [("cod", "Código", 70), ("desc", "Descripción (Anexo IV)", 700),
                                 ("n", "Líneas", 70), ("res", "Lo resuelve", 110)], altura=6,
                           on_doble_click=self._filtrar_cod)
        self.t_cod.pack(fill="both", expand=True)
        pan.add(lf1, weight=1)

        lf2 = ttk.LabelFrame(pan, text="Detalle por línea", padding=6)
        f2 = fila_botones(lf2)
        ttk.Label(f2, text="Estado:").pack(side="left")
        self.var_estado = tk.StringVar(value="Todos")
        cb = ttk.Combobox(f2, textvariable=self.var_estado, width=34, state="readonly",
                          values=["Todos", CORREGIDO, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS, NO_ENCONTRADO])
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.mostrar_detalle())
        self.var_cod = tk.StringVar(value="Todos")
        ttk.Label(f2, text="  Código:").pack(side="left")
        cb2 = ttk.Combobox(f2, textvariable=self.var_cod, width=8, state="readonly", values=["Todos"])
        cb2.pack(side="left", padx=4)
        cb2.bind("<<ComboboxSelected>>", lambda e: self.mostrar_detalle())
        self.cb_cod = cb2
        self.t_det = Tabla(lf2, [("clave", "Clave", 105), ("cuil", "CUIL", 105), ("fila", "Fila Excel", 75),
                                 ("err", "Errores SSS", 120), ("estado", "Estado", 220), ("act", "Errores actuales", 120),
                                 ("desc", "Descripción", 520)], altura=10, on_doble_click=self._abrir)
        self.t_det.pack(fill="both", expand=True)
        pan.add(lf2, weight=3)

    def cargar(self, tipo: str) -> None:
        ruta = filedialog.askopenfilename(title=f"Seleccioná el TXT {'de errores (_ERR)' if tipo == 'ERR' else 'aceptado (_OK)'}",
                                          filetypes=[("TXT", "*.txt"), ("Todos", "*.*")])
        if ruta:
            self.app.cargar_txt(ruta, tipo)

    def actualizar_archivos(self) -> None:
        partes = []
        if self.app.txt_err:
            partes.append(f"ERR: {self.app.txt_err.nombre} ({len(self.app.txt_err.registros)} líneas)")
        if self.app.txt_ok:
            partes.append(f"OK: {self.app.txt_ok.nombre} ({len(self.app.txt_ok.registros)} líneas)")
        self.lbl_archivos.config(text="   ·   ".join(partes) or "Ningún archivo cargado.")

    def mostrar(self, cruce: Optional[ResultadoCruce]) -> None:
        self.actualizar_archivos()
        self.cruce = cruce
        if cruce is None:
            for t in self.tarjetas.values():
                t.set("–")
            self.t_cod.limpiar()
            self.t_det.limpiar()
            return
        self.tarjetas["total"].set(cruce.total_err)
        for k in (CORREGIDO, PENDIENTE_MANUAL, PENDIENTE_SISTEMAS):
            self.tarjetas[k].set(cruce.por_estado.get(k, 0))
        self.tarjetas["ok_mod"].set(cruce.aceptadas_modificadas if cruce.total_ok else "–")
        filas = []
        for cod, n in sorted(cruce.por_codigo.items()):
            c = CODIGOS.get(cod)
            filas.append((cod, (cod, c.descripcion if c else "No figura en el instructivo", n, c.resuelve if c else ""), ()))
        self.t_cod.cargar(filas)
        self.cb_cod.config(values=["Todos"] + sorted(cruce.por_codigo))
        self.mostrar_detalle()

    def _filtrar_cod(self, cod: str) -> None:
        self.var_cod.set(cod)
        self.mostrar_detalle()

    def mostrar_detalle(self) -> None:
        cr = getattr(self, "cruce", None)
        if not cr:
            return
        est, cod = self.var_estado.get(), self.var_cod.get()
        tags = {CORREGIDO: "ok", PENDIENTE_MANUAL: "error", PENDIENTE_SISTEMAS: "warn", NO_ENCONTRADO: "gris"}
        filas = []
        self._lineas = [l for l in cr.lineas if (est == "Todos" or l.estado == est) and (cod == "Todos" or cod in l.codigos_sss)]
        for i, l in enumerate(self._lineas):
            desc = " | ".join(f"{c}: {CODIGOS[c].descripcion}" for c in l.codigos_sss if c in CODIGOS)
            filas.append((str(i), (l.clave, l.cuil, l.fila or "", " ".join(l.codigos_sss), l.estado,
                                   " ".join(l.errores_actuales), desc), (tags.get(l.estado, ""),)))
        self.t_det.cargar(filas)

    def _abrir(self, iid: str) -> None:
        l = self._lineas[int(iid)]
        if l.fila:
            self.app.abrir_detalle(l.fila)


# =====================================================================================
class TabRegistro(ttk.Frame):
    COLORES = {"info": "#202124", "ok": VERDE, "warn": NARANJA, "error": ROJO, "titulo": AZUL}

    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master, padding=10)
        f = fila_botones(self)
        ttk.Button(f, text="Limpiar", command=self.limpiar).pack(side="left")
        ttk.Button(f, text="Guardar registro…", command=self.exportar).pack(side="left", padx=6)
        fr = ttk.Frame(self)
        fr.pack(fill="both", expand=True)
        self.txt = tk.Text(fr, wrap="word", font=("Consolas", 10), bg="#fbfbfb", relief="flat", padx=10, pady=8)
        sb = ttk.Scrollbar(fr, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set, state="disabled")
        self.txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for k, c in self.COLORES.items():
            self.txt.tag_configure(k, foreground=c)
        self.txt.tag_configure("titulo", font=("Consolas", 10, "bold"), spacing1=8)

    def escribir(self, nivel: str, msg: str) -> None:
        import datetime as dt
        self.txt.configure(state="normal")
        hora = dt.datetime.now().strftime("%H:%M:%S")
        self.txt.insert("end", f"{hora}  {msg}\n", (nivel,))
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def limpiar(self) -> None:
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

    def exportar(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")],
                                            initialfile="registro_balidaf.txt")
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.txt.get("1.0", "end"))


# =====================================================================================
class DetalleLinea(tk.Toplevel):
    """Ventana con todo lo que pasó en una línea y en su grupo."""

    def __init__(self, app: "BalidafApp", ln: Linea):
        super().__init__(app)
        r = app.resultado
        self.title(f"Fila {ln.fila} · clave {ln.clave} · CUIL {ln.cuil}")
        self.geometry("980x640")
        self.transient(app)
        cont = ttk.Frame(self, padding=12)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text=f"CUIL {ln.cuil}  ·  práctica {ln.texto.get('cod', '')}  ·  prestación "
                             f"{ln.grupo[2]}  ·  clave {ln.clave}", style="Titulo.TLabel").pack(anchor="w")

        lf = ttk.LabelFrame(cont, text="Importes de la línea", padding=6)
        lf.pack(fill="x", pady=(8, 4))
        t = Tabla(lf, [("campo", "Campo", 260), ("col", "Columna Excel", 200), ("orig", "Original", 130),
                       ("nuevo", "Balanceado", 130), ("dif", "Diferencia", 120)], altura=9)
        t.pack(fill="x")
        filas = []
        for k in IMPORTES:
            o, n = ln.original[k], ln.monto[k]
            filas.append((k, (COL[k].titulo, COL[k].encabezado, fmt(o), fmt(n), fmt(n - o) if n != o else ""),
                          ("mod",) if n != o else ()))
        t.cargar(filas)

        g = r.grupos.get(ln.grupo) if r else None
        if g:
            lf2 = ttk.LabelFrame(cont, text=f"Grupo de la regla 624 ({len(g.lineas)} línea/s) · subsidio {fmt(g.subsidio)}"
                                            f" · aplicado {fmt(g.aplicado)}", padding=6)
            lf2.pack(fill="x", pady=4)
            t2 = Tabla(lf2, [("fila", "Fila", 60), ("clave", "Clave", 110), ("sub", "Subsidiado", 110),
                             ("sol", "Solicitado", 110), ("ret", "Retenciones", 110), ("apli", "Aplicado", 110),
                             ("tr", "Transferido", 110), ("fdo", "Fdo. propios", 110)], altura=min(6, len(g.lineas) + 1))
            t2.pack(fill="x")
            t2.cargar([(str(x.fila), (x.fila, x.clave, fmt(x.monto["subsidiado"]), fmt(x.monto["solicitado"]),
                                      fmt(x.retenciones()), fmt(x.monto["apli"]), fmt(x.monto["transferido"]),
                                      fmt(x.monto["fdo_ppio"])), ("info",) if x.fila == ln.fila else ())
                       for x in g.lineas])

        hs = [h for h in (r.despues if r else []) if h.fila == ln.fila]
        lf3 = ttk.LabelFrame(cont, text=f"Validaciones de la línea ({len(hs)})", padding=6)
        lf3.pack(fill="both", expand=True, pady=4)
        if hs:
            t3 = Tabla(lf3, [("cod", "Código", 70), ("nivel", "Nivel", 90), ("det", "Detalle", 760)], altura=5)
            t3.pack(fill="both", expand=True)
            t3.cargar([(str(i), (h.codigo, h.nivel, h.detalle), (NIVEL_TAG.get(h.nivel, ""),)) for i, h in enumerate(hs)])
        else:
            tk.Label(lf3, text="✔ La línea cumple todas las reglas de la SSS.", fg=VERDE, bg="white").pack(anchor="w")
        ttk.Button(cont, text="Cerrar", command=self.destroy).pack(anchor="e", pady=(6, 0))
