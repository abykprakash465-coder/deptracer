import sys
import json
from pathlib import Path
from ctypes import CDLL

def main():
    print("[DEMO] Starting demo application...")

    # Look for bundled assets (sys._MEIPASS) or local fallback
    bundle_dir = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    config_path = Path(bundle_dir) / "config" / "settings.json"
    
    # 1. Load runtime data file
    print(f"[DEMO] Loading config from {config_path}...")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        print(f"[DEMO] Config loaded: {data['app_name']}")
    except Exception as e:
        print(f"[DEMO ERROR] Missing data asset: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load runtime C shared library
    print("[DEMO] Loading shared library 'libplugin.so'...")
    try:
        # Load without hardcoded path: relies on bundle's LD_LIBRARY_PATH
        lib = CDLL("libplugin.so")
        result = lib.compute_magic(10)
        print(f"[DEMO] Native C function returned: {result}")
    except Exception as e:
        print(f"[DEMO ERROR] Missing shared library: {e}", file=sys.stderr)
        sys.exit(1)

    print("[DEMO SUCCESS] All runtime dependencies verified!")

if __name__ == "__main__":
    main()
