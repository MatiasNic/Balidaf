"""Componentes reutilizables y estilos de la interfaz."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# ----------------------------------------------------------------------------------------------
# Temas (sólo para la interfaz; el Excel de salida no lleva colores)
# Los componentes usan CLAVES de color (AZUL, VERDE…) que se resuelven con la paleta activa.
# ----------------------------------------------------------------------------------------------
FUENTE = "Segoe UI"

TEMAS: Dict[str, Dict[str, str]] = {
    "claro": {
        "fondo": "#ffffff", "superficie": "#f4f5f7", "borde": "#dfe3e8", "texto": "#1f2328", "texto2": "#5f6b7a",
        "acento": "#2f5d8a", "acento_hover": "#3b6fa1", "acento_txt": "#ffffff", "acento_suave": "#e8eef5",
        "cab_bg": "#24364b", "cab_fg": "#ffffff", "cab_sub": "#b8c4d2",
        "ok": "#2e7d4f", "ok_suave": "#e6f2ea", "ok_btn": "#2e7d4f", "ok_btn_hover": "#37905c",
        "error": "#b3261e", "error_suave": "#fbe9e7", "warn": "#a15c07", "warn_suave": "#fdf1e0",
        "mod_suave": "#fbf6dc", "ret_suave": "#efe9f6", "gris_suave": "#f1f2f4",
        "entrada": "#ffffff", "seleccion": "#c9d8ea", "seleccion_fg": "#1f2328", "code": "#f4f6f8",
        "heading": "#e9edf2", "deshab": "#aab4c0", "tooltip": "#fffef5",
    },
    "oscuro": {
        "fondo": "#1b1f24", "superficie": "#23282e", "borde": "#343b44", "texto": "#e3e6ea", "texto2": "#9aa4b1",
        "acento": "#6fa3d8", "acento_hover": "#86b4e2", "acento_txt": "#10161d", "acento_suave": "#22344a",
        "cab_bg": "#14181d", "cab_fg": "#e3e6ea", "cab_sub": "#8b96a3",
        "ok": "#6cc28f", "ok_suave": "#1f3528", "ok_btn": "#3f8f5f", "ok_btn_hover": "#4aa36e",
        "error": "#ef8a80", "error_suave": "#3d2321", "warn": "#e0a458", "warn_suave": "#3a2f1d",
        "mod_suave": "#37331d", "ret_suave": "#2f2a3b", "gris_suave": "#262b31",
        "entrada": "#2a3037", "seleccion": "#35506e", "seleccion_fg": "#ffffff", "code": "#262b31",
        "heading": "#2a3037", "deshab": "#55606c", "tooltip": "#2a3037",
    },
}
P: Dict[str, str] = dict(TEMAS["claro"])   # paleta activa
TEMA_ACTUAL = ["claro"]

# Claves semánticas usadas por las pestañas
AZUL, VERDE, ROJO, NARANJA, GRIS = "acento", "ok", "error", "warn", "texto2"

_observadores: List[Callable[[], None]] = []


def color(clave: str) -> str:
    """Devuelve el color de la paleta activa (o el valor tal cual si ya es un color)."""
    return P.get(clave, clave)


def al_cambiar_tema(fn: Callable[[], None]) -> None:
    """Registra una función que se llama (ahora y) cada vez que cambia el tema."""
    _observadores.append(fn)
    fn()


def aplicar_tema(root: tk.Misc, nombre: str) -> None:
    P.update(TEMAS[nombre])
    TEMA_ACTUAL[0] = nombre
    configurar_estilos(root)
    vivos = []
    for fn in _observadores:
        try:
            fn()
            vivos.append(fn)
        except tk.TclError:
            pass   # el widget ya no existe
    _observadores[:] = vivos


def configurar_estilos(root: tk.Misc) -> None:
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    base = (FUENTE, 10)
    root.option_add("*Font", base)
    for k, v in (("background", P["entrada"]), ("foreground", P["texto"]),
                 ("selectBackground", P["seleccion"]), ("selectForeground", P["seleccion_fg"])):
        root.option_add(f"*TCombobox*Listbox.{k}", v)
    try:
        root.configure(bg=P["fondo"])
    except tk.TclError:
        pass
    st.configure(".", font=base, background=P["fondo"], foreground=P["texto"], bordercolor=P["borde"],
                 lightcolor=P["borde"], darkcolor=P["borde"], troughcolor=P["superficie"],
                 fieldbackground=P["entrada"], insertcolor=P["texto"], selectbackground=P["seleccion"],
                 selectforeground=P["seleccion_fg"])
    for w in ("TFrame", "TLabel", "TRadiobutton", "TLabelframe", "TPanedwindow"):
        st.configure(w, background=P["fondo"], foreground=P["texto"])
    st.configure("Sash", background=P["borde"])
    st.configure("TLabelframe.Label", background=P["fondo"], foreground=P["acento"], font=(FUENTE, 11, "bold"))
    st.configure("TButton", padding=(10, 5), background=P["superficie"], foreground=P["texto"], bordercolor=P["borde"])
    st.map("TButton", background=[("disabled", P["superficie"]), ("active", P["acento_suave"])],
           foreground=[("disabled", P["deshab"])])
    st.configure("TEntry", fieldbackground=P["entrada"], foreground=P["texto"])
    st.configure("TCombobox", fieldbackground=P["entrada"], background=P["superficie"], foreground=P["texto"],
                 arrowcolor=P["texto2"])
    st.map("TCombobox", fieldbackground=[("readonly", P["entrada"])], foreground=[("readonly", P["texto"])],
           selectbackground=[("readonly", P["entrada"])], selectforeground=[("readonly", P["texto"])])
    for sb in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(sb, background=P["borde"], troughcolor=P["fondo"], arrowcolor=P["texto2"],
                     bordercolor=P["fondo"], lightcolor=P["borde"], darkcolor=P["borde"], gripcount=0)
        st.map(sb, background=[("active", P["texto2"])])
    st.configure("TNotebook", background=P["fondo"], borderwidth=0)
    st.configure("TNotebook.Tab", padding=(18, 8), font=(FUENTE, 10, "bold"), background=P["superficie"],
                 foreground=P["texto2"])
    st.map("TNotebook.Tab", background=[("selected", P["fondo"])], foreground=[("selected", P["acento"])])
    st.configure("Treeview", rowheight=24, font=(FUENTE, 9), background=P["entrada"], fieldbackground=P["entrada"],
                 foreground=P["texto"])
    st.map("Treeview", background=[("selected", P["seleccion"])], foreground=[("selected", P["seleccion_fg"])])
    st.configure("Treeview.Heading", font=(FUENTE, 9, "bold"), background=P["heading"], foreground=P["texto"])
    st.map("Treeview.Heading", background=[("active", P["acento_suave"])])
    st.configure("Accent.TButton", font=(FUENTE, 10, "bold"), foreground=P["acento_txt"], background=P["acento"],
                 padding=(16, 7))
    st.map("Accent.TButton", background=[("disabled", P["deshab"]), ("active", P["acento_hover"])],
           foreground=[("disabled", P["fondo"])])
    st.configure("Ok.TButton", font=(FUENTE, 10, "bold"), foreground="#ffffff", background=P["ok_btn"],
                 padding=(16, 7))
    st.map("Ok.TButton", background=[("disabled", P["deshab"]), ("active", P["ok_btn_hover"])],
           foreground=[("disabled", P["fondo"])])
    st.configure("Paso.TLabel", font=(FUENTE, 11, "bold"), foreground=P["acento"], background=P["fondo"])
    st.configure("Sub.TLabel", foreground=P["texto2"], background=P["fondo"])
    st.configure("Cab.TFrame", background=P["cab_bg"])
    st.configure("Cab.TLabel", background=P["cab_bg"], foreground=P["cab_fg"], font=(FUENTE, 14, "bold"))
    st.configure("CabSub.TLabel", background=P["cab_bg"], foreground=P["cab_sub"])
    st.configure("Cab.TButton", background=P["cab_bg"], foreground=P["cab_fg"], borderwidth=0, padding=(10, 2),
                 font=(FUENTE, 14), focusthickness=0, bordercolor=P["cab_bg"], lightcolor=P["cab_bg"],
                 darkcolor=P["cab_bg"])
    st.map("Cab.TButton", background=[("active", P["acento"])])
    st.configure("Grande.Horizontal.TProgressbar", troughcolor=P["entrada"], background=P["acento"], thickness=18,
                 bordercolor=P["borde"], lightcolor=P["acento"], darkcolor=P["acento"])


class Tarjeta(tk.Frame):
    """Indicador grande: número + leyenda."""

    def __init__(self, master, titulo: str, color_clave: str = AZUL):
        super().__init__(master, padx=14, pady=8, highlightthickness=1)
        self._base = color_clave
        self._actual = color_clave
        self.valor = tk.Label(self, text="–", font=(FUENTE, 18, "bold"))
        self.valor.pack(anchor="w")
        self.titulo = tk.Label(self, text=titulo, font=(FUENTE, 9), justify="left")
        self.titulo.pack(anchor="w")
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        self.config(bg=P["superficie"], highlightbackground=P["borde"])
        self.valor.config(bg=P["superficie"], fg=color(self._actual))
        self.titulo.config(bg=P["superficie"], fg=P["texto2"])

    def set(self, valor, color_clave: Optional[str] = None) -> None:
        self._actual = color_clave or self._base
        self.valor.config(text=f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor),
                          fg=color(self._actual))


class Aviso(tk.Label):
    """Cartel de estado con la próxima acción a realizar."""

    ESTILOS = {"info": ("acento", "acento_suave"), "ok": ("ok", "ok_suave"), "error": ("error", "error_suave"),
               "warn": ("warn", "warn_suave"), "neutro": ("texto2", "gris_suave")}

    def __init__(self, master, texto: str = ""):
        super().__init__(master, text=texto, font=(FUENTE, 11, "bold"), anchor="w", justify="left",
                         padx=14, pady=10, wraplength=1150)
        self._tipo = "neutro"
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        fg, bg = self.ESTILOS[self._tipo]
        self.config(fg=P[fg], bg=P[bg])

    def mostrar(self, texto: str, tipo: str = "info") -> None:
        self._tipo = tipo
        self.config(text=texto)
        self._tema()


class PanelProgreso(tk.Frame):
    """Barra de estado FIJA dentro de la ventana: qué está haciendo, pasos, barra y porcentaje."""

    def __init__(self, master):
        super().__init__(master, padx=14, pady=6, highlightthickness=1)
        self.titulo = tk.Label(self, text="", font=(FUENTE, 10, "bold"), width=34, anchor="w")
        self.titulo.grid(row=0, column=0, sticky="w")
        self.pb = ttk.Progressbar(self, mode="determinate", style="Grande.Horizontal.TProgressbar", maximum=100)
        self.pb.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.pct = tk.Label(self, text="", font=(FUENTE, 10, "bold"), width=6, anchor="e")
        self.pct.grid(row=0, column=2)
        self.pasos = tk.Label(self, text="", font=(FUENTE, 9), anchor="w")
        self.pasos.grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 0))
        self.columnconfigure(1, weight=1)
        self._pasos: List[Tuple[str, str]] = []
        self._estado: Dict[str, str] = {}
        self._indeterminado = False
        self._color_titulo = "texto2"
        al_cambiar_tema(self._tema)
        self.reposo("Listo. Elegí un Excel y presioná «Analizar».")

    def _tema(self) -> None:
        self.config(bg=P["acento_suave"], highlightbackground=P["borde"])
        self.titulo.config(bg=P["acento_suave"], fg=P[self._color_titulo])
        self.pct.config(bg=P["acento_suave"], fg=P["acento"])
        self.pasos.config(bg=P["acento_suave"], fg=P["texto2"])

    def _titulo(self, texto: str, clave: str) -> None:
        self._color_titulo = clave
        self.titulo.config(text=texto, fg=P[clave])

    def _pintar_pasos(self, detalle: str = "") -> None:
        marcas = {"ok": "✔", "actual": "▶", "": "○"}
        txt = "   ›   ".join(f"{marcas[self._estado.get(pid, '')]} {nombre}" for pid, nombre in self._pasos)
        self.pasos.config(text=txt + (f"      —  {detalle}" if detalle else ""))

    def reposo(self, texto: str) -> None:
        self._set_valor(0, mostrar_pct=False)
        self._titulo(f"●  {texto}", "texto2")
        self.pasos.config(text="")

    def iniciar(self, titulo: str, pasos: Sequence[Tuple[str, str]]) -> None:
        self._pasos = list(pasos)
        self._estado = {}
        self._titulo(f"⏳  {titulo}", "acento")
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
        self._titulo(("✔  " if ok else "✖  ") + texto, "ok" if ok else "error")
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
        al_cambiar_tema(self._tema)
        self._job = None
        self._orden_desc: Dict[str, bool] = {}
        if on_doble_click:
            self.tree.bind("<Double-1>", lambda e: self._doble(on_doble_click))

    def _tema(self) -> None:
        for tag, clave in [("error", "error_suave"), ("warn", "warn_suave"), ("mod", "mod_suave"),
                           ("ok", "ok_suave"), ("info", "acento_suave"), ("prop", "acento_suave"),
                           ("ret", "ret_suave"), ("gris", "gris_suave")]:
            self.tree.tag_configure(tag, background=P[clave], foreground=P["texto"])

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
        tk.Label(self.win, text=self.texto, justify="left", bg=P["tooltip"], fg=P["texto"], relief="solid", bd=1,
                 font=(FUENTE, 9), padx=8, pady=5, wraplength=380).pack()

    def _ocultar(self, _e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.win:
            self.win.destroy()
            self.win = None
