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
# Start Admin Portal
################################################################################

if [ "$SKIP_ADMIN" != "true" ] && [ -d "/opt/admin" ]; then
  echo_log "Starting Admin Portal on port ${ADMIN_PORT:-8888}..."
  cd /opt/admin
  /opt/admin/venv/bin/python app.py &
  ADMIN_PID=$!
  echo_log "Admin Portal started (PID: $ADMIN_PID)"
else
  echo_log "Admin Portal skipped"
fi

################################################################################
# Start FreeSWITCH
################################################################################

echo_log "Starting FreeSWITCH..."
echo_log "Command: $*"

# Execute FreeSWITCH with provided arguments
exec "$@"
