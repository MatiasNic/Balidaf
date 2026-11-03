"""Interfaz gráfica de Balidaf (Tkinter)."""


def run_gui() -> None:
    from .app import BalidafApp
    BalidafApp().mainloop()
