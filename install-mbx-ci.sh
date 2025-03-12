#!/bin/bash

if [[ "${MBX_CI_ALLOW_INSTALL_FAILLURE}" == "true" ]]; then
    echo "WARNING: Failures allowed. Command will exit with code 0, whatever happens."
fi

system=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')
filename="mbx-ci-${system}-${arch}"
target="${MBX_CI_INSTALL_DIR}/mbx-ci"

if [ ! -x "$target" ]; then
    mkdir -p "$MBX_CI_INSTALL_DIR"
    if ! curl -L -f --retry 3 "${MBX_CI_URL}/${filename}" -o "$target"; then
        if [[ "${MBX_CI_ALLOW_INSTALL_FAILLURE}" != "true" ]]; then
            exit 1
        fi
    fi
    chmod 755 "$target"
else
    echo "mbx-ci already installed in ${MBX_CI_INSTALL_DIR}"
fi

{
    echo 'export MBX_CI_DOMAIN=o619qyc20d.execute-api.us-east-1.amazonaws.com'
    echo 'export AWS_SDK_LOAD_CONFIG=1'
    echo "export PATH=\$PATH:${MBX_CI_INSTALL_DIR}"
} >> "${BASH_ENV:-/tmp/bash_env}"

if ! source "${BASH_ENV:-/tmp/bash_env}"; then
    if [[ "${MBX_CI_ALLOW_INSTALL_FAILLURE}" != "true" ]]; then
        exit 1
    fi
fi

if ! mbx-ci --version || ! mbx-ci --help; then
    if [[ "${MBX_CI_ALLOW_INSTALL_FAILLURE}" != "true" ]]; then
        exit 1
    fi
fi

exit 0
