# Competition Changelog

## 0.3.0 — Competition enhancement

### Fixed
- Added subprocess timeout handling.
- Added build timeout handling.
- Prevented unbounded iteration loops.
- Improved dependency parsing and system-noise filtering.
- Prevented basename collisions from hiding missing paths.
- Made spec modifications safer and atomic.
- Made resume crash-safe for in-flight iterations.

### Added
- Resume state in `.deptracer/state.json`.
- Dry-run mode.
- JSON event output.
- Custom resolver search paths.
- Parallel dependency resolution.
- Conda/virtualenv-aware search paths.
- Docker/Podman clean verification.
- License review command.
- GitHub Actions workflow.
- Runtime dependency and timeout examples.
- Automated tests for the new infrastructure.

### Known integration work
- A genuine PyInstaller runtime-dependency case must be tested on Linux.
- The clean verifier requires Docker or Podman on the test host.
- PyInstaller's Linux/glibc compatibility requirements still apply.
