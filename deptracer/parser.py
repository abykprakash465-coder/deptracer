from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

class HiddenImportDetector:
    PATTERN = re.compile(
        r"\[DEPTRACER-PROBE\].*No module named [\'\"]([a-zA-Z0-9_\.]+)[\'\"]"
    )
    PATTERN2 = re.compile(
        r"\[DEPTRACER-PROBE\].*cannot import name [\'\"]([a-zA-Z0-9_]+)[\'\"] "
        r"from [\'\"]([a-zA-Z0-9_\.]+)[\'\"]"
    )

    @classmethod
    def detect_hidden_imports(cls, stderr_log_path):
        hidden = set()
        if not stderr_log_path or not os.path.exists(stderr_log_path):
            return []
        try:
            for line in Path(stderr_log_path).read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if (m := cls.PATTERN.search(line)):
                    hidden.add(m.group(1))
                if (m := cls.PATTERN2.search(line)):
                    hidden.add(f"{m.group(2)}.{m.group(1)}")
        except OSError:
            pass
        return sorted(hidden)


class TraceParser:
    SYSCALL_ANY = re.compile(
        r'(?:openat|open|newfstatat|stat|access|readlink)\('
        r'.*?"((?:\\.|[^"\\])*)".*?\)\s*=\s*(-1\s+\w+|\d+)'
    )

    TRACKED_EXTENSIONS = {
        ".so", ".dll", ".dylib", ".pyd",
        ".pt", ".pth", ".onnx", ".pb", ".h5", ".joblib",
        ".npy", ".npz", ".pickle", ".pkl",
        ".json", ".yaml", ".yml", ".toml", ".csv",
        ".wav", ".mp3", ".flac", ".jpg", ".jpeg", ".png", ".gif",
        ".txt", ".md", ".db", ".sqlite", ".dat",
    }
    RELEVANT_ERRORS = {"ENOENT", "EACCES", "EPERM", "ENOEXEC"}
    _SYSTEM_CACHE: set[str] = set()

    @classmethod
    def load_system_cache(cls):
        if cls._SYSTEM_CACHE:
            return
        try:
            result = subprocess.run(
                ["ldconfig", "-p"], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, timeout=5, check=False
            )
            for line in result.stdout.splitlines():
                if "=>" in line:
                    name = line.split("=>", 1)[0].strip().split()[0]
                    cls._SYSTEM_CACHE.add(name)
        except (OSError, subprocess.SubprocessError):
            pass

    @classmethod
    def is_system_noise(cls, file_path: str) -> bool:
        name = os.path.basename(file_path)
        # Do not discard every underscore-prefixed file; real applications can
        # legitimately load "_model.dat" or "_plugin.so".
        if name.startswith("libpython") or "glibc-hwcaps" in file_path:
            return True
        if "lib-dynload" in file_path and ".cpython-" in name:
            return True
        base = re.sub(r"\.so(\.\d+)*$", ".so", name)
        return base in cls._SYSTEM_CACHE or name in cls._SYSTEM_CACHE

    @classmethod
    def _is_tracked(cls, path: str) -> bool:
        lower = path.lower()
        return any(
            re.search(re.escape(ext) + r"(\.\d+)*$", lower)
            for ext in cls.TRACKED_EXTENSIONS
        )

    @classmethod
    def stream_missing_libraries(cls, log_file_path, verbose=False):
        cls.load_system_cache()
        status = {}
        mapping = {}
        try:
            lines = Path(log_file_path).read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            return

        for line_no, line in enumerate(lines, 1):
            match = cls.SYSCALL_ANY.search(line)
            if not match:
                continue
            path = bytes(match.group(1), "utf-8").decode("unicode_escape")
            result = match.group(2)
            if not cls._is_tracked(path):
                continue

            filename = os.path.basename(path)
            path_key = os.path.normpath(path)
            if not result.startswith("-1"):
                status[path_key] = "FOUND"
                continue

            parts = result.split()
            if len(parts) < 2 or parts[1] not in cls.RELEVANT_ERRORS:
                continue
            errno = parts[1]
            if "..." in path:
                if verbose:
                    print(f"[PARSER] Ignoring truncated path at line {line_no}: {path}")
                continue
            if errno in {"EACCES", "EPERM"}:
                if verbose:
                    print(f"[PARSER] Unreadable dependency ({errno}): {path}")
                continue
            if errno == "ENOENT" and not cls.is_system_noise(path):
                if status.get(filename) != "FOUND":
                    status[path_key] = "MISSING"
                    mapping[path_key] = path

        for path_key, state in status.items():
            if state == "MISSING":
                yield mapping[path_key]


def extract_missing_libraries(log_file_path, verbose=False):
    yield from TraceParser.stream_missing_libraries(log_file_path, verbose)


def extract_missing_libraries_and_hidden_imports(
    log_file_path, stderr_log_path=None, verbose=False
):
    raw = list(extract_missing_libraries(log_file_path, verbose))
    binaries, data = [], []
    for item in raw:
        if item.lower().endswith((".so", ".dll", ".dylib", ".pyd")):
            binaries.append(item)
        else:
            data.append(item)
    return {
        "binaries": sorted(set(binaries)),
        "data": sorted(set(data)),
        "hidden_imports": HiddenImportDetector.detect_hidden_imports(stderr_log_path),
    }
