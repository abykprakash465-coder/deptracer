from __future__ import annotations

import os
import re
import site
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def safe_realpath(path: str, max_depth: int = 20) -> str:
    current = os.path.abspath(path)
    seen: set[str] = set()
    for _ in range(max_depth):
        if current in seen:
            return current
        seen.add(current)
        if not os.path.islink(current):
            return current
        target = os.readlink(current)
        current = os.path.abspath(
            target if os.path.isabs(target)
            else os.path.join(os.path.dirname(current), target)
        )
    return current


def is_binary_dependency(name: str) -> bool:
    lower = name.lower()
    return any(
        re.search(re.escape(ext) + r"(\.\d+)*$", lower)
        for ext in (".so", ".dll", ".dylib", ".pyd")
    )


def environment_search_paths(
    project_dir: str,
    extra: list[str] | None = None,
    *,
    is_binary: bool = True,
):
    root = Path(project_dir).resolve()
    paths = [
        root, root / "lib", root / "libs", root / "vendor",
        root / "build", root / "build" / "lib",
        root / ".venv", root / ".venv" / "lib",
    ]
    if is_binary:
        paths += [
            Path("/usr/local/lib"), Path("/usr/lib"),
            Path("/lib"), Path("/lib64"),
        ]
    try:
        paths += [Path(x) for x in site.getsitepackages()]
        paths.append(Path(site.getusersitepackages()))
    except Exception:
        pass

    prefixes = []
    if os.environ.get("CONDA_PREFIX"):
        prefixes.append(os.environ["CONDA_PREFIX"])
    if os.environ.get("VIRTUAL_ENV"):
        prefixes.append(os.environ["VIRTUAL_ENV"])
    if os.sys.prefix not in ("/usr", "/usr/local") or is_binary:
        prefixes.append(os.sys.prefix)

    for prefix in prefixes:
        p = Path(prefix)
        paths += [p, p / "lib", p / "lib64", p / "bin"]

    if extra:
        paths += [Path(x).expanduser() for x in extra]

    unique, seen = [], set()
    for p in paths:
        try:
            p = p.resolve()
        except OSError:
            continue
        if p.exists() and p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def _find_in_dir(directory: Path, variants: list[str], timeout: float):
    for variant in variants:
        candidate = directory / variant
        if candidate.is_file() and os.access(candidate, os.R_OK):
            return safe_realpath(str(candidate))

    expression = []
    for i, variant in enumerate(variants):
        if i:
            expression.append("-o")
        expression.extend(["-name", variant])

    depth = "4" if str(directory).startswith(("/usr", "/lib", "/var")) else "10"
    command = [
        "find", str(directory), "-maxdepth", depth, "-type", "f", "-readable",
        "(", *expression, ")", "-print", "-quit",
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=timeout, check=False
        )
        found = result.stdout.strip()
        return safe_realpath(found) if found else None
    except (OSError, subprocess.SubprocessError):
        return None


def hunt_missing_library(
    file_name: str,
    project_dir: str = ".",
    search_paths: list[str] | None = None,
    timeout: float = 30.0,
    verbose: bool = False,
):
    is_binary = is_binary_dependency(file_name)
    if is_binary:
        base = re.sub(r"\.so(\.\d+)*$", ".so", file_name)
        variants = list(dict.fromkeys([
            file_name, base,
            base + ".1", base + ".2", base + ".3", base + ".0"
        ]))
    else:
        variants = [file_name]

    zones = environment_search_paths(project_dir, search_paths, is_binary=is_binary)

    root = str(Path(project_dir).resolve())

    def priority(p: Path):
        text = str(p)
        if text.startswith(root):
            return 0
        if os.environ.get("VIRTUAL_ENV") and text.startswith(os.environ["VIRTUAL_ENV"]):
            return 1
        if os.environ.get("CONDA_PREFIX") and text.startswith(os.environ["CONDA_PREFIX"]):
            return 1
        return 2

    zones.sort(key=priority)
    for zone in zones:
        found = _find_in_dir(zone, variants, timeout)
        if found:
            if verbose:
                print(f"[RESOLVER] {file_name} -> {found}")
            return found
    return None


def resolve_many(
    names: list[str],
    project_dir: str,
    search_paths: list[str] | None = None,
    timeout: float = 30.0,
    workers: int = 8,
    verbose: bool = False,
):
    results = {}
    unique = list(dict.fromkeys(names))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {
            pool.submit(
                hunt_missing_library, name, project_dir,
                search_paths, timeout, verbose
            ): name
            for name in unique
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                if verbose:
                    print(f"[RESOLVER] {name}: {exc}")
                results[name] = None
    return results
