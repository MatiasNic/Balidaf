"""
Validaciones de la SSS (Anexo III del instructivo) aplicadas sobre el Excel.

Cada problema se informa como un ``Hallazgo`` con el código de rechazo de la SSS (Anexo IV)
o un código interno de Balidaf (B01…B06).

Notas sobre cómo valida la SSS (verificado con las devoluciones reales):
- CUIT del CBU: el prefijo (612) y el dígito verificador (613) sólo se exigen cuando la línea
  tiene transferencia (importe transferido > 0). Las líneas sin pago con CUIT "00020010500" se aceptan.
- CBU "0" o vacío se considera nulo (permitido).
- 602, 603, 604 y 699 no se pueden validar sólo con el Excel (dependen de DR.ENVIO / del TXT):
  se ven al cargar la devolución de la SSS.
"""

import datetime as dt
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from .excel_io import Linea, periodo_aaaamm
from .montos import fmt
from .schema import (CBU_SSS, CODIGOS, COL, CUIT_SSS, IMPORTES, MAX_IMPORTE_CENTAVOS,
                     OTROS_DESTINOS_SOLICITADO, OTROS_DESTINOS_SUBSIDIO, PREFIJOS_CUIT,
                     TIPOS_ARCHIVO)

ERROR = "Error"
ADVERTENCIA = "Advertencia"
INFO = "Info"

ProgFn = Callable[[str, int, int], None]


@dataclass
class Hallazgo:
    codigo: str
    nivel: str
    fila: int            # fila del Excel (0 = general)
    clave: str
    cuil: str
    campo: str
    detalle: str

    @property
    def descripcion(self) -> str:
        c = CODIGOS.get(self.codigo)
        return c.descripcion if c else ""


# ------------------------------------------------------------------ utilidades
def cuit_valido(c: str) -> bool:
    if len(c) != 11 or not c.isdigit():
        return False
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    r = 11 - sum(int(a) * b for a, b in zip(c[:10], pesos)) % 11
    dv = 0 if r == 11 else (9 if r == 10 else r)
    return dv == int(c[10])


def cbu_digitos_ok(c: str) -> bool:
    b1, b2 = c[:8], c[8:]
    s1 = sum(int(a) * b for a, b in zip(b1[:7], (7, 1, 3, 9, 7, 1, 3)))
    s2 = sum(int(a) * b for a, b in zip(b2[:13], (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)))
    return (10 - s1 % 10) % 10 == int(b1[7]) and (10 - s2 % 10) % 10 == int(b2[13])


def _es_nulo(v: str) -> bool:
    return v.strip() in ("", "0")


def _fecha(v) -> Optional[dt.date]:
    """None si es nula; levanta ValueError si es inválida."""
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    if s in ("", "0"):
        return None
    return dt.datetime.strptime(s, "%d/%m/%Y").date()


# ------------------------------------------------------------------ validación
def validar(lineas: List[Linea], faltantes: Iterable[str] = (), progreso: Optional[ProgFn] = None) -> List[Hallazgo]:
    progreso = progreso or (lambda *a: None)
    H: List[Hallazgo] = []

    def add(cod, nivel, ln: Optional[Linea], campo, detalle):
        H.append(Hallazgo(cod, nivel, ln.fila if ln else 0, ln.clave if ln else "",
                          ln.cuil if ln else "", campo, detalle))

    for k in faltantes:
        add("B01", ERROR, None, COL[k].encabezado, f"No se encontró la columna '{COL[k].encabezado}'")
    if any(k in ("clave", "cuil", "cod", "per_pres", "per_prest", "subsidiado", "solicitado") for k in faltantes):
        return H

    # --- datos que deben ser iguales en todo el archivo (B06) ---
    for k in ("rnos", "per_pres", "nro_envio", "tipo"):
        cnt = Counter(ln.texto.get(k, "") for ln in lineas)
        if len(cnt) > 1:
            comun = cnt.most_common(1)[0][0]
            for ln in lineas:
                if ln.texto.get(k, "") != comun:
                    add("B06", ADVERTENCIA, ln, COL[k].encabezado,
                        f"'{ln.texto.get(k, '')}' distinto del resto ('{comun}')")

    claves = Counter(ln.clave for ln in lineas)
    total = len(lineas)

    for i, ln in enumerate(lineas):
        t, m = ln.texto, ln.monto

        # 605 / 606 clave
        if not (len(ln.clave) == 11 and ln.clave.isdigit()):
            add("605", ERROR, ln, "clave_rendicion", f"'{ln.clave}' no tiene 11 dígitos")
        if claves[ln.clave] > 1:
            add("606", ERROR, ln, "clave_rendicion", f"Clave repetida {claves[ln.clave]} veces")

        # 600 / 601 / 607 / 609 formato
        rnos = t.get("rnos", "")
        if rnos and not (len(rnos) == 6 and rnos.isdigit()):
            add("600", ERROR, ln, "rnos", f"'{rnos}' debe ser numérico de 6 dígitos")
        pp = periodo_aaaamm(ln.crudo.get("per_pres"))
        if not (len(pp) == 6 and pp.isdigit() and 1 <= int(pp[4:]) <= 12):
            add("601", ERROR, ln, "periodo_presentacion", f"'{pp}' no es un período AAAAMM válido")
        ne = t.get("nro_envio", "")
        if ne and not (len(ne) <= 4 and ne.isdigit()):
            add("607", ERROR, ln, "numero_envio_afip", f"'{ne}' debe ser numérico de 4 dígitos")
        tipo = t.get("tipo", "")
        if tipo and tipo not in TIPOS_ARCHIVO:
            add("609", ERROR, ln, "tipo_archi", f"'{tipo}' no es DS, DB ni DC")

        # 610 importes
        for k in IMPORTES:
            prob = ln.problemas_monto.get(k)
            if prob == "invalido":
                add("610", ERROR, ln, COL[k].encabezado, f"'{ln.crudo.get(k)}' no es numérico")
            elif prob == "redondeo":
                add("B05", INFO, ln, COL[k].encabezado, f"{ln.crudo.get(k)} → {fmt(ln.original[k])}")
            if m[k] < 0:
                add("610", ERROR, ln, COL[k].encabezado, f"Importe negativo ({fmt(m[k])})")
            elif m[k] > MAX_IMPORTE_CENTAVOS:
                add("610", ERROR, ln, COL[k].encabezado, f"Supera 10 enteros ({fmt(m[k])})")

        # 611 / 612 / 613 CUIT del CBU
        cuit = t.get("cuit_cbu", "")
        if not (len(cuit) == 11 and cuit.isdigit()):
            add("611", ERROR, ln, "cuit_CBU", f"'{cuit}' no es numérico de 11 posiciones")
        elif m["transferido"] > 0:
            if cuit[:2] not in PREFIJOS_CUIT:
                add("612", ERROR, ln, "cuit_CBU", f"Prefijo '{cuit[:2]}' inválido (línea con transferencia)")
            elif not cuit_valido(cuit):
                add("613", ERROR, ln, "cuit_CBU", f"Dígito verificador incorrecto en '{cuit}'")

        # 614 CBU
        cbu = t.get("cbu", "")
        if not _es_nulo(cbu):
            if not (len(cbu) == 22 and cbu.isdigit()):
                add("614", ERROR, ln, "cbu", f"'{cbu}' no es numérico de 22 posiciones")
            elif not cbu_digitos_ok(cbu):
                add("B04", ADVERTENCIA, ln, "cbu", f"Dígito verificador incorrecto en '{cbu}'")

        # 615 órdenes de pago
        for k in ("opg_1", "opg_2"):
            v = t.get(k, "")
            if len(v) > 20:
                add("615", ERROR, ln, COL[k].encabezado, f"Tiene {len(v)} caracteres (máx. 20)")

        # 616 / 617 fechas
        inicio_pres = None
        if len(pp) == 6 and pp.isdigit() and 1 <= int(pp[4:]) <= 12:
            inicio_pres = dt.date(int(pp[:4]), int(pp[4:]), 1)
        for k in ("fecha_1", "fecha_2"):
            try:
                f = _fecha(ln.crudo.get(k))
            except ValueError:
                add("616", ERROR, ln, COL[k].encabezado, f"'{t.get(k, '')}' no es una fecha DD/MM/AAAA válida")
                continue
            if f and inicio_pres and f < inicio_pres:
                add("617", ERROR, ln, COL[k].encabezado,
                    f"{f:%d/%m/%Y} es anterior al período de presentación {pp}")

        # 618 / 619
        ch = t.get("cheque", "")
        if ch and not (ch.isdigit() and len(ch) <= 10):
            add("618", ERROR, ln, "cheque", f"'{ch}' debe ser numérico de hasta 10 posiciones")
        rec = t.get("recibo", "")
        if rec and not (rec.isdigit() and len(rec) <= 8):
            add("619", ERROR, ln, "nro_recibo", f"'{rec}' debe ser numérico de hasta 8 posiciones")

        # 621 devuelto a la SSS
        if m["devuelto"] > 0 and (cuit != CUIT_SSS or cbu != CBU_SSS):
            add("621", ERROR, ln, "import_devuelto_cta_sss",
                f"Devuelto {fmt(m['devuelto'])}: CUIT/CBU deben ser {CUIT_SSS} / {CBU_SSS}")

        # 622 aplicado = transferido + retenciones
        suma622 = m["transferido"] + m["ret_gan"] + m["ret_iibb"] + m["ret_otras"]
        if m["apli"] != suma622:
            add("622", ERROR, ln, "impor_apli_sss",
                f"Aplicado {fmt(m['apli'])} ≠ transferido + retenciones {fmt(suma622)} (dif. {fmt(m['apli'] - suma622)})")

        # 623 solicitado = fdo propios + otros + aplicado (excepto DB)
        if tipo != "DB":
            suma623 = m["fdo_ppio"] + m["apli"] + sum(m[k] for k in OTROS_DESTINOS_SOLICITADO)
            if m["solicitado"] != suma623:
                add("623", ERROR, ln, "importe_solicitado",
                    f"Solicitado {fmt(m['solicitado'])} ≠ suma {fmt(suma623)} (dif. {fmt(m['solicitado'] - suma623)})")

        # 625 observaciones
        if len(t.get("obs", "")) > 150:
            add("625", ERROR, ln, "obs", f"Tiene {len(t.get('obs', ''))} caracteres (máx. 150)")

        if i % 2000 == 0:
            progreso("Validando reglas de la SSS…", i, total)

    # 624 por grupo
    grupos: Dict[tuple, List[Linea]] = defaultdict(list)
    for ln in lineas:
        grupos[ln.grupo].append(ln)
    for g, lns in grupos.items():
        subs = sum(ln.monto["subsidiado"] for ln in lns)
        apl = sum(ln.monto["apli"] + sum(ln.monto[k] for k in OTROS_DESTINOS_SUBSIDIO) for ln in lns)
        if subs != apl:
            for ln in lns:
                add("624", ERROR, ln, "importe_subsidiado",
                    f"Grupo práctica {g[3]} / prestación {g[2]}: subsidio {fmt(subs)} ≠ aplicado {fmt(apl)} "
                    f"(dif. {fmt(subs - apl)}, {len(lns)} línea/s)")

    progreso("Validación terminada", total, total)
    return H


def contar(hallazgos: Iterable[Hallazgo], nivel: Optional[str] = None) -> Counter:
    return Counter(h.codigo for h in hallazgos if nivel is None or h.nivel == nivel)
