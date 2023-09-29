#!/bin/bash
set -eox pipefail

ORIGINAL_GIT_PATH="$(command -v git)"
if [[ -n "${TMPDIR}" ]]; then
    TEMP_DIR="${TMPDIR}"
else
    TEMP_DIR="/tmp"
fi
BACKUP_GIT_PATH="${TEMP_DIR%/}/git_bak"
sudo mv "${ORIGINAL_GIT_PATH}" "${BACKUP_GIT_PATH}"
echo -e '#!/bin/sh\necho "MOCKED: $0 $@"' | sudo tee "${ORIGINAL_GIT_PATH}"
sudo chmod +x "${ORIGINAL_GIT_PATH}"
echo "export ORIGINAL_GIT_PATH=\"${ORIGINAL_GIT_PATH}\"" >> $BASH_ENV
echo "export BACKUP_GIT_PATH=\"${BACKUP_GIT_PATH}\"" >> $BASH_ENV