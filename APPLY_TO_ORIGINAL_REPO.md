# Apply this competition pack to the supplied deptracer repository

This pack is an overlay for the current Linux/PyInstaller prototype.

## Replace/add these paths

Copy these files into the original repository:

- `deptracer/config.py`
- `deptracer/history.py`
- `deptracer/process.py`
- `deptracer/tracer.py`
- `deptracer/parser.py`
- `deptracer/resolver.py`
- `deptracer/fixer.py`
- `deptracer/compiler.py`
- `deptracer/core.py`
- `deptracer/explain.py`
- `deptracer/cli.py`
- `deptracer/license.py`
- `deptracer/__init__.py`
- `pyproject.toml`
- `.github/workflows/deptracer-ci.yml`

Also add the included `examples/`, `tests/`, and `deptracer_config.py.example`.

## Install and test

```bash
python -m pip install -e .
python -m pytest -q
sudo apt-get install strace bubblewrap
```

## Main competition command

```bash
deptracer build . APP_NAME APP_NAME.spec   --max-iterations 8   --max-seconds 600   -v
```

## New features to demonstrate

Dry-run:

```bash
deptracer build . APP_NAME APP_NAME.spec --dry-run
```

Resume:

```bash
deptracer build . APP_NAME APP_NAME.spec
# interrupt during a sweep, then run the same command again
```

Diagnostics:

```bash
deptracer explain --project-dir .
deptracer explain --project-dir . --json
```

Custom search paths:

```bash
deptracer build . APP_NAME APP_NAME.spec --search-path /opt/vendor/lib
```

License report:

```bash
deptracer license
deptracer license --json
```

## Competition acceptance test

Do not treat a printed success message as proof. The final acceptance test is:

**Build on one environment -> run the final executable in a genuinely clean environment -> verify the application's actual output.**

This pack deliberately focuses on making the existing Linux/PyInstaller path reliable instead of adding shallow Windows/macOS/C++ support.
