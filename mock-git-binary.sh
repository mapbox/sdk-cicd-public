#!/bin/bash
set -eox pipefail

ORIGINAL_GIT_PATH="$(readlink -f "$(command -v git)")"
if [[ -n "${TMPDIR}" ]]; then
    TEMP_DIR="${TMPDIR}"
else
    TEMP_DIR="/tmp"
fi
BACKUP_GIT_PATH="${TEMP_DIR%/}/git_bak"

# Backup and mock the primary Git binary
sudo mv "${ORIGINAL_GIT_PATH}" "${BACKUP_GIT_PATH}"
# shellcheck disable=SC2016
echo -e '#!/bin/sh\necho "MOCKED COMMAND: $0 $@"' | sudo tee "${ORIGINAL_GIT_PATH}"
sudo chmod +x "${ORIGINAL_GIT_PATH}"

# Check for macOS and mock Xcode's Git binary if it exists
if [[ "$(uname)" == "Darwin" ]]; then
    XCODE_GIT_PATH="$(xcode-select -p)/usr/bin/git"
    if [[ -f "${XCODE_GIT_PATH}" ]]; then
        BACKUP_XCODE_GIT_PATH="${TEMP_DIR%/}/xcode_git_bak"
        sudo mv "${XCODE_GIT_PATH}" "${BACKUP_XCODE_GIT_PATH}"
        sudo ln -s "${ORIGINAL_GIT_PATH}" "${XCODE_GIT_PATH}"
        echo "export BACKUP_XCODE_GIT_PATH=\"${BACKUP_XCODE_GIT_PATH}\"" >> "${BASH_ENV}"
    fi
fi


# Environment variables to restore original paths later
echo "export ORIGINAL_GIT_PATH=\"${ORIGINAL_GIT_PATH}\"" >> "${BASH_ENV}"
echo "export BACKUP_GIT_PATH=\"${BACKUP_GIT_PATH}\"" >> "${BASH_ENV}"