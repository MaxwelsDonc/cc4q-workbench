"""cc4q command line interface (WP4 will flesh out subcommands)."""

import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    print("cc4q — build, inspect, and profile labeled comment corpora")
    print()
    print("Python API:  import cc4q")
    print("Pipeline:    python scripts/01_download_repos.py / 02_... / 03_...")
    print("Demo app:    streamlit run demo/app.py")
    print()
    print("CLI subcommands land in a future release (see README).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
