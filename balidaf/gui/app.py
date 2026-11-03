"""Ventana principal de Balidaf."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from .. import APP_TITLE, __version__
from ..balanceo import Grupo
from ..devolucion import ResultadoCruce, cruzar
from ..informe import exportar, ruta_informe
from ..paths import ERROR_LOG_NAME, resource_path, write_error_log
from ..proceso import PASOS, Resultado, analizar, guardar, ruta_salida
from ..sss_txt import ArchivoTxt, leer_txt
from .tabs import DetalleLinea, TabBalancear, TabDevolucion, TabExcel, TabReglas
from .widgets import PanelProgreso, configurar_estilos


def _dpi_windows() -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


class BalidafApp(tk.Tk):
    def __init__(self):
        _dpi_windows()
        super().__init__()
        self.title(f"{APP_TITLE}  ·  v{__version__}")
        self.geometry("1320x860")
        self.minsize(1050, 680)
        try:
            self.iconbitmap(resource_path("assets", "balidaf.ico"))
        except Exception:
            pass
        configurar_estilos(self)
        self.configure(bg="white")

        self.resultado: Optional[Resultado] = None
        self.cruce: Optional[ResultadoCruce] = None
        self.txt_err: Optional[ArchivoTxt] = None
        self.txt_ok: Optional[ArchivoTxt] = None
        self._cola: "queue.Queue" = queue.Queue()
        self._ocupado = False

        cab = ttk.Frame(self, style="Cab.TFrame", padding=(16, 10))
        cab.pack(fill="x")
        ttk.Label(cab, text="Balidaf", style="Cab.TLabel").pack(side="left")
        ttk.Label(cab, text="   Balanceo de subsidios · Rendición Mecanismo Integración (SSSalud)",
                  style="CabSub.TLabel").pack(side="left")

        self.progreso = PanelProgreso(self)      # se muestra sólo mientras trabaja
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(8, 10))
        self.tab_balancear = TabBalancear(self.nb, self)
        self.tab_devolucion = TabDevolucion(self.nb, self)
        self.tab_excel = TabExcel(self.nb, self)
        self.tab_reglas = TabReglas(self.nb, self)
        self.nb.add(self.tab_balancear, text="  1 · Balancear  ")
        self.nb.add(self.tab_devolucion, text="  2 · Devolución SSS  ")
        self.nb.add(self.tab_excel, text="  Ver Excel  ")
        self.nb.add(self.tab_reglas, text="  Reglas de balanceo  ")
        self.nb.bind("<<NotebookTabChanged>>", self._cambio_pestana)
        self._habilitar()
        self.after(100, self._procesar_cola)

    # ------------------------------------------------------------------ trabajo en segundo plano
    def _procesar_cola(self) -> None:
        try:
            while True:
                tipo, *datos = self._cola.get_nowait()
                if tipo == "prog":
                    self.progreso.avanzar(*datos)
                elif tipo == "fin":
                    datos[0]()
        except queue.Empty:
            pass
        self.after(60, self._procesar_cola)

    def _prog(self, paso, texto, cur, tot):
        self._cola.put(("prog", paso, texto, cur, tot))

    def _trabajar(self, titulo: str, pasos, trabajo, al_terminar, error_titulo: str, texto_fin: str) -> None:
        """Ejecuta ``trabajo`` en otro hilo mostrando el panel de progreso y bloqueando los botones."""
        self._ocupado = True
        self._habilitar()
        self.progreso.iniciar(titulo, pasos)
        self.progreso.pack(fill="x", padx=10, pady=(8, 0), before=self.nb)
        self.config(cursor="watch")

        def run():
            try:
                res = trabajo()
                self._cola.put(("fin", lambda: self._fin(True, texto_fin, lambda: al_terminar(res))))
            except Exception as exc:
                write_error_log(f"ERROR: {error_titulo}")
                msg = str(exc)
                self._cola.put(("fin", lambda: self._fin(False, error_titulo, lambda: self._error(error_titulo, msg))))
        threading.Thread(target=run, daemon=True).start()

    def _fin(self, ok: bool, texto: str, despues) -> None:
        self.progreso.terminar(texto, ok)
        self.config(cursor="")
        self._ocupado = False
        despues()
        self._habilitar()
        self.after(2500 if ok else 6000, lambda: (not self._ocupado) and self.progreso.pack_forget())

    def _error(self, titulo: str, msg: str) -> None:
        messagebox.showerror("Balidaf", f"{titulo}.\n\n{msg}\n\nDetalle técnico en '{ERROR_LOG_NAME}'.")

    def _habilitar(self) -> None:
        self.tab_balancear.habilitar(self._ocupado)
        self.tab_devolucion.habilitar(self._ocupado)

    # ------------------------------------------------------------------ acciones
    def on_examinar(self) -> None:
        ruta = filedialog.askopenfilename(title="Seleccioná el Excel ORIGINAL de rendición",
                                          filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")])
        if ruta:
            self.tab_balancear.var_ruta.set(ruta)

    def on_analizar(self) -> None:
        ruta = self.tab_balancear.var_ruta.get().strip().strip('"')
        if not ruta or not os.path.isfile(ruta):
            messagebox.showwarning("Balidaf", "Primero elegí el archivo Excel con «Examinar…».")
            return
        self._trabajar("Analizando el Excel…", PASOS, lambda: analizar(ruta, progreso=self._prog),
                       self._analizado, "No fue posible analizar el Excel", "Análisis terminado")

    def _analizado(self, r: Resultado) -> None:
        self.resultado = r
        self._refrescar_todo()
        self.nb.select(self.tab_balancear)

    def aplicar(self, grupos: List[Grupo], cuales: str) -> None:
        r = self.resultado
        if not r:
            return
        if not grupos:
            messagebox.showinfo("Balidaf", "No hay correcciones pendientes en lo seleccionado.\n\n"
                                           "Seleccioná una o más filas (Ctrl o Shift para varias).")
            return
        lineas = sum(len(g.lineas) for g in grupos)
        if not messagebox.askyesno("Aplicar corrección",
                                   f"¿Aplicar la corrección {cuales}?\n\n"
                                   f"• Grupos: {len(grupos)}\n• Líneas que cambian: {lineas}\n\n"
                                   "Se cambian sólo los importes (aplicado, transferido, fondos propios y, si hace falta, "
                                   "retenciones). Podés deshacerlo. El archivo se modifica recién al «Guardar»."):
            return
        self._trabajar("Aplicando corrección…", [("aplicar", "Aplicar corrección"), ("validar", "Revalidar reglas SSS")],
                       lambda: (self._prog("aplicar", "Aplicando…", 0, 0),
                                r.aplicar(grupos, lambda t, c, n: self._prog("validar", t, c, n)))[1],
                       lambda n: self._refrescar_todo(), "No fue posible aplicar la corrección",
                       f"Corrección aplicada a {len(grupos)} grupos")

    def deshacer(self, grupos: List[Grupo]) -> None:
        r = self.resultado
        if not r:
            return
        if not grupos:
            messagebox.showinfo("Balidaf", "Seleccioná filas con corrección APLICADA para deshacer.")
            return
        if not messagebox.askyesno("Deshacer", f"¿Volver {len(grupos)} grupos a sus valores originales?"):
            return
        self._trabajar("Deshaciendo…", [("aplicar", "Deshacer"), ("validar", "Revalidar reglas SSS")],
                       lambda: (self._prog("aplicar", "Deshaciendo…", 0, 0),
                                r.deshacer(grupos, lambda t, c, n: self._prog("validar", t, c, n)))[1],
                       lambda n: self._refrescar_todo(), "No fue posible deshacer", f"{len(grupos)} grupos deshechos")

    def on_guardar(self) -> None:
        r = self.resultado
        if not r:
            return
        if not any(ln.modificados() for ln in r.lote.lineas):
            if not messagebox.askyesno("Balidaf", "Todavía no aplicaste ninguna corrección.\n\n"
                                                  "¿Guardar el Excel igual (sólo con los importes redondeados a 2 decimales)?"):
                return
        elif not r.listo_para_presmed:
            if not messagebox.askyesno("Balidaf", f"Quedan {r.errores_actuales} errores sin resolver.\n\n"
                                                  "¿Guardar el Excel de todas formas?"):
                return
        destino = filedialog.asksaveasfilename(
            title="Guardar Excel para Presmed", defaultextension=".xlsx",
            initialdir=os.path.dirname(r.lote.ruta), initialfile=os.path.basename(ruta_salida(r.lote.ruta)),
            filetypes=[("Excel", "*.xlsx")])
        if not destino:
            return
        if os.path.abspath(destino) == os.path.abspath(r.lote.ruta):
            if not messagebox.askyesno("Balidaf", "Vas a REEMPLAZAR el Excel original. ¿Continuar?"):
                return
        self._trabajar("Guardando el Excel…", [("guardar", "Guardar Excel")],
                       lambda: (self._prog("guardar", "Escribiendo el archivo…", 0, 0), guardar(r, destino))[1],
                       lambda d: messagebox.showinfo("Balidaf", f"Excel guardado, listo para Presmed:\n\n{d}"),
                       "No fue posible guardar (¿el archivo está abierto en Excel?)", "Excel guardado")

    def on_informe(self) -> None:
        r = self.resultado
        if not r:
            return
        destino = filedialog.asksaveasfilename(
            title="Exportar informe de detalle", defaultextension=".xlsx",
            initialdir=os.path.dirname(r.lote.ruta), initialfile=os.path.basename(ruta_informe(r.lote.ruta)),
            filetypes=[("Excel", "*.xlsx")])
        if destino:
            self._trabajar("Exportando informe…", [("informe", "Exportar informe")],
                           lambda: (self._prog("informe", "Escribiendo…", 0, 0), exportar(r, destino, self.cruce))[1],
                           lambda d: messagebox.showinfo("Balidaf", f"Informe exportado (NO es el Excel de Presmed):\n\n{d}"),
                           "No fue posible exportar el informe", "Informe exportado")

    def on_cargar_txt(self, tipo: str) -> None:
        ruta = filedialog.askopenfilename(
            title="TXT de errores de la SSS (_DR.DEVOLUCION_ERR)" if tipo == "ERR" else "TXT de aceptados (_DR.DEVOLUCION_OK)",
            filetypes=[("TXT", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return

        def hecho(a: ArchivoTxt):
            if tipo == "ERR":
                self.txt_err = a
            else:
                self.txt_ok = a
            self._refrescar_cruce()
        self._trabajar("Leyendo TXT de la SSS…", [("txt", "Leer TXT"), ("cruce", "Cruzar con el Excel")],
                       lambda: (self._prog("txt", "Leyendo…", 0, 0), leer_txt(ruta, tipo))[1],
                       hecho, "No fue posible leer el TXT", "TXT cargado")

    # ------------------------------------------------------------------ refresco de pantallas
    def _refrescar_cruce(self) -> None:
        if self.resultado and self.txt_err:
            self.cruce = cruzar(self.resultado, self.txt_err, self.txt_ok)
        else:
            self.cruce = None
        self.tab_devolucion.mostrar(self.cruce)

    def _refrescar_todo(self) -> None:
        self.tab_balancear.mostrar()
        self._refrescar_cruce()
        self.tab_excel.sucio = True
        if self.nb.select() == str(self.tab_excel):
            self.tab_excel.refrescar()

    def _cambio_pestana(self, _e=None) -> None:
        if self.nb.select() == str(self.tab_excel) and self.tab_excel.sucio and self.resultado:
            self.tab_excel.refrescar()

    def ver_excel(self, filtro: str) -> None:
        self.tab_excel.filtrar(filtro)
        self.nb.select(self.tab_excel)

    def abrir_detalle(self, fila: int) -> None:
        if not self.resultado:
            return
        ln = next((l for l in self.resultado.lote.lineas if l.fila == fila), None)
        if ln:
            DetalleLinea(self, ln)
