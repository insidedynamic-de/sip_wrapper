#!/bin/bash

################################################################################
# Docker Entrypoint for FreeSWITCH
# Runs provisioning and starts FreeSWITCH
################################################################################

set -e

echo_log() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ENTRYPOINT: $*"
}

################################################################################
# Run Provisioning
################################################################################

if [ "$SKIP_PROVISION" != "true" ]; then
  echo_log "Running provisioning..."
  /usr/local/bin/provision.sh || {
    echo_log "ERROR: Provisioning failed"
    exit 1
  }
else
  echo_log "Provisioning skipped (SKIP_PROVISION=true)"
fi

################################################################################
# Start FreeSWITCH
################################################################################

echo_log "Starting FreeSWITCH..."
echo_log "Command: $*"

# Execute FreeSWITCH with provided arguments
exec "$@"
