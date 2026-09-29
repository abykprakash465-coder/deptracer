from __future__ import annotations

import json
from pathlib import Path

from .history import History


def explain_problem(project_dir: str = ".", *, json_output: bool = False):
    history = History(project_dir).load()
    data = history.data
    if json_output:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    print("\n=== deptracer diagnostic history ===")
    print(f"Status: {data.get('status')}")
    print(f"Iteration: {data.get('iteration', 0)}")
    if data.get("last_error"):
        print(f"Last error: {data['last_error']}")
    for row in data.get("iterations", []):
        print(
            f"  #{row.get('iteration')}: {row.get('status')}"
            f" | unresolved={row.get('unresolved', [])}"
        )
    print("\nTip: inspect .deptracer/state.json and .deptracer/events.jsonl for CI/debugging.")
