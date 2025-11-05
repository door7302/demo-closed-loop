#!/usr/bin/env bash
#
# install.sh
# Automated setup for PyMongo, StackStorm, Kafka, Telegraf, InfluxDB, Grafana demo environment
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

#------------------------------------------------------------
# INSTALL Mongo DB Python lib
#------------------------------------------------------------
install_py_mongo() {
    log "Installing Mongo DB python package..."
    
    pip install pymongo
}

#------------------------------------------------------------
# INSTALL STACKSTORM
#------------------------------------------------------------
install_stackstorm() {
    log "Installing StackStorm (st2-docker)..."

    mkdir -p "${STACKSTORM_DIR}"
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

    mkdir -p "${KAFKA_DIR}"
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

    mkdir -p /opt/telegraf/{metadata,cert}
    mkdir -p /opt/influxdb/data
    mkdir -p /opt/grafana/{cert,provisioning/{datasources,dashboards},data,plugins}
    mkdir -p "${DEMO_DIR}"

    log "Copying demo configuration from ${DEMO_REPO}..."

    # Copy Grafana, InfluxDB, Telegraf configs
    cp -r "${DEMO_REPO}/grafana/"* /opt/grafana/ || err "Missing /grafana directory in demo repo"
    cp -r "${DEMO_REPO}/influxdb/"* /opt/influxdb/ || err "Missing /influxdb directory in demo repo"
    cp -r "${DEMO_REPO}/telegraf/"* /opt/telegraf/ || err "Missing /telegraf directory in demo repo"

    # Copy docker-compose and env file
    cp "${DEMO_REPO}/docker-compose.yml" "${DEMO_DIR}/" || err "Missing docker-compose.yml in demo repo"
    cp "${DEMO_REPO}/.env" "${DEMO_DIR}/" || err "Missing .env file in demo repo"

    # Copy mongo DB files
    cp "${DEMO_REPO}/provision_mongo.py" "${DEMO_DIR}/" || err "Missing provision_mongo.py in demo repo"
    cp "${DEMO_REPO}/sample_inventory.json" "${DEMO_DIR}/" || err "Missing sample_inventory.json file in demo repo"

    # Copy StackStorm demo packs
    mkdir -p "${STACKSTORM_DIR}/packs.dev"
    cp -r "${DEMO_REPO}/demo" "${STACKSTORM_DIR}/packs.dev/" || err "Missing /demo directory in demo repo"

    # Create Logs folder
    mkdir -p "${STACKSTORM_DIR}/logs"
    touch "${STACKSTORM_DIR}/logs/demo_logic.log"

    # ST2 NGINX config
    mkdir -p "${STACKSTORM_DIR}/nginx"
    mkdir -p "/var/log/nginx"
    cp "${DEMO_REPO}/st2web/st2-http.template" "${STACKSTORM_DIR}/nginx/" || err "Missing st2-http.template in demo repo"
    cp "${DEMO_REPO}/st2web/st2-https.template" "${STACKSTORM_DIR}/nginx/" || err "Missing st2-https.template in demo repo"

    
}

#------------------------------------------------------------
# MAIN
#------------------------------------------------------------
main() {
    log "Starting deployment of demo environment..."

    install_py_mongo
    install_stackstorm
    install_kafka
    prepare_folders

    log "✅ Environment setup completed successfully!"
}

main "$@"