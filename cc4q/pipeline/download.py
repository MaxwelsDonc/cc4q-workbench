"""Repository download helpers (git clone --depth 1, optional pinned ref)."""

import os
import subprocess


def clone_repo(repo, output_dir):
    """Clone one repo entry into ``output_dir``.

    ``repo`` is either a plain URL (default branch) or a mapping with
    ``url`` and an optional ``ref`` (tag/branch/commit). Existing checkouts
    are skipped when they match the requested ref. Returns True when the
    checkout satisfies the request, False otherwise.

    Raises subprocess.CalledProcessError when git clone fails.
    """
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
                      file=os.sys.stderr)
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
