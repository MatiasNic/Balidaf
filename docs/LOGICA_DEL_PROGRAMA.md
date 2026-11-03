# Balidaf · Funcionamiento y lógica del programa

## 1. Flujo general (el programa propone, el usuario decide)

1. **Analizar** (pestaña «1 · Balancear»)
   1. Lee la primera hoja del Excel de Presmed (39 columnas, una línea por prestación).
   2. Revisa **todas las reglas de la SSS** sobre el Excel original → cantidad de errores.
   3. **Calcula la corrección** de cada grupo, **sin aplicarla**.
   4. Valida cómo quedaría si se aplicara todo → «errores que NO se corrigen solos».
2. **Revisar y aplicar**: el usuario filtra, ordena, mira el detalle *original → corregido* y aplica todas,
   algunas (selección) o las de un tipo; puede **deshacer** hasta guardar. Tras cada cambio se revalida.
3. **Guardar Excel para Presmed**: genera `<archivo>_balidaf.xlsx` con lo aplicado. Sólo cambian valores: sin
   colores, formatos, fórmulas ni hojas nuevas. El original no se modifica.
4. **Devolución SSS** (cuando la SSS rechaza): se cargan los TXT `_ERR` (y opcional `_OK`), se cruzan por
   `clave_rendicion` con el Excel analizado y para cada rechazo se muestra la corrección propuesta y su estado.
   El usuario decide «Corregir seleccionadas / todas las de la lista» o «Deshacer». Luego guarda en el Paso 3.

## 2. Columnas

| Uso | Columnas del Excel |
|---|---|
| **Lee** | `clave_rendicion`, `cuil`, `cod_prestac`, `periodo_presentacion`, `perio_prestac`, `importe_subsidiado`, `importe_solicitado`, `retencion_ganancias`, `retencion_IIBB`, `otras_retnciones`, `fdo_ppio_otras_ctas`, `reversion_import_trasl`, `import_devuelto_cta_sss`, `saldo_no_apli`, `recup_fdos_ppios` |
| **Puede modificar** | `impor_apli_sss`, `importe_transferido`, `fdo_ppio_ingre_cta_disca`; y `retencion_ganancias` / `retencion_IIBB` / `otras_retnciones` **sólo** si el subsidio no alcanza a cubrirlas |
| **Nunca modifica** | Campos 2 a 9 de la SSS (`rnos`, `tipo_archi`, `periodo_presentacion`, `perio_prestac`, `cuil`, `cod_prestac`, `importe_subsidiado`, `importe_solicitado`), CUIT, CBU, órdenes de pago, fechas, cheque, recibo, observaciones |

## 3. Grupo

```
GRUPO = cuil + periodo_presentacion + perio_prestac + cod_prestac      (regla 624 de la SSS)
```
El subsidio se informa en una línea del grupo y se reparte entre todas sus líneas.

## 4. Cálculo de la corrección de un grupo

```
SUBSIDIO   = Σ importe_subsidiado del grupo
A_APLICAR  = SUBSIDIO − Σ (reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)

Por línea:
  OTROS        = fdo_ppio_otras_ctas + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios
  TOPE         = importe_solicitado − OTROS
  RETENCIONES  = retencion_ganancias + retencion_IIBB + otras_retnciones

Orden de reparto: primero las líneas CON retenciones (el transferido nunca queda negativo), luego el resto.

  impor_apli_sss            = mínimo entre TOPE y lo que queda de A_APLICAR
  si RETENCIONES > impor_apli_sss → se reducen ganancias → IIBB → otras hasta igualar (transferido = 0)
  importe_transferido       = impor_apli_sss − RETENCIONES
  fdo_ppio_ingre_cta_disca  = importe_solicitado − impor_apli_sss − OTROS
```

- Si el grupo **ya cumple** 622, 623 y 624 sin negativos → **no se toca**.
- Si el subsidio supera lo aplicable (Σ TOPE) → **no se puede balancear** (error B02, revisión manual).
- Todo se calcula en **centavos exactos**.

**Ejemplo:** subsidio 1.010.735,49 · solicitado 1.364.492,91 · retenciones 27.289,86 + 27.289,86
→ original: aplicado 1.364.492,91 / transferido 1.309.913,19 / fondos propios 0 (error 624)
→ corregido: aplicado 1.010.735,49 / transferido 956.155,77 / fondos propios 353.757,42 ✔

## 5. Tipo de corrección (para filtrar)

| Tipo | Cuándo |
|---|---|
| Aplicado mayor al subsidio | Se había aplicado más que el subsidio del grupo |
| Aplicado menor al subsidio | Se había aplicado menos que el subsidio |
| Fondos propios / reparto | El total estaba bien pero faltaban fondos propios o el reparto entre líneas |
| Ajuste de centavos | Ningún importe cambia más de $1 |
| Reduce retenciones | El subsidio no alcanza para cubrir las retenciones de alguna línea |
| No se puede balancear | El subsidio es mayor a lo que se puede aplicar |

## 6. Reglas que debe cumplir el resultado (SSS)

```
622  impor_apli_sss = importe_transferido + retencion_ganancias + retencion_IIBB + otras_retnciones
623  importe_solicitado = fdo_ppio_ingre_cta_disca + fdo_ppio_otras_ctas + impor_apli_sss + reversion_import_trasl
                          + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios      (no aplica a tipo DB)
624  por GRUPO: Σ importe_subsidiado = Σ (impor_apli_sss + reversion_import_trasl + import_devuelto_cta_sss
                                          + saldo_no_apli + recup_fdos_ppios)
```

## 7. Todos los controles (instructivo SSS, Anexos III y IV)

| Código | Control | Lo resuelve |
|---|---|---|
| 600 | RNOS numérico de 6 dígitos / coincide con el archivo | Sistemas |
| 601 | Período de presentación válido (AAAAMM) | Sistemas |
| 602 | Campos 2 a 9 iguales al DR.ENVIO (Balidaf nunca los cambia) | Sistemas · se ve en la devolución |
| 603 / 604 | Clave inexistente / faltante respecto del DR.ENVIO | Sistemas · se ve en la devolución |
| 605 | Clave de 11 dígitos | Manual |
| 606 | Clave duplicada | Manual |
| 607 | Nro. envío AFIP | Sistemas |
| 609 | Tipo de archivo DS / DB / DC | Manual |
| 610 | Importes numéricos 10,2, no negativos | Manual |
| 611 / 612 / 613 | CUIT del CBU: 11 dígitos · prefijo · dígito verificador (612/613 sólo si hay transferencia) | Manual |
| 614 | CBU de 22 dígitos o nulo | Manual |
| 615 | Órdenes de pago hasta 20 caracteres | Manual |
| 616 / 617 | Fechas DD/MM/AAAA válidas y ≥ período de presentación | Manual |
| 618 / 619 | Cheque (≤10) / recibo (≤8) numéricos | Manual |
| 621 | Si hay importe devuelto, CUIT/CBU de la SSS | Manual |
| **622 / 623 / 624** | Fórmulas de importes (ver arriba) | **Balanceo** |
| 625 | Observaciones hasta 150 caracteres | Manual |
| 699 | Diseño de registro del TXT | Sistemas · se ve en la devolución |
| B01–B06 | Controles propios: columna faltante, no balanceable, retenciones reducidas, dígito del CBU, redondeo, datos distintos al resto | — |

## 8. Estados

- **Grupo**: Pendiente (propuesta sin aplicar) · Aplicada · Sin cambios.
- **Línea rechazada (Devolución)**: Corrección propuesta (sin aplicar) · Corrección aplicada · Requiere corrección
  manual · Lo resuelve Sistemas / Presmed · Ya cumple las reglas en el Excel · No está en el Excel.
- **Validación**: Error · Advertencia · Info.

## 9. Archivos

- Entrada: Excel de Presmed (`.xlsx`), TXT de la SSS `######-AAAAMM_DR.DEVOLUCION_ERR.txt` / `_OK.txt`.
- Salida: `<archivo>_balidaf.xlsx` (para Presmed) y, opcional, `<archivo>_informe_balidaf.xlsx`
  (Resumen, Cambios antes/después, Validación, Devolución SSS).
