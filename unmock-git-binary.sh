#!/bin/bash
set -eox pipefail

sudo mv "${BACKUP_GIT_PATH}" "${ORIGINAL_GIT_PATH}"
echo "unset ORIGINAL_GIT_PATH" >> $BASH_ENV
echo "unset BACKUP_GIT_PATH" >> $BASH_ENV