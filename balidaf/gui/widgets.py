"""Componentes reutilizables y estilos de la interfaz."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# Paleta (sólo para la interfaz; el Excel de salida no lleva colores)
AZUL = "#1f4e79"
AZUL_CLARO = "#ddebf7"
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


def configurar_estilos(root: tk.Tk) -> None:
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    base = ("Segoe UI", 10)
    root.option_add("*Font", base)
    st.configure(".", font=base, background=FONDO)
    st.configure("TFrame", background=FONDO)
    st.configure("TLabel", background=FONDO)
    st.configure("TLabelframe", background=FONDO)
    st.configure("TLabelframe.Label", background=FONDO, foreground=AZUL, font=("Segoe UI", 10, "bold"))
    st.configure("TNotebook", background=GRIS_CLARO, borderwidth=0)
    st.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10))
    st.map("TNotebook.Tab", background=[("selected", FONDO)], foreground=[("selected", AZUL)])
    st.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
    st.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background=AZUL_CLARO)
    st.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="white", background=AZUL, padding=(14, 6))
    st.map("Accent.TButton", background=[("disabled", "#9bb3cc"), ("active", "#2b6aa3")])
    st.configure("Ok.TButton", font=("Segoe UI", 10, "bold"), foreground="white", background=VERDE, padding=(14, 6))
    st.map("Ok.TButton", background=[("disabled", "#a9c9b1"), ("active", "#26963f")])
    st.configure("TButton", padding=(10, 5))
    st.configure("Titulo.TLabel", font=("Segoe UI", 15, "bold"), foreground=AZUL)
    st.configure("Sub.TLabel", foreground=GRIS)
    st.configure("Cab.TFrame", background=AZUL)
    st.configure("Cab.TLabel", background=AZUL, foreground="white", font=("Segoe UI", 14, "bold"))
    st.configure("CabSub.TLabel", background=AZUL, foreground="#cfe0f1")
    st.configure("Horizontal.TProgressbar", troughcolor=GRIS_CLARO, background=AZUL)


class Tarjeta(tk.Frame):
    """Indicador grande: número + leyenda."""

    def __init__(self, master, titulo: str, color: str = AZUL, fondo: str = GRIS_CLARO):
        super().__init__(master, bg=fondo, padx=14, pady=10, highlightthickness=1, highlightbackground="#e0e0e0")
        self._color = color
        self.valor = tk.Label(self, text="–", font=("Segoe UI", 20, "bold"), fg=color, bg=fondo)
        self.valor.pack(anchor="w")
        self.titulo = tk.Label(self, text=titulo, font=("Segoe UI", 9), fg=GRIS, bg=fondo, justify="left", wraplength=170)
        self.titulo.pack(anchor="w")

    def set(self, valor, color: Optional[str] = None) -> None:
        self.valor.config(text=f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor),
                          fg=color or self._color)


class Tabla(ttk.Frame):
    """Treeview con scrollbars, encabezados ordenables y carga por partes (no congela la ventana)."""

    def __init__(self, master, columnas: Sequence[Tuple[str, str, int]], altura: int = 12,
                 on_doble_click: Optional[Callable[[str], None]] = None):
        super().__init__(master)
        self.ids = [c[0] for c in columnas]
        self.tree = ttk.Treeview(self, columns=self.ids, show="headings", height=altura, selectmode="browse")
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
                        ("ok", VERDE_CLARO), ("info", AZUL_CLARO), ("ret", VIOLETA_CLARO), ("gris", GRIS_CLARO)]:
            self.tree.tag_configure(tag, background=bg)
        self._job = None
        self._orden_desc: Dict[str, bool] = {}
        if on_doble_click:
            self.tree.bind("<Double-1>", lambda e: self._doble(on_doble_click))

    def _doble(self, fn):
        sel = self.tree.selection()
        if sel:
            fn(sel[0])

    def limpiar(self) -> None:
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.tree.delete(*self.tree.get_children())

    def cargar(self, filas: List[Tuple[str, Sequence, Tuple[str, ...]]], lote: int = 1500,
               al_terminar: Optional[Callable[[], None]] = None) -> None:
        """filas: (iid, valores, tags)."""
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


def fila_botones(master) -> ttk.Frame:
    f = ttk.Frame(master)
    f.pack(fill="x", pady=(0, 6))
    return f
