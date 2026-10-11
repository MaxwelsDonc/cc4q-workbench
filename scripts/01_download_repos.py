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
"""

import os
import subprocess
import sys

import yaml


def clone_repo(repo, output_dir):
    if isinstance(repo, str):
        url, ref = repo, None
    else:
        url, ref = repo['url'], repo.get('ref')
    name = url.strip().split('/')[-1].replace('.git', '')
    repo_path = os.path.join(output_dir, name)

    if os.path.exists(repo_path):
        if ref:
            actual = subprocess.run(
                ['git', '-C', repo_path, 'describe', '--tags', '--always'],
                capture_output=True, text=True, check=True).stdout.strip()
            if actual != ref:
                print(f'[✗] {name}: existing checkout is at "{actual}", '
                      f'expected "{ref}" - remove {repo_path} to re-clone',
                      file=sys.stderr)
                return False
        print(f'[✓] Skipping existing repo: {name}')
        return True

    cmd = ['git', 'clone', '--depth', '1']
    if ref:
        cmd += ['--branch', ref]
    cmd += [url, repo_path]
    label = f'{name}@{ref}' if ref else name
    print(f'[→] Cloning {label}...')
    subprocess.run(cmd, check=True)
    return True


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
