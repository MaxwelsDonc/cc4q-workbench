"""Clone the repositories listed in a repo-list config into the input dir.

Each entry in `repos` is either a plain URL (clones the default branch) or a
mapping with `url` and an optional `ref` (tag, branch, or commit) to pin the
checkout, e.g.:

    repos:
      - https://github.com/Qiskit/qiskit-aer
      - url: https://github.com/qiskit-community/qiskit-nature
        ref: "0.8"

Usage:
    python scripts/01_download_repos.py [config/repo_list.yaml]

Exit status is nonzero if any clone fails or an existing checkout does not
match the requested ref. The implementation lives in cc4q.pipeline.download.
"""

import os
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cc4q.pipeline.download import clone_repo


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        'config', 'repo_list.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    output_dir = config.get('output_dir', 'data/input')
    os.makedirs(output_dir, exist_ok=True)
    failed = False
    for repo in config['repos']:
        try:
            if not clone_repo(repo, output_dir):
                failed = True
        except subprocess.CalledProcessError:
            print(f'[✗] Failed to clone: {repo}', file=sys.stderr)
            failed = True
    if failed:
        print('[✗] One or more repositories could not be prepared',
              file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
