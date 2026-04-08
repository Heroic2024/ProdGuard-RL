from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SERVER_PATH = Path(__file__).with_name("server.py")
_SPEC = spec_from_file_location("prodguard_server_root", _SERVER_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load server.py")

_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

app = _MODULE.app


def main() -> None:
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
