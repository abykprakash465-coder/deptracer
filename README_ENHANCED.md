# DepTracer Competition Build — v0.3

This branch turns the prototype into a reliability-first dependency repair loop.

## What changed

### Reliability
- Hard timeouts for tracing and PyInstaller builds.
- Process-group termination on timeout; no orphaned child processes.
- Global iteration and wall-clock budgets.
- Durable per-project state under `.deptracer/state.json`.
- Resume after interruption.
- Safe stop when no new dependency can be resolved.
- Structured JSONL events under `.deptracer/events.jsonl`.

### Faster resolution
- Resolves independent missing files in parallel.
- Project/vendor/virtualenv paths are preferred before global system paths.
- Conda, Poetry/Pipenv-style active environments are covered through `sys.prefix`, `CONDA_PREFIX`, and site-package discovery.
- Safer relative symlink resolution.

### Better diagnostics
- `deptracer explain --project-dir .`
- `deptracer explain --project-dir . --json`
- Specific dependency names are printed while resolving.
- CI can consume JSONL output.

### Safe preview
```bash
deptracer build . my_app my_app.spec --dry-run
```
Dry-run traces and resolves but does not modify the spec or rebuild.

### Custom search paths
Create `deptracer_config.py` from the example and add:
```python
SEARCH_PATHS = ["/opt/vendor/lib", "/home/me/vendor"]
```

## Competition demo

1. Build a deliberately incomplete PyInstaller application.
2. Run the binary in a clean/isolated environment and capture the failure.
3. Run:
```bash
deptracer build . demo demo.spec --max-iterations 8 --max-seconds 600
```
4. Show the dependency discovered, resolver path, spec patch, and rebuild.
5. Interrupt after an iteration.
6. Run the same command again and show `RESUME`.
7. Run a deliberately hanging demo and show the trace timeout.
8. Use `--dry-run` to show the planned patch without modifying the project.
9. Finally execute the rebuilt binary in a clean environment and show that it exits successfully.

## Important engineering note

A clean-machine test is the acceptance criterion. A successful log line alone is not proof of correctness.

This competition build intentionally prioritizes reliable Linux/PyInstaller support over attempting a shallow Windows/macOS/C++ implementation at the same time.
