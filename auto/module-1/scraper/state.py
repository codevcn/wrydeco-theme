from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, load_json


STATUSES = ("pending", "crawled", "price_verified", "content_ready", "applied", "failed", "needs_attention")


@dataclass
class ProductWorkspace:
    root: Path

    @classmethod
    def create(cls, runs_dir: Path, run_id: str, asin: str) -> "ProductWorkspace":
        root = runs_dir / run_id / asin
        (root / "evidence").mkdir(parents=True, exist_ok=True)
        workspace = cls(root)
        if not workspace.state_path.exists():
            workspace.set_status("pending")
        return workspace

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    def path(self, name: str) -> Path:
        return self.root / name

    def state(self) -> dict[str, Any]:
        return load_json(self.state_path) if self.state_path.exists() else {"status": "pending"}

    def set_status(self, status: str, **details: Any) -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        previous = self.state() if self.state_path.exists() else {}
        history = list(previous.get("history", []))
        timestamp = datetime.now(timezone.utc).isoformat()
        history.append({"status": status, "at": timestamp, **details})
        atomic_write_json(self.state_path, {"status": status, "updated_at": timestamp, "history": history, **details})

    def write(self, name: str, payload: Any) -> Path:
        target = self.path(name)
        atomic_write_json(target, payload)
        return target

