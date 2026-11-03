# Balidaf – Balanceo de subsidios - IDAF

Programa de escritorio que toma el **Excel de rendición** (formato Presmed), lo **balancea** y lo
**valida contra todas las reglas del instructivo de la Superintendencia de Servicios de Salud**
(Mecanismo Integración – Rendición DR.DEVOLUCION) antes de cargarlo en Presmed.

```
Excel (Presmed) ──► Balidaf ──► Excel balanceado (limpio) ──► Presmed ──► DR.DEVOLUCION.txt ──► FTP SSS
                                                                                   │
                         Balidaf «Devolución SSS» ◄── DEVOLUCION_OK.txt / DEVOLUCION_ERR.txt
```

## Cómo se usa (el programa propone, vos decidís)

**Pestaña «1 · Balancear»**

1. **Paso 1:** «Examinar…» → elegí el Excel **original** de Presmed → **«Analizar»**.
   Un panel azul muestra el avance: *Leer el Excel › Revisar reglas › Calcular la corrección › Validar*.
2. **Paso 2:** aparece la lista de **correcciones propuestas** (una fila por grupo). **Todavía no se aplicó nada.**
   Al hacer clic en un grupo, abajo se ve cada línea con el **original → corregido**.
   - **«Aplicar todas»** o seleccioná algunas (Ctrl / Shift) y **«Aplicar seleccionadas»**.
   - **«Deshacer seleccionadas»** vuelve esos grupos a los valores originales.
3. **Paso 3:** **«Guardar Excel para Presmed»** → genera `<archivo>_balidaf.xlsx` con lo aplicado
   (sin colores ni hojas nuevas). El original no se toca.

**Pestaña «2 · Devolución SSS»** (cuando la SSS rechaza líneas)

1. Analizá el Excel original en «1 · Balancear».
2. **«Cargar TXT de errores (_ERR)»** (y, si querés, el `_OK`).
3. Para cada línea rechazada se ve: el error de la SSS y su descripción, el **estado** y la
   **corrección propuesta (original → corregido)**. Estados:
   - *Corrección propuesta (sin aplicar)*: Balidaf sabe corregirla; vos decidís.
   - *Corrección aplicada*: ya la aplicaste.
   - *Requiere corrección manual*: hay que corregir un dato en el Excel (columna «Qué falta»).
   - *Lo resuelve Sistemas / Presmed*: por ejemplo 604 / 699.
4. **«Corregir seleccionadas en el Excel»** o **«Corregir todas las que tienen propuesta»**, y después guardás en «1 · Balancear».

> Si corregís **sólo** los grupos rechazados, pueden quedar diferencias de centavos en líneas que la SSS
> aceptó (las tolera). Aplicando **todas** las correcciones el Excel queda exacto.

**Pestaña «Ver Excel»:** el Excel completo con los valores actuales; colores sólo en pantalla
(pendiente / corregida / retenciones reducidas / error). Doble clic: detalle de la línea y su grupo.

**Pestaña «Reglas de balanceo»:** la lógica completa con los nombres de las columnas y todos los controles de la SSS.

## Qué hace el balanceo

| Paso | Detalle |
|---|---|
| **Agrupa** | Por **CUIL + período de presentación + período de prestación + código de práctica** (regla 624). No hace falta `CONCATENAR`. |
| **Reparte** | El subsidio del grupo entre sus líneas, sin superar lo solicitado; primero las líneas **con retenciones** (el transferido nunca queda negativo). |
| **Ajusta retenciones** | Si el subsidio no alcanza para cubrirlas, las reduce (ganancias → IIBB → otras) y el transferido queda en 0. |
| **No toca** | Los grupos que ya cumplen las reglas 622, 623 y 624. |
| **Valida** | Todas las reglas del Anexo III (600–625) + controles propios (B01–B06). |

### Columnas que Balidaf puede modificar

`impor_apli_sss`, `importe_transferido`, `fdo_ppio_ingre_cta_disca` y, solo cuando el subsidio no alcanza,
`retencion_ganancias` / `retencion_IIBB` / `otras_retnciones`.
**Nunca** modifica los campos 2 a 9 (RNOS, tipo, períodos, CUIL, práctica, subsidiado, solicitado), CUIT, CBU,
órdenes de pago ni fechas.

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
│   └── gui/                ← interfaz: app.py (ventana), tabs.py (pestañas), widgets.py
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
python main.py archivo.xlsx            :: analiza, aplica todas las correcciones y guarda
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
