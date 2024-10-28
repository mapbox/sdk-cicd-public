#!/bin/bash

# Usage: ./download-release.sh owner repo tag "asset1 asset2 asset3"
# Example: ./download-release.sh cli cli v1.0.0 "cli-linux-amd64 cli-darwin-amd64 cli-windows-amd64.exe"

if [ "$#" -lt 4 ]; then
    echo "Usage: $0 owner repo tag \"asset1 asset2 ...\""
    echo "Example: $0 kubernetes kubectl v1.28.0 \"kubectl-linux-amd64.tar.gz kubectl-darwin-amd64.tar.gz\""
    exit 1
fi

OWNER=$1
REPO=$2
TAG=$3
ASSETS=$4

# Get the release information once
RELEASE_INFO=$(curl -s "https://api.github.com/repos/$OWNER/$REPO/releases/tags/$TAG")

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch release information"
    exit 1
fi

# Function to download a single asset
download_asset() {
    local asset_name=$1
    local asset_url=$(echo "$RELEASE_INFO" | grep -o "https://.*$asset_name" | head -n1)
    
    if [ -z "$asset_url" ]; then
        echo "Warning: Asset '$asset_name' not found in release"
        return 1
    fi

    echo "Downloading $asset_name..."
    curl -L -H "Accept: application/octet-stream" \
         --progress-bar \
         -o "$asset_name" \
         "$asset_url"
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully downloaded: $asset_name"
        return 0
    else
        echo "✗ Failed to download: $asset_name"
        return 1
    fi
}

# Initialize counters
total=0
successful=0

# Download each asset
for asset in $ASSETS; do
    total=$((total + 1))
    if download_asset "$asset"; then
        successful=$((successful + 1))
    fi
    echo "----------------------------------------"
done

# Print summary
echo "Download Summary:"
echo "Successfully downloaded: $successful/$total assets"
if [ $successful -ne $total ]; then
    echo "Failed downloads: $((total - successful))"
    exit 1
fi