"""Ventana principal de Balidaf."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .. import APP_TITLE, __version__
from ..devolucion import ResultadoCruce, cruzar
from ..informe import exportar, ruta_informe
from ..paths import ERROR_LOG_NAME, resource_path, write_error_log
from ..proceso import Resultado, guardar, procesar, ruta_salida
from ..sss_txt import ArchivoTxt, leer_txt
from .tabs import (DetalleLinea, TabDevolucion, TabExcel, TabRegistro, TabResumen,
                   TabValidacion)
from .widgets import configurar_estilos


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
        self.geometry("1280x820")
        self.minsize(1000, 640)
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

        self._armar_cabecera()
        self._armar_barra()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.tab_resumen = TabResumen(self.nb, self)
        self.tab_validacion = TabValidacion(self.nb, self)
        self.tab_excel = TabExcel(self.nb, self)
        self.tab_devolucion = TabDevolucion(self.nb, self)
        self.tab_registro = TabRegistro(self.nb, self)
        self.nb.add(self.tab_resumen, text="  Resumen  ")
        self.nb.add(self.tab_validacion, text="  Validación SSS  ")
        self.nb.add(self.tab_excel, text="  Excel resultante  ")
        self.nb.add(self.tab_devolucion, text="  Devolución SSS  ")
        self.nb.add(self.tab_registro, text="  Registro  ")
        self._armar_estado()

        self.log("titulo", f"{APP_TITLE} v{__version__}")
        self.log("info", "Seleccioná el Excel de rendición para balancear.")
        self.after(100, self._procesar_cola)

    # ------------------------------------------------------------------ armado
    def _armar_cabecera(self) -> None:
        cab = ttk.Frame(self, style="Cab.TFrame", padding=(16, 10))
        cab.pack(fill="x")
        ttk.Label(cab, text="Balidaf", style="Cab.TLabel").pack(side="left")
        ttk.Label(cab, text="   Balanceo de subsidios · Rendición Mecanismo Integración (SSSalud)",
                  style="CabSub.TLabel").pack(side="left")

    def _armar_barra(self) -> None:
        bar = ttk.Frame(self, padding=(10, 10, 10, 6))
        bar.pack(fill="x")
        ttk.Label(bar, text="Excel de rendición:").pack(side="left")
        self.var_ruta = tk.StringVar()
        ttk.Entry(bar, textvariable=self.var_ruta).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(bar, text="Examinar…", command=self.on_examinar).pack(side="left")
        self.btn_procesar = ttk.Button(bar, text="Balancear y validar", style="Accent.TButton",
                                       command=self.on_procesar)
        self.btn_procesar.pack(side="left", padx=(10, 4))
        self.btn_guardar = ttk.Button(bar, text="Guardar Excel para Presmed", style="Ok.TButton",
                                      command=self.on_guardar, state="disabled")
        self.btn_guardar.pack(side="left", padx=4)
        self.btn_informe = ttk.Button(bar, text="Exportar informe…", command=self.on_informe, state="disabled")
        self.btn_informe.pack(side="left", padx=4)

    def _armar_estado(self) -> None:
        est = ttk.Frame(self, padding=(10, 0, 10, 8))
        est.pack(fill="x")
        self.lbl_estado = ttk.Label(est, text="Listo.", style="Sub.TLabel")
        self.lbl_estado.pack(side="left")
        self.pb = ttk.Progressbar(est, mode="determinate", length=320)
        self.pb.pack(side="right")

    # ------------------------------------------------------------------ comunicación con hilos
    def log(self, nivel: str, msg: str) -> None:
        self.tab_registro.escribir(nivel, msg)

    def _procesar_cola(self) -> None:
        try:
            while True:
                tipo, *datos = self._cola.get_nowait()
                if tipo == "log":
                    self.log(*datos)
                elif tipo == "prog":
                    etapa, cur, tot = datos
                    self.lbl_estado.config(text=etapa)
                    self.pb["maximum"] = max(tot, 1)
                    self.pb["value"] = cur
                elif tipo == "fin":
                    datos[0]()
        except queue.Empty:
            pass
        self.after(80, self._procesar_cola)

    def _en_hilo(self, trabajo, al_terminar, error_titulo: str) -> None:
        self._ocupado = True
        self._botones()

        def run():
            try:
                res = trabajo()
                self._cola.put(("fin", lambda: (self._fin(), al_terminar(res))))
            except Exception as exc:
                write_error_log(f"ERROR: {error_titulo}")
                msg = str(exc)
                self._cola.put(("fin", lambda: (self._fin(), self._error(error_titulo, msg))))
        threading.Thread(target=run, daemon=True).start()

    def _fin(self) -> None:
        self._ocupado = False
        self.pb["value"] = 0
        self.lbl_estado.config(text="Listo.")
        self._botones()

    def _error(self, titulo: str, msg: str) -> None:
        self.log("error", f"{titulo}: {msg}")
        messagebox.showerror("Balidaf", f"{titulo}.\n\n{msg}\n\nDetalle técnico en '{ERROR_LOG_NAME}'.")

    def _botones(self) -> None:
        hay = self.resultado is not None and not self.resultado.lote.faltantes
        self.btn_procesar.config(state="disabled" if self._ocupado else "normal")
        self.btn_guardar.config(state="normal" if hay and not self._ocupado else "disabled")
        self.btn_informe.config(state="normal" if self.resultado and not self._ocupado else "disabled")

    def _log_hilo(self, nivel, msg):
        self._cola.put(("log", nivel, msg))

    def _prog_hilo(self, etapa, cur, tot):
        self._cola.put(("prog", etapa, cur, tot))

    # ------------------------------------------------------------------ acciones
    def on_examinar(self) -> None:
        ruta = filedialog.askopenfilename(title="Seleccioná el Excel de rendición",
                                          filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")])
        if ruta:
            self.var_ruta.set(ruta)

    def on_procesar(self) -> None:
        ruta = self.var_ruta.get().strip().strip('"')
        if not ruta or not os.path.isfile(ruta):
            messagebox.showwarning("Balidaf", "Seleccioná un archivo Excel válido.")
            return
        self.nb.select(self.tab_registro)
        self._en_hilo(lambda: procesar(ruta, self._log_hilo, self._prog_hilo), self._procesado,
                      "No fue posible procesar el Excel")

    def _procesado(self, r: Resultado) -> None:
        self.resultado = r
        self._actualizar_cruce()
        self.tab_resumen.mostrar(r)
        self.tab_validacion.refrescar()
        self.tab_excel.refrescar()
        self._botones()
        self.nb.select(self.tab_resumen)

    def on_guardar(self) -> None:
        r = self.resultado
        if not r:
            return
        if not r.listo_para_presmed:
            if not messagebox.askyesno("Balidaf", f"Quedan {r.errores_despues} errores sin resolver.\n\n"
                                                  "¿Guardar el Excel de todas formas?"):
                return
        destino = filedialog.asksaveasfilename(
            title="Guardar Excel para Presmed", defaultextension=".xlsx",
            initialdir=os.path.dirname(r.lote.ruta), initialfile=os.path.basename(ruta_salida(r.lote.ruta)),
            filetypes=[("Excel", "*.xlsx")])
        if not destino:
            return
        if os.path.abspath(destino) == os.path.abspath(r.lote.ruta):
            if not messagebox.askyesno("Balidaf", "Vas a reemplazar el Excel ORIGINAL. ¿Continuar?"):
                return

        def hecho(d):
            messagebox.showinfo("Balidaf", f"Excel guardado sin formatos agregados, listo para Presmed:\n\n{d}")
        self._en_hilo(lambda: (self._prog_hilo("Guardando Excel…", 0, 1), guardar(r, destino, self._log_hilo))[1],
                      hecho, "No fue posible guardar el Excel (¿está abierto en Excel?)")

    def on_informe(self) -> None:
        r = self.resultado
        if not r:
            return
        destino = filedialog.asksaveasfilename(
            title="Exportar informe de detalle", defaultextension=".xlsx",
            initialdir=os.path.dirname(r.lote.ruta), initialfile=os.path.basename(ruta_informe(r.lote.ruta)),
            filetypes=[("Excel", "*.xlsx")])
        if not destino:
            return

        def hecho(d):
            self.log("ok", f"Informe exportado: {d}")
            messagebox.showinfo("Balidaf", f"Informe exportado (archivo aparte, NO es el de Presmed):\n\n{d}")
        self._en_hilo(lambda: exportar(r, destino, self.cruce), hecho, "No fue posible exportar el informe")

    def cargar_txt(self, ruta: str, tipo: str) -> None:
        def hecho(a: ArchivoTxt):
            if tipo == "ERR":
                self.txt_err = a
            else:
                self.txt_ok = a
            self.log("info", f"TXT {tipo} cargado: {a.nombre} ({len(a.registros)} líneas)")
            if self.resultado is None:
                messagebox.showinfo("Balidaf", "TXT cargado. Ahora procesá el Excel original para cruzar la información.")
            self._actualizar_cruce()
        self._en_hilo(lambda: leer_txt(ruta, tipo), hecho, "No fue posible leer el TXT")

    def _actualizar_cruce(self) -> None:
        if self.resultado and (self.txt_err or self.txt_ok):
            self.cruce = cruzar(self.resultado.lote, self.resultado.despues, self.txt_err, self.txt_ok)
            c = self.cruce
            self.log("titulo", "Cruce con la devolución de la SSS")
            for est, n in c.por_estado.items():
                self.log("ok" if est.startswith("Corregido") else "warn", f"  {est}: {n}")
        else:
            self.cruce = None
        self.tab_devolucion.mostrar(self.cruce)

    def abrir_detalle(self, fila: int) -> None:
        if not self.resultado:
            return
        ln = next((l for l in self.resultado.lote.lineas if l.fila == fila), None)
        if ln:
            DetalleLinea(self, ln)
