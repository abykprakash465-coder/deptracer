from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import time
from typing import Any


class History:
    """Durable, structured build state.

    State is kept under <project>/.deptracer/state.json rather than a single
    global/flat file, so concurrent projects do not overwrite one another.
    """

    VERSION = 1

    def __init__(self, project_dir: str | Path):
        self.root = Path(project_dir).resolve()
        self.dir = self.root / ".deptracer"
        self.path = self.dir / "state.json"
        self.data: dict[str, Any] = {
            "version": self.VERSION,
            "status": "new",
            "started_at": None,
            "updated_at": None,
            "iteration": 0,
            "injected": {"binaries": [], "data": [], "hidden_imports": []},
            "unresolved": [],
            "iterations": [],
            "last_error": None,
        }

    def load(self) -> "History":
        if not self.path.exists():
            return self
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError):
            # Corrupt state must not make a build impossible.
            backup = self.path.with_suffix(".corrupt.json")
            try:
                self.path.replace(backup)
            except OSError:
                pass
        return self

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = time.time()
        fd, tmp = tempfile.mkstemp(prefix=".state-", dir=self.dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def start(self, resume: bool) -> int:
        if resume and self.data.get("status") == "running":
            # Resume the in-flight iteration. The state is checkpointed before
            # tracing/patching/building, so repeating that iteration is safer
            # than skipping a partially completed build.
            return max(1, int(self.data.get("iteration", 0)))
        self.data = {
            "version": self.VERSION,
            "status": "running",
            "started_at": time.time(),
            "updated_at": time.time(),
            "iteration": 0,
            "injected": {"binaries": [], "data": [], "hidden_imports": []},
            "unresolved": [],
            "iterations": [],
            "last_error": None,
        }
        self.save()
        return 1

    def record(self, iteration: int, **values: Any) -> None:
        self.data["iteration"] = iteration
        row = {"iteration": iteration, "time": time.time(), **values}
        self.data.setdefault("iterations", []).append(row)
        self.save()

    def mark_injected(self, category: str, value: str) -> None:
        self.data.setdefault("injected", {}).setdefault(category, [])
        if value not in self.data["injected"][category]:
            self.data["injected"][category].append(value)
        self.save()

    def is_injected(self, category: str, value: str) -> bool:
        return value in self.data.get("injected", {}).get(category, [])

    def finish(self, status: str, error: str | None = None) -> None:
        self.data["status"] = status
        self.data["last_error"] = error
        self.save()

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
