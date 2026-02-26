"""
Fetch raw ephemeris text files for 50 NEOCP objects from NEOScan (G83/LBT).
Saves each result to tests/neoscan_ephemeris_{objname}_G83.txt.
Run from the project root: python tests/fetch_ephemeris.py
"""
import time
from pathlib import Path

from raprock.neoscan import get_objects, _post_ephemeris_request

TSTART = {"year0": "2026", "month0": "02", "day0": "26", "hour0": "18", "mins0": "00"}
TEND   = {"year1": "2026", "month1": "03", "day1": "10", "hour1": "18", "mins1": "00"}
STEP   = {"interval": "60.0", "intunit": "minutes"}
CODE   = "G83"

OUT_DIR = Path(__file__).parent
MAX_OBJECTS = 50
WAIT_S = 30


def main():
    print("Fetching NEOCP object list...")
    objects = get_objects()
    targets = objects[:MAX_OBJECTS]
    print(f"  {len(objects)} objects available, fetching ephemeris for {len(targets)}")

    for i, name in enumerate(targets, 1):
        out_path = OUT_DIR / f"neoscan_ephemeris_{name}_G83.txt"

        if out_path.exists():
            print(f"[{i:2d}/{len(targets)}] {name}: already exists, skipping")
            continue

        payload = {"any_name": name, "code": CODE, **TSTART, **TEND, **STEP}

        print(f"[{i:2d}/{len(targets)}] {name}: requesting...", end=" ", flush=True)
        try:
            eph_text = _post_ephemeris_request(payload)
            out_path.write_text(eph_text)
            print(f"saved ({len(eph_text):,} bytes)")
        except Exception as e:
            print(f"FAILED: {e}")

        if i < len(targets):
            print(f"  waiting {WAIT_S}s...")
            time.sleep(WAIT_S)


if __name__ == "__main__":
    main()
