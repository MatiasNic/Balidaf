#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balidaf – Balanceo de subsidios - IDAF
--------------------------------------
- Trabaja sobre la PRIMERA hoja del Excel.
- Solo escribe en 3 columnas objetivo: impor_apli_sss, importe_transferido, fdo_ppio_ingre_cta_disca.
- Agrega una hoja LOG (sin 'fila' ni '<letra> celda') con detalle por línea.
- Lee valores desde un workbook data_only=True (para tomar el valor real de CONCATENAR si es fórmula)
  y escribe en otro workbook (para preservar formatos y crear columnas faltantes sin afectar lectura).
- Ícono de ventana: requiere compilar con PyInstaller incluyendo el recurso:
      --icon "balidaf.ico" --add-data "balidaf.ico;."
"""

import os, sys, traceback
from collections import OrderedDict
from typing import Dict, List, Tuple, Any

# ====== Requisitos de versión ======
if sys.version_info < (3,8):
    print("ERROR: Se requiere Python 3.8 o superior.")
    sys.exit(1)

# ====== Dependencias ======
try:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
except Exception:
    print("ERROR: No se pudo importar openpyxl. Instale con: pip install openpyxl")
    sys.exit(1)

# ====== Utilidades de encabezados y parsing ======
def _norm(s: str) -> str:
    if s is None:
        return ""
    return str(s).strip().upper().replace(" ", "").replace("_", "").replace("-", "")

ALIASES: Dict[str, List[str]] = {
    "key": ["CONCATENAR", "SOCIO", "ID_SOCIO", "NRO_USUARIO", "USUARIO", "AFILIADO"],
    "subsidiado": ["IMPORTE_SUBSIDIADO", "IMPORTEDESUBSIDIO", "IMPSUBSIDIADO", "SUBSIDIADO"],
    "apli_sss": ["IMPOR_APLI_SSS", "IMPORTE_APLICADO_SSS", "IMP_APLI_SSS", "APLICADOSSS"],
    "ret_gcias": ["RETENCION_GANANCIAS", "RETENCIONGCIA", "RET_GANANCIAS", "GANANCIAS"],
    "ret_iibb": ["RETENCION_IIBB", "RETENCION_INGRESOS_BRUTOS", "RET_IIBB", "INGRESOSBRUTOS"],
    "ret_otras": ["OTRAS_RETNciones", "OTRAS_RETENCIONES", "OTRAS_RET", "OTRASRET", "OTRAS"],
    "solicitado": ["IMPORTE_SOLICITADO", "IMP_SOLICITADO", "IMPORTE_SOL", "SOLICITADO"],
    "transferido": ["IMPORTE_TRANSFERIDO", "IMP_TRANSFERIDO", "IMPOR_TRANSFERIDO", "TRANSFERIDO"],
    "fdo_ppio": [
        "FDO_PPIO_INGRE_CTA_DISCA", "FDO_PPIO_INGRE_CTA_DISCA ",
        "FDO_PPIO_INGRESOS_CTA_DISCA", "FONDO_PROPIO_INGRE_CTA_DISCA",
        "FDO_PPIO", "FONDO_PROPIO"
    ],
}

def _lookup_flexible(cols_norm_map: Dict[str, int], alias_list: List[str]) -> int:
    # Exacta
    for a in alias_list:
        an = _norm(a)
        if an in cols_norm_map:
            return cols_norm_map[an]
    # Contiene
    candidates: List[Tuple[int, int]] = []
    for a in alias_list:
        an = _norm(a)
        for k_norm, idx in cols_norm_map.items():
            if an and (an in k_norm or k_norm in an):
                candidates.append((max(len(an), len(k_norm)), idx))
    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]
    return 0

def find_columns(ws) -> Dict[str, int]:
    cols_norm_map: Dict[str, int] = {}
    max_col = ws.max_column
    for c in range(1, max_col + 1):
        header = ws.cell(row=1, column=c).value
        cols_norm_map[_norm(header)] = c

    mapping: Dict[str, int] = {}
    missing: List[str] = []

    # Requeridas de entrada
    for canon in ["key", "subsidiado", "ret_gcias", "ret_iibb", "ret_otras", "solicitado"]:
        col_idx = _lookup_flexible(cols_norm_map, ALIASES[canon])
        if col_idx:
            mapping[canon] = col_idx
        else:
            missing.append(canon)

    # Salidas (crear si faltan en el workbook de ESCRITURA)
    for out_key, header_name, aliases in [
        ("apli_sss", "impor_apli_sss", ALIASES["apli_sss"]),
        ("transferido", "importe_transferido", ALIASES["transferido"]),
        ("fdo_ppio", "fdo_ppio_ingre_cta_disca", ALIASES["fdo_ppio"]),
    ]:
        col_idx = _lookup_flexible(cols_norm_map, aliases)
        if not col_idx:
            max_col += 1
            col_idx = max_col
            ws.cell(row=1, column=col_idx, value=header_name)
            cols_norm_map[_norm(header_name)] = col_idx
        mapping[out_key] = col_idx

    if missing:
        nombre = {
            "key": "CONCATENAR (clave de socio)",
            "subsidiado": "IMPORTE_SUBSIDIADO",
            "ret_gcias": "RETENCION_GANANCIAS",
            "ret_iibb": "RETENCION_IIBB",
            "ret_otras": "OTRAS_RETENCIONES",
            "solicitado": "IMPORTE_SOLICITADO",
        }
        raise ValueError("Faltan columnas requeridas: " + ", ".join(nombre[m] for m in missing))
    return mapping

def to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return 0.0
    s2 = s.replace(" ", "")
    if "," in s2 and "." in s2:
        s2 = s2.replace(".", "").replace(",", ".")
    elif "," in s2 and "." not in s2:
        s2 = s2.replace(",", ".")
    try:
        return float(s2)
    except Exception:
        return 0.0

# ====== Núcleo: lee de ws_read (data_only) y escribe en ws_write ======
def balancear_y_log(ws_read, ws_write, mapping_write: Dict[str, int], log, prog) -> List[List[Any]]:
    r1, rN = 2, ws_write.max_row  # asumimos mismas filas
    # Construir orden y grupos leyendo la clave desde ws_read (valor calculado si era fórmula)
    order_keys: List[Tuple[int, str]] = []
    for r in range(r1, rN + 1):
        key_val = ws_read.cell(row=r, column=mapping_write["key"]).value
        key_str = "" if key_val is None else str(key_val)
        order_keys.append((r, key_str))

    groups = OrderedDict()
    for r, k in order_keys:
        groups.setdefault(k, []).append(r)

    total_groups = len(groups)
    gi = 0

    # Subsidio total por grupo (leer de ws_read)
    subsidio_por_grupo: Dict[str, float] = {}
    subs_col = mapping_write["subsidiado"]
    for k, rows in groups.items():
        s_total = 0.0
        for r in rows:
            s_total += to_float(ws_read.cell(row=r, column=subs_col).value)
        subsidio_por_grupo[k] = round(s_total, 2)

    # Columnas de escritura (ws_write)
    apli_c = mapping_write["apli_sss"]; apli_letter = get_column_letter(apli_c)
    tran_c = mapping_write["transferido"]; tran_letter = get_column_letter(tran_c)
    fdo_c  = mapping_write["fdo_ppio"];  fdo_letter  = get_column_letter(fdo_c)

    # LOG rows (en memoria) — SIN 'fila' y SIN columnas '<letra> celda'
    log_rows: List[List[Any]] = []
    log_rows.append([
        "socio", "subsidio_total_grupo", "subsidio_rest_antes", "subsidio_rest_despues",
        "solicitado", "ret_ganancias", "ret_iibb", "ret_otras", "ret_total",
        f"{apli_letter} (impor_apli_sss)",
        f"{tran_letter} (importe_transferido)",
        f"{fdo_letter} (fdo_ppio_ingre_cta_disca)"
    ])

    for k, rows in groups.items():
        gi += 1
        subsidio_rest = subsidio_por_grupo.get(k, 0.0)
        aplicado_total = 0.0

        # Log de grupo: mostrar valor real de la clave (no fórmula)
        log(f"[SOCIO {k}] Subsidio total: {subsidio_rest:.2f} | filas: {len(rows)}")

        for r in rows:
            rg = to_float(ws_read.cell(row=r, column=mapping_write["ret_gcias"]).value)
            ri = to_float(ws_read.cell(row=r, column=mapping_write["ret_iibb"]).value)
            ro = to_float(ws_read.cell(row=r, column=mapping_write["ret_otras"]).value)
            solicitado = round(to_float(ws_read.cell(row=r, column=mapping_write["solicitado"]).value), 2)

            ret_total = round(rg + ri + ro, 2)
            imp_apli_bruto = solicitado
            subsidio_rest_antes = subsidio_rest

            if subsidio_rest <= 0:
                imp_apli_final = 0.0
            else:
                imp_apli_final = imp_apli_bruto if imp_apli_bruto <= subsidio_rest else subsidio_rest

            imp_trans_final = round(imp_apli_final - ret_total, 2)
            diff = round((imp_trans_final + ret_total) - solicitado, 2)
            fdo_val = abs(diff)

            # Escribir solo en ws_write (preservando el resto)
            ws_write.cell(row=r, column=apli_c).value = round(imp_apli_final, 2)
            ws_write.cell(row=r, column=tran_c).value = round(imp_trans_final, 2)
            ws_write.cell(row=r, column=fdo_c).value  = round(fdo_val, 2)

            subsidio_rest = round(subsidio_rest - imp_apli_final, 2)
            aplicado_total = round(aplicado_total + imp_apli_final, 2)

            # LOG en memoria — SIN 'fila' y SIN '<letra> celda'
            log_rows.append([
                k, subsidio_por_grupo[k], subsidio_rest_antes, subsidio_rest,
                solicitado, rg, ri, ro, ret_total,
                round(imp_apli_final, 2),
                round(imp_trans_final, 2),
                round(fdo_val, 2)
            ])

        log(f"  → Aplicado: {aplicado_total:.2f} | Remanente: {round(subsidio_rest, 2):.2f}")
        prog(gi, total_groups)

    return log_rows

def write_log_sheet(wb, log_rows: List[List[Any]], sheet_name: str = "LOG"):
    if sheet_name in wb.sheetnames:
        wb.remove(wb[sheet_name])
    ws = wb.create_sheet(title=sheet_name)
    for ri, row in enumerate(log_rows, start=1):
        for ci, val in enumerate(row, start=1):
            ws.cell(row=ri, column=ci, value=val)

# ====== Interfaz gráfica (Tkinter) ======
def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
    import threading

    APP_TITLE = "Balidaf – Balanceo de subsidios - IDAF"

    class App(tk.Tk):
        def __init__(self):
            super().__init__()

            # --- Ícono de la ventana (funciona en .py y en .exe onefile) ---
            # En PyInstaller onefile, los recursos se extraen en _MEIPASS
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
            ico_path = os.path.join(base_path, "balidaf.ico")
            try:
                self.iconbitmap(ico_path)  # Windows usa .ico
            except Exception:
                pass

            self.title(APP_TITLE)
            self.geometry("760x540")
            self.resizable(True, True)

            self.var_path = tk.StringVar()

            frm_top = ttk.Frame(self, padding=10); frm_top.pack(fill="x")
            ttk.Label(frm_top, text="Archivo Excel:").pack(anchor="w")
            row = ttk.Frame(frm_top); row.pack(fill="x", pady=4)
            ttk.Entry(row, textvariable=self.var_path).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="Examinar…", command=self.on_browse).pack(side="left", padx=6)

            frm_mid = ttk.Frame(self, padding=(10,0,10,10)); frm_mid.pack(fill="x")
            self.btn = ttk.Button(frm_mid, text="Procesar", command=self.on_process, state="disabled"); self.btn.pack(side="left")
            self.pb = ttk.Progressbar(frm_mid, mode="determinate"); self.pb.pack(side="left", fill="x", expand=True, padx=10)

            frm_log = ttk.Frame(self, padding=10); frm_log.pack(fill="both", expand=True)
            ttk.Label(frm_log, text="Registro del proceso:").pack(anchor="w")
            self.logbox = ScrolledText(frm_log, height=18, wrap="word"); self.logbox.pack(fill="both", expand=True)

            # Mensaje inicial requerido
            self.logbox.insert("end", "Seleccione un archivo Excel para procesar.\n")
            self.logbox.see("end"); self.update_idletasks()

        def clear_log(self):
            self.logbox.delete("1.0", "end")

        def log(self, msg:str):
            self.logbox.insert("end", msg + "\n"); self.logbox.see("end"); self.update_idletasks()

        def set_progress(self, cur:int, tot:int):
            self.pb["maximum"] = max(tot,1); self.pb["value"] = cur; self.update_idletasks()

        def on_browse(self):
            path = filedialog.askopenfilename(
                title="Seleccione el Excel de entrada",
                filetypes=[("Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("Todos", "*.*")]
            )
            if not path:
                return
            self.var_path.set(path)
            # No escribir en el registro al cargar (requisito)
            self.btn["state"] = "normal"

        def on_process(self):
            path = self.var_path.get().strip()
            if not path or not os.path.isfile(path):
                messagebox.showwarning("Atención", "Seleccioná un archivo válido."); return
            self.btn["state"] = "disabled"
            self.clear_log()
            self.log("Iniciando procesamiento…")

            def worker():
                try:
                    # Workbook para LECTURA de valores (incluye resultados de fórmula si existen)
                    wb_read = load_workbook(path, data_only=True)
                    ws_read = wb_read.worksheets[0]
                    sheet_used = ws_read.title

                    # Workbook para ESCRITURA (preserva formatos y permite crear columnas)
                    wb_write = load_workbook(path, data_only=False)
                    ws_write = wb_write.worksheets[0]

                    # Detectar/crear columnas en el workbook de ESCRITURA
                    mapping_write = find_columns(ws_write)

                    # Proceso con lectura desde ws_read y escritura en ws_write
                    def ui_log(s): self.after(0, self.log, s)
                    def ui_prog(c,t): self.after(0, self.set_progress, c, t)

                    log_rows = balancear_y_log(ws_read, ws_write, mapping_write, ui_log, ui_prog)

                    # Crear hoja LOG en wb_write
                    write_log_sheet(wb_write, log_rows, sheet_name="LOG")

                    # Salida con sufijo _balidaf
                    out_path = os.path.splitext(path)[0] + "_balidaf.xlsx"
                    wb_write.save(out_path)

                    self.after(0, self.log, "")
                    self.after(0, self.log, "RESUMEN")
                    self.after(0, self.log, f"- Hoja utilizada        : {sheet_used}")
                    self.after(0, self.log, f"- Archivo generado      : {out_path}")
                    self.after(0, self.set_progress, 0, 1)
                    self.after(0, self.btn.config, {"state":"normal"})
                    messagebox.showinfo("Proceso completado", f"Archivo generado:\n{out_path}")
                except Exception:
                    try:
                        with open(os.path.join(os.path.dirname(__file__), "balidaf_errores.log"), "w", encoding="utf-8") as f:
                            f.write("ERROR RUNTIME:\n")
                            traceback.print_exc(file=f)
                    except Exception:
                        pass
                    self.after(0, self.btn.config, {"state":"normal"})
                    messagebox.showerror("Error", "No fue posible completar el proceso.\nRevise el archivo 'balidaf_errores.log' para más detalles.")
                    self.after(0, self.log, "ERROR: No fue posible completar el proceso. Consulte balidaf_errores.log.")

            threading.Thread(target=worker, daemon=True).start()

    app = App(); app.mainloop()

if __name__ == "__main__":
    try:
        run_gui()
    except Exception:
        # Error al inicializar GUI (p.ej., Tkinter ausente)
        try:
            with open(os.path.join(os.path.dirname(__file__), "balidaf_errores.log"), "w", encoding="utf-8") as f:
                f.write("ERROR INICIALIZANDO GUI:\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        print("ERROR: No fue posible iniciar la interfaz gráfica.")
        sys.exit(2)
