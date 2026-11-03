"""
Balidaf – Balanceo de subsidios - IDAF.

Balancea el Excel de rendición (Mecanismo Integración – SSSalud) y lo valida
contra todas las reglas del instructivo "Rendición DR.DEVOLUCION" antes de cargarlo en Presmed.

Módulos:
    schema     → columnas del Excel y códigos de error de la SSS (Anexo IV)
    montos     → manejo exacto de importes en centavos
    excel_io   → lectura/escritura del Excel (sin agregar formatos)
    balanceo   → algoritmo de balanceo por grupo (CUIL + períodos + práctica)
    validacion → todas las validaciones del Anexo III
    sss_txt    → lectura de los TXT DR.DEVOLUCION / _OK / _ERR
    devolucion → cruce de la devolución de la SSS con el Excel
    proceso    → orquesta todo (lo usan la GUI y la línea de comandos)
    informe    → informe de detalle en un Excel aparte
    gui        → interfaz gráfica (Tkinter)
"""

__version__ = "2.0.0"
APP_TITLE = "Balidaf – Balanceo de subsidios - IDAF"
