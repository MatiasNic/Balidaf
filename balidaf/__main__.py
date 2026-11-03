"""
Punto de entrada.

    python main.py                                   → abre la interfaz gráfica
    python main.py archivo.xlsx                      → balancea y valida por consola
    python main.py archivo.xlsx -o salida.xlsx       → salida personalizada
    python main.py archivo.xlsx --err ERR.txt        → además cruza con la devolución de la SSS
    python main.py archivo.xlsx --informe            → además exporta el informe de detalle
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


def _cli(args) -> int:
    from .devolucion import cruzar
    from .informe import exportar, ruta_informe
    from .proceso import guardar, procesar
    from .sss_txt import leer_txt

    def log(nivel, msg):
        print(("\n" if nivel == "titulo" else "") + msg)

    try:
        r = procesar(args.excel, log=log)
        if r.lote.faltantes:
            return 1
        guardar(r, args.output, log=log)
        cruce = None
        if args.err or args.ok:
            cruce = cruzar(r.lote, r.despues, leer_txt(args.err, "ERR") if args.err else None,
                           leer_txt(args.ok, "OK") if args.ok else None)
            log("titulo", "Cruce con la devolución de la SSS")
            for est, n in cruce.por_estado.items():
                log("info", f"  {est}: {n}")
        if args.informe:
            log("ok", f"Informe: {exportar(r, ruta_informe(args.excel), cruce)}")
    except Exception as exc:
        write_error_log("ERROR CLI:")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0 if r.listo_para_presmed else 3


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="balidaf", description=APP_TITLE)
    p.add_argument("excel", nargs="?", help="Excel a procesar. Si se omite, se abre la interfaz gráfica.")
    p.add_argument("-o", "--output", help="Excel de salida (por defecto <archivo>_balidaf.xlsx).")
    p.add_argument("--err", help="TXT de errores de la SSS (_DR.DEVOLUCION_ERR.txt) para cruzar.")
    p.add_argument("--ok", help="TXT de aceptados de la SSS (_DR.DEVOLUCION_OK.txt) para cruzar.")
    p.add_argument("--informe", action="store_true", help="Exportar el informe de detalle (Excel aparte).")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.excel:
        return _cli(args)
    try:
        from .gui import run_gui
        run_gui()
        return 0
    except Exception:
        write_error_log("ERROR INICIALIZANDO GUI:")
        print("ERROR: No fue posible iniciar la interfaz gráfica.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
