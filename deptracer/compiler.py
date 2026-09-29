from __future__ import annotations

import sys
from pathlib import Path

from .process import run


def build(
    spec_path: str,
    iteration: int = 1,
    verbose: bool = False,
    timeout: float = 300.0,
):
    spec = Path(spec_path).resolve()
    if not spec.exists():
        return False

    cmd = [sys.executable, "-m", "PyInstaller", "-y"]
    if iteration == 1:
        cmd.append("--clean")
    cmd.append(spec.name)

    result = run(cmd, cwd=str(spec.parent), timeout=timeout)
    if verbose and result.stdout:
        print(result.stdout)
    if result.stderr and (verbose or result.returncode != 0):
        print(result.stderr)

    if result.timed_out:
        print(f"[COMPILER] Build timeout after {timeout:.0f}s.")
        return False
    if result.returncode != 0:
        print(f"[COMPILER] PyInstaller failed with exit code {result.returncode}.")
        return False
    return True
