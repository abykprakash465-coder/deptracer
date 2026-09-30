from __future__ import annotations

import argparse

from . import __version__
from .config import Config
from .core import run_akdeptracer
from .explain import explain_problem
from .license import scan_environment
from .clean_verify import verify_clean


def main():
    p = argparse.ArgumentParser(
        prog="deptracer",
        description="Runtime dependency tracer and PyInstaller auto-patcher",
    )
    p.add_argument("--version", action="version", version=f"deptracer {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", dest="verbose_root")
    sub = p.add_subparsers(dest="command")

    b = sub.add_parser("build", help="Trace, patch, rebuild and verify")
    b.add_argument("project_dir")
    b.add_argument("binary_name")
    b.add_argument("spec_name")
    b.add_argument("-v", "--verbose", action="store_true", dest="verbose_sub")
    b.add_argument("--timeout", type=float, help="trace timeout in seconds")
    b.add_argument("--build-timeout", type=float)
    b.add_argument("--max-iterations", type=int)
    b.add_argument("--max-seconds", type=float)
    b.add_argument("--resolver-timeout", type=float)
    b.add_argument("--workers", type=int)
    b.add_argument("--search-path", action="append", default=[])
    b.add_argument("--no-resume", action="store_true")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--json", action="store_true")

    e = sub.add_parser("explain", help="Show structured history from the last run")
    e.add_argument("--project-dir", default=".")
    e.add_argument("--json", action="store_true")
    e.add_argument("-v", "--verbose", action="store_true", dest="verbose_sub")

    c = sub.add_parser("verify-clean", help="Run the final binary in a disposable Docker/Podman environment")
    c.add_argument("binary")
    c.add_argument("--image", default="ubuntu:24.04")
    c.add_argument("--timeout", type=float, default=180.0)
    c.add_argument("-v", "--verbose", action="store_true", dest="verbose_sub")

    l = sub.add_parser("license", help="Report package license metadata in the build environment")
    l.add_argument("--json", action="store_true")
    l.add_argument("--fail-on-gpl", action="store_true")
    l.add_argument("-v", "--verbose", action="store_true", dest="verbose_sub")

    args = p.parse_args()
    verbose = bool(args.verbose_root or getattr(args, "verbose_sub", False))

    if args.command == "build":
        cfg = Config(
            verbose=verbose,
            trace_timeout=args.timeout or 120.0,
            build_timeout=args.build_timeout or 300.0,
            max_iterations=args.max_iterations or 10,
            max_seconds=args.max_seconds or 1800.0,
            resolver_timeout=args.resolver_timeout or 30.0,
            max_resolver_workers=args.workers or 8,
            resume=not args.no_resume,
            dry_run=args.dry_run,
            json_output=args.json,
            search_paths=args.search_path,
        )
        ok = run_akdeptracer(
            args.project_dir, args.binary_name, args.spec_name,
            verbose=verbose, config=cfg
        )
        raise SystemExit(0 if ok else 1)

    if args.command == "explain":
        explain_problem(args.project_dir, json_output=args.json)
        return

    if args.command == "verify-clean":
        try:
            ok, output = verify_clean(args.binary, image=args.image, timeout=args.timeout)
        except (RuntimeError, FileNotFoundError) as exc:
            print(f"[VERIFY] {exc}")
            raise SystemExit(2)
        print(output)
        print("[VERIFY] CLEAN ENVIRONMENT: " + ("PASS" if ok else "FAIL"))
        raise SystemExit(0 if ok else 1)

    if args.command == "license":
        rows = scan_environment()
        flagged = [r for r in rows if r["flag"]]
        if args.json:
            import json
            print(json.dumps(rows, indent=2))
        else:
            print("Package license report")
            for row in rows:
                marker = "  <-- REVIEW" if row["flag"] else ""
                print(f"{row['package']}: {row['license']}{marker}")
        if args.fail_on_gpl and flagged:
            raise SystemExit(2)
        return

    p.print_help()


if __name__ == "__main__":
    main()
