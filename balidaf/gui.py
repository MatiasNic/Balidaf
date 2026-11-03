"""Interfaz gráfica (Tkinter)."""

import os
import threading

from . import APP_TITLE
from .core import process_file
from .paths import ERROR_LOG_NAME, resource_path, write_error_log


def run_gui() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText

    class App(tk.Tk):
        def __init__(self):
            super().__init__()

            # --- Ícono de la ventana (funciona en .py y en .exe onefile) ---
            try:
                self.iconbitmap(resource_path("assets", "balidaf.ico"))  # Windows usa .ico
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

            frm_mid = ttk.Frame(self, padding=(10, 0, 10, 10)); frm_mid.pack(fill="x")
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

        def log(self, msg: str):
            self.logbox.insert("end", msg + "\n"); self.logbox.see("end"); self.update_idletasks()

        def set_progress(self, cur: int, tot: int):
            self.pb["maximum"] = max(tot, 1); self.pb["value"] = cur; self.update_idletasks()

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
                    def ui_log(s): self.after(0, self.log, s)
                    def ui_prog(c, t): self.after(0, self.set_progress, c, t)

                    result = process_file(path, ui_log, ui_prog)

                    self.after(0, self.log, "")
                    self.after(0, self.log, "RESUMEN")
                    self.after(0, self.log, f"- Hoja utilizada        : {result.sheet_used}")
                    self.after(0, self.log, f"- Archivo generado      : {result.out_path}")
                    self.after(0, self.set_progress, 0, 1)
                    self.after(0, self.btn.config, {"state": "normal"})
                    messagebox.showinfo("Proceso completado", f"Archivo generado:\n{result.out_path}")
                except Exception:
                    write_error_log("ERROR RUNTIME:")
                    self.after(0, self.btn.config, {"state": "normal"})
                    messagebox.showerror("Error", f"No fue posible completar el proceso.\nRevise el archivo '{ERROR_LOG_NAME}' para más detalles.")
                    self.after(0, self.log, f"ERROR: No fue posible completar el proceso. Consulte {ERROR_LOG_NAME}.")

            threading.Thread(target=worker, daemon=True).start()

    app = App(); app.mainloop()
