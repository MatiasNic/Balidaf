"""Componentes reutilizables y estilos de la interfaz."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# Paleta (sólo para la interfaz; el Excel de salida no lleva colores)
AZUL = "#1f4e79"
AZUL_CLARO = "#ddebf7"
CELESTE_CLARO = "#e3f2fd"
VERDE = "#1e7b34"
VERDE_CLARO = "#e2f0d9"
ROJO = "#b00020"
ROJO_CLARO = "#fde2e1"
NARANJA = "#b35c00"
NARANJA_CLARO = "#fff1d6"
AMARILLO_CLARO = "#fff9c4"
VIOLETA_CLARO = "#ede1f7"
GRIS = "#5f6368"
GRIS_CLARO = "#f3f4f6"
FONDO = "#ffffff"
FUENTE = "Segoe UI"


def configurar_estilos(root: tk.Tk) -> None:
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    base = (FUENTE, 10)
    root.option_add("*Font", base)
    st.configure(".", font=base, background=FONDO)
    st.configure("TFrame", background=FONDO)
    st.configure("TLabel", background=FONDO)
    st.configure("TRadiobutton", background=FONDO)
    st.configure("TLabelframe", background=FONDO)
    st.configure("TLabelframe.Label", background=FONDO, foreground=AZUL, font=(FUENTE, 11, "bold"))
    st.configure("TNotebook", background=GRIS_CLARO, borderwidth=0)
    st.configure("TNotebook.Tab", padding=(18, 8), font=(FUENTE, 10, "bold"))
    st.map("TNotebook.Tab", background=[("selected", FONDO)], foreground=[("selected", AZUL)])
    st.configure("Treeview", rowheight=24, font=(FUENTE, 9))
    st.configure("Treeview.Heading", font=(FUENTE, 9, "bold"), background=AZUL_CLARO)
    st.configure("Accent.TButton", font=(FUENTE, 10, "bold"), foreground="white", background=AZUL, padding=(16, 7))
    st.map("Accent.TButton", background=[("disabled", "#9bb3cc"), ("active", "#2b6aa3")])
    st.configure("Ok.TButton", font=(FUENTE, 10, "bold"), foreground="white", background=VERDE, padding=(16, 7))
    st.map("Ok.TButton", background=[("disabled", "#a9c9b1"), ("active", "#26963f")])
    st.configure("TButton", padding=(10, 5))
    st.configure("Paso.TLabel", font=(FUENTE, 11, "bold"), foreground=AZUL)
    st.configure("Sub.TLabel", foreground=GRIS)
    st.configure("Cab.TFrame", background=AZUL)
    st.configure("Cab.TLabel", background=AZUL, foreground="white", font=(FUENTE, 14, "bold"))
    st.configure("CabSub.TLabel", background=AZUL, foreground="#cfe0f1")
    st.configure("Grande.Horizontal.TProgressbar", troughcolor="#ffffff", background=AZUL, thickness=22)


class Tarjeta(tk.Frame):
    """Indicador grande: número + leyenda."""

    def __init__(self, master, titulo: str, color: str = AZUL, fondo: str = GRIS_CLARO):
        super().__init__(master, bg=fondo, padx=14, pady=8, highlightthickness=1, highlightbackground="#e0e0e0")
        self._color = color
        self.valor = tk.Label(self, text="–", font=(FUENTE, 18, "bold"), fg=color, bg=fondo)
        self.valor.pack(anchor="w")
        self.titulo = tk.Label(self, text=titulo, font=(FUENTE, 9), fg=GRIS, bg=fondo, justify="left")
        self.titulo.pack(anchor="w")

    def set(self, valor, color: Optional[str] = None) -> None:
        self.valor.config(text=f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor),
                          fg=color or self._color)


class Aviso(tk.Label):
    """Cartel de estado con la próxima acción a realizar."""

    ESTILOS = {"info": (AZUL, CELESTE_CLARO), "ok": (VERDE, VERDE_CLARO), "error": (ROJO, ROJO_CLARO),
               "warn": (NARANJA, NARANJA_CLARO), "neutro": (GRIS, GRIS_CLARO)}

    def __init__(self, master, texto: str = ""):
        super().__init__(master, text=texto, font=(FUENTE, 11, "bold"), anchor="w", justify="left",
                         padx=14, pady=10, wraplength=1150)
        self.mostrar(texto, "neutro")

    def mostrar(self, texto: str, tipo: str = "info") -> None:
        fg, bg = self.ESTILOS[tipo]
        self.config(text=texto, fg=fg, bg=bg)


class PanelProgreso(tk.Frame):
    """Barra de estado FIJA dentro de la ventana: qué está haciendo, pasos, barra y porcentaje."""

    def __init__(self, master):
        super().__init__(master, bg=CELESTE_CLARO, padx=14, pady=6, highlightthickness=1,
                         highlightbackground="#90caf9")
        self.titulo = tk.Label(self, text="", font=(FUENTE, 10, "bold"), fg=AZUL, bg=CELESTE_CLARO,
                               width=34, anchor="w")
        self.titulo.grid(row=0, column=0, sticky="w")
        self.pb = ttk.Progressbar(self, mode="determinate", style="Grande.Horizontal.TProgressbar", maximum=100)
        self.pb.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.pct = tk.Label(self, text="", font=(FUENTE, 10, "bold"), fg=AZUL, bg=CELESTE_CLARO, width=6, anchor="e")
        self.pct.grid(row=0, column=2)
        self.pasos = tk.Label(self, text="", font=(FUENTE, 9), fg=GRIS, bg=CELESTE_CLARO, anchor="w")
        self.pasos.grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 0))
        self.columnconfigure(1, weight=1)
        self._pasos: List[Tuple[str, str]] = []
        self._estado: Dict[str, str] = {}
        self._indeterminado = False
        self.reposo("Listo. Elegí un Excel y presioná «Analizar».")

    def _pintar_pasos(self, detalle: str = "") -> None:
        marcas = {"ok": "✔", "actual": "▶", "": "○"}
        txt = "   ›   ".join(f"{marcas[self._estado.get(pid, '')]} {nombre}" for pid, nombre in self._pasos)
        self.pasos.config(text=txt + (f"      —  {detalle}" if detalle else ""))

    def reposo(self, texto: str) -> None:
        self._set_valor(0, mostrar_pct=False)
        self.titulo.config(text=f"●  {texto}", fg=GRIS)
        self.pasos.config(text="")

    def iniciar(self, titulo: str, pasos: Sequence[Tuple[str, str]]) -> None:
        self._pasos = list(pasos)
        self._estado = {}
        self.titulo.config(text=f"⏳  {titulo}", fg=AZUL)
        self._set_valor(0)
        self._pintar_pasos()

    def avanzar(self, paso: str, texto: str, cur: int, tot: int) -> None:
        ids = [p for p, _ in self._pasos]
        if paso in ids:
            for pid in ids:
                if ids.index(pid) < ids.index(paso):
                    self._estado[pid] = "ok"
            self._estado[paso] = "actual"
        self._pintar_pasos(texto)
        n = max(len(ids), 1)
        idx = ids.index(paso) if paso in ids else 0
        if tot <= 0:
            if not self._indeterminado:
                self.pb.config(mode="indeterminate")
                self.pb.start(15)
                self._indeterminado = True
            self.pct.config(text="")
        else:
            self._set_valor(100 * (idx + min(cur / tot, 1)) / n)

    def _set_valor(self, v: float, mostrar_pct: bool = True) -> None:
        if self._indeterminado:
            self.pb.stop()
            self.pb.config(mode="determinate")
            self._indeterminado = False
        self.pb["value"] = v
        self.pct.config(text=f"{int(v)} %" if mostrar_pct else "")

    def terminar(self, texto: str, ok: bool = True) -> None:
        for pid, _ in self._pasos:
            self._estado[pid] = "ok"
        self._set_valor(100)
        self.titulo.config(text=("✔  " if ok else "✖  ") + texto, fg=VERDE if ok else ROJO)
        self._pintar_pasos()


class ComboFiltro(ttk.Frame):
    """Lista desplegable compacta para filtrar (muestra la cantidad de cada opción)."""

    def __init__(self, master, etiqueta: str, ancho: int, al_elegir: Callable[[str], None]):
        super().__init__(master)
        ttk.Label(self, text=etiqueta).pack(side="left")
        self.var = tk.StringVar()
        self.cb = ttk.Combobox(self, textvariable=self.var, width=ancho, state="readonly")
        self.cb.pack(side="left", padx=(4, 0))
        self.cb.bind("<<ComboboxSelected>>", lambda e: al_elegir(self._mapa.get(self.var.get(), "")))
        self._mapa: Dict[str, str] = {}

    def cargar(self, opciones: Sequence[Tuple[str, str, int]], actual: str) -> None:
        """opciones: (valor, texto, cantidad)."""
        self._mapa = {}
        textos = []
        for valor, texto, n in opciones:
            t = f"{texto}  ({n:,})".replace(",", ".")
            self._mapa[t] = valor
            textos.append(t)
            if valor == actual:
                self.var.set(t)
        self.cb.config(values=textos)


class Tabla(ttk.Frame):
    """Treeview con scrollbars, encabezados ordenables y carga por partes (no congela la ventana)."""

    def __init__(self, master, columnas: Sequence[Tuple[str, str, int]], altura: int = 12,
                 on_doble_click: Optional[Callable[[str], None]] = None, seleccion: str = "browse"):
        super().__init__(master)
        self.ids = [c[0] for c in columnas]
        self._titulos = {cid: titulo for cid, titulo, _ in columnas}
        self.tree = ttk.Treeview(self, columns=self.ids, show="headings", height=altura, selectmode=seleccion)
        for cid, titulo, ancho in columnas:
            self.tree.heading(cid, text=titulo, command=lambda c=cid: self.ordenar(c))
            self.tree.column(cid, width=ancho, minwidth=40, stretch=False, anchor="w")
        ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for tag, bg in [("error", ROJO_CLARO), ("warn", NARANJA_CLARO), ("mod", AMARILLO_CLARO),
                        ("ok", VERDE_CLARO), ("info", AZUL_CLARO), ("prop", CELESTE_CLARO),
                        ("ret", VIOLETA_CLARO), ("gris", GRIS_CLARO)]:
            self.tree.tag_configure(tag, background=bg)
        self._job = None
        self._orden_desc: Dict[str, bool] = {}
        if on_doble_click:
            self.tree.bind("<Double-1>", lambda e: self._doble(on_doble_click))

    def _doble(self, fn):
        sel = self.tree.selection()
        if sel:
            fn(sel[0])

    def seleccionados(self) -> List[str]:
        return list(self.tree.selection())

    def todos(self) -> List[str]:
        return list(self.tree.get_children(""))

    def limpiar(self) -> None:
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.tree.delete(*self.tree.get_children())
        for cid, titulo in self._titulos.items():
            self.tree.heading(cid, text=titulo)

    def cargar(self, filas: List[Tuple[str, Sequence, Tuple[str, ...]]], lote: int = 1500,
               al_terminar: Optional[Callable[[], None]] = None) -> None:
        """filas: (iid, valores, tags). Se insertan por partes para no congelar la ventana."""
        self.limpiar()

        def paso(i=0):
            for iid, valores, tags in filas[i:i + lote]:
                self.tree.insert("", "end", iid=iid, values=list(valores), tags=tags)
            if i + lote < len(filas):
                self._job = self.after(1, paso, i + lote)
            else:
                self._job = None
                if al_terminar:
                    al_terminar()
        paso()

    def ordenar(self, col: str) -> None:
        desc = not self._orden_desc.get(col, False)
        self._orden_desc[col] = desc
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        def clave(v):
            s = v[0].replace(".", "").replace(",", ".")
            try:
                return (0, float(s))
            except ValueError:
                return (1, v[0])
        items.sort(key=clave, reverse=desc)
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)
        for cid, titulo in self._titulos.items():
            flecha = (" ▼" if desc else " ▲") if cid == col else ""
            self.tree.heading(cid, text=titulo + flecha)


def fila(master, **pack) -> ttk.Frame:
    opciones = {"pady": (0, 6)}
    opciones.update(pack)
    f = ttk.Frame(master)
    f.pack(fill="x", **opciones)
    return f


class Ayuda:
    """Texto de ayuda que aparece al dejar el mouse sobre un control."""

    def __init__(self, widget, texto: str):
        self.widget, self.texto, self.win, self._job = widget, texto, None, None
        widget.bind("<Enter>", self._programar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<ButtonPress>", self._ocultar, add="+")

    def _programar(self, _e=None):
        self._job = self.widget.after(500, self._mostrar)

    def _mostrar(self):
        if self.win:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.win = tk.Toplevel(self.widget)
        self.win.wm_overrideredirect(True)
        self.win.wm_geometry(f"+{x}+{y}")
        tk.Label(self.win, text=self.texto, justify="left", bg="#fffde7", fg="#333", relief="solid", bd=1,
                 font=(FUENTE, 9), padx=8, pady=5, wraplength=380).pack()

    def _ocultar(self, _e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.win:
            self.win.destroy()
            self.win = None
