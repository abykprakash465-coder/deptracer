# Original DepTracer vs Enhanced DepTracer

This repository is an enhanced, competition-oriented version of the original
[TatHack-Tathva/deptracer](https://github.com/TatHack-Tathva/deptracer).

## What was present in the supplied/original repository

| Area | Original repository | Enhanced version |
|---|---|---|
| Runtime tracing | `strace` + bubblewrap | Same approach, with process timeout and better tracing/parsing |
| Dependency parser | File-open parsing with broad noise filtering | More syscall forms, versioned shared libraries, safer noise filtering, exact-path status tracking |
| Dependency resolver | Sequential search with `find` | Multiple search zones, custom paths, Conda/venv awareness, parallel resolution, per-search timeout |
| Spec patching | Line-oriented `binaries`/`datas` insertion | Managed additions, duplicate prevention, safe Python literals, atomic spec update |
| Build loop | Rebuild/retrace until clean | Iteration limit + wall-clock budget + checkpoints + better failure handling |
| Build timeout | Missing | Configurable timeout with process-group termination |
| Trace timeout | Missing | Configurable timeout with process-group termination |
| Resume | Flat `.akdeptracer_state` | Structured `.deptracer/state.json`; resumes an in-flight iteration safely |
| Dry run | Missing | `--dry-run` previews fixes without rebuilding |
| JSON output | Missing | Structured JSON events + JSON explain mode |
| Custom search paths | Not fully wired | Repeatable `--search-path` and config support |
| Conda/Poetry/Pipenv layouts | Limited | Searches common virtualenv/Conda/project locations |
| Clean verification | Concept described | `verify-clean` using Docker/Podman when available |
| License review | Missing | Optional installed-package license/classifier scan |
| CI | Missing | GitHub Actions workflow for tests/build checks |
| Hanging-process protection | Missing | Dedicated process runner with timeout and process-group cleanup |
| Test coverage | Limited | Parser, fixer, process, history, and clean-verifier tests |
| CLI | Basic build/explain | Build, explain, verify-clean, license, timeout/budget/search-path options |
| Architecture & documentation | Minimal README, no system design or workflow diagrams | Comprehensive architecture documentation with Mermaid lifecycle flowchart and component breakdown |

## Important corrections

### 1. Process timeouts
The original tracer and compiler could wait indefinitely. The enhanced
implementation routes subprocess execution through `deptracer/process.py`,
which terminates the process group on timeout.

### 2. Safer parser filtering
The original parser treated names beginning with `_` as system noise. That can
hide legitimate runtime assets such as `_plugin.so` or `_model.pt`. The enhanced
parser removes that broad rule and uses narrower system-specific filters.

### 3. Exact-path dependency status
Dependency state is tracked using normalized paths instead of only basenames.
This avoids a found file with a common basename masking a missing file at a
different path.

### 4. Controlled iteration
The enhanced core has both a maximum iteration count and a maximum wall-clock
budget. This prevents an endless dependency-fix loop from consuming the whole
CI/demo machine.

### 5. Crash-safe resume
The enhanced core checkpoints an iteration as `running` before tracing. If the
process is interrupted after a patch but before the build finishes, resume
repeats that in-flight iteration instead of skipping the rebuild.

### 6. Clean-environment proof
The enhanced project adds an explicit `verify-clean` command. This is the
competition acceptance step: the fixed binary should be executed in a disposable
Docker/Podman environment rather than relying only on the tracing sandbox.

### 7. Clear architecture & workflow documentation
The original codebase lacked high-level architectural documentation and visual workflow representations. The enhanced version adds a comprehensive Mermaid architecture diagram and component breakdown in the README, detailing the multi-stage convergence loop from Bubblewrap isolation to container-based clean verification.

## New competition features

- `--timeout`
- `--build-timeout`
- `--max-iterations`
- `--max-seconds`
- `--resolver-timeout`
- `--workers`
- `--search-path`
- `--dry-run`
- `--no-resume`
- `--json`
- `verify-clean`
- `license`
- structured state/history
- JSON event logging
- GitHub Actions CI
- examples for runtime dependencies and hanging processes
- end-to-end Mermaid architecture and lifecycle workflow diagram in README

## Validation already performed on the enhanced code

The enhanced pack was unit-tested successfully with:

```text
7 passed in 0.27s
```

The package was also built and installed successfully as version `0.3.0`, and:

```text
deptracer --version
```

reports:

```text
deptracer 0.3.0
```

A full PyInstaller + strace + bubblewrap + clean-container integration test
still needs to be executed in a Linux environment that has those tools. Do not
claim the competition's final clean-machine requirement is proven until that
integration test passes.
