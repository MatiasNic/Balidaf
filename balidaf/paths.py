"""Rutas de recursos y del archivo de errores (funciona en .py y en .exe onefile de PyInstaller)."""

import os
import sys

ERROR_LOG_NAME = "balidaf_errores.log"


def resource_path(*parts: str) -> str:
    """Ruta a un recurso empaquetado (p. ej. ``resource_path("assets", "balidaf.ico")``).

    En PyInstaller onefile los recursos se extraen en ``sys._MEIPASS``; desde el código
    fuente se resuelven relativo a la raíz del repositorio.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


def error_log_path() -> str:
    """``balidaf_errores.log`` junto al ejecutable (``.exe``) o junto a ``main.py``."""
    base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
    return os.path.join(base, ERROR_LOG_NAME)


def write_error_log(header: str) -> None:
    """Escribe el traceback actual en el archivo de errores (silencioso si falla)."""
    import traceback
    try:
        with open(error_log_path(), "w", encoding="utf-8") as f:
            f.write(header + "\n")
            traceback.print_exc(file=f)
    except Exception:
        pass
