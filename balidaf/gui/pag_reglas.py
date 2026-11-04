"""Pestaña «Reglas de balanceo»: página de lectura con la lógica del programa y todos los controles."""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict, List

from ..balanceo import TIPOS
from ..schema import CODIGOS
from .componentes import Caja, Lbl, Segmentado, Tabla
from .tema import F, P, al_cambiar_tema

if TYPE_CHECKING:
    from .app import BalidafApp

ANCHO = 1000

FLUJO = [("Paso 1", "Analizar", "Lee el Excel, revisa las reglas de la SSS en el original, calcula la corrección de "
                                "cada grupo y valida cómo quedaría."),
         ("Paso 2", "Revisar y aplicar", "Filtrás, ordenás, mirás el detalle original → corregido y aplicás todas, "
                                         "algunas o las de un tipo. Se puede deshacer."),
         ("Paso 3", "Guardar para Presmed", "Genera <archivo>_balidaf.xlsx. Sólo cambian valores: sin colores, "
                                            "formatos, fórmulas ni hojas nuevas."),
         ("Si la SSS rechaza", "Devolución SSS", "Se cargan los TXT _ERR (y _OK), se cruzan por clave_rendicion y "
                                                 "decidís qué corregir.")]
LEE = ["clave_rendicion", "cuil", "cod_prestac", "periodo_presentacion", "perio_prestac", "importe_subsidiado",
       "importe_solicitado", "retencion_ganancias", "retencion_IIBB", "otras_retnciones", "fdo_ppio_otras_ctas",
       "reversion_import_trasl", "import_devuelto_cta_sss", "saldo_no_apli", "recup_fdos_ppios"]
MODIFICA = ["impor_apli_sss", "importe_transferido", "fdo_ppio_ingre_cta_disca"]
RETEN = ["retencion_ganancias", "retencion_IIBB", "otras_retnciones"]
DESC_TIPOS = {
    "Aplicado mayor al subsidio": "Se había aplicado más que el subsidio del grupo.",
    "Aplicado menor al subsidio": "Se había aplicado menos que el subsidio.",
    "Fondos propios / reparto": "El total estaba bien pero faltaban fondos propios o el reparto entre líneas.",
    "Ajuste de centavos": "Ningún importe cambia más de $1.",
    "Reduce retenciones": "El subsidio no alcanza para cubrir las retenciones de alguna línea.",
    "No se puede balancear": "El subsidio es mayor a lo que se puede aplicar: revisión manual.",
}
CALCULO = """GRUPO       = cuil + periodo_presentacion + perio_prestac + cod_prestac      (regla 624)

SUBSIDIO    = Σ importe_subsidiado del grupo
A_APLICAR   = SUBSIDIO − Σ (reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)

Por línea:
  OTROS        = fdo_ppio_otras_ctas + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios
  TOPE         = importe_solicitado − OTROS
  RETENCIONES  = retencion_ganancias + retencion_IIBB + otras_retnciones

Orden de reparto: primero las líneas CON retenciones (el transferido nunca queda negativo), luego el resto.

  impor_apli_sss            = mínimo entre TOPE y lo que queda de A_APLICAR
  si RETENCIONES > impor_apli_sss → se reducen ganancias → IIBB → otras (transferido = 0)
  importe_transferido       = impor_apli_sss − RETENCIONES
  fdo_ppio_ingre_cta_disca  = importe_solicitado − impor_apli_sss − OTROS"""
REGLAS = [("622", "impor_apli_sss = importe_transferido + retencion_ganancias + retencion_IIBB + otras_retnciones"),
          ("623", "importe_solicitado = fdo_ppio_ingre_cta_disca + fdo_ppio_otras_ctas + impor_apli_sss + "
                  "reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios  "
                  "(no aplica a tipo DB)"),
          ("624", "Por GRUPO: Σ importe_subsidiado = Σ (impor_apli_sss + reversion_import_trasl + "
                  "import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)")]


class PagReglas(tk.Frame):
    def __init__(self, master, app: "BalidafApp"):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.pag = tk.Frame(self.canvas, width=ANCHO)
        self._win = self.canvas.create_window(0, 0, window=self.pag, anchor="nw", width=ANCHO)
        self.pag.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._centrar)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._rueda))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        al_cambiar_tema(lambda: (self.config(bg=P["bg"]), self.canvas.config(bg=P["bg"]), self.pag.config(bg=P["bg"])))
        self._secciones: Dict[str, tk.Widget] = {}
        self._construir()

    def _centrar(self, e) -> None:
        ancho = min(ANCHO, e.width - 40)
        self.canvas.itemconfigure(self._win, width=ancho)
        self.canvas.coords(self._win, max((e.width - ancho) // 2, 0), 0)

    def _rueda(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def _ir(self, clave: str) -> None:
        w = self._secciones[clave]
        self.update_idletasks()
        total = self.pag.winfo_height() or 1
        self.canvas.yview_moveto(max(0, (w.winfo_y() - 10) / total))

    # ------------------------------------------------------------------ helpers
    def _seccion(self, clave: str, titulo: str) -> tk.Frame:
        c = Caja(self.pag, padx=20, pady=16)
        c.pack(fill="x", pady=(12, 0))
        Lbl(c, titulo, 15, "semibold").pack(anchor="w", pady=(0, 10))
        self._secciones[clave] = c
        return c

    def _chips(self, master, nombres: List[str], fam: str) -> tk.Frame:
        f = tk.Frame(master)
        al_cambiar_tema(lambda: f.config(bg=P["surface"]))
        col = fila = 0
        for n in nombres:
            Lbl(f, n, 12, mono=True, fondo=f"{fam}_bg" if fam != "neu" else "neu_bg",
                color="ink" if fam == "neu" else f"{fam}_fg", padx=8, pady=2).grid(
                row=fila, column=col, padx=(0, 6), pady=3, sticky="w")
            col += 1
            if col == 4:
                col, fila = 0, fila + 1
        return f

    def _codigo(self, master, texto: str) -> None:
        t = tk.Text(master, height=texto.count("\n") + 1, wrap="none", relief="flat", padx=14, pady=10,
                    font=F(12.5, mono=True), highlightthickness=0, bd=0)
        t.insert("1.0", texto)
        t.configure(state="disabled")
        t.pack(fill="x")
        al_cambiar_tema(lambda: t.config(bg=P["code"], fg=P["ink"]))

    # ------------------------------------------------------------------ contenido
    def _construir(self) -> None:
        cab = tk.Frame(self.pag)
        cab.pack(fill="x", pady=(18, 0))
        al_cambiar_tema(lambda: cab.config(bg=P["bg"]))
        Lbl(cab, "Cómo balancea Balidaf", 22, "semibold", fondo="bg").pack(anchor="w")
        Lbl(cab, "Balidaf trabaja sobre la primera hoja del Excel de Presmed. Primero propone la corrección y sólo la "
                 "aplica cuando vos lo decidís (botones «Aplicar…» / «Corregir…»).", 13.5, color="ink2", fondo="bg",
            wraplength=ANCHO, justify="left").pack(anchor="w", pady=(6, 10))
        idx = tk.Frame(cab)
        idx.pack(anchor="w")
        al_cambiar_tema(lambda: idx.config(bg=P["bg"]))
        for clave, txt in (("col", "Columnas"), ("calc", "Cálculo"), ("tipos", "Tipos"), ("reglas", "Reglas 622–624"),
                           ("ej", "Ejemplo"), ("ctrl", "Controles SSS")):
            b = Lbl(idx, txt, 12, color="ink2", fondo="surface", padx=10, pady=3, cursor="hand2",
                    highlightthickness=1)
            al_cambiar_tema(lambda b=b: b.config(highlightbackground=P["line_strong"]))
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, c=clave: self._ir(c))

        flujo = tk.Frame(self.pag)
        flujo.pack(fill="x", pady=(14, 0))
        al_cambiar_tema(lambda: flujo.config(bg=P["bg"]))
        for i, (paso, tit, txt) in enumerate(FLUJO):
            c = Caja(flujo, padx=14, pady=12)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            flujo.columnconfigure(i, weight=1, uniform="f")
            Lbl(c, paso, 12, "semibold", color="accent").pack(anchor="w")
            Lbl(c, tit, 13.5, "semibold").pack(anchor="w", pady=(4, 4))
            Lbl(c, txt, 12.5, color="ink2", wraplength=215, justify="left").pack(anchor="w")

        s = self._seccion("col", "1 · Columnas")
        for etiqueta, contenido in (("Lee", lambda m: self._chips(m, LEE, "neu")),
                                    ("Puede modificar", None), ("Nunca modifica", None)):
            fila = tk.Frame(s)
            fila.pack(fill="x", pady=4)
            al_cambiar_tema(lambda f=fila: f.config(bg=P["surface"]))
            Lbl(fila, etiqueta, 12.5, "semibold", width=16, anchor="nw").pack(side="left", anchor="n")
            if etiqueta == "Lee":
                contenido(fila).pack(side="left")
            elif etiqueta == "Puede modificar":
                col = tk.Frame(fila)
                col.pack(side="left")
                al_cambiar_tema(lambda c=col: c.config(bg=P["surface"]))
                self._chips(col, MODIFICA, "pend").pack(anchor="w")
                f2 = tk.Frame(col)
                f2.pack(anchor="w")
                al_cambiar_tema(lambda c=f2: c.config(bg=P["surface"]))
                self._chips(f2, RETEN, "vio").pack(side="left")
                Lbl(f2, "sólo si el subsidio no alcanza a cubrirlas", 12, color="ink3").pack(side="left", padx=6)
            else:
                Lbl(fila, "Campos 2 a 9 de la SSS (rnos, tipo_archi, periodo_presentacion, perio_prestac, cuil, "
                          "cod_prestac, importe_subsidiado, importe_solicitado), CUIT, CBU, órdenes de pago, fechas, "
                          "cheque, recibo y observaciones.", 12.5, color="ink2", wraplength=800,
                    justify="left").pack(side="left")

        s = self._seccion("calc", "2 · Grupos y cálculo")
        Lbl(s, "Las líneas se agrupan como lo controla la SSS en la regla 624. El subsidio se informa en una línea del "
               "grupo y se reparte entre todas sus líneas. Si el grupo ya cumple 622, 623 y 624, no se toca. Todo se "
               "calcula en centavos exactos.", 12.5, color="ink2", wraplength=950, justify="left").pack(
            anchor="w", pady=(0, 8))
        self._codigo(s, CALCULO)

        s = self._seccion("tipos", "3 · Tipos de corrección")
        t = Tabla(s, [("t", "Tipo", 260), ("d", "Cuándo", 640, "w", True)], altura=len(TIPOS))
        t.pack(fill="x")
        t.cargar([(str(i), (x, DESC_TIPOS.get(x, "")), "") for i, x in enumerate(TIPOS)])

        s = self._seccion("reglas", "4 · Reglas que debe cumplir el resultado")
        for cod, formula in REGLAS:
            f = tk.Frame(s)
            f.pack(fill="x", pady=3)
            al_cambiar_tema(lambda f=f: f.config(bg=P["surface"]))
            Lbl(f, cod, 13, "semibold", color="accent", mono=True, width=5, anchor="nw").pack(side="left", anchor="n")
            Lbl(f, formula, 12.5, mono=True, wraplength=900, justify="left").pack(side="left")

        s = self._seccion("ej", "5 · Ejemplo (caso real de la rendición 202606)")
        Lbl(s, "Subsidio 1.010.735,49 · solicitado 1.364.492,91 · retenciones 27.289,86 + 27.289,86", 12.5,
            color="ink2").pack(anchor="w", pady=(0, 8))
        g = tk.Frame(s, highlightthickness=1)
        g.pack(fill="x")
        al_cambiar_tema(lambda: g.config(bg=P["surface"], highlightbackground=P["line"]))
        cab_ej = ["", "Aplicado", "Transferido", "Fondos propios", "Resultado"]
        filas_ej = [("Original", "1.364.492,91", "1.309.913,19", "0,00", ("Error 624", "err")),
                    ("Corregido", "1.010.735,49", "956.155,77", "353.757,42", ("OK", "ok"))]
        for j, h in enumerate(cab_ej):
            Lbl(g, h, 12, "semibold", color="ink2", fondo="head", anchor="e" if 0 < j < 4 else "w",
                padx=12, pady=6).grid(row=0, column=j, sticky="ew")
        for i, fila in enumerate(filas_ej, start=1):
            for j, v in enumerate(fila):
                if j == 4:
                    Lbl(g, v[0], 11.5, "semibold", fondo=f"{v[1]}_bg", color=f"{v[1]}_fg", padx=8).grid(
                        row=i, column=j, sticky="w", padx=12, pady=6)
                else:
                    Lbl(g, v, 13, "semibold" if (i == 2 and j) or j == 0 else "normal",
                        anchor="e" if j else "w", padx=12, pady=6).grid(row=i, column=j, sticky="ew")
        for j in range(5):
            g.columnconfigure(j, weight=1)

        s = self._seccion("ctrl", "6 · Todos los controles (instructivo SSS, Anexos III y IV)")
        self.seg = Segmentado(s, [("Todos", "Todos"), ("Balanceo", "Balanceo"), ("Manual", "Manual"),
                                  ("Sistemas", "Sistemas"), ("Propios", "Propios")], self._filtrar_ctrl)
        self.seg.pack(anchor="w", pady=(0, 8))
        self.t_ctrl = Tabla(s, [("c", "Código", 70), ("campo", "Campo", 210), ("d", "Control", 560, "w", True),
                                ("r", "Lo resuelve", 110)], altura=10)
        self.t_ctrl.pack(fill="x")
        self._filtrar_ctrl("Todos")
        tk.Frame(self.pag, height=24).pack()

    def _filtrar_ctrl(self, v: str) -> None:
        fam = {"Balanceo": "pend", "Manual": "err", "Sistemas": "warn"}
        filas = []
        for c in CODIGOS.values():
            propio = c.codigo.startswith("B")
            if v == "Propios" and not propio or v not in ("Todos", "Propios") and (propio or c.resuelve != v):
                continue
            res = "Balidaf" if propio else c.resuelve
            filas.append((c.codigo, (c.codigo, c.campo, c.descripcion, res), "neu" if propio else fam.get(res, "")))
        self.t_ctrl.tree.configure(height=min(len(filas), 14))
        self.t_ctrl.cargar(filas)
