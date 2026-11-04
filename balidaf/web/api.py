"""
Puente entre la interfaz (HTML) y el motor de Balidaf.

La interfaz llama a estos métodos (vía pywebview o, en modo navegador, vía HTTP). Las tareas largas
(analizar, aplicar, guardar…) corren en segundo plano y la interfaz consulta ``progreso()``.
Los importes viajan en CENTAVOS (enteros); la interfaz los formatea.

IMPORTANTE: todos los atributos de estado son privados (con «_») para que pywebview no los
recorra al exponer la API.
"""

import datetime as dt
import os
import subprocess
import sys
import threading
import traceback
from typing import Any, Dict, List, Optional

from ..balanceo import APLICADA, PENDIENTE, TIPOS, tipo_correccion
from ..devolucion import ESTADOS, cruzar
from ..excel_io import texto_celda
from ..informe import exportar, ruta_informe
from ..paths import write_error_log
from ..proceso import PASOS, analizar, guardar, ruta_salida
from ..schema import CODIGOS, COL, IMPORTES
from ..sss_txt import leer_txt
from ..validacion import ADVERTENCIA, ERROR
from .preferencias import guardar_preferencia, leer_preferencia

PESOS = {
    "analizar": {"leer": 0.60, "original": 0.15, "balancear": 0.15, "propuesta": 0.10},
    "guardar": {"preparar": 0.1, "escribir": 0.8, "verificar": 0.1},
}
RET = ("ret_gan", "ret_iibb", "ret_otras")
CLAVE_EXCEL = [("clave", "clave_rendicion"), ("cuil", "cuil"), ("cod", "cod_prestac"), ("per_prest", "perio_prestac"),
               ("subsidiado", "importe_subsidiado"), ("solicitado", "importe_solicitado"), ("apli", "impor_apli_sss"),
               ("transferido", "importe_transferido"), ("_ret", "retenciones"), ("fdo_ppio", "fdo_ppio_ingre_cta_disca")]


class Api:
    def __init__(self) -> None:
        self._ventana = None            # ventana de pywebview (si existe)
        self._r = None                  # Resultado del análisis
        self._txt_err = None
        self._txt_ok = None
        self._cruce = None
        self._ruta = ""
        self._ocupado = False
        self._prog: Dict[str, Any] = {"estado": "idle", "titulo": "Listo. Elegí un Excel y presioná «Analizar»",
                                      "detalle": "Nada se modifica hasta que lo apliques.", "pasos": [], "actual": -1,
                                      "pct": 0}
        self._pesos: Dict[str, float] = {}
        self._ultimo: Optional[dict] = None   # resultado de la última tarea (para avisos / toast)
        self._version = 0                     # aumenta con cada cambio de datos
        self._cambios = False
        self._guardado: Optional[dict] = None
        self._grupos: List = []

    def _set_ventana(self, w) -> None:
        self._ventana = w

    # ================================================================== estado general
    def inicio(self) -> dict:
        from .. import __version__
        return {"version": __version__, "tema": leer_preferencia("tema", "claro"), "tipos": TIPOS, "estados": ESTADOS,
                "codigos": {c: {"campo": v.campo, "descripcion": v.descripcion, "accion": v.accion,
                                "resuelve": v.resuelve, "validable": v.validable} for c, v in CODIGOS.items()}}

    def tema(self, nombre: str) -> bool:
        guardar_preferencia("tema", nombre)
        return True

    def progreso(self) -> dict:
        return {"ocupado": self._ocupado, "prog": self._prog, "version": self._version, "ultimo": self._ultimo}

    def estado(self) -> dict:
        r = self._r
        d: Dict[str, Any] = {"ruta": self._ruta, "analizado": r is not None, "ocupado": self._ocupado,
                             "version": self._version, "cambios": self._cambios, "guardado": self._guardado,
                             "txt": [a.nombre for a in (self._txt_err, self._txt_ok) if a],
                             "txt_err": bool(self._txt_err)}
        if r is None:
            return d
        pend, apl = r.grupos_con(PENDIENTE), r.grupos_con(APLICADA)
        d.update({
            "archivo": os.path.basename(r.lote.ruta), "lineas": len(r.lote.lineas), "columnas": len(r.lote.encabezados),
            "faltantes": [COL[k].encabezado for k in r.lote.faltantes],
            "errores_antes": r.errores_antes, "errores": r.errores_actuales, "manual": r.errores_propuesta,
            "pend": len(pend), "pend_lineas": sum(len(g.lineas) for g in pend),
            "apl": len(apl), "apl_lineas": sum(len(g.lineas) for g in apl),
            "salida": os.path.basename(ruta_salida(r.lote.ruta)),
        })
        if self._cruce:
            c = self._cruce
            d["cruce"] = {"total": c.total_err, "por_estado": dict(c.por_estado), "aceptadas": c.aceptadas_que_cambian}
        return d

    # ================================================================== datos para las tablas
    def grupos(self) -> List[dict]:
        r = self._r
        if r is None:
            return []
        self._grupos = list(r.grupos.values())
        filas = []
        for i, g in enumerate(self._grupos):
            if g.estado not in (PENDIENTE, APLICADA):
                continue
            filas_g = {ln.fila for ln in g.lineas}
            errs = sorted({h.codigo for h in r.antes if h.fila in filas_g and h.nivel == ERROR})
            ao = sum(ln.original["apli"] for ln in g.lineas)
            an = sum(ln.propuesta["apli"] for ln in g.lineas)
            filas.append({"id": i, "estado": "pend" if g.estado == PENDIENTE else "apl", "tipo": tipo_correccion(g),
                          "cuil": g.clave[0], "cod": g.clave[3], "pres": g.clave[2], "n": len(g.lineas),
                          "sub": g.subsidio, "ao": ao, "an": an, "dif": an - ao, "errs": " ".join(errs),
                          "claves": " ".join(ln.clave for ln in g.lineas), "ret": bool(g.retenciones_reducidas)})
        return filas

    def detalle_grupo(self, gid: int) -> dict:
        g = self._grupos[gid]
        lineas = []
        for ln in g.lineas:
            o, n = ln.original, ln.propuesta
            lineas.append({"fila": ln.fila, "clave": ln.clave, "sol": o["solicitado"],
                           "ret": [sum(o[k] for k in RET), sum(n[k] for k in RET)],
                           "apli": [o["apli"], n["apli"]], "tr": [o["transferido"], n["transferido"]],
                           "fdo": [o["fdo_ppio"], n["fdo_ppio"]], "retred": ln.fila in g.retenciones_reducidas})
        return {"id": gid, "estado": "pend" if g.estado == PENDIENTE else "apl", "cuil": g.clave[0], "cod": g.clave[3],
                "pres": g.clave[2], "sub": g.subsidio, "ao": sum(ln.original["apli"] for ln in g.lineas),
                "an": sum(ln.propuesta["apli"] for ln in g.lineas), "tipo": tipo_correccion(g), "lineas": lineas}

    def cruce(self) -> dict:
        c = self._cruce
        if c is None:
            return {"filas": []}
        gid = {id(g): i for i, g in enumerate(self._grupos)} if self._grupos else {}
        if not gid and self._r:
            self._grupos = list(self._r.grupos.values())
            gid = {id(g): i for i, g in enumerate(self._grupos)}
        filas = []
        for i, l in enumerate(c.lineas):
            filas.append({"id": i, "clave": l.clave, "cuil": l.cuil, "fila": l.fila, "errs": l.codigos_sss,
                          "estado": l.estado, "corr": l.correccion, "pend": l.pendientes,
                          "gid": gid.get(id(l.grupo)) if l.grupo is not None else None,
                          "gest": ("pend" if l.grupo.estado == PENDIENTE else "apl" if l.grupo.estado == APLICADA
                                   else "") if l.grupo is not None else ""})
        return {"filas": filas, "por_estado": dict(c.por_estado), "total": c.total_err,
                "aceptadas": c.aceptadas_que_cambian}

    def excel(self, vista: str = "clave") -> dict:
        r = self._r
        if r is None:
            return {"cols": [], "filas": []}
        lote = r.lote
        manual = r.filas_con(ERROR, r.propuesta)
        advs = r.filas_con(ADVERTENCIA)
        est = {ln.fila: g.estado for g in r.grupos.values() for ln in g.lineas}
        ret = {f for g in r.grupos.values() if g.estado == APLICADA for f in g.retenciones_reducidas}
        a_clave = {v: k for k, v in lote.columnas.items()}
        if vista == "clave":
            cols = [{"k": k, "t": t, "m": k in IMPORTES or k == "_ret"} for k, t in CLAVE_EXCEL]
        else:
            cols = [{"k": a_clave.get(i + 1, f"c{i}"), "t": h or f"Col {i + 1}", "m": a_clave.get(i + 1) in IMPORTES}
                    for i, h in enumerate(lote.encabezados)]
        filas = []
        for ln, crudo in zip(lote.lineas, lote.filas):
            f, e = ln.fila, est.get(ln.fila)
            fam = ("err" if f in manual else "pend" if e == PENDIENTE else "vio" if f in ret else
                   "ok" if e == APLICADA else "warn" if f in advs else "")
            if vista == "clave":
                vals = []
                for k, _ in CLAVE_EXCEL:
                    if k == "_ret":
                        vals.append(sum(ln.monto[x] for x in RET))
                    elif k in ln.monto:
                        vals.append(ln.monto[k])
                    else:
                        vals.append(texto_celda(ln.crudo.get(k)))
            else:
                vals = [ln.monto[a_clave[i + 1]] if a_clave.get(i + 1) in ln.monto else texto_celda(v)
                        for i, v in enumerate(crudo)]
            filas.append({"fila": f, "fam": fam, "cuil": ln.cuil, "clave": ln.clave, "v": vals})
        return {"cols": cols, "filas": filas}

    def detalle_linea(self, fila: int) -> dict:
        r = self._r
        ln = next((l for l in r.lote.lineas if l.fila == fila), None)
        if ln is None:
            return {}
        g = r.grupo_de_fila(fila)
        gid = self._grupos.index(g) if g is not None and g in self._grupos else None
        importes = [{"t": COL[k].titulo, "col": COL[k].encabezado, "o": ln.original[k],
                     "p": ln.propuesta.get(k, ln.original[k]), "a": ln.monto[k]} for k in IMPORTES]
        grupo = None
        if g is not None:
            grupo = {"id": gid, "estado": {PENDIENTE: "pend", APLICADA: "apl"}.get(g.estado, ""), "n": len(g.lineas),
                     "sub": g.subsidio, "tipo": tipo_correccion(g) if g.tiene_propuesta else "sin cambios",
                     "lineas": [{"fila": x.fila, "clave": x.clave, "sub": x.original["subsidiado"],
                                 "sol": x.original["solicitado"], "ao": x.original["apli"],
                                 "ap": x.propuesta.get("apli", 0), "fdo": x.propuesta.get("fdo_ppio", 0)}
                                for x in g.lineas]}
        vals = [{"c": h.codigo, "n": h.nivel, "d": h.detalle} for h in r.actual if h.fila == fila]
        return {"fila": fila, "cuil": ln.cuil, "cod": ln.texto.get("cod", ""), "pres": ln.grupo[2], "clave": ln.clave,
                "importes": importes, "grupo": grupo, "validaciones": vals}

    # ================================================================== diálogos de archivo
    def _dialogo(self, tipo: str, titulo: str, filtros: List[str], sugerido: str = "", carpeta: str = "") -> str:
        prueba = os.environ.get("BALIDAF_PRUEBA_" + tipo.upper())
        if prueba is not None:
            return prueba
        if self._ventana is not None:
            import webview
            modo = webview.FileDialog.SAVE if tipo == "guardar" else webview.FileDialog.OPEN
            res = self._ventana.create_file_dialog(modo, directory=carpeta or "", save_filename=sugerido,
                                                   file_types=tuple(filtros))
            if not res:
                return ""
            return res if isinstance(res, str) else res[0]
        # modo navegador: diálogo de Tkinter en un proceso aparte (evita problemas de hilos)
        codigo = ("import sys,tkinter as tk;from tkinter import filedialog as fd;r=tk.Tk();r.withdraw();"
                  "r.attributes('-topmost',True);a=sys.argv;"
                  "p=(fd.asksaveasfilename(title=a[2],initialfile=a[3],initialdir=a[4],defaultextension='.xlsx')"
                  " if a[1]=='guardar' else fd.askopenfilename(title=a[2],initialdir=a[4]));print(p or '')")
        try:
            out = subprocess.run([sys.executable, "-c", codigo, tipo, titulo, sugerido, carpeta],
                                 capture_output=True, text=True, timeout=600)
            return out.stdout.strip()
        except Exception:
            return ""

    def elegir_excel(self) -> str:
        return self._dialogo("excel", "Elegí el Excel ORIGINAL de Presmed", ["Excel (*.xlsx;*.xlsm)", "Todos (*.*)"])

    def elegir_txt(self, tipo: str) -> str:
        return self._dialogo("txt", "TXT de la SSS (_DR.DEVOLUCION_" + tipo + ")", ["TXT (*.txt)", "Todos (*.*)"])

    def elegir_destino(self, cual: str = "excel") -> str:
        if self._r is None:
            return ""
        base = ruta_salida(self._r.lote.ruta) if cual == "excel" else ruta_informe(self._r.lote.ruta)
        return self._dialogo("guardar", "Guardar como", ["Excel (*.xlsx)"], os.path.basename(base),
                             os.path.dirname(self._r.lote.ruta))

    # ================================================================== tareas en segundo plano
    def _iniciar(self, titulo: str, pasos, pesos: Optional[dict], trabajo, al_terminar) -> dict:
        if self._ocupado:
            return {"ok": False, "error": "Hay una tarea en curso."}
        self._ocupado = True
        n = len(pasos) or 1
        self._pesos = pesos or {p: 1 / n for p, _ in pasos}
        self._prog = {"estado": "run", "titulo": titulo, "detalle": "", "pasos": [p for p in pasos], "actual": 0,
                      "pct": 0}

        def run():
            try:
                res = trabajo()
                al_terminar(res)
            except Exception as exc:
                write_error_log(f"ERROR: {titulo}")
                traceback.print_exc()
                self._prog.update({"estado": "error", "titulo": "No fue posible completar la tarea", "detalle": str(exc)})
                self._ultimo = {"ok": False, "error": str(exc), "titulo": titulo}
            finally:
                self._ocupado = False
                self._version += 1
        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def _avance(self, paso: str, texto: str, cur: int, tot: int) -> None:
        ids = [p for p, _ in self._prog["pasos"]]
        if paso not in ids:
            return
        i = ids.index(paso)
        base = sum(self._pesos.get(p, 0) for p in ids[:i])
        frac = (cur / tot) if tot > 0 else 0.15
        self._prog.update({"actual": i, "detalle": texto,
                           "pct": round(100 * (base + self._pesos.get(paso, 0) * min(frac, 1)), 1),
                           "indeterminado": tot <= 0})

    def _terminar(self, titulo: str, detalle: str, ultimo: dict) -> None:
        self._prog.update({"estado": "done", "titulo": titulo, "detalle": detalle, "pct": 100,
                           "actual": len(self._prog["pasos"]), "indeterminado": False})
        self._ultimo = dict(ultimo, ok=True, t=dt.datetime.now().timestamp())

    # ---------------- Paso 1
    def analizar(self, ruta: str) -> dict:
        ruta = (ruta or "").strip().strip('"')
        if not os.path.isfile(ruta):
            return {"ok": False, "error": "No se encontró el archivo."}
        self._ruta = ruta

        def trabajo():
            return analizar(ruta, progreso=self._avance)

        def fin(r):
            self._r, self._cambios, self._guardado = r, False, None
            self._grupos = list(r.grupos.values())
            self._recruzar()
            self._terminar("Análisis terminado", f"{len(r.lote.lineas):,} líneas · {len(r.grupos_con(PENDIENTE)):,} "
                                                 "grupos con corrección propuesta".replace(",", "."),
                           {"tipo": "analizar"})
        self._r = None
        self._cruce = None
        return self._iniciar("Analizando el Excel…", PASOS, PESOS["analizar"], trabajo, fin)

    # ---------------- Paso 2
    def _sel_grupos(self, ids: List[int], estado: str) -> List:
        return [self._grupos[i] for i in ids if 0 <= i < len(self._grupos) and self._grupos[i].estado == estado]

    def resumen(self, ids: List[int], accion: str = "aplicar") -> dict:
        gs = self._sel_grupos(ids, PENDIENTE if accion == "aplicar" else APLICADA)
        return {"grupos": len(gs), "lineas": sum(len(g.lineas) for g in gs),
                "dif": sum(ln.propuesta["apli"] - ln.original["apli"] for g in gs for ln in g.lineas)}

    def aplicar(self, ids: List[int]) -> dict:
        return self._modificar(ids, True)

    def deshacer(self, ids: List[int]) -> dict:
        return self._modificar(ids, False)

    def _modificar(self, ids: List[int], aplicar: bool) -> dict:
        r = self._r
        gs = self._sel_grupos(ids, PENDIENTE if aplicar else APLICADA)
        if r is None or not gs:
            return {"ok": False, "error": "No hay correcciones para " + ("aplicar." if aplicar else "deshacer.")}
        lineas = sum(len(g.lineas) for g in gs)
        idx = [self._grupos.index(g) for g in gs]
        pasos = [("aplicar", "Aplicar corrección" if aplicar else "Deshacer"), ("validar", "Revalidar reglas SSS")]

        def trabajo():
            self._avance("aplicar", "Aplicando…" if aplicar else "Deshaciendo…", 0, 0)
            prog = lambda t, c, n: self._avance("validar", t, c, n)
            return r.aplicar(gs, prog) if aplicar else r.deshacer(gs, prog)

        def fin(_):
            self._cambios = any(ln.modificados() for ln in r.lote.lineas)
            self._guardado = None
            self._recruzar()
            verbo = "aplicaron" if aplicar else "deshicieron"
            self._terminar("Corrección aplicada" if aplicar else "Corrección deshecha",
                           f"{len(gs):,} grupos · {lineas:,} líneas".replace(",", "."),
                           {"tipo": "aplicar" if aplicar else "deshacer", "ids": idx,
                            "mensaje": f"Se {verbo} {len(gs):,} correcciones ({lineas:,} líneas).".replace(",", ".")})
        return self._iniciar("Aplicando la corrección…" if aplicar else "Deshaciendo…", pasos, None, trabajo, fin)

    # ---------------- Paso 3
    def guardar(self, destino: str) -> dict:
        r = self._r
        if r is None or not destino:
            return {"ok": False, "error": "Nada para guardar."}

        def trabajo():
            self._avance("preparar", "Preparando los valores…", 1, 1)
            self._avance("escribir", "Escribiendo el archivo…", 0, 0)
            guardar(r, destino)
            self._avance("verificar", "Verificando el archivo…", 1, 1)
            if not os.path.isfile(destino) or os.path.getsize(destino) == 0:
                raise IOError("El archivo guardado está vacío.")
            return destino

        def fin(d):
            self._cambios = False
            self._guardado = {"archivo": os.path.basename(d), "ruta": d, "hora": dt.datetime.now().strftime("%H:%M")}
            self._terminar("Excel guardado", d, {"tipo": "guardar", "mensaje": f"Excel guardado como {os.path.basename(d)}."})
        return self._iniciar("Guardando el Excel…", [("preparar", "Preparar valores"), ("escribir", "Escribir Excel"),
                                                      ("verificar", "Verificar archivo")], PESOS["guardar"], trabajo, fin)

    def exportar_informe(self, destino: str) -> dict:
        r = self._r
        if r is None or not destino:
            return {"ok": False}

        def trabajo():
            self._avance("informe", "Escribiendo…", 0, 0)
            return exportar(r, destino, self._cruce)
        return self._iniciar("Exportando el informe…", [("informe", "Exportar informe")], None, trabajo,
                             lambda d: self._terminar("Informe exportado", d, {
                                 "tipo": "informe", "mensaje": "Informe exportado (no es el Excel de Presmed)."}))

    # ---------------- Devolución SSS
    def cargar_txt(self, tipo: str, ruta: str) -> dict:
        if not ruta or not os.path.isfile(ruta):
            return {"ok": False, "error": "No se encontró el archivo."}

        def trabajo():
            self._avance("txt", "Leyendo…", 0, 0)
            a = leer_txt(ruta, tipo)
            self._avance("cruce", "Cruzando con el Excel…", 1, 1)
            return a

        def fin(a):
            if tipo == "ERR":
                self._txt_err = a
            else:
                self._txt_ok = a
            self._recruzar()
            self._terminar("TXT cargado", f"{a.nombre} · {len(a.registros):,} líneas".replace(",", "."),
                           {"tipo": "txt"})
        return self._iniciar("Leyendo el TXT de la SSS…", [("txt", "Leer TXT"), ("cruce", "Cruzar con el Excel")],
                             None, trabajo, fin)

    def _recruzar(self) -> None:
        self._cruce = cruzar(self._r, self._txt_err, self._txt_ok) if self._r and self._txt_err else None
