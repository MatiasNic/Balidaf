"""Preferencias del usuario (p. ej. tema claro/oscuro), guardadas en ~/.balidaf.json."""

import json
import os
from typing import Any

RUTA = os.path.join(os.path.expanduser("~"), ".balidaf.json")


def _leer() -> dict:
    try:
        with open(RUTA, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception:
        return {}


def leer_preferencia(clave: str, defecto: Any = None) -> Any:
    return _leer().get(clave, defecto)


def guardar_preferencia(clave: str, valor: Any) -> None:
    datos = _leer()
    datos[clave] = valor
    try:
        with open(RUTA, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass   # si no se puede guardar, no es grave
