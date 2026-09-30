from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def verify_clean(binary: str, *, image: str = "ubuntu:24.04", timeout: float = 180.0, command: str | None = None):
    """Run the produced executable in a disposable Docker/Podman container.

    This is deliberately an integration check: a successful deptracer sweep is
    not accepted as proof until the final binary actually runs without the
    developer's Python environment.
    """
    engine = shutil.which("docker") or shutil.which("podman")
    if not engine:
        raise RuntimeError("Neither docker nor podman is installed")
    binary_path = Path(binary).resolve()
    if not binary_path.exists():
        raise FileNotFoundError(f"Binary or directory not found: {binary_path}")

    if binary_path.is_dir():
        inner = command or f"/opt/app/{binary_path.name}"
        mount_arg = f"{binary_path}:/opt/app:ro"
    else:
        inner = command or f"/opt/app/{binary_path.name}"
        mount_arg = f"{binary_path}:/opt/app/{binary_path.name}:ro"

    cmd = [engine, "run", "--rm", "--network", "none", "-v", mount_arg, image, "sh", "-lc", inner]
    try:
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return False, "clean verification timed out"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()
