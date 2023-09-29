#!/bin/bash
set -eox pipefail

sudo mv "${BACKUP_GIT_PATH}" "${ORIGINAL_GIT_PATH}"
# shellcheck disable=SC2086
echo "unset ORIGINAL_GIT_PATH" >> $BASH_ENV
# shellcheck disable=SC2086
echo "unset BACKUP_GIT_PATH" >> $BASH_ENV