"""Ventana principal de Balidaf (rediseño)."""

import datetime as dt
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Optional

from .. import APP_TITLE, __version__
from ..balanceo import APLICADA, PENDIENTE, Grupo
from ..devolucion import PROPUESTA, ResultadoCruce, cruzar
from ..informe import exportar, ruta_informe
from ..montos import fmt
from ..paths import ERROR_LOG_NAME, resource_path, write_error_log
from ..proceso import PASOS, Resultado, analizar, guardar, ruta_salida
from ..sss_txt import ArchivoTxt, leer_txt
from .componentes import (Ayuda, BarraPestanas, BarraProgreso, Boton, Caja, Circulo, Lbl, Linea, Marca, Toast,
                          confirmar, fmt_n)
from .detalle import DetalleLinea
from .pag_balancear import PagBalancear
from .pag_devolucion import PagDevolucion
from .pag_excel import PagExcel
from .pag_reglas import PagReglas
from .preferencias import guardar_preferencia, leer_preferencia
from .tema import TEMA_ACTUAL, P, al_cambiar_tema, aplicar_tema, configurar_estilos, inicializar_fuentes

PESOS_ANALISIS = {"leer": 0.60, "original": 0.15, "balancear": 0.15, "propuesta": 0.10}


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
        self.geometry("1440x900")
        self.minsize(1180, 720)
        if sys.platform.startswith("win"):
            try:
                self.state("zoomed")      # en Windows abre maximizada
            except tk.TclError:
                pass
        try:
            self.iconbitmap(resource_path("assets", "balidaf.ico"))
        except Exception:
            pass
        inicializar_fuentes(self)
        configurar_estilos(self)

        # ---- estado
        self.resultado: Optional[Resultado] = None
        self.cruce: Optional[ResultadoCruce] = None
        self.txt_err: Optional[ArchivoTxt] = None
        self.txt_ok: Optional[ArchivoTxt] = None
        self.ocupado = False
        self.cambios_sin_guardar = False
        self.guardado_como: Optional[str] = None
        self.guardado_hora = ""
        self._cola: "queue.Queue" = queue.Queue()

        self._armar_encabezado()
        self.progreso = BarraProgreso(self)
        self.progreso.pack(fill="x")
        Linea(self).pack(fill="x")
        self.pestanas = BarraPestanas(self, self.ir)
        self.pestanas.pack(fill="x")
        self.pestanas.agregar("balancear", "Balancear", "1")
        self.pestanas.agregar("devolucion", "Devolución SSS", "2")
        self.pestanas.separador()
        self.pestanas.agregar("excel", "Ver Excel")
        self.pestanas.agregar("reglas", "Reglas de balanceo")
        Linea(self).pack(fill="x")

        self.pie = self._armar_pie()
        self.cuerpo = tk.Frame(self)
        self.cuerpo.pack(fill="both", expand=True)
        al_cambiar_tema(lambda: self.cuerpo.config(bg=P["bg"]))
        self.pag_balancear = PagBalancear(self.cuerpo, self)
        self.pag_devolucion = PagDevolucion(self.cuerpo, self)
        self.pag_excel = PagExcel(self.cuerpo, self)
        self.pag_reglas = PagReglas(self.cuerpo, self)
        self.paginas = {"balancear": self.pag_balancear, "devolucion": self.pag_devolucion,
                        "excel": self.pag_excel, "reglas": self.pag_reglas}
        for p in self.paginas.values():
            p.place(in_=self.cuerpo, x=0, y=0, relwidth=1, relheight=1)
        self.toast = Toast(self)
        self.actual = "balancear"
        self.ir("balancear")
        self._aplicar_tema(leer_preferencia("tema", "claro"))
        self.refrescar()
        self.after(80, self._procesar_cola)

    # ================================================================== armado
    def _armar_encabezado(self) -> None:
        cab = tk.Frame(self, padx=20, height=52)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        al_cambiar_tema(lambda: cab.config(bg=P["surface"]))
        Marca(cab).pack(side="left")
        Lbl(cab, "Balidaf", 15, "bold").pack(side="left", padx=(10, 12))
        Linea(cab, vertical=True).pack(side="left", fill="y", pady=16)
        Lbl(cab, "Balanceo de subsidios · Rendición Mecanismo Integración (SSSalud)", 13, color="ink2").pack(
            side="left", padx=(12, 0))
        self.btn_tema = tk.Label(cab, width=3, font=("Segoe UI Symbol", 13), cursor="hand2", highlightthickness=1)
        self.btn_tema.pack(side="right", ipady=2)
        self.btn_tema.bind("<Button-1>", lambda e: self.cambiar_tema())
        Ayuda(self.btn_tema, "Cambiar entre modo claro y modo oscuro")
        al_cambiar_tema(lambda: self.btn_tema.config(bg=P["surface2"], fg=P["ink"], highlightbackground=P["line"]))
        self.chip_archivo = Caja(cab, fondo="surface2", borde="line", padx=10, pady=4)
        cuadro = tk.Frame(self.chip_archivo, width=8, height=8)
        cuadro.pack(side="left", padx=(0, 8))
        al_cambiar_tema(lambda: cuadro.config(bg=P["ok_fg"]))
        self.lbl_archivo = Lbl(self.chip_archivo, "", 12, mono=True, fondo="surface2")
        self.lbl_archivo.pack(side="left")
        self.lbl_archivo2 = Lbl(self.chip_archivo, "", 12, color="ink3", fondo="surface2")
        self.lbl_archivo2.pack(side="left", padx=(8, 0))
        Linea(self).pack(fill="x")

    def _armar_pie(self) -> tk.Frame:
        pie = tk.Frame(self)
        pie.pack(side="bottom", fill="x")
        Linea(pie).pack(fill="x")
        fila = tk.Frame(pie, padx=20, pady=10)
        fila.pack(fill="x")
        al_cambiar_tema(lambda: (pie.config(bg=P["surface"]), fila.config(bg=P["surface"])))
        self.c3 = Circulo(fila, "3", "pendiente")
        self.c3.pack(side="left", padx=(0, 10))
        Lbl(fila, "Guardar", 13.5, "semibold").pack(side="left", padx=(0, 12))
        self.btn_guardar = Boton(fila, "Guardar Excel para Presmed", self.on_guardar, "guardar")
        self.btn_guardar.pack(side="right")
        self.btn_informe = Boton(fila, "Exportar informe (opcional)…", self.on_informe)
        self.btn_informe.pack(side="right", padx=(0, 8))
        Ayuda(self.btn_informe, "Excel APARTE con el detalle de cambios y validaciones. No se carga en Presmed.")
        self.lbl_pie = Lbl(fila, "", 12.5, color="ink2", anchor="w")
        self.lbl_pie.pack(side="left", fill="x", expand=True)
        return pie

    # ================================================================== navegación y tema
    def ir(self, pid: str) -> None:
        self.actual = pid
        self.paginas[pid].tkraise()
        self.pestanas.set_activa(pid)
        if pid in ("balancear", "devolucion"):
            self.pie.pack(side="bottom", fill="x", before=self.cuerpo)
        else:
            self.pie.pack_forget()
        if pid == "excel" and self.pag_excel.sucio and self.resultado:
            self.pag_excel.refrescar()

    def ver_excel(self, filtro: str) -> None:
        self.pag_excel.filtro = filtro
        self.pag_excel.sucio = True
        self.ir("excel")

    def _aplicar_tema(self, nombre: str) -> None:
        aplicar_tema(self, nombre if nombre in ("claro", "oscuro") else "claro")
        self.btn_tema.config(text="☀" if TEMA_ACTUAL[0] == "oscuro" else "☾")
        self.refrescar()

    def cambiar_tema(self) -> None:
        nuevo = "claro" if TEMA_ACTUAL[0] == "oscuro" else "oscuro"
        self._aplicar_tema(nuevo)
        guardar_preferencia("tema", nuevo)

    # ================================================================== refresco
    def refrescar(self) -> None:
        r = self.resultado
        if not hasattr(self, "pag_balancear"):
            return
        if r:
            self.lbl_archivo.config(text=os.path.basename(r.lote.ruta))
            self.lbl_archivo2.config(text=f"{fmt_n(len(r.lote.lineas))} líneas · {len(r.lote.encabezados)} columnas")
            self.chip_archivo.pack(side="right", padx=(0, 10))
        else:
            self.chip_archivo.pack_forget()
        self.pestanas.set_contador("balancear", len(r.grupos_con(PENDIENTE)) if r else None)
        self.pestanas.set_contador("devolucion", self.cruce.por_estado.get(PROPUESTA, 0) if self.cruce else None)
        self.pag_balancear.mostrar()
        self.pag_devolucion.mostrar()
        self.pag_excel.sucio = True
        if self.actual == "excel" and r:
            self.pag_excel.refrescar()
        self._pintar_pie()
        self.actualizar_botones()

    def _pintar_pie(self) -> None:
        r = self.resultado
        if r is None:
            self.c3.set(estado="pendiente")
            self.lbl_pie.config(text="Primero analizá el Excel original (Paso 1).")
            return
        apl = len(r.grupos_con(APLICADA))
        destino = os.path.basename(ruta_salida(r.lote.ruta))
        if self.guardado_como and not self.cambios_sin_guardar:
            self.c3.set(estado="hecho")
            self.lbl_pie.config(text=f"Guardado a las {self.guardado_hora} como {self.guardado_como}. "
                                     "Ya podés cargarlo en Presmed.")
        else:
            self.c3.set(estado="actual" if apl else "pendiente")
            self.lbl_pie.config(text=f"{fmt_n(apl)} correcciones aplicadas · se guarda como {destino} "
                                     "(sin colores ni hojas nuevas).")

    def actualizar_botones(self) -> None:
        if not hasattr(self, "pag_devolucion"):
            return
        hay = self.resultado is not None and not self.resultado.lote.faltantes
        self.btn_guardar.habilitar(hay and not self.ocupado)
        self.btn_informe.habilitar(self.resultado is not None and not self.ocupado)
        self.pag_balancear.habilitar(self.ocupado)
        self.pag_devolucion.habilitar(self.ocupado)

    # ================================================================== tareas en segundo plano
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

    def _tarea(self, titulo: str, pasos, trabajo, al_terminar, fin_titulo, fin_detalle=lambda res: "",
               error_titulo: str = "No fue posible completar la tarea", pesos=None) -> None:
        self.ocupado = True
        self.actualizar_botones()
        self.progreso.iniciar(titulo, pasos, pesos)
        self.config(cursor="watch")

        def run():
            try:
                res = trabajo()
                self._cola.put(("fin", lambda: self._fin(True, fin_titulo, fin_detalle(res), lambda: al_terminar(res))))
            except Exception as exc:
                write_error_log(f"ERROR: {error_titulo}")
                msg = str(exc)
                self._cola.put(("fin", lambda: self._fin(False, error_titulo, msg,
                                                          lambda: messagebox.showerror(
                                                              "Balidaf", f"{error_titulo}.\n\n{msg}\n\nDetalle técnico "
                                                                         f"en '{ERROR_LOG_NAME}'."))))
        threading.Thread(target=run, daemon=True).start()

    def _fin(self, ok: bool, titulo: str, detalle: str, despues) -> None:
        self.progreso.terminar(titulo, detalle, ok)
        self.config(cursor="")
        self.ocupado = False
        despues()
        self.actualizar_botones()

    # ================================================================== acciones: Paso 1
    def on_examinar(self) -> None:
        ruta = filedialog.askopenfilename(title="Elegí el Excel ORIGINAL de Presmed",
                                          filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")])
        if ruta:
            self.pag_balancear.ruta.set(ruta)
            self.actualizar_botones()

    def on_analizar(self) -> None:
        ruta = self.pag_balancear.ruta.get()
        if not ruta or not os.path.isfile(ruta):
            messagebox.showwarning("Balidaf", "Elegí el archivo Excel con «Examinar…».")
            return
        if self.cambios_sin_guardar and not confirmar(
                self, "Volver a analizar", "Hay correcciones aplicadas que todavía no guardaste. Si volvés a analizar, "
                                           "se descartan.", nota="Esta acción no se puede deshacer.",
                accion="Descartar y analizar", tipo="peligro"):
            return
        self.resultado, self.cruce = None, None
        self.cambios_sin_guardar, self.guardado_como = False, None
        self.refrescar()
        self.ocupado = True
        self.pag_balancear.mostrar()
        self._tarea("Analizando el Excel…", PASOS, lambda: analizar(ruta, progreso=self._prog), self._analizado,
                    "Análisis terminado",
                    lambda r: f"{fmt_n(len(r.lote.lineas))} líneas · {fmt_n(len(r.grupos_con(PENDIENTE)))} grupos con "
                              "corrección propuesta", "No fue posible analizar el Excel", PESOS_ANALISIS)

    def _analizado(self, r: Resultado) -> None:
        self.resultado = r
        self._recalcular_cruce()
        self.refrescar()
        self.ir("balancear")

    # ================================================================== acciones: Paso 2
    def _resumen(self, grupos: List[Grupo], campo: str = "propuesta") -> list:
        lineas = sum(len(g.lineas) for g in grupos)
        dif = sum(ln.propuesta["apli"] - ln.original["apli"] for g in grupos for ln in g.lineas)
        return [("Grupos", fmt_n(len(grupos))), ("Líneas", fmt_n(lineas)), ("Diferencia en aplicado", fmt(dif))]

    def aplicar(self, grupos: List[Grupo], confirmar_antes: bool = True) -> None:
        r = self.resultado
        grupos = [g for g in grupos if g.estado == PENDIENTE]
        if not r or not grupos or self.ocupado:
            return
        if confirmar_antes and not confirmar(
                self, "Aplicar correcciones",
                "Se modifican sólo impor_apli_sss, importe_transferido y fdo_ppio_ingre_cta_disca (y las retenciones si "
                "el subsidio no alcanza). El Excel original no se toca y podés deshacer hasta guardar.",
                self._resumen(grupos), accion=f"Aplicar {fmt_n(len(grupos))}"):
            return
        lineas = sum(len(g.lineas) for g in grupos)
        self._tarea("Aplicando la corrección…", [("aplicar", "Aplicar corrección"), ("validar", "Revalidar reglas SSS")],
                    lambda: (self._prog("aplicar", "Aplicando…", 0, 0),
                             r.aplicar(grupos, lambda t, c, n: self._prog("validar", t, c, n)))[1],
                    lambda n: self._modificado(f"Se aplicaron {fmt_n(len(grupos))} correcciones ({fmt_n(lineas)} líneas).",
                                               ("Deshacer", lambda: self.deshacer(grupos, False))),
                    "Corrección aplicada", lambda n: f"{fmt_n(len(grupos))} grupos · {fmt_n(lineas)} líneas",
                    "No fue posible aplicar la corrección")

    def deshacer(self, grupos: List[Grupo], confirmar_antes: bool = True) -> None:
        r = self.resultado
        grupos = [g for g in grupos if g.estado == APLICADA]
        if not r or not grupos or self.ocupado:
            return
        if confirmar_antes and not confirmar(
                self, "Deshacer correcciones", "Los grupos vuelven a sus valores originales. La corrección queda "
                                               "propuesta y la podés volver a aplicar.",
                self._resumen(grupos), accion=f"Deshacer {fmt_n(len(grupos))}"):
            return
        lineas = sum(len(g.lineas) for g in grupos)
        self._tarea("Deshaciendo…", [("aplicar", "Deshacer"), ("validar", "Revalidar reglas SSS")],
                    lambda: (self._prog("aplicar", "Deshaciendo…", 0, 0),
                             r.deshacer(grupos, lambda t, c, n: self._prog("validar", t, c, n)))[1],
                    lambda n: self._modificado(f"Se deshicieron {fmt_n(len(grupos))} correcciones ({fmt_n(lineas)} líneas).",
                                               ("Volver a aplicar", lambda: self.aplicar(grupos, False))),
                    "Corrección deshecha", lambda n: f"{fmt_n(len(grupos))} grupos · {fmt_n(lineas)} líneas",
                    "No fue posible deshacer")

    def _modificado(self, mensaje: str, accion) -> None:
        self.cambios_sin_guardar = any(ln.modificados() for ln in self.resultado.lote.lineas)
        self.guardado_como = None
        self._recalcular_cruce()
        self.refrescar()
        self.toast.mostrar(mensaje, accion)

    # ================================================================== acciones: Paso 3
    def on_guardar(self) -> None:
        r = self.resultado
        if not r or self.ocupado:
            return
        apl, pend = len(r.grupos_con(APLICADA)), len(r.grupos_con(PENDIENTE))
        nota = []
        if pend:
            nota.append(f"Quedan {fmt_n(pend)} correcciones propuestas sin aplicar.")
        if r.errores_actuales:
            nota.append(f"El Excel todavía tiene {fmt_n(r.errores_actuales)} errores: la SSS los va a rechazar.")
        if not confirmar(self, "Guardar Excel para Presmed",
                         "Se guarda un Excel nuevo con las correcciones aplicadas. Sólo cambian valores: sin colores, "
                         "formatos ni hojas nuevas. El original no se modifica.",
                         [("Archivo", os.path.basename(ruta_salida(r.lote.ruta))),
                          ("Correcciones aplicadas", fmt_n(apl)), ("Propuestas sin aplicar", fmt_n(pend)),
                          ("Errores a corregir a mano", fmt_n(r.errores_propuesta))],
                         " ".join(nota), "Guardar", "guardar"):
            return
        destino = filedialog.asksaveasfilename(
            title="Guardar Excel para Presmed", defaultextension=".xlsx", initialdir=os.path.dirname(r.lote.ruta),
            initialfile=os.path.basename(ruta_salida(r.lote.ruta)), filetypes=[("Excel", "*.xlsx")])
        if not destino:
            return
        if os.path.abspath(destino) == os.path.abspath(r.lote.ruta) and not confirmar(
                self, "Reemplazar el original", "Elegiste el mismo archivo que el Excel ORIGINAL.",
                accion="Reemplazar", tipo="peligro"):
            return

        def trabajo():
            self._prog("preparar", "Preparando los valores…", 1, 1)
            self._prog("escribir", "Escribiendo el archivo…", 0, 0)
            guardar(r, destino)
            self._prog("verificar", "Verificando el archivo…", 1, 1)
            if not os.path.isfile(destino) or os.path.getsize(destino) == 0:
                raise IOError("El archivo guardado está vacío.")
            return destino

        def hecho(d):
            self.cambios_sin_guardar = False
            self.guardado_como = os.path.basename(d)
            self.guardado_hora = dt.datetime.now().strftime("%H:%M")
            self.refrescar()
            self.toast.mostrar(f"Excel guardado como {self.guardado_como}.")
        self._tarea("Guardando el Excel…", [("preparar", "Preparar valores"), ("escribir", "Escribir Excel"),
                                            ("verificar", "Verificar archivo")], trabajo, hecho, "Excel guardado",
                    lambda d: d, "No fue posible guardar (¿el archivo está abierto en Excel?)",
                    {"preparar": 0.1, "escribir": 0.8, "verificar": 0.1})

    def on_informe(self) -> None:
        r = self.resultado
        if not r or self.ocupado:
            return
        destino = filedialog.asksaveasfilename(
            title="Exportar informe de detalle", defaultextension=".xlsx", initialdir=os.path.dirname(r.lote.ruta),
            initialfile=os.path.basename(ruta_informe(r.lote.ruta)), filetypes=[("Excel", "*.xlsx")])
        if destino:
            self._tarea("Exportando el informe…", [("informe", "Exportar informe")],
                        lambda: (self._prog("informe", "Escribiendo…", 0, 0), exportar(r, destino, self.cruce))[1],
                        lambda d: self.toast.mostrar("Informe exportado (no es el Excel de Presmed)."),
                        "Informe exportado", lambda d: d, "No fue posible exportar el informe")

    # ================================================================== Devolución SSS
    def on_cargar_txt(self, tipo: str) -> None:
        ruta = filedialog.askopenfilename(
            title="TXT de errores de la SSS (_DR.DEVOLUCION_ERR)" if tipo == "ERR" else "TXT de aceptados (_OK)",
            filetypes=[("TXT", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return

        def trabajo():
            self._prog("txt", "Leyendo…", 0, 0)
            a = leer_txt(ruta, tipo)
            self._prog("cruce", "Cruzando con el Excel…", 1, 1)
            return a

        def hecho(a: ArchivoTxt):
            if tipo == "ERR":
                self.txt_err = a
            else:
                self.txt_ok = a
            self._recalcular_cruce()
            self.refrescar()
            self.ir("devolucion")
        self._tarea("Leyendo el TXT de la SSS…", [("txt", "Leer TXT"), ("cruce", "Cruzar con el Excel")], trabajo,
                    hecho, "TXT cargado",
                    lambda a: f"{a.nombre} · {fmt_n(len(a.registros))} líneas", "No fue posible leer el TXT")

    def _recalcular_cruce(self) -> None:
        self.cruce = cruzar(self.resultado, self.txt_err, self.txt_ok) if self.resultado and self.txt_err else None

    # ================================================================== detalle
    def abrir_detalle(self, fila: int) -> None:
        if not self.resultado:
            return
        ln = next((l for l in self.resultado.lote.lineas if l.fila == fila), None)
        if ln:
            DetalleLinea(self, ln)
