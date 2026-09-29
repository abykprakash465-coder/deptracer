from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import importlib.util
import os
from typing import Any


@dataclass
class Config:
    trace_timeout: float = 120.0
    build_timeout: float = 300.0
    max_iterations: int = 10
    max_seconds: float = 1800.0
    resolver_timeout: float = 30.0
    max_resolver_workers: int = 8
    resume: bool = True
    dry_run: bool = False
    json_output: bool = False
    verbose: bool = False
    exclude_system: bool = False
    search_paths: list[str] = field(default_factory=list)
    license_scan: bool = False
    fail_on_gpl: bool = False

    def merge(self, values: dict[str, Any]) -> "Config":
        for key, value in values.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.max_iterations = max(1, int(self.max_iterations))
        self.max_seconds = max(1.0, float(self.max_seconds))
        self.trace_timeout = max(1.0, float(self.trace_timeout))
        self.build_timeout = max(1.0, float(self.build_timeout))
        self.resolver_timeout = max(1.0, float(self.resolver_timeout))
        self.max_resolver_workers = max(1, int(self.max_resolver_workers))
        return self


def load_config(project_dir: str | Path) -> Config:
    """Load optional deptracer_config.py without importing project packages."""
    root = Path(project_dir).resolve()
    cfg = Config()
    module_path = root / "deptracer_config.py"
    if module_path.exists():
        spec = importlib.util.spec_from_file_location("_deptracer_user_config", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            values = {
                name.lower(): getattr(module, name)
                for name in dir(module)
                if name.isupper()
            }
            cfg.merge(values)
    # Environment variables are deliberately limited to primitive values.
    env = {
        "trace_timeout": os.getenv("DEPTRACER_TRACE_TIMEOUT"),
        "build_timeout": os.getenv("DEPTRACER_BUILD_TIMEOUT"),
        "max_iterations": os.getenv("DEPTRACER_MAX_ITERATIONS"),
        "max_seconds": os.getenv("DEPTRACER_MAX_SECONDS"),
    }
    for key, value in env.items():
        if value is not None:
            cfg.merge({key: float(value) if key != "max_iterations" else int(value)})
    return cfg
