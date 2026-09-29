from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path


START = "# --- deptracer managed additions ---"
END = "# --- end deptracer additions ---"


def _safe_literal(value: str) -> str:
    return repr(str(value))


def _analysis_end(lines: list[str]) -> int:
    depth = 0
    started = False
    for i, line in enumerate(lines):
        if re.search(r"\bAnalysis\s*\(", line):
            started = True
        if started:
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                return i + 1
    raise ValueError("Could not locate Analysis(...) in spec file")


def _build_additions(payload) -> list[str]:
    additions = []
    for name, path in payload.get("binaries", []):
        if os.path.isfile(path):
            additions.append(
                f"a.binaries += [({_safe_literal(path)}, '.')]\n"
            )
    for name, path in payload.get("data", []):
        if os.path.isfile(path):
            additions.append(
                f"a.datas += [({_safe_literal(path)}, '.')]\n"
            )
    hidden = [
        x for x in payload.get("hidden_imports", [])
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", x)
    ]
    if hidden:
        additions.append(
            "a.hiddenimports += [\n" +
            "".join(f"    {_safe_literal(x)},\n" for x in hidden) +
            "]\n"
        )
    return additions


def patch_spec_file(spec_path, resolved_payload, *, dry_run=False):
    spec = Path(spec_path)
    if not spec.is_file() or not os.access(spec, os.W_OK):
        raise PermissionError(f"Spec file is missing or not writable: {spec}")

    original = spec.read_text(encoding="utf-8")
    additions = _build_additions(resolved_payload)
    if not additions:
        return False

    # Avoid duplicate managed entries across repeated/resumed runs.
    additions = [
        line for line in additions
        if line.strip() and line.strip() not in {
            existing.strip()
            for existing in original.splitlines()
            if existing.strip()
        }
    ]
    if not additions:
        return False

    block = "\n".join(additions)
    if START in original:
        # Add new entries before END; this allows multiple sweep iterations.
        end_index = original.find(END)
        if end_index < 0:
            raise ValueError("Corrupt deptracer managed block in spec")
        new_text = original[:end_index] + block + "\n" + original[end_index:]
    else:
        lines = original.splitlines(True)
        insert_at = _analysis_end(lines)
        managed = f"\n{START}\n{block}\n{END}\n"
        lines.insert(insert_at, managed)
        new_text = "".join(lines)

    if new_text == original:
        return False
    if dry_run:
        return True

    fd, tmp = tempfile.mkstemp(prefix=".deptracer-", dir=str(spec.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp, spec)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True
