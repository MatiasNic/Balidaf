"""Componentes visuales del rediseño (Tkinter). Todos se repintan solos al cambiar el tema."""

import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .tema import F, P, al_cambiar_tema

# Familias de color semántico → (fondo chip, texto, fila)
SEM = {
    "pend": ("pend_bg", "pend_fg", "pend_row"), "ok": ("ok_bg", "ok_fg", "ok_row"),
    "err": ("err_bg", "err_fg", "err_row"), "warn": ("warn_bg", "warn_fg", "warn_row"),
    "vio": ("vio_bg", "vio_fg", "vio_row"), "neu": ("neu_bg", "neu_fg", "surface"),
    "accent": ("accent_soft", "accent", "surface"),
}


def fmt_n(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ==============================================================================================
# Básicos
# ==============================================================================================
class Lbl(tk.Label):
    """Label con colores por token (se repinta con el tema)."""

    def __init__(self, master, texto: str = "", px: float = 13, peso: str = "normal", color: str = "ink",
                 fondo: str = "surface", mono: bool = False, **kw):
        super().__init__(master, text=texto, font=F(px, peso, mono), **kw)
        self._color, self._fondo = color, fondo
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        self.config(fg=P[self._color], bg=P[self._fondo])

    def set_color(self, color: str) -> None:
        self._color = color
        self.config(fg=P[color])


class Caja(tk.Frame):
    """Frame con fondo y borde de 1 px por token (las «tarjetas» del diseño)."""

    def __init__(self, master, fondo: str = "surface", borde: Optional[str] = "line", **kw):
        super().__init__(master, highlightthickness=1 if borde else 0, **kw)
        self._fondo, self._borde = fondo, borde
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        self.config(bg=P[self._fondo])
        if self._borde:
            self.config(highlightbackground=P[self._borde], highlightcolor=P[self._borde])

    def set_estilo(self, fondo: str, borde: Optional[str]) -> None:
        self._fondo, self._borde = fondo, borde or self._borde
        self._tema()


class Linea(tk.Frame):
    """Línea divisoria de 1 px."""

    def __init__(self, master, color: str = "line", vertical: bool = False, **kw):
        super().__init__(master, **({"width": 1} if vertical else {"height": 1}), **kw)
        al_cambiar_tema(lambda: self.config(bg=P[color]))


class Circulo(tk.Canvas):
    """Círculo con texto: indicador de paso (hecho ✓ / actual / pendiente) o ícono de estado."""

    ESTADOS = {"hecho": ("ok_bg", "ok_fg"), "actual": ("accent", "on_accent"), "pendiente": ("head", "ink3"),
               "idle": ("neu_bg", "ink3"), "curso": ("accent_soft", "accent"), "ok": ("ok_bg", "ok_fg"),
               "error": ("err_bg", "err_fg")}

    def __init__(self, master, texto: str = "", estado: str = "pendiente", tam: int = 22, fondo: str = "surface"):
        super().__init__(master, width=tam, height=tam, highlightthickness=0, bd=0)
        self._texto, self._estado, self._tam, self._fondo = texto, estado, tam, fondo
        al_cambiar_tema(self._dibujar)

    def set(self, texto: Optional[str] = None, estado: Optional[str] = None) -> None:
        if texto is not None:
            self._texto = texto
        if estado is not None:
            self._estado = estado
        self._dibujar()

    def _dibujar(self) -> None:
        bg, fg = self.ESTADOS[self._estado]
        t = self._tam
        self.config(bg=P[self._fondo])
        self.delete("all")
        self.create_oval(1, 1, t - 1, t - 1, fill=P[bg], outline=P[bg])
        texto = "✓" if self._estado in ("hecho", "ok") and not self._texto else self._texto
        self.create_text(t / 2, t / 2, text=texto, fill=P[fg], font=F(11 if t <= 20 else 12, "bold"))


class Marca(tk.Canvas):
    """Marca «B» (cuadrado redondeado 26×26, fondo accent)."""

    def __init__(self, master, fondo: str = "surface"):
        super().__init__(master, width=26, height=26, highlightthickness=0, bd=0)
        self._fondo = fondo
        al_cambiar_tema(self._dibujar)

    def _dibujar(self) -> None:
        self.config(bg=P[self._fondo])
        self.delete("all")
        r, w = 7, 26
        pts = [r, 0, w - r, 0, w, 0, w, r, w, w - r, w, w, w - r, w, r, w, 0, w, 0, w - r, 0, r, 0, 0]
        self.create_polygon(pts, smooth=True, fill=P["accent"], outline=P["accent"])
        self.create_text(13, 13, text="B", fill=P["on_accent"], font=F(14, "bold"))


class Boton(ttk.Button):
    """Botón con estilos del diseño: primario / secundario / guardar / peligro / chico."""

    ESTILOS = {"primario": "Primario.TButton", "secundario": "Secundario.TButton", "guardar": "Guardar.TButton",
               "peligro": "Peligro.TButton", "chico": "Chico.TButton", "chico_primario": "ChicoPrimario.TButton"}

    def __init__(self, master, texto: str, comando=None, tipo: str = "secundario", **kw):
        super().__init__(master, text=texto, command=comando, style=self.ESTILOS[tipo], cursor="hand2", **kw)

    def habilitar(self, si: bool) -> None:
        self.state(["!disabled"] if si else ["disabled"])


class Ayuda:
    """Tooltip simple."""

    def __init__(self, widget, texto: str):
        self.widget, self.texto, self.win, self._job = widget, texto, None, None
        widget.bind("<Enter>", self._programar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<ButtonPress>", self._ocultar, add="+")

    def _programar(self, _e=None):
        self._job = self.widget.after(450, self._mostrar)

    def _mostrar(self):
        if self.win or not self.texto:
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.win = tk.Toplevel(self.widget)
        self.win.wm_overrideredirect(True)
        self.win.wm_geometry(f"+{x}+{y}")
        tk.Label(self.win, text=self.texto, justify="left", bg=P["ink"], fg=P["surface"], font=F(12),
                 padx=9, pady=6, wraplength=380).pack()

    def _ocultar(self, _e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.win:
            self.win.destroy()
            self.win = None


# ==============================================================================================
# Controles
# ==============================================================================================
class Segmentado(tk.Frame):
    """Control segmentado: contenedor «head», opción activa con fondo «surface»."""

    def __init__(self, master, opciones: Sequence[Tuple[str, str]], al_elegir: Callable[[str], None],
                 activo: Optional[str] = None):
        super().__init__(master, highlightthickness=1, padx=2, pady=2)
        self._cb = al_elegir
        self._items: Dict[str, tk.Label] = {}
        self._activo = activo or opciones[0][0]
        for valor, texto in opciones:
            lb = tk.Label(self, text=texto, font=F(12.5, "semibold"), padx=9, pady=3, cursor="hand2")
            lb.pack(side="left", padx=1)
            lb.bind("<Button-1>", lambda e, v=valor: self._elegir(v))
            self._items[valor] = lb
        al_cambiar_tema(self._tema)

    def _elegir(self, valor: str) -> None:
        self.set(valor)
        self._cb(valor)

    def set(self, valor: str) -> None:
        self._activo = valor
        self._tema()

    def set_textos(self, textos: Dict[str, str]) -> None:
        for v, t in textos.items():
            if v in self._items:
                self._items[v].config(text=t)

    def _tema(self) -> None:
        self.config(bg=P["head"], highlightbackground=P["line"])
        for v, lb in self._items.items():
            act = v == self._activo
            lb.config(bg=P["surface"] if act else P["head"], fg=P["ink"] if act else P["ink2"])


class ChipFiltro(tk.Frame):
    """Chip-filtro que funciona como leyenda: cuadradito de color + nombre + cantidad."""

    def __init__(self, master, texto: str, familia: Optional[str], al_click: Callable[[], None]):
        super().__init__(master, highlightthickness=1, padx=8, pady=3, cursor="hand2")
        self._familia, self._activo = familia, False
        self.cuadro = tk.Frame(self, width=10, height=10, highlightthickness=1)
        self.cuadro.pack(side="left", padx=(0, 6))
        self.txt = tk.Label(self, text=texto, font=F(12.5, "semibold"))
        self.txt.pack(side="left")
        self.cant = tk.Label(self, text="", font=F(12))
        self.cant.pack(side="left", padx=(6, 0))
        for w in (self, self.cuadro, self.txt, self.cant):
            w.bind("<Button-1>", lambda e: al_click())
        al_cambiar_tema(self._tema)

    def set(self, cantidad: Optional[int] = None, activo: Optional[bool] = None) -> None:
        if cantidad is not None:
            self.cant.config(text=fmt_n(cantidad))
        if activo is not None:
            self._activo = activo
        self._tema()

    def _tema(self) -> None:
        bg = P["accent_soft"] if self._activo else P["surface"]
        self.config(bg=bg, highlightbackground=P["accent"] if self._activo else P["line_strong"])
        if self._familia:
            fbg, ffg, frow = SEM[self._familia]
            self.cuadro.config(bg=P[fbg], highlightbackground=P[ffg])
        else:
            self.cuadro.config(bg=bg, highlightbackground=P["ink3"])
        self.txt.config(bg=bg, fg=P["ink"])
        self.cant.config(bg=bg, fg=P["ink3"])


class Buscador(tk.Frame):
    """Campo de búsqueda con placeholder, filtrado mientras se escribe y × para limpiar."""

    def __init__(self, master, al_cambiar: Callable[[str], None], placeholder: str = "Buscar CUIL o clave",
                 ancho: int = 22):
        super().__init__(master, highlightthickness=1, padx=6)
        self._cb, self._job, self._ph = al_cambiar, None, placeholder
        self.lupa = tk.Label(self, text="⌕", font=F(13))
        self.lupa.pack(side="left")
        self.var = tk.StringVar()
        self.e = tk.Entry(self, textvariable=self.var, relief="flat", width=ancho, font=F(13), bd=0)
        self.e.pack(side="left", ipady=4, padx=(4, 0))
        self.x = tk.Label(self, text="×", font=F(14), cursor="hand2")
        self.x.bind("<Button-1>", lambda e: self.limpiar())
        self._con_ph = True
        self.e.bind("<FocusIn>", self._focus_in)
        self.e.bind("<FocusOut>", self._focus_out)
        self.var.trace_add("write", lambda *a: self._programar())
        al_cambiar_tema(self._tema)
        self._focus_out()

    def valor(self) -> str:
        return "" if self._con_ph else self.var.get().strip()

    def limpiar(self) -> None:
        self._con_ph = False
        self.var.set("")
        self._focus_out()

    def _focus_in(self, _e=None):
        if self._con_ph:
            self._con_ph = False
            self.var.set("")
            self._tema()

    def _focus_out(self, _e=None):
        if not self.var.get():
            self._con_ph = True
            self.var.set(self._ph)
        self._tema()

    def _programar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(280, self._disparar)
        if self.valor():
            self.x.pack(side="left", padx=(4, 0))
        else:
            self.x.pack_forget()

    def _disparar(self):
        self._job = None
        self._cb(self.valor())

    def _tema(self) -> None:
        self.config(bg=P["surface"], highlightbackground=P["line_strong"], highlightcolor=P["accent"])
        for w in (self.lupa, self.x):
            w.config(bg=P["surface"], fg=P["ink3"])
        self.e.config(bg=P["surface"], fg=P["ink3"] if self._con_ph else P["ink"], insertbackground=P["ink"])


class Combo(ttk.Combobox):
    """Combobox con opciones (valor, texto, cantidad) → muestra «texto (N)»."""

    def __init__(self, master, ancho: int, al_elegir: Callable[[str], None]):
        self.var = tk.StringVar()
        super().__init__(master, textvariable=self.var, width=ancho, state="readonly", font=F(13))
        self._mapa: Dict[str, str] = {}
        self.bind("<<ComboboxSelected>>", lambda e: al_elegir(self._mapa.get(self.var.get(), "")))

    def cargar(self, opciones: Iterable[Tuple[str, str, int]], actual: str) -> None:
        self._mapa, textos = {}, []
        for valor, texto, n in opciones:
            t = f"{texto} ({fmt_n(n)})"
            self._mapa[t] = valor
            textos.append(t)
            if valor == actual:
                self.var.set(t)
        self.config(values=textos)


# ==============================================================================================
# Bloques
# ==============================================================================================
class Indicador(Caja):
    """Indicador: punto de color + etiqueta · número grande + subtexto. Clic opcional."""

    def __init__(self, master, etiqueta: str, familia: str, al_click: Optional[Callable[[], None]] = None):
        super().__init__(master, fondo="surface", borde="line", padx=14, pady=9)
        self._familia, self._activo = familia, False
        fila = tk.Frame(self)
        fila.pack(anchor="w", fill="x")
        self.punto = tk.Canvas(fila, width=8, height=8, highlightthickness=0, bd=0)
        self.punto.pack(side="left", padx=(0, 6))
        self.etq = tk.Label(fila, text=etiqueta, font=F(12))
        self.etq.pack(side="left")
        fila2 = tk.Frame(self)
        fila2.pack(anchor="w", fill="x")
        self.num = tk.Label(fila2, text="–", font=F(24, "semibold"))
        self.num.pack(side="left")
        self.sub = tk.Label(fila2, text="", font=F(12))
        self.sub.pack(side="left", padx=(8, 0), pady=(8, 0))
        self._filas = (fila, fila2)
        if al_click:
            for w in (self, fila, fila2, self.etq, self.num, self.sub, self.punto):
                w.bind("<Button-1>", lambda e: al_click())
                w.config(cursor="hand2")
        al_cambiar_tema(self._tema2)

    def _color(self) -> str:
        return P["accent"] if self._familia == "accent" else P[SEM[self._familia][1]]

    def _tema2(self) -> None:
        bg = P["surface2"] if self._activo else P["surface"]
        self.config(bg=bg, highlightbackground=P["line_strong"] if self._activo else P["line"])
        for w in self._filas + (self.etq, self.num, self.sub, self.punto):
            w.config(bg=bg)
        self.etq.config(fg=P["ink2"])
        self.sub.config(fg=P["ink3"])
        self.num.config(fg=self._color())
        self.punto.delete("all")
        self.punto.create_oval(0, 0, 7, 7, fill=self._color(), outline=self._color())

    def set(self, numero, subtexto: str = "", activo: Optional[bool] = None) -> None:
        self.num.config(text=fmt_n(numero) if isinstance(numero, int) else str(numero))
        self.sub.config(text=subtexto)
        if activo is not None:
            self._activo = activo
            self._tema2()


class Aviso(tk.Frame):
    """Aviso de estado con ícono, frase y botón de acción opcional."""

    TIPOS = {"neutro": ("neu_bg", "ink2", "○"), "info": ("accent_soft", "accent", "i"),
             "ok": ("ok_bg", "ok_fg", "✓"), "error": ("err_bg", "err_fg", "!"), "warn": ("warn_bg", "warn_fg", "!")}

    def __init__(self, master):
        super().__init__(master, padx=14, pady=8)
        self.icono = tk.Label(self, font=F(13, "bold"), width=2)
        self.icono.pack(side="left")
        self.txt = tk.Label(self, font=F(13, "semibold"), anchor="w", justify="left", wraplength=1050)
        self.txt.pack(side="left", fill="x", expand=True)
        self.marco_btn = tk.Frame(self, highlightthickness=1, cursor="hand2")
        self.btn = tk.Label(self.marco_btn, font=F(12.5, "semibold"), padx=10, pady=3, cursor="hand2")
        self.btn.pack()
        self._tipo, self._accion = "neutro", None
        for w in (self.marco_btn, self.btn):
            w.bind("<Button-1>", lambda e: self._accion and self._accion())
        al_cambiar_tema(self._tema)

    def mostrar(self, texto: str, tipo: str = "info", accion: Optional[Tuple[str, Callable[[], None]]] = None):
        self._tipo = tipo
        self.txt.config(text=texto)
        if accion:
            self.btn.config(text=accion[0])
            self._accion = accion[1]
            self.marco_btn.pack(side="right", padx=(10, 0))
        else:
            self._accion = None
            self.marco_btn.pack_forget()
        self._tema()

    def _tema(self) -> None:
        bg, fg, ic = self.TIPOS[self._tipo]
        for w in (self, self.icono, self.txt, self.marco_btn, self.btn):
            w.config(bg=P[bg])
        self.icono.config(text=ic, fg=P[fg])
        self.txt.config(fg=P[fg])
        self.btn.config(fg=P[fg])
        self.marco_btn.config(highlightbackground=P[fg])


class EstadoVacio(tk.Frame):
    """Estado vacío centrado (título + explicación + botón opcional)."""

    def __init__(self, master, fondo: str = "surface"):
        super().__init__(master)
        self._fondo = fondo
        self.titulo = tk.Label(self, font=F(15, "semibold"))
        self.titulo.pack(pady=(0, 6))
        self.txt = tk.Label(self, font=F(13), justify="center", wraplength=560)
        self.txt.pack()
        self.btn = Boton(self, "", tipo="secundario")
        al_cambiar_tema(self._tema)

    def mostrar(self, sobre: tk.Widget, titulo: str, texto: str,
                boton: Optional[Tuple[str, Callable[[], None]]] = None) -> None:
        self.titulo.config(text=titulo)
        self.txt.config(text=texto)
        if boton:
            self.btn.config(text=boton[0], command=boton[1])
            self.btn.pack(pady=(12, 0))
        else:
            self.btn.pack_forget()
        self.place(in_=sobre, relx=0.5, rely=0.5, anchor="center")
        self.lift()

    def ocultar(self) -> None:
        self.place_forget()

    def _tema(self) -> None:
        for w in (self, self.titulo, self.txt):
            w.config(bg=P[self._fondo])
        self.titulo.config(fg=P["ink"])
        self.txt.config(fg=P["ink3"])


# ==============================================================================================
# Tabla
# ==============================================================================================
class Tabla(tk.Frame):
    """Treeview del diseño: encabezado «head», tintes de fila por estado, números a la derecha,
    orden por columna (▲ → ▼ → sin orden) y casillas opcionales (columna ☐/☑)."""

    def __init__(self, master, columnas: Sequence[Tuple], checks: bool = False, altura: int = 8,
                 al_enfocar: Optional[Callable[[str], None]] = None,
                 al_doble: Optional[Callable[[str], None]] = None,
                 al_marcar: Optional[Callable[[], None]] = None):
        """columnas: (id, título, ancho[, 'e' para alinear a la derecha[, stretch]])."""
        super().__init__(master, highlightthickness=0)
        self.checks = checks
        self._titulos: Dict[str, str] = {}
        self._anclas: Dict[str, str] = {}
        ids = (["_chk"] if checks else []) + [c[0] for c in columnas]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", height=altura, selectmode="browse")
        if checks:
            self.tree.heading("_chk", text="☐", anchor="center", command=self._marcar_todos_toggle)
            self.tree.column("_chk", width=34, minwidth=34, stretch=False, anchor="center")
        for c in columnas:
            cid, titulo, ancho = c[0], c[1], c[2]
            ancla = c[3] if len(c) > 3 and c[3] else "w"
            stretch = bool(c[4]) if len(c) > 4 else False
            self._titulos[cid], self._anclas[cid] = titulo, ancla
            self.tree.heading(cid, text=titulo, anchor=ancla, command=lambda x=cid: self.ordenar(x))
            self.tree.column(cid, width=ancho, minwidth=40, stretch=stretch, anchor=ancla)
        self.ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.xs = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.ys.set, xscrollcommand=self.xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.ys.grid(row=0, column=1, sticky="ns")
        self.xs.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.marcados: set = set()
        self._orden: Tuple[Optional[str], int] = (None, 0)     # (columna, 1 asc / -1 desc / 0)
        self._original: List[str] = []
        self._job = None
        self._al_enfocar, self._al_marcar = al_enfocar, al_marcar
        self.tree.bind("<Button-1>", self._clic, add="+")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._enfocado())
        if al_doble:
            self.tree.bind("<Double-1>", lambda e: self._doble(e, al_doble))
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        self.config(bg=P["surface"])
        for fam, (bg, fg, row) in SEM.items():
            self.tree.tag_configure(fam, background=P[row], foreground=P["ink"])
        self.tree.tag_configure("foco", background=P["focus_row"])

    # ---- eventos
    def _clic(self, e):
        if not self.checks:
            return None
        region = self.tree.identify_region(e.x, e.y)
        col = self.tree.identify_column(e.x)
        if region == "cell" and col == "#1":
            iid = self.tree.identify_row(e.y)
            if iid:
                self.alternar(iid)
            return "break"
        return None

    def _doble(self, e, fn):
        if self.checks and self.tree.identify_column(e.x) == "#1":
            return
        iid = self.tree.identify_row(e.y)
        if iid:
            fn(iid)

    def _enfocado(self):
        sel = self.tree.selection()
        if sel and self._al_enfocar:
            self._al_enfocar(sel[0])

    # ---- casillas
    def alternar(self, iid: str) -> None:
        if iid in self.marcados:
            self.marcados.discard(iid)
        else:
            self.marcados.add(iid)
        self.tree.set(iid, "_chk", "☑" if iid in self.marcados else "☐")
        self._actualizar_cabecera()
        if self._al_marcar:
            self._al_marcar()

    def marcar_todos(self, si: bool) -> None:
        todos = self.tree.get_children("")
        self.marcados = set(todos) if si else set()
        for iid in todos:
            self.tree.set(iid, "_chk", "☑" if si else "☐")
        self._actualizar_cabecera()
        if self._al_marcar:
            self._al_marcar()

    def _marcar_todos_toggle(self) -> None:
        todos = self.tree.get_children("")
        self.marcar_todos(not (todos and len(self.marcados) >= len(todos)))

    def _actualizar_cabecera(self) -> None:
        if self.checks:
            n, total = len(self.marcados), len(self.tree.get_children(""))
            self.tree.heading("_chk", text="☑" if total and n >= total else ("◪" if n else "☐"))

    # ---- datos
    def limpiar(self) -> None:
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.tree.delete(*self.tree.get_children())
        self._original = []

    def cargando(self) -> bool:
        return self._job is not None

    def todos(self) -> List[str]:
        return list(self.tree.get_children(""))

    def cargar(self, filas: List[Tuple[str, Sequence, str]], lote: int = 1500) -> None:
        """filas: (iid, valores, familia de tinte o '')."""
        foco = self.tree.selection()
        self.limpiar()
        ids = {f[0] for f in filas}
        self.marcados &= ids
        self._original = [f[0] for f in filas]

        def paso(i=0):
            for iid, valores, fam in filas[i:i + lote]:
                vals = (["☑" if iid in self.marcados else "☐"] if self.checks else []) + list(valores)
                self.tree.insert("", "end", iid=iid, values=vals, tags=(fam,) if fam else ())
            if i + lote < len(filas):
                self._job = self.after(1, paso, i + lote)
            else:
                self._job = None
                self._reordenar()
                self._actualizar_cabecera()
                if foco and self.tree.exists(foco[0]):
                    self.tree.selection_set(foco[0])
                    self.tree.see(foco[0])
        paso()

    # ---- orden (▲ → ▼ → sin orden)
    def ordenar(self, col: str) -> None:
        actual, d = self._orden
        d = 1 if actual != col else (-1 if d == 1 else (0 if d == -1 else 1))
        self._orden = (col if d else None, d)
        self._reordenar()

    def _reordenar(self) -> None:
        col, d = self._orden
        if col and d:
            def clave(iid):
                v = str(self.tree.set(iid, col))
                s = v.split("→")[-1].strip().replace(".", "").replace(",", ".")
                try:
                    return (0, float(s))
                except ValueError:
                    return (1, v)
            items = sorted(self.tree.get_children(""), key=clave, reverse=d == -1)
        else:
            items = [i for i in self._original if self.tree.exists(i)]
        for i, k in enumerate(items):
            self.tree.move(k, "", i)
        for cid, titulo in self._titulos.items():
            flecha = ("  ▲" if d == 1 else "  ▼") if cid == col and d else ""
            self.tree.heading(cid, text=titulo + flecha)


class BarraFina(tk.Frame):
    """Barra de progreso fina (alto fijo en px) dibujada con frames: Tk no permite 3 px con ttk."""

    def __init__(self, master, alto: int = 3, color: str = "accent", fondo: str = "line", ancho: Optional[int] = None):
        super().__init__(master, height=alto, **({"width": ancho} if ancho else {}))
        self.pack_propagate(False)
        self._color, self._fondo, self._v, self._job, self._pos = color, fondo, 0.0, None, 0.0
        self.relleno = tk.Frame(self, height=alto)
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        self.config(bg=P[self._fondo])
        self.relleno.config(bg=P[self._color])

    def set_color(self, color: str) -> None:
        self._color = color
        self._tema()

    def set(self, valor: float) -> None:
        self.detener()
        self._v = max(0.0, min(100.0, valor))
        self.relleno.place_forget()
        if self._v > 0:
            self.relleno.place(relx=0, x=0, y=0, relheight=1, relwidth=self._v / 100)

    def indeterminado(self) -> None:
        if self._job:
            return

        def paso():
            self._pos = (self._pos + 0.012) % 1.25
            self.relleno.place(relx=self._pos - 0.25, y=0, relheight=1, relwidth=0.25)
            self._job = self.after(16, paso)
        paso()

    def detener(self) -> None:
        if self._job:
            self.after_cancel(self._job)
            self._job = None


# ==============================================================================================
# Barra de progreso integrada
# ==============================================================================================
class BarraProgreso(tk.Frame):
    """Progreso fijo debajo del encabezado: ícono · título/detalle · pasos · % · barra de 3 px."""

    def __init__(self, master):
        super().__init__(master)
        fila = tk.Frame(self, padx=20, pady=8)
        fila.pack(fill="x")
        self.icono = Circulo(fila, "●", "idle", 22, fondo="surface2")
        self.icono.pack(side="left", padx=(0, 10))
        tit = tk.Frame(fila)
        tit.pack(side="left")
        self.titulo = tk.Label(tit, font=F(13, "semibold"), anchor="w")
        self.titulo.pack(anchor="w")
        self.detalle = tk.Label(tit, font=F(12), anchor="w")
        self.detalle.pack(anchor="w")
        self.pasos = tk.Frame(fila)
        self.pasos.pack(side="left", padx=(24, 0))
        self.pct = tk.Label(fila, font=F(13, "semibold"), width=6, anchor="e")
        self.pct.pack(side="right")
        self.pb = BarraFina(self, 3, "accent", "line")
        self.pb.pack(fill="x", side="bottom")
        self._marcos = (self, fila, tit, self.pasos)
        self._pasos: List[Tuple[str, str]] = []
        self._pesos: Dict[str, float] = {}
        self._estado: Dict[str, str] = {}
        self._indet = False
        self._color_tit = "ink"
        al_cambiar_tema(self._tema)
        self.reposo("Listo", "Elegí el Excel original de Presmed y presioná «Analizar».")

    def _tema(self) -> None:
        for w in self._marcos:
            w.config(bg=P["surface2"])
        self.titulo.config(bg=P["surface2"], fg=P[self._color_tit])
        self.detalle.config(bg=P["surface2"], fg=P["ink3"])
        self.pct.config(bg=P["surface2"], fg=P["ink"])
        self._pintar_pasos()

    def _pintar_pasos(self) -> None:
        for w in self.pasos.winfo_children():
            w.destroy()
        for i, (pid, nombre) in enumerate(self._pasos):
            if i:
                tk.Label(self.pasos, text="›", bg=P["surface2"], fg=P["ink3"], font=F(12)).pack(side="left", padx=6)
            est = self._estado.get(pid, "")
            txt, fg, peso = {"ok": (f"✓ {nombre}", "ink2", "normal"), "actual": (f"▸ {nombre}", "accent", "semibold"),
                             "": (f"○ {nombre}", "ink3", "normal")}[est]
            tk.Label(self.pasos, text=txt, bg=P["surface2"], fg=P[fg], font=F(12, peso)).pack(side="left")

    def _valor(self, v: float, pct: bool = True) -> None:
        self._indet = False
        self.pb.set(v)
        self.pct.config(text=f"{int(v)} %" if pct else "")

    def reposo(self, titulo: str, detalle: str = "") -> None:
        self._pasos, self._estado = [], {}
        self._color_tit = "ink"
        self.icono.set("●", "idle")
        self.titulo.config(text=titulo, fg=P["ink"])
        self.detalle.config(text=detalle)
        self.pb.set_color("accent")
        self._valor(0, pct=False)
        self._pintar_pasos()

    def iniciar(self, titulo: str, pasos: Sequence[Tuple[str, str]], pesos: Optional[Dict[str, float]] = None):
        self._pasos = list(pasos)
        n = len(self._pasos) or 1
        self._pesos = pesos or {p: 1 / n for p, _ in self._pasos}
        self._estado = {}
        self._color_tit = "ink"
        self.icono.set("…", "curso")
        self.titulo.config(text=titulo, fg=P["ink"])
        self.detalle.config(text="")
        self.pb.set_color("accent")
        self._valor(0)
        self._pintar_pasos()

    def avanzar(self, paso: str, texto: str, cur: int, tot: int) -> None:
        ids = [p for p, _ in self._pasos]
        if paso in ids:
            cambio = self._estado.get(paso) != "actual"
            for pid in ids[:ids.index(paso)]:
                self._estado[pid] = "ok"
            self._estado[paso] = "actual"
            if cambio:
                self._pintar_pasos()
        self.detalle.config(text=texto)
        base = sum(self._pesos.get(p, 0) for p in ids[:ids.index(paso)]) if paso in ids else 0
        peso = self._pesos.get(paso, 0)
        if tot <= 0:
            if not self._indet:
                self.pb.indeterminado()
                self._indet = True
            self.pct.config(text=f"{int(base * 100)} %")
        else:
            self._valor(100 * (base + peso * min(cur / tot, 1)))

    def terminar(self, titulo: str, detalle: str = "", ok: bool = True) -> None:
        for pid, _ in self._pasos:
            self._estado[pid] = "ok"
        self._valor(100)
        self.pb.set_color("ok_fg" if ok else "err_fg")
        self._color_tit = "ink" if ok else "err_fg"
        self.icono.set("" if ok else "!", "ok" if ok else "error")
        self.titulo.config(text=titulo, fg=P[self._color_tit])
        self.detalle.config(text=detalle)
        self._pintar_pasos()


# ==============================================================================================
# Pestañas propias (círculo con número + texto + contador + subrayado de 2 px)
# ==============================================================================================
class BarraPestanas(tk.Frame):
    def __init__(self, master, al_elegir: Callable[[str], None]):
        super().__init__(master, padx=14)
        self._cb = al_elegir
        self._items: Dict[str, dict] = {}
        self._activa: Optional[str] = None
        self._seps: List[tk.Frame] = []
        al_cambiar_tema(self._tema)

    def agregar(self, pid: str, texto: str, numero: Optional[str] = None) -> None:
        cont = tk.Frame(self, cursor="hand2")
        cont.pack(side="left", padx=(0, 4))
        fila = tk.Frame(cont, padx=12, pady=9, cursor="hand2")
        fila.pack()
        circ = Circulo(fila, numero, "pendiente", 20) if numero else None
        if circ:
            circ.pack(side="left", padx=(0, 8))
        lb = tk.Label(fila, text=texto, font=F(13.5, "semibold"), cursor="hand2")
        lb.pack(side="left")
        pill = tk.Label(fila, text="", font=F(11.5, "semibold"), padx=7)
        sub = tk.Frame(cont, height=2)
        sub.pack(fill="x", side="bottom")
        for w in (cont, fila, lb, pill) + ((circ,) if circ else ()):
            w.bind("<Button-1>", lambda e, p=pid: self._cb(p))
        self._items[pid] = {"cont": cont, "fila": fila, "circ": circ, "lb": lb, "pill": pill, "sub": sub, "n": None}
        self._tema()

    def separador(self) -> None:
        s = tk.Frame(self, width=1, height=20)
        s.pack(side="left", padx=8, pady=12)
        self._seps.append(s)
        self._tema()

    def set_activa(self, pid: str) -> None:
        self._activa = pid
        self._tema()

    def set_contador(self, pid: str, n: Optional[int]) -> None:
        it = self._items[pid]
        it["n"] = n
        if not n:
            it["pill"].pack_forget()
        else:
            it["pill"].config(text=fmt_n(n))
            it["pill"].pack(side="left", padx=(8, 0))

    def _tema(self) -> None:
        self.config(bg=P["surface"])
        for s in self._seps:
            s.config(bg=P["line"])
        for pid, it in self._items.items():
            act = pid == self._activa
            for w in (it["cont"], it["fila"], it["lb"]):
                w.config(bg=P["surface"])
            it["lb"].config(fg=P["ink"] if act else P["ink2"])
            it["sub"].config(bg=P["accent"] if act else P["surface"])
            it["pill"].config(bg=P["pend_bg"], fg=P["pend_fg"])
            if it["circ"]:
                it["circ"]._fondo = "surface"
                it["circ"].set(estado="actual" if act else "pendiente")


# ==============================================================================================
# Toast y diálogos
# ==============================================================================================
class Toast(tk.Frame):
    """Aviso flotante abajo al centro: «✓ Se aplicaron N correcciones.» [Deshacer] ×. Se cierra a los 7 s."""

    def __init__(self, root: tk.Misc):
        super().__init__(root, padx=14, pady=9)
        self.ic = tk.Label(self, text="✓", font=F(13, "bold"))
        self.ic.pack(side="left", padx=(0, 8))
        self.txt = tk.Label(self, font=F(13))
        self.txt.pack(side="left")
        self.acc = tk.Label(self, font=F(13, "semibold"), cursor="hand2", padx=12)
        self.cerrar = tk.Label(self, text="×", font=F(15), cursor="hand2")
        self.cerrar.pack(side="right", padx=(8, 0))
        self.cerrar.bind("<Button-1>", lambda e: self.ocultar())
        self._job, self._fn = None, None
        self.acc.bind("<Button-1>", lambda e: (self.ocultar(), self._fn and self._fn()))
        al_cambiar_tema(self._tema)

    def _tema(self) -> None:
        for w in (self, self.ic, self.txt, self.acc, self.cerrar):
            w.config(bg=P["ink"])
        self.txt.config(fg=P["surface"])
        self.ic.config(fg=P["ok_bg"])
        self.acc.config(fg=P["accent_soft"])
        self.cerrar.config(fg=P["line_strong"])

    def mostrar(self, texto: str, accion: Optional[Tuple[str, Callable[[], None]]] = None) -> None:
        self.txt.config(text=texto)
        if accion:
            self.acc.config(text=accion[0])
            self._fn = accion[1]
            self.acc.pack(side="left", before=self.cerrar)
        else:
            self._fn = None
            self.acc.pack_forget()
        self.place(relx=0.5, rely=1.0, y=-70, anchor="s")
        self.lift()
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(7000, self.ocultar)

    def ocultar(self) -> None:
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.place_forget()


class _Velo:
    """Oscurece la ventana detrás de un modal (sólo Windows, donde Tk soporta transparencia)."""

    def __init__(self, root: tk.Misc):
        self.win = None
        if not sys.platform.startswith("win"):
            return
        try:
            self.win = tk.Toplevel(root)
            self.win.overrideredirect(True)
            self.win.configure(bg=P["overlay"])
            self.win.attributes("-alpha", 0.42)
            self.win.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_rootx()}+{root.winfo_rooty()}")
        except tk.TclError:
            self.win = None

    def cerrar(self) -> None:
        if self.win:
            self.win.destroy()


def confirmar(root: tk.Misc, titulo: str, texto: str, resumen: Sequence[Tuple[str, str]] = (),
              nota: str = "", accion: str = "Aceptar", tipo: str = "primario") -> bool:
    """Diálogo modal de confirmación (500 px): título · texto · tabla de resumen · nota · [Cancelar] [Acción]."""
    velo = _Velo(root)
    win = tk.Toplevel(root)
    win.withdraw()
    win.title(titulo)
    win.transient(root)
    win.resizable(False, False)
    win.configure(bg=P["surface"])
    cont = tk.Frame(win, bg=P["surface"], padx=22, pady=18)
    cont.pack(fill="both", expand=True)
    tk.Label(cont, text=titulo, font=F(16, "semibold"), bg=P["surface"], fg=P["ink"], anchor="w").pack(fill="x")
    tk.Label(cont, text=texto, font=F(13), bg=P["surface"], fg=P["ink2"], anchor="w", justify="left",
             wraplength=456).pack(fill="x", pady=(6, 12))
    if resumen:
        tabla = tk.Frame(cont, bg=P["surface"], highlightthickness=1, highlightbackground=P["line"])
        tabla.pack(fill="x")
        for i, (k, v) in enumerate(resumen):
            if i:
                tk.Frame(tabla, bg=P["line"], height=1).pack(fill="x")
            f = tk.Frame(tabla, bg=P["surface"], padx=10, pady=7)
            f.pack(fill="x")
            tk.Label(f, text=k, font=F(13), bg=P["surface"], fg=P["ink2"]).pack(side="left")
            tk.Label(f, text=v, font=F(13, "semibold"), bg=P["surface"], fg=P["ink"]).pack(side="right")
    if nota:
        tk.Label(cont, text=nota, font=F(12.5), bg=P["warn_bg"], fg=P["warn_fg"], justify="left", anchor="w",
                 wraplength=440, padx=12, pady=9).pack(fill="x", pady=(12, 0))
    botones = tk.Frame(cont, bg=P["surface"])
    botones.pack(fill="x", pady=(16, 0))
    res = {"ok": False}

    def cerrar(ok: bool):
        res["ok"] = ok
        win.grab_release()
        win.destroy()
    Boton(botones, accion, lambda: cerrar(True), tipo=tipo).pack(side="right")
    Boton(botones, "Cancelar", lambda: cerrar(False)).pack(side="right", padx=(0, 8))
    win.bind("<Escape>", lambda e: cerrar(False))
    win.protocol("WM_DELETE_WINDOW", lambda: cerrar(False))
    win.update_idletasks()
    w = 500
    h = win.winfo_reqheight()
    x = root.winfo_rootx() + (root.winfo_width() - w) // 2
    y = root.winfo_rooty() + (root.winfo_height() - h) // 3
    win.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
    win.deiconify()
    win.grab_set()
    win.focus_set()
    root.wait_window(win)
    velo.cerrar()
    return res["ok"]
