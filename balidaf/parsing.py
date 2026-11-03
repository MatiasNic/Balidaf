"""Conversión de valores de celda a número."""


def to_float(v) -> float:
    """Convierte un valor de celda a float.

    Acepta números, ``None``/vacío (→ 0.0) y texto con formato local
    (``"1.234,56"`` → 1234.56, ``"12,5"`` → 12.5). Texto no numérico → 0.0.
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return 0.0
    s2 = s.replace(" ", "")
    if "," in s2 and "." in s2:
        s2 = s2.replace(".", "").replace(",", ".")
    elif "," in s2 and "." not in s2:
        s2 = s2.replace(",", ".")
    try:
        return float(s2)
    except Exception:
        return 0.0
