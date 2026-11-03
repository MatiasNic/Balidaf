# Balidaf · Brief de diseño (para Claude Design)

> Todas las capturas usan **datos ficticios** (CUIL, CBU e importes inventados).

## 1. Qué es Balidaf

Balidaf es una aplicación de escritorio (Windows) que usa el área de discapacidad de una obra social para la
**rendición de subsidios ante la Superintendencia de Servicios de Salud (SSS)**, dentro del *Mecanismo Integración*.

Circuito real de trabajo:

```
Excel de Presmed ─► BALIDAF (analiza, propone y aplica correcciones) ─► Excel balanceado ─► Presmed ─► TXT ─► FTP de la SSS
                                                                                                          │
              BALIDAF «Devolución SSS» ◄── TXT de aceptados (_OK) / TXT de rechazados con código de error (_ERR)
```

- El Excel tiene **~16.000 líneas** y **39 columnas** (una línea = una prestación pagada a un prestador por un beneficiario).
- La SSS exige que los importes cierren **exacto** según reglas (aplicado, transferido, retenciones, fondos propios,
  subsidio por grupo). Si no cierran, **rechaza** las líneas con un código de error.
- Balidaf **calcula la corrección, la muestra y el usuario decide** qué aplicar. Recién al guardar se escribe el Excel.

## 2. Usuarios

- Personal administrativo / contable del área de discapacidad. No son técnicos.
- Trabajan con archivos grandes, con cuidado y bajo plazos de presentación: **necesitan confianza y control**
  (ver antes de aplicar, poder deshacer, saber siempre qué está pasando).
- Usan la app en monitores de oficina (1366×768 a 1920×1080). Idioma: **español (Argentina)**.

## 3. Qué pedimos del diseño

- **Profesional, organizado, dinámico y amigable.** Que se entienda el próximo paso sin leer un manual.
- **Diseño original**, no una plantilla genérica.
- **Colores sobrios**, nada chillón. Los colores semánticos (ok / error / advertencia / pendiente) tienen que ser
  suaves y legibles, también en tablas largas.
- **Modo claro y modo oscuro**, con un **ícono para cambiar en el margen superior derecho** (hoy: ☾ / ☀).
- **La información se muestra completa** (los usuarios la quieren ver), pero **bien organizada**: filtros simples
  arriba de las tablas, orden por columna, detalle abajo. *Nada de paneles laterales que ocupen mucho espacio.*
- **El progreso tiene que estar integrado en la ventana** (no un pop-up): pasos, barra y porcentaje.
- Tablas densas pero cómodas: números alineados a la derecha, formato argentino (`1.234.567,89`), filas con
  estado de color tenue, encabezados ordenables con ▲/▼.
- Pensar estados vacíos, carga, éxito, error, y confirmaciones antes de cambiar datos.

## 4. Estructura actual de la ventana

```
┌ Encabezado: «Balidaf · Balanceo de subsidios · Rendición Mecanismo Integración (SSSalud)»        [☾/☀] ┐
├ Barra de progreso FIJA: estado · barra · % · pasos (✔ hecho ▶ en curso ○ pendiente) · detalle            ┤
├ Pestañas: [1 · Balancear] [2 · Devolución SSS] [Ver Excel] [Reglas de balanceo]                          ┤
│  contenido de la pestaña                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 5. Pantallas (capturas en `imagenes/claro` e `imagenes/oscuro`)

| # | Archivo | Pantalla / estado |
|---|---|---|
| 01 | `01_inicio.png` | Inicio: todavía no se analizó nada. |
| 02 | `02_devolucion_sin_datos.png` | Devolución SSS sin TXT cargado. |
| 03 | `03_ver_excel_sin_datos.png` | Ver Excel sin datos. |
| 04 | `04_analizando_progreso.png` | **Analizando**: barra de progreso con pasos (botones bloqueados). |
| 05 | `05_balancear_correcciones_propuestas.png` | Resultado del análisis: errores, correcciones propuestas (sin aplicar). |
| 06 | `06_balancear_detalle_de_grupo.png` | Un grupo seleccionado: detalle línea por línea *original → corregido*. |
| 07 | `07_balancear_filtro_tipo_y_orden.png` | Filtro por tipo de corrección + orden por «Diferencia» + selección múltiple. |
| 08 | `08_devolucion_cruce_y_detalle.png` | TXT de rechazos cruzado con el Excel; caja con explicación de la línea. |
| 09 | `09_devolucion_requiere_correccion_manual.png` | Filtro «Requiere corrección manual» (p. ej. falta el CUIT). |
| 10 | `10_balancear_correcciones_aplicadas.png` | Lista de correcciones ya aplicadas (se pueden deshacer). |
| 11 | `11_balancear_todo_aplicado.png` | Todo aplicado; quedan errores que hay que corregir a mano. |
| 12 | `12_devolucion_luego_de_aplicar.png` | Devolución luego de aplicar: estados «Corrección aplicada». |
| 13 | `13_ver_excel_importes_clave.png` | Excel resultante, vista «Importes y datos clave». |
| 14 | `14_ver_excel_todas_las_columnas.png` | Excel resultante, las 39 columnas. |
| 15 | `15_ver_excel_filtro_con_errores.png` | Excel filtrado «Con errores». |
| 16 | `16_detalle_de_linea.png` | Ventana de detalle de una línea (importes, grupo, validaciones). |
| 17 | `17_reglas_de_balanceo.png` | Pestaña de reglas (lógica con nombres de columnas). |
| 18 | `18_reglas_controles_sss.png` | Lista de todos los controles de la SSS. |

### 5.1 Pestaña «1 · Balancear» (pantalla principal)

1. **Paso 1** – Ruta del Excel · botón *Examinar…* · botón principal **Analizar**.
2. **Aviso de estado** (una frase con el próximo paso). Tipos: neutro, info, ok, advertencia, error.
3. **4 indicadores**: *Errores en el Excel (ahora)* · *Correcciones pendientes* · *Correcciones aplicadas* ·
   *Errores que NO se corrigen solos*.
4. **Paso 2** – Filtros en una línea: **Estado** (Pendientes / Aplicadas / Todas, con cantidad) ·
   **Tipo de corrección** (con cantidad) · **Buscar CUIL o clave**.
   Acciones: **Aplicar seleccionadas** · **Aplicar todas las de la lista (N)** · **Deshacer seleccionadas**.
   Resumen: *N grupos · N líneas · diferencia en aplicado*.
5. **Tabla de grupos** (una fila = un grupo CUIL + períodos + práctica): Estado · Tipo de corrección · CUIL ·
   Práctica · Prestación · Líneas · Subsidio · Aplicado original · Aplicado corregido · Diferencia · Errores SSS.
6. **Detalle del grupo** (abajo): por línea → Fila · Clave · Solicitado · Retenciones · Aplicado · Transferido ·
   Fondos propios, cada importe como *original → corregido*.
7. **Paso 3** (siempre visible abajo): **Guardar Excel para Presmed** (acción principal final) ·
   *Exportar informe (opcional)*.

### 5.2 Pestaña «2 · Devolución SSS»

- Guía: *1 · Analizá el Excel › 2 · Cargá el TXT de errores › 3 · Revisá y decidí qué corregir*.
- Botones: **Cargar TXT de errores (_ERR)** · Cargar TXT aceptados (_OK) (opcional) · nombre de archivos cargados.
- Aviso de estado + **5 indicadores**: Líneas rechazadas · Con corrección propuesta · Corrección aplicada ·
  Requieren corrección manual · Las resuelve Sistemas.
- Filtros en una línea: **Estado** · **Error SSS** (604, 611, 623, 624, 699…) · buscador.
- Acciones: **Corregir seleccionadas en el Excel** · **Corregir todas las de la lista (N)** · **Deshacer**.
- Tabla: Clave · CUIL · Fila · Error SSS · Estado · Corrección propuesta (*original → corregido*) · Qué falta.
- **Caja de detalle** de la línea seleccionada: descripción oficial del error, acción sugerida, quién lo resuelve,
  corrección propuesta completa y qué falta.

### 5.3 Pestaña «Ver Excel»

- Filtro **Mostrar** (Todas / Con corrección pendiente / Corregidas / Con errores / Con advertencias /
  Con retenciones reducidas) · buscador · **Columnas** (Importes y datos clave / Todas las columnas).
- Leyenda de colores (sólo en pantalla; el Excel se guarda sin formato).
- Tabla con todas las líneas (miles) · doble clic → detalle de línea.

### 5.4 Pestaña «Reglas de balanceo»

Texto de referencia con la lógica completa (ver `LOGICA_DEL_PROGRAMA.md`) y la lista de controles de la SSS.

### 5.5 Ventana «Detalle de línea»

Importes de la línea (Original · Corrección propuesta · Actual), el grupo al que pertenece y las validaciones.

## 6. Estados y semántica de colores

| Concepto | Valores | Uso de color actual (tenue) |
|---|---|---|
| Estado de un grupo | **Pendiente** (propuesta sin aplicar) · **Aplicada** · Sin cambios | azul suave · amarillo suave · sin color |
| Tipo de corrección | Aplicado mayor al subsidio · Aplicado menor al subsidio · Fondos propios / reparto · Ajuste de centavos · Reduce retenciones · No se puede balancear | texto (sin color propio) |
| Estado en Devolución | Corrección propuesta (sin aplicar) · Corrección aplicada · Requiere corrección manual · Lo resuelve Sistemas / Presmed · Ya cumple las reglas · No está en el Excel | azul · verde · rojo · naranja · verde · gris |
| Nivel de validación | Error · Advertencia · Info | rojo · naranja · azul |
| Aviso | neutro · info · ok · advertencia · error | gris · azul · verde · naranja · rojo |

## 7. Volúmenes reales (para dimensionar el diseño)

- Excel: **15.912 líneas**, 39 columnas · **10.894 grupos**.
- Análisis: ~**15 segundos** (lectura del Excel ≈ 60 % del tiempo).
- Errores en el original: **10.021** · correcciones propuestas: **3.384 grupos**
  (1.848 ajuste de centavos · 1.263 aplicado mayor al subsidio · 235 aplicado menor · 37 reduce retenciones · 1 otros).
- TXT de rechazos de la SSS: **2.775 líneas** (624: 2.772 · 623: 416 · 611: 2 · 604/699: 1).

## 8. Restricciones técnicas

- Hoy: **Python + Tkinter/ttk** (escritorio Windows; se distribuye como `.exe`). El diseño debería poder
  implementarse con widgets de escritorio (tablas, listas desplegables, botones, pestañas, barra de progreso).
  Si el diseño propone otra tecnología (p. ej. web local), indicarlo como opción.
- El **Excel de salida no lleva formato** (lo consume Presmed): los colores son sólo de la interfaz.
- Las tareas largas corren en segundo plano: la UI debe mostrar progreso y bloquear acciones mientras tanto.
- Toda modificación de datos pide **confirmación** y se puede **deshacer** hasta guardar.

## 9. Entregables esperados de Claude Design

1. **Sistema visual**: paletas claro/oscuro (sobrias), tipografía, espaciado, estilos de tabla, botones (primario /
   secundario / peligro), indicadores, avisos, chips de estado.
2. **Pantallas**: Balancear (vacío · analizando · propuesta · todo aplicado), Devolución SSS (vacío · cruce ·
   corrección manual), Ver Excel, Reglas, Detalle de línea, diálogos de confirmación (aplicar / deshacer / guardar).
3. **Barra de progreso integrada** y el **toggle claro/oscuro** arriba a la derecha.
4. Propuesta de **jerarquía y flujo** (Paso 1 → 2 → 3) que guíe sin saturar.

### Prompt sugerido

> Diseñá la interfaz de escritorio de «Balidaf», una herramienta para que personal administrativo balancee y valide
> la rendición de subsidios por discapacidad ante la Superintendencia de Servicios de Salud (Argentina). Adjunto el
> brief, la lógica del programa y capturas de la versión actual en modo claro y oscuro. Quiero un diseño
> profesional, organizado, dinámico y amigable, original, con colores sobrios (sin tonos chillones), modo claro y
> oscuro con un ícono en la esquina superior derecha, barra de progreso integrada en la ventana, filtros simples
> arriba de las tablas y toda la información visible pero bien jerarquizada. Respetá el flujo Paso 1 (Analizar) →
> Paso 2 (revisar y aplicar correcciones, con deshacer) → Paso 3 (Guardar Excel para Presmed), y la pestaña de
> Devolución SSS donde se cruzan los rechazos y el usuario decide qué corregir.
