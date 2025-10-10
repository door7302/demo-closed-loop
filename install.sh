#!/usr/bin/env bash
#
# setup_demo_env.sh
# Automated setup for StackStorm, Kafka, Telegraf, InfluxDB, Grafana demo environment
#

set -euo pipefail

#------------------------------------------------------------
# CONFIGURATION
#------------------------------------------------------------
STACKSTORM_DIR="/opt/stackstorm"
KAFKA_DIR="/opt/kafka"
DEMO_REPO="/var/demo-repo"
DEMO_DIR="/opt/demo"

KAFKA_VERSION="3.8.0"
KAFKA_TGZ="kafka_2.13-${KAFKA_VERSION}.tgz"
KAFKA_URL="https://downloads.apache.org/kafka/${KAFKA_VERSION}/${KAFKA_TGZ}"

#------------------------------------------------------------
# HELPERS
#------------------------------------------------------------
log() { echo -e "\033[1;32m[+] $*\033[0m"; }
err() { echo -e "\033[1;31m[ERROR] $*\033[0m" >&2; exit 1; }

ensure_dir() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        log "Creating missing directory: $dir"
        mkdir -p "$dir"
    fi
}

#------------------------------------------------------------
# INSTALL STACKSTORM
#------------------------------------------------------------
install_stackstorm() {
    log "Installing StackStorm (st2-docker)..."

    ensure_dir "${STACKSTORM_DIR}"
    cd "${STACKSTORM_DIR}"

    if [ ! -d "${STACKSTORM_DIR}/.git" ]; then
        git clone https://github.com/stackstorm/st2-docker . || err "Failed to clone st2-docker repo"
    else
        log "StackStorm repository already exists — skipping clone."
    fi
}

#------------------------------------------------------------
# INSTALL KAFKA TOOLS
#------------------------------------------------------------
install_kafka() {
    log "Installing Kafka tools version ${KAFKA_VERSION}..."

    ensure_dir "${KAFKA_DIR}"
    cd /tmp

    if [ ! -d "${KAFKA_DIR}/bin" ]; then
        curl -O "${KAFKA_URL}" || err "Failed to download Kafka package"
        tar -xzf "${KAFKA_TGZ}"
        mv "kafka_2.13-${KAFKA_VERSION}/"* "${KAFKA_DIR}/"
        rm -rf "kafka_2.13-${KAFKA_VERSION}" "${KAFKA_TGZ}"
    else
        log "Kafka already installed — skipping."
    fi
}

#------------------------------------------------------------
# PREPARE FOLDERS
#------------------------------------------------------------
prepare_folders() {
    log "Creating directory structure under /opt..."

    ensure_dir /opt/telegraf/metadata
    ensure_dir /opt/telegraf/cert
    ensure_dir /opt/influxdb/data
    ensure_dir /opt/grafana/cert
    ensure_dir /opt/grafana/provisioning/datasources
    ensure_dir /opt/grafana/provisioning/dashboards
    ensure_dir /opt/grafana/data
    ensure_dir /opt/grafana/plugins
    ensure_dir "${DEMO_DIR}"
    ensure_dir "${STACKSTORM_DIR}/packs.dev"
    ensure_dir "${STACKSTORM_DIR}/virtualenvs"

    log "Copying demo configuration from ${DEMO_REPO}..."

    # Safely copy Grafana, InfluxDB, Telegraf configs
    if [ -d "${DEMO_REPO}/grafana" ]; then
        cp -r "${DEMO_REPO}/grafana/"* /opt/grafana/
    else
        err "Missing /grafana directory in demo repo"
    fi

    if [ -d "${DEMO_REPO}/influxdb" ]; then
        cp -r "${DEMO_REPO}/influxdb/"* /opt/influxdb/
    else
        err "Missing /influxdb directory in demo repo"
    fi

    if [ -d "${DEMO_REPO}/telegraf" ]; then
        cp -r "${DEMO_REPO}/telegraf/"* /opt/telegraf/
    else
        err "Missing /telegraf directory in demo repo"
    fi

    # Copy docker-compose and env file
    if [ -f "${DEMO_REPO}/docker-compose.yml" ]; then
        cp "${DEMO_REPO}/docker-compose.yml" "${DEMO_DIR}/"
    else
        err "Missing docker-compose.yml in demo repo"
    fi

    if [ -f "${DEMO_REPO}/.env" ]; then
        cp "${DEMO_REPO}/.env" "${DEMO_DIR}/"
    else
        err "Missing .env file in demo repo"
    fi

    # Copy StackStorm demo pack
    if [ -d "${DEMO_REPO}/demo" ]; then
        cp -r "${DEMO_REPO}/demo" "${STACKSTORM_DIR}/packs.dev/"
    else
        err "Missing /demo directory in demo repo"
    fi
}

#------------------------------------------------------------
# MAIN
#------------------------------------------------------------
main() {
    log "Starting full demo environment setup..."

    install_stackstorm
    install_kafka
    prepare_folders

    log "✅ Environment setup completed successfully!"
}

main "$@"