#!/bin/sh

########################################################################
# deploy.sh: Update and restart the Finance Dashboard service
#
#  Description:
#  Pull the latest revision, refresh the virtual environment, fix the
#  ownership of the application directory, and restart the systemd unit
#  that serves the dashboard.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - POSIX shell, git, python3, sudo, systemd
#
#  Usage:
#      ./deploy.sh
#      ./deploy.sh -h | --help
#
#  Options:
#  - -h, --help
#      Display this help and exit.
#
#  Environment Variables:
#  - APP_ROOT: Application directory. Defaults to /var/www/finance-dashboard.
#  - APP_USER: Owner of the application directory. Defaults to www-data.
#  - APP_SERVICE: systemd unit name. Defaults to finance-dashboard.
#
#  Version History:
#  v1.0 2026-07-25
#       Deploy the Python application instead of the Sinatra application.
#
########################################################################

APP_ROOT=${APP_ROOT:-/var/www/finance-dashboard}
APP_USER=${APP_USER:-www-data}
APP_SERVICE=${APP_SERVICE:-finance-dashboard}

# Display this script's header as usage information
usage() {
    awk '
        BEGIN { in_header = 0 }
        /^#+$/ && length($0) >= 10 { if (!in_header) { in_header = 1; next } else exit }
        in_header && /^# ?/ { print substr($0, 3) }
    ' "$0"
    exit 0
}

# Check that the required commands are available
check_commands() {
    for cmd in git python3 sudo systemctl; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "[ERROR] Command not found: $cmd" >&2
            exit 127
        fi
    done
}

# Check that the application directory exists
check_environment() {
    if [ ! -d "$APP_ROOT" ]; then
        echo "[ERROR] Application directory does not exist: $APP_ROOT" >&2
        exit 1
    fi
}

# Update the working tree and the virtual environment
update_application() {
    cd "$APP_ROOT" || exit 1

    echo "[INFO] Updating the working tree in $APP_ROOT"
    git pull || exit 1

    if [ ! -d "$APP_ROOT/.venv" ]; then
        echo "[INFO] Creating the virtual environment"
        python3 -m venv "$APP_ROOT/.venv" || exit 1
    fi

    echo "[INFO] Installing dependencies"
    "$APP_ROOT/.venv/bin/pip" install --upgrade --quiet . || exit 1
}

# Restore ownership and permissions, then restart the service
restart_service() {
    echo "[INFO] Fixing ownership and permissions"
    sudo chown -R "$APP_USER:$APP_USER" "$APP_ROOT" || exit 1
    sudo chmod -R g+rw,o-rwx "$APP_ROOT" || exit 1

    echo "[INFO] Restarting $APP_SERVICE"
    sudo systemctl restart "$APP_SERVICE" || exit 1
}

# Main entry point of the script
main() {
    case "$1" in
        -h|--help) usage ;;
    esac
    check_commands
    check_environment
    update_application
    restart_service
    echo "[INFO] Deployment finished"
    return 0
}

# Execute main function
main "$@"
