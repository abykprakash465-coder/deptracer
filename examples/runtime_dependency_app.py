import os
import sys
from ctypes import CDLL
from pathlib import Path

# This example demonstrates runtime-loaded dependencies that static PyInstaller analysis misses:
# 1. A runtime data file located in data/sample_data.json
# 2. A native shared library loaded dynamically via ctypes.CDLL


def main():
    print("[APP] Starting runtime dependency demo application...")

    # 1. Runtime Data Dependency
    # PyInstaller extracts bundled files to sys._MEIPASS in onefile mode or next to the executable
    bundle_dir = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    data_file = Path(bundle_dir) / "data" / "sample_data.json"

    print(f"[APP] Reading runtime data file: {data_file}")
    if not data_file.exists():
        # Fallback to local repo path if running unbundled
        local_data = Path(__file__).resolve().parent / "data" / "sample_data.json"
        if local_data.exists():
            data_file = local_data
        else:
            print(f"[APP] Missing required runtime data: {data_file}", file=sys.stderr)
            sys.exit(1)

    print(f"[APP] Successfully read runtime data: {data_file.read_text(encoding='utf-8').strip()}")

    # 2. Runtime Dynamic Shared Library Dependency
    lib_path = os.environ.get("SAMPLE_LIB_PATH", "libsample.so")
    print(f"[APP] Attempting to load dynamic shared library: {lib_path}")
    try:
        CDLL(lib_path)
        print(f"[APP] Successfully loaded {lib_path} via CDLL.")
    except OSError as exc:
        print(f"[APP] Could not load dynamic library: {exc}", file=sys.stderr)
        # If running as a test demo, exit with code 1 so deptracer detects missing dependency
        sys.exit(1)

    print("[APP] All runtime dependencies verified.")


if __name__ == "__main__":
    main()
