"""
elma bridge: reads JSON-RPC requests on stdin, writes responses on stdout.

The Tauri side spawns this as a long-lived process so the device connection
stays open across commands — reconnecting per request is slow.

Protocol (one JSON object per line):
  request  : {"id": 1, "method": "app.list", "params": {...}}
  response : {"id": 1, "ok": true, "result": ...}
             {"id": 1, "ok": false, "error": {"kind": "...", "message": "..."}}
  event    : {"event": "progress", "data": {...}}
"""
import asyncio
import json
import sys
import traceback
from typing import Any

from . import handlers


def _write(obj: dict[str, Any]) -> None:
    """Write one JSON line and flush — the caller is waiting on it."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _emit(event: str, data: Any) -> None:
    """Progress notification, for long operations such as a backup."""
    _write({"event": event, "data": data})


async def _serve() -> int:
    registry = handlers.build_registry(emit=_emit)
    loop = asyncio.get_running_loop()

    while True:
        # stdin is blocking; keep the event loop free while we wait.
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            _write({"id": None, "ok": False,
                    "error": {"kind": "invalid_json", "message": str(e)}})
            continue

        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        fn = registry.get(method)
        if fn is None:
            _write({"id": req_id, "ok": False,
                    "error": {"kind": "unknown_method",
                              "message": f"no such method: {method}"}})
            continue

        try:
            result = await fn(**params)
            _write({"id": req_id, "ok": True, "result": result})
        except handlers.ElmaError as e:
            _write({"id": req_id, "ok": False,
                    "error": {"kind": e.kind, "message": str(e)}})
        except Exception as e:  # unexpected — trace to stderr, summary to caller
            traceback.print_exc(file=sys.stderr)
            _write({"id": req_id, "ok": False,
                    "error": {"kind": "unexpected", "message": str(e)}})

    return 0


def main() -> int:
    try:
        return asyncio.run(_serve())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
