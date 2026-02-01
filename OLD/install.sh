#!/bin/bash

################################################################################
# FreeSWITCH Installation Script
# Install FreeSWITCH from official SignalWire repositories on Debian/Ubuntu
# For production use - clean installation without examples
################################################################################

set -e

echo_log() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"
}

error_exit() {
  echo_log "ERROR: $*" >&2
  exit 1
}

check_root() {
  if [ "$(id -u)" -ne 0 ]; then
    error_exit "This script must be run as root or with sudo"
  fi
}

detect_os() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
    CODENAME=$VERSION_CODENAME
  else
    error_exit "Cannot detect OS. /etc/os-release not found"
  fi

  echo_log "Detected OS: $OS $VER ($CODENAME)"

  case $OS in
    debian|ubuntu)
      ;;
    *)
      error_exit "Unsupported OS: $OS. Only Debian/Ubuntu are supported"
      ;;
  esac
}

install_dependencies() {
  echo_log "Installing dependencies..."

  apt-get update -qq
  apt-get install -y -qq \
    wget \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    lsb-release \
    curl \
    software-properties-common

  echo_log "Dependencies installed"
}

add_signalwire_repo() {
  echo_log "Adding SignalWire repository..."

  # SignalWire Token (Personal Access Token required for access)
  # You should set this as environment variable: SIGNALWIRE_TOKEN
  TOKEN="${SIGNALWIRE_TOKEN:-}"

  if [ -z "$TOKEN" ]; then
    echo_log "WARNING: SIGNALWIRE_TOKEN not set. Trying public repository..."
    echo_log "For production, obtain a token from: https://developer.signalwire.com/freeswitch"
  fi

  # Add SignalWire GPG key
  wget --http-user=signalwire --http-password="$TOKEN" \
    -O /usr/share/keyrings/signalwire-freeswitch-repo.gpg \
    https://freeswitch.signalwire.com/repo/deb/debian-release/signalwire-freeswitch-repo.gpg \
    2>/dev/null || {
      echo_log "Trying alternative repository method..."
      wget -O- https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | \
        gpg --dearmor -o /usr/share/keyrings/signalwire-freeswitch-repo.gpg
    }

  # Add repository
  if [ -n "$TOKEN" ]; then
    echo "deb [signed-by=/usr/share/keyrings/signalwire-freeswitch-repo.gpg] https://freeswitch.signalwire.com/repo/deb/debian-release/ $CODENAME main" \
      > /etc/apt/sources.list.d/freeswitch.list
  else
    echo "deb [signed-by=/usr/share/keyrings/signalwire-freeswitch-repo.gpg] https://files.freeswitch.org/repo/deb/debian-release/ $CODENAME main" \
      > /etc/apt/sources.list.d/freeswitch.list
  fi

  apt-get update -qq

  echo_log "SignalWire repository added"
}

install_freeswitch() {
  echo_log "Installing FreeSWITCH..."

  # Install FreeSWITCH packages
  apt-get install -y -qq \
    freeswitch-meta-all \
    freeswitch-all-dbg

  echo_log "FreeSWITCH installed successfully"
}

clean_default_config() {
  echo_log "Cleaning default/example configuration..."

  FS_CONF="/etc/freeswitch"

  # Backup original configuration
  if [ -d "$FS_CONF" ] && [ ! -d "${FS_CONF}.orig" ]; then
    cp -a "$FS_CONF" "${FS_CONF}.orig"
    echo_log "Original config backed up to ${FS_CONF}.orig"
  fi

  # Remove all example/demo files but keep directory structure
  find "$FS_CONF/dialplan" -type f -name "*.xml" -delete 2>/dev/null || true
  find "$FS_CONF/directory" -type f -name "*.xml" -delete 2>/dev/null || true
  find "$FS_CONF/sip_profiles" -type f -name "*.xml" ! -name "internal.xml" ! -name "external.xml" -delete 2>/dev/null || true
  find "$FS_CONF/autoload_configs" -type f -name "*.xml" ! -name "modules.conf.xml" ! -name "switch.conf.xml" -delete 2>/dev/null || true

  # Remove example gateways
  rm -rf "$FS_CONF/sip_profiles/external"/*.xml 2>/dev/null || true
  rm -rf "$FS_CONF/sip_profiles/internal"/*.xml 2>/dev/null || true

  echo_log "Default configuration cleaned"
}

setup_minimal_config() {
  echo_log "Setting up minimal configuration structure..."

  FS_CONF="/etc/freeswitch"

  # Create necessary directories
  mkdir -p "$FS_CONF"/{dialplan/{default,public},directory/default,sip_profiles/{internal,external}}
  mkdir -p "$FS_CONF/autoload_configs"

  # Create minimal modules.conf.xml if not exists
  if [ ! -f "$FS_CONF/autoload_configs/modules.conf.xml" ]; then
    cat > "$FS_CONF/autoload_configs/modules.conf.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<configuration name="modules.conf" description="Modules">
  <modules>
    <!-- Core Modules -->
    <load module="mod_console"/>
    <load module="mod_logfile"/>
    <load module="mod_event_socket"/>

    <!-- Dialplan -->
    <load module="mod_dialplan_xml"/>

    <!-- Endpoints -->
    <load module="mod_sofia"/>

    <!-- Applications -->
    <load module="mod_commands"/>
    <load module="mod_dptools"/>
    <load module="mod_db"/>

    <!-- Codecs -->
    <load module="mod_spandsp"/>
    <load module="mod_g723_1"/>
    <load module="mod_g729"/>
    <load module="mod_amr"/>
    <load module="mod_opus"/>
    <load module="mod_h26x"/>

    <!-- Formats -->
    <load module="mod_sndfile"/>
    <load module="mod_native_file"/>
    <load module="mod_local_stream"/>
    <load module="mod_tone_stream"/>
  </modules>
</configuration>
EOF
    echo_log "Created minimal modules.conf.xml"
  fi

  # Create minimal switch.conf.xml if not exists
  if [ ! -f "$FS_CONF/autoload_configs/switch.conf.xml" ]; then
    cat > "$FS_CONF/autoload_configs/switch.conf.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<configuration name="switch.conf" description="Core Configuration">
  <settings>
    <param name="colorize-console" value="true"/>
    <param name="max-sessions" value="1000"/>
    <param name="sessions-per-second" value="30"/>
    <param name="loglevel" value="info"/>
  </settings>
</configuration>
EOF
    echo_log "Created minimal switch.conf.xml"
  fi

  echo_log "Minimal configuration structure created"
}

configure_service() {
  echo_log "Configuring FreeSWITCH service..."

  # Enable service to start on boot
  systemctl enable freeswitch

  echo_log "FreeSWITCH service configured"
}

show_summary() {
  echo_log ""
  echo_log "=============================================="
  echo_log "FreeSWITCH Installation Complete"
  echo_log "=============================================="
  echo_log ""
  echo_log "Installation directory: /usr/bin/freeswitch"
  echo_log "Configuration directory: /etc/freeswitch"
  echo_log "Original config backup: /etc/freeswitch.orig"
  echo_log ""
  echo_log "Next steps:"
  echo_log "1. Run provision.sh to generate configuration from ENV variables"
  echo_log "2. Start FreeSWITCH: systemctl start freeswitch"
  echo_log "3. Check status: systemctl status freeswitch"
  echo_log "4. Connect to CLI: fs_cli"
  echo_log ""
  echo_log "Useful commands:"
  echo_log "  - fs_cli -x 'sofia status'"
  echo_log "  - fs_cli -x 'show registrations'"
  echo_log "  - fs_cli -x 'show channels'"
  echo_log ""
}

main() {
  echo_log "Starting FreeSWITCH installation..."

  check_root
  detect_os
  install_dependencies
  add_signalwire_repo
  install_freeswitch
  clean_default_config
  setup_minimal_config
  configure_service
  show_summary

  echo_log "Installation completed successfully!"
}

main "$@"
