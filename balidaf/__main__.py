"""
Punto de entrada.

    python main.py                       → abre la interfaz gráfica
    python main.py archivo.xlsx          → procesa sin interfaz (consola)
    python main.py archivo.xlsx -o salida.xlsx
    python -m balidaf ...                → equivalente
"""

import argparse
import sys

if sys.version_info < (3, 8):
    print("ERROR: Se requiere Python 3.8 o superior.")
    sys.exit(1)

try:
    import openpyxl  # noqa: F401
except Exception:
    print("ERROR: No se pudo importar openpyxl. Instale con: pip install -r requirements.txt")
    sys.exit(1)

from . import APP_TITLE, __version__
from .paths import write_error_log


def _run_cli(path: str, out_path=None) -> int:
    from .core import process_file

    try:
        result = process_file(path, log=print, out_path=out_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print()
    print("RESUMEN")
    print(f"- Hoja utilizada        : {result.sheet_used}")
    print(f"- Archivo generado      : {result.out_path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="balidaf", description=APP_TITLE)
    parser.add_argument("excel", nargs="?", help="Excel a procesar. Si se omite, se abre la interfaz gráfica.")
    parser.add_argument("-o", "--output", help="Ruta del Excel de salida (por defecto <archivo>_balidaf.xlsx).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    if args.excel:
        return _run_cli(args.excel, args.output)

    try:
        from .gui import run_gui
        run_gui()
        return 0
    except Exception:
        # Error al inicializar GUI (p.ej., Tkinter ausente)
        write_error_log("ERROR INICIALIZANDO GUI:")
        print("ERROR: No fue posible iniciar la interfaz gráfica.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
