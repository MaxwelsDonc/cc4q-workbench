"""Download and verify the CC4Q model checkpoints (CLI).

The checkpoints ship as release assets of this repository (they are too
large for git):

    https://github.com/MaxwelsDonc/cc4q-workbench/releases/tag/v0.2.0

Usage (from the workbench root, Python >= 3.11, no extra deps):

    python scripts/download_models.py            # download what is missing
    python scripts/download_models.py --check    # verify only, exit 1 if incomplete

Each asset is a tar.gz of one checkpoint directory. After download the
SHA256 checksum is verified before extraction into models_checkpoints/.
The implementation lives in cc4q.models.hub.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cc4q.models.hub import ensure_checkpoints, missing_checkpoints


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="verify only; exit 1 if any checkpoint is missing")
    parser.add_argument("--with-base", action="store_true",
                        help="also fetch the bert-base-uncased base model "
                             "(only needed for from-scratch fine-tuning)")
    args = parser.parse_args()

    missing = missing_checkpoints()
    if args.check:
        if missing:
            print(f"MISSING: {', '.join(missing)}")
            print("Run: python scripts/download_models.py")
            sys.exit(1)
        print("OK: all model checkpoints present.")
        return

    still_missing = ensure_checkpoints(with_base=args.with_base)
    if still_missing:
        print(f"FAILED: still missing {', '.join(still_missing)}")
        sys.exit(1)
    print("Done — all model checkpoints present.")


if __name__ == "__main__":
    main()
