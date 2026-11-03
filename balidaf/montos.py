"""
Importes exactos en centavos (enteros).

Trabajar con enteros evita las diferencias de centavos que produce ``float``
(p. ej. 150848.96000000002), que fueron causa de rechazos en las reglas 623/624.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional, Tuple


def a_centavos(valor: Any) -> Tuple[int, Optional[str]]:
    """Convierte un valor de celda a centavos.

    Devuelve ``(centavos, problema)`` donde ``problema`` es ``None`` si el valor es válido,
    ``"redondeo"`` si tenía más de 2 decimales, o ``"invalido"`` si no es numérico.
    Vacío / ``None`` → 0.
    """
    if valor is None:
        return 0, None
    if isinstance(valor, bool):
        return 0, "invalido"
    if isinstance(valor, int):
        return valor * 100, None
    if isinstance(valor, float):
        d = Decimal(repr(valor))
    else:
        s = str(valor).strip().replace(" ", "").replace("$", "")
        if s == "":
            return 0, None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            d = Decimal(s)
        except InvalidOperation:
            return 0, "invalido"
    c = (d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    problema = None
    # más de 2 decimales "reales" (se toleran restos de float como 0.00000000002)
    if abs(d * 100 - c) > Decimal("0.0001"):
        problema = "redondeo"
    return int(c), problema


def a_excel(centavos: int):
    """Valor para escribir en la celda: número con 2 decimales como máximo."""
    if centavos % 100 == 0:
        return centavos // 100
    return round(centavos / 100, 2)


def fmt(centavos: int) -> str:
    """Formato argentino: 1.234.567,89"""
    neg = centavos < 0
    c = abs(centavos)
    entero, dec = divmod(c, 100)
    s = f"{entero:,}".replace(",", ".") + f",{dec:02d}"
    return ("-" if neg else "") + s
