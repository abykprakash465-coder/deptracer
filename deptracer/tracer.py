from __future__ import annotations

import os
import shutil
from pathlib import Path

from .process import run


def _sandbox_command(executable_path: str, project_dir: str) -> list[str]:
    """Build a conservative Linux sandbox command.

    The application gets read-only access to the root filesystem and the project,
    while network/IPC/etc. are isolated. --tmpfs /tmp ensures PyInstaller onefile
    extractors work, while --die-with-parent prevents orphaned traced applications.
    Active external virtualenv or conda directories are masked with --tmpfs so
    unbundled dependencies trigger ENOENT during trace instead of silently leaking.
    """
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise RuntimeError("bubblewrap (bwrap) is required; install bubblewrap first")

    exe = str(Path(executable_path).resolve())
    project = str(Path(project_dir).resolve())
    cmd = [
        bwrap,
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--ro-bind", project, project,
        "--bind", exe, exe,
        "--chdir", project,
        "--unshare-all",
        "--die-with-parent",
    ]

    for env_var in ("VIRTUAL_ENV", "CONDA_PREFIX"):
        val = os.environ.get(env_var)
        if val and os.path.isdir(val):
            p = str(Path(val).resolve())
            if not p.startswith(project):
                cmd.extend(["--tmpfs", p])

    cmd.extend(["--", exe])
    return cmd


def run_and_trace(
    executable_path: str,
    project_dir: str = ".",
    log_name: str | None = None,
    verbose: bool = False,
    timeout: float = 120.0,
):
    if log_name is None:
        log_name = os.path.abspath(f"trace_{os.getpid()}.log")
    stderr_log = log_name.replace(".log", ".stderr")
    command = [
        "strace", "-f", "-s", "4096", "-o", log_name,
        "-e", "trace=file",
    ] + _sandbox_command(executable_path, project_dir)

    result = run(command, cwd=project_dir, timeout=timeout)
    Path(stderr_log).write_text(result.stderr, encoding="utf-8", errors="replace")

    if verbose and result.stdout:
        print(result.stdout)
    if verbose and result.stderr:
        print(result.stderr)
    if result.timed_out:
        print(f"[TRACER] Timeout after {timeout:.0f}s; child process tree terminated.")
        return log_name, stderr_log, 124
    return log_name, stderr_log, result.returncode
