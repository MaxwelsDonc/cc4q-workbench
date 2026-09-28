import os
import subprocess
import yaml

def clone_repo(repo_url, output_dir):
    repo_name = repo_url.strip().split('/')[-1].replace('.git', '')
    repo_path = os.path.join(output_dir, repo_name)
    if os.path.exists(repo_path):
        print(f'[✓] Skipping existing repo: {repo_name}')
    else:
        print(f'[→] Cloning {repo_name}...')
        subprocess.run(['git', 'clone', '--depth', '1', repo_url, repo_path], check=True)

def main():
    config_path = os.path.join('config', 'repo_list.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    output_dir = config.get('output_dir', 'data/input')
    os.makedirs(output_dir, exist_ok=True)
    for repo_url in config['repos']:
        try:
            clone_repo(repo_url, output_dir)
        except subprocess.CalledProcessError:
            print(f'[✗] Failed to clone: {repo_url}')
if __name__ == '__main__':
    main()
