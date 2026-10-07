from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


EventCallback = Callable[[dict[str, Any]], None]


def emit(callback: EventCallback | None, event: str, **payload: Any) -> None:
    if callback is None:
        return
    callback({
        "event": event,
        "at": datetime.now(timezone.utc).isoformat(),
        **payload,
    })
