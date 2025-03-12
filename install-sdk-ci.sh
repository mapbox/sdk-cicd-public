#!/bin/bash

SDK_CI_INSTALL_STRATEGY="${SDK_CI_INSTALL_STRATEGY:-executable}"

if [[ "$SDK_CI_ALLOW_FAILURE" == "true" ]]; then
    echo "WARNING: Failures allowed. Command will exit with code 0, whatever happens."
fi

main() {
    if command -v sdk-ci &>/dev/null; then
        echo "sdk-ci already installed"
        exit 0
    fi

    if [[ "$SDK_CI_INSTALL_STRATEGY" == "executable" ]]; then
        curl -sL --retry 3 https://raw.githubusercontent.com/mapbox/sdk-cicd-public/main/download-scripts.sh | bash
        source $BASH_ENV

        # Function to set PIP_PATH based on the Python command
        set_pip_path_from_python() {
            # Check if the python command has pip available
            if $1 -m pip --version &>/dev/null; then
                PIP_PATH="$1 -m pip"
                return 0
            fi
            return 1
        }

        # Check if pip is available
        if command -v pip3 &>/dev/null; then
            PIP_PATH=$(command -v pip3)
        elif command -v pip &>/dev/null; then
            PIP_PATH=$(command -v pip)
        elif set_pip_path_from_python python3; then
            :
        elif set_pip_path_from_python python; then
            :
        else
            echo "pip is not installed and cannot be found under python or python3."
        fi

        install_certifi_cmd="$PIP_PATH --disable-pip-version-check install --upgrade certifi"
        $install_certifi_cmd --user || $install_certifi_cmd || true

        if (python3 "${SDK_CICD_PUBLIC_SCRIPTS_PATH}/install_cli_executable.py" \
            --owner mapbox \
            --repo sdk-cicd \
            --version $SDK_CI_VERSION \
            --token="$(mbx-ci github reader token)" \
            --asset_name="sdk-ci-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/').tar.gz" \
            --output_dir "${HOME}/sdk-ci" && source $BASH_ENV && sdk-ci --version); then
            exit 0
        else
            rm -rf "${HOME}/sdk-ci"
            echo "sdk-ci executable installation unsuccessful, fallback to installation from source"
            export SDK_CI_INSTALL_STRATEGY="https_api"
        fi
    fi

    TEMP_DIR="/tmp/"

    SDK_CI_VENV_DIR="${TEMP_DIR%/}/venv_sdk_ci"
    venv_create_cmd="python3 -m venv ${SDK_CI_VENV_DIR}"

    echo "Creating venv at ${SDK_CI_VENV_DIR} ..."
    install_python3_venv_cmd="sudo apt-get install --no-install-recommends python3-venv -y"
    # Check if the virtual environment directory exists.
    if ! test -d "${SDK_CI_VENV_DIR}/bin/python"; then
        echo "Virtual environment directory does not exist. Attempting to create..."
        # Attempt to create the virtual environment.
        if ! $venv_create_cmd; then
            echo "Failed to create virtual environment. Trying to install python3-venv..."
            # Update the system's package lists.
            sudo apt-get update || true
            # Install python3-venv package.
            if sudo apt-get install python3-venv -y; then
                echo "Successfully installed python3-venv. Attempting to create virtual environment again..."
                # Attempt to create the virtual environment again.
                if ! $venv_create_cmd; then
                    echo "Failed to create the virtual environment after installing python3-venv."
                else
                    echo "Successfully created the virtual environment."
                fi
            else
                echo "Failed to install python3-venv."
            fi
        else
            echo "Virtual environment created successfully."
        fi
    else
        echo "Virtual environment directory already exists."
    fi

    echo "Activating venv..."
    . $SDK_CI_VENV_DIR/bin/activate

    pip3 --disable-pip-version-check install wheel
    if [[ "$SDK_CI_INSTALL_STRATEGY" == "git_ssh" ]]; then
        pip3 --disable-pip-version-check install git+ssh://git@github.com/mapbox/sdk-cicd.git@$SDK_CI_VERSION
    elif [[ "$SDK_CI_INSTALL_STRATEGY" == "git_https" ]]; then
        GITHUB_ACCESS_TOKEN=$(mbx-ci github reader token)
        pip3 --disable-pip-version-check install git+https://x-access-token:${GITHUB_ACCESS_TOKEN}@github.com/mapbox/sdk-cicd.git@$SDK_CI_VERSION
    elif [[ "$SDK_CI_INSTALL_STRATEGY" == "https_api" ]]; then
        GITHUB_ACCESS_TOKEN=$(mbx-ci github reader token)
        pip3 --disable-pip-version-check install https://x-access-token:${GITHUB_ACCESS_TOKEN}@api.github.com/repos/mapbox/sdk-cicd/tarball/$SDK_CI_VERSION
    fi
    pip3 --disable-pip-version-check freeze >$SDK_CI_VENV_DIR/requirements.txt
    echo "Deps written to $SDK_CI_VENV_DIR/requirements.txt"
    cat $SDK_CI_VENV_DIR/requirements.txt

    deactivate

    echo "Adding to PATH..."
    echo 'export PATH=$PATH:'"${SDK_CI_VENV_DIR}/bin" >>$BASH_ENV
}
main || $SDK_CI_ALLOW_FAILURE
