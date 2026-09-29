from __future__ import annotations

from importlib import metadata
import json
import re
from pathlib import Path


RISKY = ("GPL", "AGPL", "LGPL")


def scan_environment() -> list[dict]:
    rows = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or dist.name
        license_text = (dist.metadata.get("License") or "").strip()
        classifiers = dist.metadata.get_all("Classifier") or []
        licenses = [x.split(" :: ")[-1] for x in classifiers
                    if x.startswith("License :: ")]
        if license_text:
            licenses.append(license_text)
        text = "; ".join(dict.fromkeys(licenses))
        if not text:
            continue
        risk = any(re.search(rf"\b{re.escape(x)}\b", text, re.I) for x in RISKY)
        rows.append({"package": name, "license": text, "flag": risk})
    return sorted(rows, key=lambda x: x["package"].lower())


def write_report(path: str | Path) -> list[dict]:
    rows = scan_environment()
    Path(path).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows
