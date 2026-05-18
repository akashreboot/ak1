"""Boot/teardown for the local Flask mocks.

Each mock site runs in its own daemon thread on a fixed port. The
verification workflow points its adapters at these ports (via the YAMLs
or the REAL_DRE_BASE_<STATE> env overrides). The whole thing comes up in
under a second and dies with the Python process.
"""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass

from werkzeug.serving import make_server


@dataclass
class _ServerHandle:
    name: str
    port: int
    thread: threading.Thread
    server: object  # werkzeug.serving.BaseWSGIServer


_servers: dict[str, _ServerHandle] = {}
_lock = threading.Lock()


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _start(name: str, app, port: int) -> None:
    if name in _servers:
        return  # already running in this process
    if _port_in_use(port):
        # Could be a leftover from a previous Streamlit run; treat as live.
        _servers[name] = _ServerHandle(name=name, port=port, thread=None, server=None)
        return
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name=f"mock-{name}")
    thread.start()
    _servers[name] = _ServerHandle(name=name, port=port, thread=thread, server=server)


def start_all() -> dict[str, int]:
    """Start every mock site if not already running. Returns name->port map."""
    from verifier.mock_sites.joinreal import create_app as joinreal_app
    from verifier.mock_sites.dre_ca import create_app as ca_app
    from verifier.mock_sites.dre_tx import create_app as tx_app
    from verifier.mock_sites.dre_hi import create_app as hi_app

    with _lock:
        _start("joinreal", joinreal_app(), 8801)
        _start("dre_ca",   ca_app(),       8802)
        _start("dre_tx",   tx_app(),       8803)
        _start("dre_hi",   hi_app(),       8804)
        # Give Werkzeug a beat to bind sockets.
        time.sleep(0.25)

    return {name: handle.port for name, handle in _servers.items()}


def status() -> dict[str, dict]:
    return {
        name: {"port": h.port, "running": _port_in_use(h.port)}
        for name, h in _servers.items()
    }
