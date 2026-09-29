from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run(
    command: Sequence[str],
    *,
    cwd: str | None = None,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> ProcessResult:
    """Run a child process and reliably terminate its process group on timeout."""
    kwargs = dict(
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    if os.name == "posix":
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(list(command), **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout)
        return ProcessResult(proc.returncode, out, err)
    except subprocess.TimeoutExpired as exc:
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                out, err = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                out, err = proc.communicate()
        else:
            proc.kill()
            out, err = proc.communicate()

        out = (out or "") + (exc.stdout or "")
        err = (err or "") + (exc.stderr or "")
        return ProcessResult(proc.returncode or -signal.SIGTERM, out, err, True)
