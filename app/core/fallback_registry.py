"""Registry em memória de fallbacks reais PostGIS → filesystem.

Conta apenas fallback operacional da API Gold (`X-Data-Source=fallback_filesystem`).
Não persiste em disco/banco; reiniciar a API zera o estado.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

RECENT_EVENTS_LIMIT = 50

_lock = threading.Lock()
_state: dict[str, Any] = {
    "total_fallbacks": 0,
    "by_endpoint": {},
    "by_table": {},
    "by_scope": {},
    "by_reason": {},
    "last_fallback_at": None,
    "recent_events": deque(maxlen=RECENT_EVENTS_LIMIT),
}


def _bump(bucket: dict[str, int], key: str | None) -> None:
    label = key if key else "(none)"
    bucket[label] = int(bucket.get(label, 0)) + 1


def reset() -> None:
    """Zera o registry (útil em testes)."""
    with _lock:
        _state["total_fallbacks"] = 0
        _state["by_endpoint"] = {}
        _state["by_table"] = {}
        _state["by_scope"] = {}
        _state["by_reason"] = {}
        _state["last_fallback_at"] = None
        _state["recent_events"] = deque(maxlen=RECENT_EVENTS_LIMIT)


def record_fallback(
    *,
    endpoint: str,
    table_name: str | None,
    scope: str | None,
    ano: int | None,
    mes: int | None,
    reason: str,
) -> None:
    """Registra um fallback real PostGIS → filesystem."""
    ts = datetime.now(timezone.utc).isoformat()
    event = {
        "timestamp": ts,
        "endpoint": endpoint,
        "table_name": table_name,
        "scope": scope,
        "ano": ano,
        "mes": mes,
        "reason": reason,
    }
    with _lock:
        _state["total_fallbacks"] = int(_state["total_fallbacks"]) + 1
        _bump(_state["by_endpoint"], endpoint)
        _bump(_state["by_table"], table_name)
        _bump(_state["by_scope"], scope)
        _bump(_state["by_reason"], reason)
        _state["last_fallback_at"] = ts
        _state["recent_events"].append(event)


def snapshot() -> dict[str, Any]:
    """Snapshot JSON-serializável do contador."""
    with _lock:
        return {
            "total_fallbacks": int(_state["total_fallbacks"]),
            "by_endpoint": dict(_state["by_endpoint"]),
            "by_table": dict(_state["by_table"]),
            "by_scope": dict(_state["by_scope"]),
            "by_reason": dict(_state["by_reason"]),
            "last_fallback_at": _state["last_fallback_at"],
            "recent_events": list(_state["recent_events"]),
        }


# Alias explícito para a rota ops.
get_fallback_snapshot = snapshot
