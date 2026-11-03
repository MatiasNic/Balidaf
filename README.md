# Balidaf – Balanceo de subsidios - IDAF

Aplicación de escritorio (Tkinter + openpyxl) que toma un Excel, agrupa las líneas por socio
(`CONCATENAR`) y distribuye el subsidio de cada socio entre sus líneas, calculando:

| Columna de salida            | Cálculo                                                           |
|------------------------------|-------------------------------------------------------------------|
| `impor_apli_sss`             | `min(IMPORTE_SOLICITADO, subsidio restante del socio)` (0 si no queda) |
| `importe_transferido`        | `impor_apli_sss − (RET_GANANCIAS + RET_IIBB + OTRAS_RETENCIONES)` |
| `fdo_ppio_ingre_cta_disca`   | `abs(importe_transferido + retenciones − IMPORTE_SOLICITADO)`      |

- Trabaja sobre la **primera hoja** del Excel; detecta columnas por encabezado (con alias flexibles).
- Solo escribe en las 3 columnas de salida (las crea si no existen) y agrega una hoja **LOG** con el detalle por línea.
- Guarda el resultado como `<archivo>_balidaf.xlsx` junto al original.

## Estructura del proyecto

```
Balidaf/
├── main.py                  ← punto de entrada (F5 en VS Code)
├── balidaf/                 ← paquete de la aplicación
│   ├── __main__.py          ← CLI / arranque de la GUI
│   ├── gui.py               ← interfaz Tkinter
│   ├── core.py              ← lógica de balanceo (sin UI) + process_file()
│   ├── columns.py           ← alias y detección de columnas
│   ├── parsing.py           ← conversión de valores (to_float)
│   └── paths.py             ← rutas de recursos y log de errores
├── assets/balidaf.ico       ← ícono de la ventana / del .exe
├── tests/                   ← pruebas (pytest), incluye paridad con la versión original
├── scripts/
│   ├── generar_ejemplo.py   ← crea un Excel de prueba con datos ficticios
│   └── build_exe.bat        ← compila dist\Balidaf.exe
├── legacy/                  ← código original sin modificar (referencia para comparar)
├── Balidaf.spec             ← configuración de PyInstaller
├── requirements.txt         ← dependencias de ejecución
└── requirements-dev.txt     ← + pytest y pyinstaller
```

## Puesta en marcha (Windows + VS Code)

1. Clonar el repositorio y abrir la carpeta en VS Code.
2. Crear el entorno virtual e instalar dependencias (terminal de VS Code):

   ```bat
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

3. `Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv`.
4. Pestaña **Run and Debug** (`Ctrl+Shift+D`) y elegir una configuración:
   - **Balidaf: GUI (main.py)** – abre la ventana (equivale al .exe).
   - **Balidaf: procesar ejemplo (sin GUI)** – genera `data/ejemplo.xlsx` y lo procesa por consola.
   - **Balidaf: procesar archivo elegido (sin GUI)** – pide una ruta y la procesa.

## Uso por línea de comandos

```bat
python main.py                          :: interfaz gráfica
python main.py archivo.xlsx             :: procesa sin GUI → archivo_balidaf.xlsx
python main.py archivo.xlsx -o out.xlsx :: salida personalizada
```

## Pruebas

```bat
python -m pytest -v
```

`tests/test_core.py` ejecuta tanto la versión nueva como `legacy/Balidaf.py` sobre los mismos datos y
verifica que el Excel resultante sea idéntico. Sirve de red de seguridad durante las optimizaciones.

## Compilar el ejecutable

```bat
scripts\build_exe.bat
```

Genera `dist\Balidaf.exe` (carpetas `build/` y `dist/` están en `.gitignore`).
