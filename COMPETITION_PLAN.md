# Competition implementation plan

## Core story

**Problem:** PyInstaller can miss runtime-loaded libraries/data.

**Solution:** trace the real executable, resolve what it actually tries to open, patch the spec, rebuild, and verify in a clean environment.

## Features to present

1. **Reliability** — tracing/build timeouts and process-tree cleanup.
2. **Bounded execution** — iteration + wall-clock budgets.
3. **Resume** — checkpointed state and structured history.
4. **Parallel resolver** — independent dependency lookups run concurrently.
5. **Dry run** — preview changes before touching the spec.
6. **Environment coverage** — venv/Conda/site-package/custom-path search.
7. **Diagnostics** — per-iteration state and JSON events.
8. **License review** — flag GPL/AGPL/LGPL metadata for human review.
9. **CI** — run regression tests on every push/PR.
10. **Clean verification** — optional Docker/Podman execution of the final binary.

## Demo sequence

### 1. Show the failure

Build a small PyInstaller application with a genuine runtime dependency that is not collected automatically. Run the original binary in an environment where that dependency is absent.

### 2. Run DepTracer

```bash
deptracer build . app app.spec -v --max-iterations 8 --max-seconds 600
```

Show the trace → missing dependency → resolver → spec patch → rebuild cycle.

### 3. Prove it

```bash
deptracer verify-clean dist/app
```

Then show the application's actual output, not just DepTracer's success message.

### 4. Stress reliability

Run `examples/hanging_app.py` or an equivalent frozen test and show that the trace/build timeout terminates the process tree instead of hanging the pipeline.

### 5. Show developer experience

```bash
deptracer build . app app.spec --dry-run
deptracer explain --project-dir . --json
deptracer license
```

## Trade-offs to explain

- Linux-first rather than shallow cross-platform support.
- Parallel lookup improves latency but uses more I/O.
- Clean-container verification is stronger than trusting the host, but it tests the selected container image rather than every Linux distribution.
- PyInstaller still relies on compatible system `glibc`; DepTracer does not and should not attempt to bundle arbitrary core OS libraries.
- License scanning is a warning/reporting aid, not legal advice.
