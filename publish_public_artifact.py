#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import os
from urllib import parse, request
from urllib.error import HTTPError

API_URL = "https://api.github.com"


def get_release_by_tag(token, api_url, repo_owner, repo_name, tag_name):
    """Get release information by tag name."""
    url = f"{api_url}/repos/{repo_owner}/{repo_name}/releases/tags/{tag_name}"
    req = request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with request.urlopen(req) as f:
            return json.loads(f.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        return json.loads(e.read().decode("utf-8"))


def create_release(token, api_url, repo_owner, repo_name, tag_name):
    """Create a release if it doesn't exist."""
    url = f"{api_url}/repos/{repo_owner}/{repo_name}/releases"
    data = json.dumps(
        {
            "tag_name": tag_name,
            "name": tag_name,
            "body": "see assets below",
            "make_latest": str(False).lower(),
            "draft": False,
            "prerelease": False,
        }
    ).encode("utf-8")

    req = request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with request.urlopen(req) as f:
            return json.loads(f.read().decode("utf-8"))
    except HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def delete_asset(token, api_url, repo_owner, repo_name, asset_id):
    """Delete an existing asset."""
    url = f"{api_url}/repos/{repo_owner}/{repo_name}/releases/assets/{asset_id}"
    req = request.Request(url, method="DELETE")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        request.urlopen(req)
        return True
    except HTTPError:
        return False


def upload_asset(token, upload_url, file_path, file_name):
    """Upload an asset to the release."""
    params = {"name": file_name}
    query_string = parse.urlencode(params)
    upload_url = f"{upload_url}?{query_string}"

    with open(file_path, "rb") as f:
        data = f.read()

    req = request.Request(upload_url, data=data, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Content-Type", "application/zip")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with request.urlopen(req) as f:
            return json.loads(f.read().decode("utf-8"))
    except HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def get_upload_files(directory, tag, short_commit):
    """Get list of files to upload with their target names."""
    files = []
    for filename in os.listdir(directory):
        if not os.path.isfile(os.path.join(directory, filename)):
            continue

        base_name, ext = os.path.splitext(filename)

        # Create versioned and latest variants for each file
        files.append(
            {
                "source_path": os.path.join(directory, filename),
                "versioned_name": f"{tag}-{base_name}-{short_commit}{ext}",
                "latest_name": f"{tag}-{base_name}-latest{ext}",
            }
        )
    return files


def upload_file_pair(args):
    """Upload both versioned and latest variants of a file."""
    token, upload_url, file_info = args
    results = []

    # Upload versioned file
    print(f"Uploading {file_info['versioned_name']}")
    version_result = upload_asset(
        token, upload_url, file_info["source_path"], file_info["versioned_name"]
    )
    results.append(version_result)

    # Upload latest file
    print(f"Uploading {file_info['latest_name']}")
    latest_result = upload_asset(
        token, upload_url, file_info["source_path"], file_info["latest_name"]
    )
    results.append(latest_result)

    return results


def main(args):
    # Check if release exists
    release_info = get_release_by_tag(
        args.token, API_URL, args.repo_owner, args.repo_name, args.tag
    )

    # Create release if it doesn't exist
    if not release_info:
        print(f"Creating new release for {args.tag}")
        release_info = create_release(
            args.token, API_URL, args.repo_owner, args.repo_name, args.tag
        )
        if "id" not in release_info:
            print("Failed to create release:", release_info)
            exit(1)

    upload_url = release_info["upload_url"].split("{")[0]
    short_commit = args.commit_sha[:7]

    # Get list of files to upload
    if os.path.isdir(args.path):
        files = get_upload_files(args.path, args.tag, short_commit)
    else:
        # Single file mode
        _, ext = os.path.splitext(os.path.basename(args.path))
        files = [
            {
                "source_path": args.path,
                "versioned_name": f"{args.tag}-{short_commit}{ext}",
                "latest_name": f"{args.tag}-latest{ext}",
            }
        ]

    # Delete existing latest assets if they exist
    for asset in release_info.get("assets", []):
        for file_info in files:
            if asset["name"] == file_info["latest_name"]:
                print(f"Removing existing {asset['name']}")
                delete_asset(
                    args.token, API_URL, args.repo_owner, args.repo_name, asset["id"]
                )

    # Upload files in parallel
    success = True
    upload_args = [(args.token, upload_url, file_info) for file_info in files]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(upload_file_pair, arg) for arg in upload_args]
        for future in concurrent.futures.as_completed(futures):
            try:
                results = future.result()
                for result in results:
                    if "id" not in result:
                        success = False
                        print("Failed to upload:", result)
            except Exception as e:
                success = False
                print(f"Error during upload: {e}")

    if success:
        print("\nAll uploads successful!")
        print("\nDownload URLs:")
        for file_info in files:
            print(f"\nFor {os.path.basename(file_info['source_path'])}:")
            print(
                f"Versioned: https://github.com/{args.repo_owner}/{args.repo_name}/releases/download/{args.tag}/{file_info['versioned_name']}"
            )
            print(
                f"Latest: https://github.com/{args.repo_owner}/{args.repo_name}/releases/download/{args.tag}/{file_info['latest_name']}"
            )
    else:
        print("\nSome uploads failed!")
        exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload tag releases to GitHub with versioned and latest artifacts."
    )
    parser.add_argument("--token", required=True, help="GitHub access token")
    parser.add_argument(
        "--repo_owner", required=False, default="mapbox", help="Owner of the repository"
    )
    parser.add_argument(
        "--repo_name",
        required=False,
        default="sdk-cicd-public",
        help="Name of the repository",
    )
    parser.add_argument("--tag", required=True, help="Name of the tag")
    parser.add_argument(
        "--commit_sha", required=True, help="Commit SHA or version identifier"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to either a single file or directory containing multiple files to upload",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
