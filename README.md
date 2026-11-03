# Balidaf – Balanceo de subsidios - IDAF

Programa de escritorio que toma el **Excel de rendición** (formato Presmed), lo **balancea** y lo
**valida contra todas las reglas del instructivo de la Superintendencia de Servicios de Salud**
(Mecanismo Integración – Rendición DR.DEVOLUCION) antes de cargarlo en Presmed.

```
Excel (Presmed) ──► Balidaf ──► Excel balanceado (limpio) ──► Presmed ──► DR.DEVOLUCION.txt ──► FTP SSS
                                                                                   │
                         Balidaf «Devolución SSS» ◄── DEVOLUCION_OK.txt / DEVOLUCION_ERR.txt
```

## Qué hace

| Paso | Detalle |
|---|---|
| **Agrupa** | Por **CUIL + período de presentación + período de prestación + código de práctica** (la clave de la regla 624). Ya no hace falta la columna `CONCATENAR`. |
| **Balancea** | Reparte el subsidio de cada grupo entre sus líneas sin superar lo solicitado. Primero cubre las líneas **con retenciones**, para que el transferido nunca quede negativo. |
| **Ajusta retenciones** | Si el subsidio no alcanza para cubrir las retenciones de una línea, las reduce (ganancias → IIBB → otras) y el transferido queda en 0. |
| **Valida** | Todas las reglas del Anexo III: 600, 601, 605, 606, 607, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 621, **622, 623, 624** y 625. Además, controles propios (B01–B06). |
| **Guarda** | `<archivo>_balidaf.xlsx`: **solo cambia valores**, sin colores, formatos, fórmulas ni hojas nuevas. Listo para Presmed. |
| **Cruza la devolución** | Cargando los TXT `_ERR` / `_OK` de la SSS, muestra cada rechazo, su descripción y si el balanceo lo corrige. |

### Columnas que Balidaf puede modificar

`impor_apli_sss`, `importe_transferido`, `fdo_ppio_ingre_cta_disca` y, solo cuando el subsidio no alcanza,
`retencion_ganancias` / `retencion_IIBB` / `otras_retnciones`.
**Nunca** modifica los campos 2 a 9 (RNOS, tipo, períodos, CUIL, práctica, subsidiado, solicitado), que la
SSS exige idénticos al DR.ENVIO (error 602). Tampoco modifica CUIT, CBU, órdenes de pago ni fechas.

Las fórmulas 623 y 624 también tienen en cuenta `fdo_ppio_otras_ctas`, `reversion_import_trasl`,
`import_devuelto_cta_sss`, `saldo_no_apli` y `recup_fdos_ppios` si tienen valores.

## Pantallas

| Pestaña | Contenido |
|---|---|
| **Resumen** | Indicadores (líneas, grupos, cambios, errores antes/después) y tabla de **todas las reglas de la SSS** con su resultado. |
| **Validación SSS** | Cada hallazgo con fila, clave, CUIL, código y detalle. Filtros por código, nivel y búsqueda. Se puede ver el Excel original o el balanceado. |
| **Excel resultante** | El Excel completo, tal como se va a guardar. Colores **solo en pantalla** (modificada / retención reducida / error / advertencia). Doble clic: detalle de la línea y de su grupo. |
| **Devolución SSS** | Carga de los TXT `_ERR` y `_OK`, resumen por código de error y estado de cada línea rechazada. |
| **Registro** | Bitácora del proceso, con colores; se puede guardar en .txt. |

**Exportar informe…** genera un Excel **aparte** (no es el de Presmed) con las hojas Resumen, Cambios
(antes/después), Validación y Devolución SSS.

## Estructura del proyecto

```
Balidaf/
├── main.py                 ← punto de entrada (F5 en VS Code)
├── balidaf/
│   ├── schema.py           ← columnas del Excel y códigos de error de la SSS (Anexo IV)
│   ├── montos.py           ← importes exactos en centavos (sin errores de redondeo)
│   ├── excel_io.py         ← lectura y escritura del Excel (sin agregar formatos)
│   ├── balanceo.py         ← algoritmo de balanceo por grupo
│   ├── validacion.py       ← todas las validaciones del Anexo III
│   ├── sss_txt.py          ← lectura de los TXT DR.DEVOLUCION / _OK / _ERR
│   ├── devolucion.py       ← cruce de la devolución SSS con el Excel
│   ├── proceso.py          ← orquesta todo (GUI y consola)
│   ├── informe.py          ← informe de detalle (Excel aparte)
│   └── gui/                ← interfaz (app.py, tabs.py, widgets.py)
├── docs/ANALISIS_202606.md ← análisis de la rendición 202606 que originó esta versión
├── tests/                  ← pruebas automáticas (pytest)
├── scripts/
│   ├── generar_ejemplo.py  ← Excel de prueba con datos FICTICIOS
│   └── build_exe.bat       ← compila dist\Balidaf.exe
├── assets/balidaf.ico
└── Balidaf.spec            ← configuración de PyInstaller
```

## Puesta en marcha (Windows + VS Code)

1. `Ctrl+Shift+P` → **Git: Clone** → `MatiasNic/Balidaf`.
2. `Ctrl+Shift+P` → **Python: Create Environment** → **Venv** → Python 3.13 → tildar `requirements-dev.txt`.
3. `Ctrl+Shift+D` → **Balidaf: GUI (main.py)** → **F5**.

## Uso por consola

```bat
python main.py archivo.xlsx
python main.py archivo.xlsx --err 900805-202606_DR.DEVOLUCION_ERR.txt --ok 900805-202606_DR.DEVOLUCION_OK.txt --informe
```

Código de salida: `0` = listo para Presmed, `3` = quedan errores, `1` = no se pudo procesar.

## Pruebas

```bat
python -m pytest -v
```

## Compilar el ejecutable

```bat
scripts\build_exe.bat
```

> ⚠️ No subir al repositorio Excel ni TXT reales: contienen datos personales (CUIL, CBU).
> La carpeta `data/` y los archivos `*.txt` / `*.xlsx` de trabajo están excluidos en `.gitignore`.
