import json
import os
import tarfile
import argparse
import urllib.request
from urllib.error import HTTPError
from tempfile import gettempdir


def download_asset(asset_url, token, save_path):
    """Download a release asset from GitHub."""
    request = urllib.request.Request(asset_url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/octet-stream")

    try:
        with urllib.request.urlopen(request) as response:
            with open(save_path, "wb") as f:
                f.write(response.read())
        print(f"Asset downloaded successfully and saved to {save_path}")
    except HTTPError as e:
        print(f"Error downloading asset: HTTP {e.code} - {e.reason}")
        raise


def get_release_by_tag(owner, repo, tag, token):
    """Retrieve a release by its tag."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(request) as response:
            release = json.load(response)
            return release
    except HTTPError as e:
        if e.code == 404:
            return None  # Release not found
        else:
            raise


def get_latest_release(owner, repo, token):
    """Fetch the latest release from the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(request) as response:
            release = json.load(response)
            return release
    except HTTPError as e:
        print(f"Error fetching latest release: HTTP {e.code} - {e.reason}")
        raise


def untar_strip_components(tar, strip: int):
    """Helper to strip components from paths in tar files."""
    for member in tar.getmembers():
        parts = member.path.split("/", strip)
        if len(parts) == strip:
            continue
        member.path = parts[-1]
        yield member


def main(args):
    owner = args.owner
    repo = args.repo
    version = args.version
    token = args.token
    asset_name = args.asset_name
    output_dir = args.output_dir

    matching_release = (
        get_latest_release(owner, repo, token)
        if version == "develop"
        else get_release_by_tag(owner, repo, version, token)
    )
    if version == "develop":
        matching_release = get_latest_release(owner, repo, token)
    else:
        try:
            matching_release = get_release_by_tag(owner, repo, version, token)
        except Exception:
            matching_release = get_release_by_tag(
                owner, repo, f"untagged-{version[:7]}", token
            )

    if not matching_release:
        print(f"No release found for version {version}")
        exit(1)

    filtered_assets = [
        asset for asset in matching_release["assets"] if asset_name in asset["name"]
    ]
    if not filtered_assets:
        print("No assets match the specified pattern.")
        exit(1)

    asset = filtered_assets[0]
    asset_path = os.path.join(gettempdir(), asset["name"])
    asset_url = asset["url"]
    print(f"Downloading to {asset_path} ...")
    download_asset(asset_url, token, asset_path)

    with tarfile.open(asset_path) as tar_archive:
        tar_archive.extractall(
            path=output_dir, members=untar_strip_components(tar_archive, 1)
        )
    print(f"Files have been extracted to {output_dir}")

    os.remove(asset_path)
    if os.getenv("CIRCLECI"):
        appended_path = f"export PATH={output_dir}:$PATH"
        print(f"Populated BASH_ENV with {appended_path}")
        with open(os.getenv("BASH_ENV"), "w") as f:
            f.write(appended_path + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and extract GitHub repository assets."
    )
    parser.add_argument("--owner", required=True, help="GitHub repository owner")
    parser.add_argument("--repo", required=True, help="GitHub repository name")
    parser.add_argument(
        "--version",
        required=True,
        help="Release version or 'develop' for the latest release",
    )
    parser.add_argument("--token", required=True, help="GitHub API token")
    parser.add_argument("--asset_name", required=True, help="Asset name")
    parser.add_argument(
        "--output_dir", required=True, help="Place for the asset contents"
    )
    args = parser.parse_args()
    main(args)
