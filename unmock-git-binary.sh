#!/bin/bash
set -eox pipefail

# Restore the primary Git binary
sudo mv "${BACKUP_GIT_PATH}" "${ORIGINAL_GIT_PATH}"

# Restore Xcode's Git binary if it was backed up
if [[ -n "${BACKUP_XCODE_GIT_PATH}" ]]; then
    XCODE_GIT_PATH="$(xcode-select -p)/usr/bin/git"
    sudo mv "${BACKUP_XCODE_GIT_PATH}" "${XCODE_GIT_PATH}"
    echo "unset BACKUP_XCODE_GIT_PATH" >> "${BASH_ENV}"
fi

# Clean up environment variables
echo "unset ORIGINAL_GIT_PATH" >> "${BASH_ENV}"
echo "unset BACKUP_GIT_PATH" >> "${BASH_ENV}"