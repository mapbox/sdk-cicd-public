#!/bin/bash
set -eox pipefail

ORIGINAL_GIT_PATH="$(readlink -f "$(command -v git)")"
if [[ -n "${TMPDIR}" ]]; then
    TEMP_DIR="${TMPDIR}"
else
    TEMP_DIR="/tmp"
fi
BACKUP_GIT_PATH="${TEMP_DIR%/}/git_bak"
sudo mv "${ORIGINAL_GIT_PATH}" "${BACKUP_GIT_PATH}"
# shellcheck disable=SC2016
echo -e '#!/bin/sh\necho "MOCKED COMMAND: $0 $@"' | sudo tee "${ORIGINAL_GIT_PATH}"
sudo chmod +x "${ORIGINAL_GIT_PATH}"
# shellcheck disable=SC2086
echo "export ORIGINAL_GIT_PATH=\"${ORIGINAL_GIT_PATH}\"" >> $BASH_ENV
# shellcheck disable=SC2086
echo "export BACKUP_GIT_PATH=\"${BACKUP_GIT_PATH}\"" >> $BASH_ENV