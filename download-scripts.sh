#!/bin/bash
set -eox pipefail

if [[ -n "${TMPDIR}" ]]; then
    TEMP_DIR="${TMPDIR}"
else
    TEMP_DIR="/tmp"
fi

SDK_CICD_PUBLIC_SCRIPTS_PATH="${TEMP_DIR%/}/sdk-cicd-public"

mkdir -p "${SDK_CICD_PUBLIC_SCRIPTS_PATH}"
curl -L https://github.com/mapbox/sdk-cicd-public/archive/refs/heads/main.tar.gz -o "${SDK_CICD_PUBLIC_SCRIPTS_PATH}/scripts.tar.gz"
tar -xzf "${SDK_CICD_PUBLIC_SCRIPTS_PATH}/scripts.tar.gz" --strip-components=1 -C "${SDK_CICD_PUBLIC_SCRIPTS_PATH}" && rm "${SDK_CICD_PUBLIC_SCRIPTS_PATH}/scripts.tar.gz"

echo "export SDK_CICD_PUBLIC_SCRIPTS_PATH=\"${SDK_CICD_PUBLIC_SCRIPTS_PATH}\"" >> $BASH_ENV
