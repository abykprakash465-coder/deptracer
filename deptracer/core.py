from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

from . import compiler, fixer, parser, resolver, tracer
from .config import Config, load_config
from .history import History


class UI:
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[34m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def step(cls, module, text):
        print(f"{cls.BLUE}{cls.BOLD}[{module}]{cls.RESET} {text}")

    @classmethod
    def success(cls, module, text):
        print(f"{cls.GREEN}{cls.BOLD}[{module}] {text}{cls.RESET}")

    @classmethod
    def error(cls, module, text):
        print(f"{cls.RED}{cls.BOLD}[{module}] {text}{cls.RESET}")

    @classmethod
    def warn(cls, module, text):
        print(f"{cls.YELLOW}{cls.BOLD}[{module}] {text}{cls.RESET}")


def _write_json_event(path: Path, event: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def run_akdeptracer(
    project_dir,
    binary_name,
    spec_name,
    verbose=False,
    *,
    config: Config | None = None,
    trace_timeout: float | None = None,
    build_timeout: float | None = None,
    max_iterations: int | None = None,
    max_seconds: float | None = None,
    dry_run: bool | None = None,
    resume: bool | None = None,
    json_output: bool | None = None,
):
    if platform.system().lower() != "linux":
        UI.error("CORE", "Linux is required by the current tracer backend.")
        return False

    root = Path(project_dir).resolve()
    spec_file = root / spec_name
    target = root / "dist" / binary_name
    if not spec_file.exists():
        UI.error("CORE", f"Spec file not found: {spec_file}")
        return False
    if not target.exists() and not (dry_run is True):
        UI.step("COMPILER", "Initial executable not found; building from the supplied .spec first.")
        if not compiler.build(str(spec_file), iteration=1, verbose=verbose, timeout=build_timeout or 300.0):
            UI.error("COMPILER", "Initial PyInstaller build failed.")
            return False
    if not target.exists():
        UI.error("CORE", f"Binary not found after initial build: {target}")
        return False

    cfg = config or load_config(root)
    overrides = {
        "verbose": verbose,
        "trace_timeout": trace_timeout,
        "build_timeout": build_timeout,
        "max_iterations": max_iterations,
        "max_seconds": max_seconds,
        "dry_run": dry_run,
        "resume": resume,
        "json_output": json_output,
    }
    cfg.merge({k: v for k, v in overrides.items() if v is not None})

    history = History(root).load()
    start_iteration = history.start(cfg.resume)
    started = time.monotonic()
    event_log = root / ".deptracer" / "events.jsonl"

    if cfg.dry_run:
        UI.step("DRY-RUN", "No spec or binary will be modified.")
    if start_iteration > 1:
        UI.step("RESUME", f"Continuing from iteration {start_iteration}.")

    for iteration in range(start_iteration, cfg.max_iterations + 1):
        elapsed = time.monotonic() - started
        if elapsed >= cfg.max_seconds:
            history.finish("budget_exceeded", "Overall time budget reached.")
            UI.error("BUDGET", "Overall time budget reached before convergence.")
            return False

        UI.step("CORE", f"Iteration {iteration} ({elapsed:.0f}s elapsed)")
        history.record(iteration, status="running")
        event = {"event": "iteration_started", "iteration": iteration, "elapsed": elapsed}
        if cfg.json_output:
            _write_json_event(event_log, event)

        try:
            result = tracer.run_and_trace(
                str(target), str(root),
                verbose=cfg.verbose, timeout=cfg.trace_timeout
            )
        except Exception as exc:
            history.finish("tracer_failed", str(exc))
            UI.error("TRACER", str(exc))
            return False

        log_path, stderr_path, returncode = result
        deps = parser.extract_missing_libraries_and_hidden_imports(
            log_path, stderr_path, verbose=cfg.verbose
        )

        missing_count = sum(len(deps[k]) for k in ("binaries", "data", "hidden_imports"))
        if missing_count == 0:
            if returncode == 0:
                history.finish("success")
                history.record(iteration, status="clean", returncode=returncode)
                UI.success("CORE", "Verified: no missing traced dependencies and process exited cleanly.")
                if cfg.json_output:
                    _write_json_event(event_log, {
                        "event": "success", "iteration": iteration
                    })
                return True
            history.finish("application_failed", f"exit code {returncode}")
            history.record(iteration, status="application_failed", returncode=returncode)
            UI.error(
                "CORE",
                f"No missing dependencies were detected, but the application exited with {returncode}."
            )
            return False

        payload = {"binaries": [], "data": [], "hidden_imports": []}
        names = deps["binaries"] + deps["data"]
        already = set(history.data.get("injected", {}).get("binaries", []))
        already |= set(history.data.get("injected", {}).get("data", []))
        names = [n for n in names if os.path.basename(n) not in already]

        UI.step("PARSER", f"Found {missing_count} runtime issue(s).")
        resolutions = resolver.resolve_many(
            names, str(root),
            search_paths=cfg.search_paths,
            timeout=cfg.resolver_timeout,
            workers=cfg.max_resolver_workers,
            verbose=cfg.verbose,
        )

        unresolved = []
        for category in ("binaries", "data"):
            for missing in deps[category]:
                base = os.path.basename(missing)
                found = resolutions.get(base)
                if found:
                    payload[category].append((base, found))
                    UI.step("RESOLVER", f"{base} -> {found}")
                else:
                    unresolved.append(base)

        for module in deps["hidden_imports"]:
            if not history.is_injected("hidden_imports", module):
                payload["hidden_imports"].append(module)
                UI.step("PARSER", f"Hidden import -> {module}")

        total_new = sum(len(v) for v in payload.values())
        if total_new == 0:
            history.finish("unresolved", ", ".join(sorted(set(unresolved))) or "no new fixes")
            history.record(
                iteration, status="unresolved",
                unresolved=sorted(set(unresolved)), returncode=returncode
            )
            UI.error("CORE", "No new safe fix was found; stopping instead of looping forever.")
            return False

        if cfg.dry_run:
            history.record(
                iteration, status="dry_run",
                payload=payload, unresolved=sorted(set(unresolved))
            )
            UI.success("DRY-RUN", f"Would patch {total_new} item(s) and rebuild.")
            history.finish("dry_run")
            return True

        patched = fixer.patch_spec_file(str(spec_file), payload)
        if not patched:
            history.finish("fixer_noop", "Spec already contains managed additions.")
            UI.error("FIXER", "No new spec changes were produced.")
            return False

        for category in ("binaries", "data"):
            for name, _ in payload[category]:
                history.mark_injected(category, name)
        for module in payload["hidden_imports"]:
            history.mark_injected("hidden_imports", module)

        UI.step("FIXER", f"Patched spec with {total_new} new item(s).")
        if not compiler.build(
            str(spec_file), iteration=iteration,
            verbose=cfg.verbose, timeout=cfg.build_timeout
        ):
            history.finish("build_failed", "PyInstaller build failed or timed out.")
            return False

        history.record(
            iteration, status="rebuilt",
            payload=payload, unresolved=sorted(set(unresolved)),
            returncode=returncode,
        )
        _write_json_event(event_log, {
            "event": "iteration_completed",
            "iteration": iteration,
            "payload": payload,
            "unresolved": sorted(set(unresolved)),
        })

    history.finish("iteration_budget_exceeded", f"max_iterations={cfg.max_iterations}")
    UI.error("BUDGET", f"Maximum iterations ({cfg.max_iterations}) reached.")
    return False
