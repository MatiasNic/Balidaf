# Análisis de la rendición 202606 (RNOS 900805)

Archivos analizados: Excel original (sin balancear), `DR.DEVOLUCION.txt` generado por Presmed,
devolución de la SSS (`_OK` y `_ERR`) y el archivo final aceptado luego de la corrección manual (`_OK_2`).
Referencia: instructivo SSS "Mecanismo Integración – Rendición" (actualizado al 10/09/2024).

## 1. Resultado de la presentación original

| | Líneas |
|---|---|
| Total enviadas | 15.912 (10.894 grupos CUIL + períodos + práctica) |
| Aceptadas (`_OK`) | 13.138 |
| Rechazadas (`_ERR`) | 2.774 |

| Código | Líneas | Causa encontrada |
|---|---|---|
| 624 | 2.357 | La suma de lo aplicado no coincide con el subsidio del grupo: en 1.261 grupos se aplicó **más** que el subsidio (se aplicó todo lo solicitado) y en 214, **menos**. |
| 623 + 624 | 413 | Lo mismo, y además `fdo_ppio_ingre_cta_disca` vacío. |
| 623 | 1 | `fdo_ppio_ingre_cta_disca` vacío (faltaban $2.085.547,92). |
| 611 + 623 + 624 | 2 | Línea sin CUIT ni CBU. |
| 604 / 699 | 1 | Diseño de registro / clave: lo resuelve Sistemas. |

**Causa raíz:** el Excel cargado en Presmed no había pasado por el balanceo (la columna de fondos propios estaba vacía
y el aplicado era igual al solicitado aun cuando el subsidio era menor).

## 2. Cómo se corrigió manualmente (`_OK_2`)

- Cumple **exacto** (sin centavos de diferencia) las reglas 622, 623 y 624.
- Usa las mismas fórmulas que Balidaf: aplicado ≤ solicitado, transferido = aplicado − retenciones,
  fondos propios = solicitado − aplicado.
- Dos criterios que la versión anterior de Balidaf no tenía:
  1. **Nunca dejar transferido negativo**: se cubren primero las líneas con retenciones
     (la versión anterior lo habría dejado negativo en 14 líneas).
  2. **Reducir retenciones** cuando el subsidio no alcanza (45 líneas): el transferido queda en 0.
- También se corrigieron 2.433 líneas aceptadas con diferencias de centavos.

## 3. Tolerancia observada en la SSS

La SSS aceptó diferencias de hasta $18,48 y rechazó desde $20,20, pero esa tolerancia **no está en el
instructivo**. Balidaf valida **exacto** (por eso informa más "errores" que la SSS en el Excel original:
10.021 contra 2.774); es el criterio seguro.

## 4. Validaciones calibradas con los datos reales

- Dígito verificador de CUIT y de CBU: coinciden en el 100 % de los 7.980 CUIT y CBU aceptados.
- Las 466 líneas sin pago (todo en 0, CUIT `00020010500`, CBU `0`) fueron aceptadas: el prefijo y el dígito
  verificador del CUIT solo se exigen cuando hay transferencia. CBU `0` o vacío se considera nulo.
- 33 líneas sin CBU recibieron subsidio en la versión final y fueron aceptadas (el CBU puede ser nulo),
  pero se completó el CUIT del prestador.

## 5. Resultado de Balidaf 2.0 sobre el Excel original

| | |
|---|---|
| Errores antes del balanceo | 10.021 (623: 3.540 · 624: 6.481) |
| Grupos balanceados / líneas modificadas | 3.384 / 4.410 |
| Líneas con retenciones reducidas | 39 |
| Errores después del balanceo | **0** |
| Coincidencia con el archivo aceptado por la SSS (`_OK_2`) | **99 %** de las líneas idénticas |
| Rechazos de la SSS que quedan corregidos | 2.773 de 2.775 (los 2 restantes: 604/699, Sistemas) |
| Celdas con formato modificado / hojas agregadas | 0 / 0 |

El 1 % restante son grupos con varias líneas donde el subsidio se reparte en otro orden; ambas
distribuciones cumplen las reglas de la SSS.
