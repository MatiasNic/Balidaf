"""
Tema visual de Balidaf (diseño «Rediseño Balidaf»): tokens de color claro/oscuro, tipografías y estilos ttk.

Los componentes piden colores por NOMBRE de token (``P["accent"]``) y se registran con
``al_cambiar_tema`` para repintarse cuando el usuario alterna ☾ / ☀.
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Dict, List

# ----------------------------------------------------------------------------------------------
# Tokens (convertidos del diseño en oklch a hex)
# ----------------------------------------------------------------------------------------------
TEMAS: Dict[str, Dict[str, str]] = {
    "claro": {
        "bg": "#f3f3f0", "surface": "#ffffff", "surface2": "#f8f8f6", "head": "#f0f0ec",
        "line": "#e4e3de", "line_strong": "#cbc9c2", "ink": "#1c2024", "ink2": "#545b62", "ink3": "#858a90",
        "accent": "#1a6382", "accent_hover": "#005170", "on_accent": "#ffffff", "accent_soft": "#e2f1fa",
        "focus_row": "#d0ebfa",
        "pend_bg": "#daeefe", "pend_fg": "#12557c", "pend_row": "#f2f9fe",
        "ok_bg": "#daf3e1", "ok_fg": "#225a39", "ok_row": "#f2faf4",
        "err_bg": "#ffe4e1", "err_fg": "#9a3936", "err_row": "#fff3f2",
        "warn_bg": "#fde8cb", "warn_fg": "#7d4f1b", "warn_row": "#fff7e9",
        "vio_bg": "#eee7fd", "vio_fg": "#5c4a7b", "vio_row": "#f8f5ff",
        "neu_bg": "#ecebe7", "neu_fg": "#545b62", "code": "#f4f4f1", "overlay": "#181c20",
    },
    "oscuro": {
        "bg": "#131518", "surface": "#1a1d21", "surface2": "#1f2226", "head": "#22262b",
        "line": "#2c3137", "line_strong": "#3d434a", "ink": "#e5e7e9", "ink2": "#a6acb3", "ink3": "#767d85",
        "accent": "#71b5d7", "accent_hover": "#81c5e8", "on_accent": "#0f1720", "accent_soft": "#152f3c",
        "focus_row": "#113545",
        "pend_bg": "#18364a", "pend_fg": "#9ecef1", "pend_row": "#131d24",
        "ok_bg": "#1c3a27", "ok_fg": "#9ed7b1", "ok_row": "#131f17",
        "err_bg": "#502825", "err_fg": "#f4b0aa", "err_row": "#2b1817",
        "warn_bg": "#473418", "warn_fg": "#eac490", "warn_row": "#251c11",
        "vio_bg": "#372d49", "vio_fg": "#cebeef", "vio_row": "#1e1b26",
        "neu_bg": "#2a2e33", "neu_fg": "#a6acb3", "code": "#16191c", "overlay": "#000000",
    },
}
P: Dict[str, str] = dict(TEMAS["claro"])      # paleta activa
TEMA_ACTUAL = ["claro"]

# Tipografías: IBM Plex si está instalada; si no, Segoe UI / Consolas
FUENTES = {"ui": "Segoe UI", "mono": "Consolas"}


def inicializar_fuentes(root: tk.Misc) -> None:
    familias = set(tkfont.families(root))
    for clave, opciones in (("ui", ("IBM Plex Sans", "Segoe UI", "Helvetica")),
                            ("mono", ("IBM Plex Mono", "Consolas", "Courier New", "Courier"))):
        for f in opciones:
            if f in familias:
                FUENTES[clave] = f
                break


def F(px: float, peso: str = "normal", mono: bool = False):
    """Fuente según tamaño del diseño en px (13 px de diseño ≈ 10 pt)."""
    pt = max(7, round(px * 0.75 + 0.25))
    return (FUENTES["mono" if mono else "ui"], pt, "bold" if peso in ("bold", "semibold") else "normal")


# ----------------------------------------------------------------------------------------------
# Cambio de tema
# ----------------------------------------------------------------------------------------------
_observadores: List[Callable[[], None]] = []


def al_cambiar_tema(fn: Callable[[], None]) -> None:
    """Registra una función de repintado; se ejecuta ahora y en cada cambio de tema."""
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
            pass
    _observadores[:] = vivos


def mezclar(c1: str, c2: str, t: float) -> str:
    """Mezcla dos colores hex (t = 0 → c1, t = 1 → c2). Se usa para simular opacidad."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def deshabilitado(color: str, fondo: str = "surface") -> str:
    """Color a 42 % de opacidad sobre el fondo (botones deshabilitados del diseño)."""
    return mezclar(P[fondo], color, 0.42)


def configurar_estilos(root: tk.Misc) -> None:
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    root.option_add("*Font", F(13))
    for k, v in (("background", P["surface"]), ("foreground", P["ink"]),
                 ("selectBackground", P["focus_row"]), ("selectForeground", P["ink"]), ("font", F(13))):
        root.option_add(f"*TCombobox*Listbox.{k}", v)
    try:
        root.configure(bg=P["bg"])
    except tk.TclError:
        pass

    st.configure(".", font=F(13), background=P["bg"], foreground=P["ink"], bordercolor=P["line"],
                 lightcolor=P["line"], darkcolor=P["line"], troughcolor=P["surface2"],
                 fieldbackground=P["surface"], insertcolor=P["ink"], selectbackground=P["focus_row"],
                 selectforeground=P["ink"], focuscolor=P["accent"])
    for fondo in ("bg", "surface", "surface2", "head"):
        st.configure(f"{fondo}.TFrame", background=P[fondo])
    st.configure("TFrame", background=P["bg"])
    st.configure("TLabel", background=P["bg"], foreground=P["ink"])
    st.configure("TPanedwindow", background=P["surface"])
    st.configure("Sash", background=P["line_strong"], sashthickness=4)

    # ---- Botones: principal / secundario / guardar / peligro (alto 32–34, radio no disponible en ttk)
    def boton(nombre, bg, fg, borde, hover, fuente_peso="semibold", pad=(16, 6)):
        st.configure(nombre, background=bg, foreground=fg, bordercolor=borde, lightcolor=borde, darkcolor=borde,
                     font=F(13, fuente_peso), padding=pad, focusthickness=0, relief="flat")
        st.map(nombre,
               background=[("disabled", deshabilitado(bg, "surface") if bg != P["surface"] else P["surface"]),
                           ("pressed", hover), ("active", hover)],
               foreground=[("disabled", deshabilitado(fg, "surface") if bg == P["surface"] else
                            mezclar(deshabilitado(bg, "surface"), fg, 0.75))],
               bordercolor=[("disabled", deshabilitado(borde, "surface")), ("active", hover if bg != P["surface"] else borde)],
               lightcolor=[("disabled", deshabilitado(borde, "surface")), ("active", hover if bg != P["surface"] else borde)],
               darkcolor=[("disabled", deshabilitado(borde, "surface")), ("active", hover if bg != P["surface"] else borde)])

    boton("Primario.TButton", P["accent"], P["on_accent"], P["accent"], P["accent_hover"])
    boton("Secundario.TButton", P["surface"], P["ink"], P["line_strong"], P["surface2"], "normal", (12, 6))
    boton("Guardar.TButton", P["ok_fg"], P["surface"], P["ok_fg"], mezclar(P["ok_fg"], P["ink"], 0.15))
    boton("Peligro.TButton", P["err_fg"], P["surface"], P["err_fg"], mezclar(P["err_fg"], P["ink"], 0.15))
    boton("Chico.TButton", P["surface"], P["ink"], P["line_strong"], P["surface2"], "semibold", (10, 3))
    boton("ChicoPrimario.TButton", P["accent"], P["on_accent"], P["accent"], P["accent_hover"], "semibold", (10, 3))
    st.configure("TButton", padding=(10, 5))

    # ---- Entradas
    st.configure("TEntry", fieldbackground=P["surface"], foreground=P["ink"], bordercolor=P["line_strong"],
                 lightcolor=P["line_strong"], darkcolor=P["line_strong"], padding=(8, 5))
    st.map("TEntry", bordercolor=[("focus", P["accent"])], lightcolor=[("focus", P["accent"])])
    st.configure("Ruta.TEntry", fieldbackground=P["surface2"], foreground=P["ink"], padding=(10, 6))
    st.configure("TCombobox", fieldbackground=P["surface"], background=P["surface"], foreground=P["ink"],
                 arrowcolor=P["ink2"], bordercolor=P["line_strong"], lightcolor=P["surface"],
                 darkcolor=P["surface"], padding=(8, 4))
    st.map("TCombobox", fieldbackground=[("readonly", P["surface"])], foreground=[("readonly", P["ink"])],
           selectbackground=[("readonly", P["surface"])], selectforeground=[("readonly", P["ink"])],
           bordercolor=[("focus", P["accent"])])

    # ---- Scrollbars finas
    for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(sb, background=P["line_strong"], troughcolor=P["surface"], arrowcolor=P["ink3"],
                     bordercolor=P["surface"], lightcolor=P["line_strong"], darkcolor=P["line_strong"],
                     gripcount=0, arrowsize=11)
        st.map(sb, background=[("active", P["ink3"])])

    # ---- Tablas
    st.configure("Treeview", rowheight=31, font=F(13), background=P["surface"], fieldbackground=P["surface"],
                 foreground=P["ink"], bordercolor=P["line"], borderwidth=0, relief="flat")
    st.map("Treeview", background=[("selected", P["focus_row"])], foreground=[("selected", P["ink"])])
    st.configure("Treeview.Heading", font=F(12, "semibold"), background=P["head"], foreground=P["ink2"],
                 bordercolor=P["line"], lightcolor=P["head"], darkcolor=P["line"], relief="flat", padding=(8, 6))
    st.map("Treeview.Heading", background=[("active", P["line"])], foreground=[("active", P["ink"])])
    st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # ---- Progreso
    st.configure("Fina.Horizontal.TProgressbar", troughcolor=P["line"], background=P["accent"], thickness=3,
                 bordercolor=P["line"], lightcolor=P["accent"], darkcolor=P["accent"])
    st.configure("FinaOk.Horizontal.TProgressbar", troughcolor=P["line"], background=P["ok_fg"], thickness=3,
                 bordercolor=P["line"], lightcolor=P["ok_fg"], darkcolor=P["ok_fg"])
    st.configure("Mini.Horizontal.TProgressbar", troughcolor=P["line"], background=P["ok_fg"], thickness=6,
                 bordercolor=P["line"], lightcolor=P["ok_fg"], darkcolor=P["ok_fg"])
