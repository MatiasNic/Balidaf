"""
Abre la interfaz de Balidaf.

1. Con pywebview (WebView2 de Windows): ventana propia del programa.
2. Si pywebview no está disponible: servidor local + navegador predeterminado (mismo diseño).
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .. import APP_TITLE, __version__
from ..paths import resource_path
from .api import Api


def carpeta_web() -> str:
    """Carpeta con index.html (funciona desde el código fuente y desde el .exe)."""
    candidata = resource_path("balidaf", "web")
    if os.path.isfile(os.path.join(candidata, "index.html")):
        return candidata
    return os.path.dirname(os.path.abspath(__file__))


def abrir_ventana() -> None:
    import webview
    api = Api()
    ventana = webview.create_window(f"{APP_TITLE} · v{__version__}", url=os.path.join(carpeta_web(), "index.html"),
                                    js_api=api, width=1440, height=900, min_size=(1180, 720),
                                    background_color="#f3f3f0", text_select=True)
    api._set_ventana(ventana)

    def maximizar():
        try:
            ventana.maximize()
        except Exception:
            pass
    ventana.events.shown += maximizar
    webview.start(gui="edgechromium" if sys.platform.startswith("win") else None, http_server=True)


def _handler(api: Api, raiz: str):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=raiz, **k)

        def log_message(self, *a):
            pass

        def do_POST(self):
            if not self.path.startswith("/api/"):
                self.send_error(404)
                return
            metodo = self.path[5:].split("?")[0]
            largo = int(self.headers.get("Content-Length") or 0)
            args = json.loads(self.rfile.read(largo) or b"[]")
            fn = getattr(api, metodo, None)
            if metodo.startswith("_") or not callable(fn):
                self.send_error(404)
                return
            try:
                cuerpo = json.dumps(fn(*args), ensure_ascii=False).encode("utf-8")
                self.send_response(200)
            except Exception as exc:
                cuerpo = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
    return Handler


def servir_en_navegador(puerto: int = 0, abrir: bool = True) -> ThreadingHTTPServer:
    """Modo alternativo: sirve la interfaz en http://127.0.0.1:<puerto>/index.html?modo=web"""
    srv = ThreadingHTTPServer(("127.0.0.1", puerto), _handler(Api(), carpeta_web()))
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html?modo=web"
    print(f"Balidaf abierto en el navegador: {url}  (cerrá esta ventana para salir)")
    if abrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    return srv


def run() -> None:
    try:
        import webview  # noqa: F401
    except Exception:
        srv = servir_en_navegador()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return
    abrir_ventana()
