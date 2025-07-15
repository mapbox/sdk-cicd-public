#!/usr/bin/env python3
import json
import os
import tarfile
import argparse
import urllib.request
from urllib.error import HTTPError
from tempfile import gettempdir
import ssl

try:
    import certifi

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    handler = urllib.request.HTTPSHandler(context=ssl_context)
    opener = urllib.request.build_opener(handler)
    urllib.request.install_opener(opener)
except ImportError:
    pass


class NoRedirectsHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Prevent urllib from automatically following the redirect
        raise HTTPError(newurl, code, msg, headers, fp)


def download_asset(asset_url, token, save_path):
    """
    Download a release asset from GitHub. Will follow Azure redirects
    and strip Authorization header if needed.
    https://github.com/orgs/community/discussions/88698
    """
    request = urllib.request.Request(asset_url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/octet-stream")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

    opener = urllib.request.build_opener(NoRedirectsHandler())

    try:
        response = opener.open(request)
        with open(save_path, "wb") as f:
            f.write(response.read())
        print(f"Asset downloaded successfully to {save_path}")
        return
    except HTTPError as e:
        if e.code == 302:
            redirect_url = e.headers.get("Location")
            print("Redirected...")
            download_request = urllib.request.Request(redirect_url)
            with urllib.request.urlopen(download_request) as redirect_response:
                with open(save_path, "wb") as f:
                    f.write(redirect_response.read())
            print(f"Asset downloaded after redirect to {save_path}")
        else:
            print(f"Error downloading asset: HTTP {e.code} - {e.reason}")
            raise


def get_release_by_tag(owner, repo, tag, token):
    """Retrieve a release by its tag."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/vnd.github.v3+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

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
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urllib.request.urlopen(request) as response:
            release = json.load(response)
            return release
    except HTTPError as e:
        print(f"Error fetching latest release: HTTP {e.code} - {e.reason}")
        raise


def get_commit_hashes(owner, repo, branch, token):
    """Returns list of latest commit hashes for branch"""
    query_string = urllib.parse.urlencode({"sha": branch})
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?{query_string}"

    # Prepare the request
    request = urllib.request.Request(api_url)
    request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/vnd.github.v3+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urllib.request.urlopen(request) as response:
            data = response.read()
            commits = json.loads(data)
            commit_hashes = [commit["sha"] for commit in commits]
            return commit_hashes
    except HTTPError:
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

    if version == "develop":
        print("Searching latest release...")
        matching_release = get_latest_release(owner, repo, token)
    else:
        try:
            print(f"Searching tag {version}...")
            matching_release = get_release_by_tag(owner, repo, version, token)
            if not matching_release:
                raise
        except Exception:
            try:
                untagged_version = f"untagged-{version[:7]}"
                print(f"Searching untagged_version {untagged_version}...")
                matching_release = get_release_by_tag(
                    owner, repo, untagged_version, token
                )
                if not matching_release:
                    raise
            except Exception:
                print(f"Searching release from branch {version}...")
                for sha in get_commit_hashes(owner, repo, version, token):
                    untagged_version = f"untagged-{sha[:7]}"
                    matching_release = get_release_by_tag(
                        owner, repo, untagged_version, token
                    )
                    if matching_release:
                        print(f"Found untagged_version {untagged_version}")
                        break

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
        appended_path = f"export PATH=\"{output_dir}:$PATH\""
        print(f"Populated BASH_ENV with {appended_path}")
        with open(os.getenv("BASH_ENV"), "a") as f:
            f.write(appended_path)


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
