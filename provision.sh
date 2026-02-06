#!/bin/bash

################################################################################
# FreeSWITCH Provisioning Script
# Generate complete FreeSWITCH configuration from environment variables
# Production-ready, no demo/example configurations
################################################################################

set -e

# Enable verbose mode if DEBUG=true
if [ "${DEBUG:-false}" = "true" ]; then
  set -x
  echo "[DEBUG MODE ENABLED]"
fi

################################################################################
# Configuration
################################################################################

FS_CONF="${FS_CONF:-/etc/freeswitch}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/freeswitch}"
TIMESTAMP=$(date -u '+%Y%m%d-%H%M%S')

# JSON Config file path
CONFIG_FILE="${CONFIG_FILE:-/var/lib/freeswitch/wrapper_config.json}"
USE_JSON_CONFIG=false

################################################################################
# JSON Config Loading
################################################################################

check_json_config() {
  # Verify jq is available
  if ! command -v jq >/dev/null 2>&1; then
    echo_log "WARNING: jq not installed, using ENV fallback"
    return 1
  fi

  if [ -f "$CONFIG_FILE" ]; then
    # Verify JSON is valid
    if jq empty "$CONFIG_FILE" 2>/dev/null; then
      USE_JSON_CONFIG=true
      echo_log "Using JSON config: $CONFIG_FILE"
      return 0
    else
      echo_log "WARNING: JSON config exists but is invalid, using ENV fallback"
      return 1
    fi
  fi

  # No JSON config - try to create from ENV if variables are set
  if [ -n "$USERS" ] || [ -n "$GATEWAYS" ]; then
    echo_log "No JSON config found, creating from ENV variables..."
    create_json_from_env
    return 0
  fi

  echo_log "No JSON config and no USERS/GATEWAYS in ENV"
  return 1
}

get_json_value() {
  # Get a value from JSON config
  # Usage: get_json_value '.settings.fs_domain'
  local path="$1"
  local default="${2:-}"
  if [ "$USE_JSON_CONFIG" = true ]; then
    local value
    value=$(jq -r "$path // empty" "$CONFIG_FILE" 2>/dev/null)
    if [ -n "$value" ] && [ "$value" != "null" ]; then
      echo "$value"
      return
    fi
  fi
  echo "$default"
}

get_json_array_length() {
  # Get length of JSON array
  local path="$1"
  if [ "$USE_JSON_CONFIG" = true ]; then
    jq -r "$path | length // 0" "$CONFIG_FILE" 2>/dev/null
  else
    echo "0"
  fi
}

get_json_array_item() {
  # Get item from JSON array by index
  local path="$1"
  local index="$2"
  local field="$3"
  if [ "$USE_JSON_CONFIG" = true ]; then
    jq -r "${path}[$index].${field} // empty" "$CONFIG_FILE" 2>/dev/null
  fi
}

create_json_from_env() {
  # Create JSON config from ENV variables if it doesn't exist
  echo_log "Creating JSON config from ENV variables..."

  # Ensure directory exists
  mkdir -p "$(dirname "$CONFIG_FILE")"

  # Start building JSON
  local json='{"version":1,"license":{},"settings":{},"users":[],"acl_users":[],"gateways":[],"routes":{}}'

  # License
  if [ -n "$LICENSE_KEY" ]; then
    json=$(echo "$json" | jq --arg k "$LICENSE_KEY" --arg c "${CLIENT_NAME:-}" '.license = {key:$k,client_name:$c}')
  fi

  # Settings
  json=$(echo "$json" | jq \
    --arg domain "${FS_DOMAIN:-}" \
    --arg sip_ip "${EXTERNAL_SIP_IP:-}" \
    --arg rtp_ip "${EXTERNAL_RTP_IP:-}" \
    --arg int_port "${INTERNAL_SIP_PORT:-5060}" \
    --arg ext_port "${EXTERNAL_SIP_PORT:-5080}" \
    --arg rtp_start "${RTP_START_PORT:-16384}" \
    --arg rtp_end "${RTP_END_PORT:-32768}" \
    --arg codecs "${CODEC_PREFS:-PCMU,PCMA,G729,opus}" \
    --arg country "${DEFAULT_COUNTRY_CODE:-49}" \
    '.settings = {
      fs_domain:$domain,
      external_sip_ip:$sip_ip,
      external_rtp_ip:$rtp_ip,
      internal_sip_port:($int_port|tonumber),
      external_sip_port:($ext_port|tonumber),
      rtp_start_port:($rtp_start|tonumber),
      rtp_end_port:($rtp_end|tonumber),
      codec_prefs:$codecs,
      default_country_code:$country
    }')

  # Users (format: username:password:extension:enabled,...)
  if [ -n "$USERS" ]; then
    local users_json="[]"
    IFS=',' read -ra USER_ARRAY <<< "$USERS"
    for user in "${USER_ARRAY[@]}"; do
      IFS=':' read -r u_name u_pass u_ext u_enabled <<< "$user"
      if [ -n "$u_name" ]; then
        users_json=$(echo "$users_json" | jq \
          --arg name "$u_name" \
          --arg pass "${u_pass:-}" \
          --arg ext "${u_ext:-}" \
          --arg en "${u_enabled:-true}" \
          '. += [{username:$name,password:$pass,extension:$ext,enabled:($en=="true" or $en=="1")}]')
      fi
    done
    json=$(echo "$json" | jq --argjson users "$users_json" '.users = $users')
  fi

  # ACL Users (format: username:ip:extension:callerid,...)
  if [ -n "$ACL_USERS" ]; then
    local acl_json="[]"
    IFS=',' read -ra ACL_ARRAY <<< "$ACL_USERS"
    for acl in "${ACL_ARRAY[@]}"; do
      IFS=':' read -r a_name a_ip a_ext a_cid <<< "$acl"
      if [ -n "$a_name" ]; then
        acl_json=$(echo "$acl_json" | jq \
          --arg name "$a_name" \
          --arg ip "${a_ip:-}" \
          --arg ext "${a_ext:-}" \
          --arg cid "${a_cid:-}" \
          '. += [{username:$name,ip_address:$ip,extension:$ext,caller_id:$cid}]')
      fi
    done
    json=$(echo "$json" | jq --argjson acl "$acl_json" '.acl_users = $acl')
  fi

  # Gateways (format: type:name:host:port:username:password:register:transport:auth_user,...)
  if [ -n "$GATEWAYS" ]; then
    local gw_json="[]"
    IFS=',' read -ra GW_ARRAY <<< "$GATEWAYS"
    for gw in "${GW_ARRAY[@]}"; do
      IFS=':' read -r g_type g_name g_host g_port g_user g_pass g_reg g_trans g_auth <<< "$gw"
      if [ -n "$g_name" ] && [ -n "$g_host" ]; then
        gw_json=$(echo "$gw_json" | jq \
          --arg type "${g_type:-sip}" \
          --arg name "$g_name" \
          --arg host "$g_host" \
          --arg port "${g_port:-5060}" \
          --arg user "${g_user:-}" \
          --arg pass "${g_pass:-}" \
          --arg reg "${g_reg:-true}" \
          --arg trans "${g_trans:-udp}" \
          --arg auth "${g_auth:-}" \
          '. += [{
            type:$type,name:$name,host:$host,
            port:($port|tonumber),username:$user,password:$pass,
            register:($reg=="true" or $reg=="1"),
            transport:$trans,auth_username:$auth,enabled:true
          }]')
      fi
    done
    json=$(echo "$json" | jq --argjson gw "$gw_json" '.gateways = $gw')
  fi

  # Routes
  local routes_json='{}'
  routes_json=$(echo "$routes_json" | jq \
    --arg dg "${DEFAULT_GATEWAY:-}" \
    --arg de "${DEFAULT_EXTENSION:-}" \
    --arg oc "${OUTBOUND_CALLER_ID:-}" \
    '.default_gateway=$dg|.default_extension=$de|.outbound_caller_id=$oc')

  # Inbound routes (format: gateway:extension,...)
  if [ -n "$INBOUND_ROUTES" ]; then
    local inbound_json="[]"
    IFS=',' read -ra IN_ARRAY <<< "$INBOUND_ROUTES"
    for route in "${IN_ARRAY[@]}"; do
      IFS=':' read -r r_did r_dest r_type <<< "$route"
      if [ -n "$r_did" ] && [ -n "$r_dest" ]; then
        inbound_json=$(echo "$inbound_json" | jq \
          --arg did "$r_did" \
          --arg dest "$r_dest" \
          --arg type "${r_type:-extension}" \
          '. += [{did:$did,destination:$dest,destination_type:$type}]')
      fi
    done
    routes_json=$(echo "$routes_json" | jq --argjson inb "$inbound_json" '.inbound = $inb')
  fi

  # User routes (format: username:gateway,...)
  if [ -n "$OUTBOUND_USER_ROUTES" ]; then
    local ur_json="[]"
    IFS=',' read -ra UR_ARRAY <<< "$OUTBOUND_USER_ROUTES"
    for ur in "${UR_ARRAY[@]}"; do
      IFS=':' read -r ur_user ur_gw <<< "$ur"
      if [ -n "$ur_user" ] && [ -n "$ur_gw" ]; then
        ur_json=$(echo "$ur_json" | jq \
          --arg user "$ur_user" \
          --arg gw "$ur_gw" \
          '. += [{username:$user,gateway:$gw}]')
      fi
    done
    routes_json=$(echo "$routes_json" | jq --argjson ur "$ur_json" '.user_routes = $ur')
  fi

  json=$(echo "$json" | jq --argjson routes "$routes_json" '.routes = $routes')

  # Write JSON file
  echo "$json" | jq '.' > "$CONFIG_FILE"
  echo_log "Created JSON config: $CONFIG_FILE"

  # Now use JSON config
  USE_JSON_CONFIG=true
}

################################################################################
# Logging
################################################################################

echo_log() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"
}

error_exit() {
  echo_log "ERROR: $*" >&2
  exit 1
}

################################################################################
# Banner
################################################################################

show_banner() {
  local license
  local client

  # Try JSON first, then ENV
  if [ "$USE_JSON_CONFIG" = true ]; then
    license=$(get_json_value '.license.key' 'UNLICENSED')
    client=$(get_json_value '.license.client_name' '')
  else
    license="${LICENSE_KEY:-UNLICENSED}"
    client="${CLIENT_NAME:-}"
  fi

  echo ""
  echo "================================================================================"
  if [ -n "$client" ]; then
    echo "  InsideDynamic Wrapper - ($license) für $client"
  else
    echo "  InsideDynamic Wrapper - ($license)"
  fi
  echo "================================================================================"
  echo "  https://github.com/insidedynamic-de/sip_wrapper"
  echo "  (c) 2025 InsideDynamic GmbH - Mannheim, Germany"
  echo "================================================================================"
  echo ""
}

################################################################################
# Build User-Agent String
################################################################################

build_user_agent() {
  local custom_ua

  # Check JSON config for custom user agent
  if [ "$USE_JSON_CONFIG" = true ]; then
    custom_ua=$(get_json_value '.settings.sip_user_agent' '')
    if [ -n "$custom_ua" ] && [ "$custom_ua" != "InsideDynamic-Wrapper" ]; then
      SIP_USER_AGENT="$custom_ua"
      export SIP_USER_AGENT
      echo_log "Using custom SIP User-Agent from JSON: $SIP_USER_AGENT"
      return
    fi
  fi

  # If SIP_USER_AGENT is already set by user, use it as-is
  if [ -n "$SIP_USER_AGENT" ] && [ "$SIP_USER_AGENT" != "InsideDynamic-Wrapper" ]; then
    echo_log "Using custom SIP User-Agent: $SIP_USER_AGENT"
    return
  fi

  # Build User-Agent like banner: InsideDynamic-Wrapper-(LICENSE_KEY) or InsideDynamic-Wrapper-(LICENSE_KEY)-CLIENT_NAME
  local license
  local client

  if [ "$USE_JSON_CONFIG" = true ]; then
    license=$(get_json_value '.license.key' 'UNLICENSED')
    client=$(get_json_value '.license.client_name' '')
  else
    license="${LICENSE_KEY:-UNLICENSED}"
    client="${CLIENT_NAME:-}"
  fi

  if [ -n "$client" ]; then
    # Replace spaces with underscores in client name for User-Agent
    client=$(echo "$client" | tr ' ' '_')
    SIP_USER_AGENT="InsideDynamic-Wrapper-($license)-$client"
  else
    SIP_USER_AGENT="InsideDynamic-Wrapper-($license)"
  fi

  export SIP_USER_AGENT
  echo_log "SIP User-Agent: $SIP_USER_AGENT"
}

################################################################################
# Validation
################################################################################

require_env() {
  local var_name="$1"
  local var_value="${!var_name}"

  if [ -z "$var_value" ]; then
    error_exit "Required environment variable $var_name is not set"
  fi
}

validate_config() {
  echo_log "Validating configuration..."

  if [ "$USE_JSON_CONFIG" = true ]; then
    # Validate JSON config
    local fs_domain
    fs_domain=$(get_json_value '.settings.fs_domain' '')
    if [ -z "$fs_domain" ]; then
      error_exit "JSON config: settings.fs_domain is required"
    fi

    local users_count
    local gateways_count
    users_count=$(get_json_array_length '.users')
    gateways_count=$(get_json_array_length '.gateways')

    if [ "$users_count" -eq 0 ] && [ "$gateways_count" -eq 0 ]; then
      error_exit "JSON config: At least one user or gateway must be defined"
    fi

    echo_log "JSON config validated: $users_count users, $gateways_count gateways"
  else
    # Required variables
    require_env "FS_DOMAIN"
    require_env "EXTERNAL_SIP_IP"
    require_env "EXTERNAL_RTP_IP"

    # At least one user or gateway should be defined
    if [ -z "$USERS" ] && [ -z "$GATEWAYS" ]; then
      error_exit "At least one USER or GATEWAY must be defined"
    fi

    echo_log "ENV configuration validated"
  fi
}

################################################################################
# Backup
################################################################################

backup_config() {
  echo_log "Backing up existing configuration..."

  if [ -d "$FS_CONF" ]; then
    mkdir -p "$BACKUP_DIR"
    tar -czf "$BACKUP_DIR/freeswitch-$TIMESTAMP.tar.gz" \
      -C "$(dirname "$FS_CONF")" "$(basename "$FS_CONF")" 2>/dev/null || true
    echo_log "Backup saved to: $BACKUP_DIR/freeswitch-$TIMESTAMP.tar.gz"
  fi
}


################################################################################
# Clean Configuration
################################################################################

clean_config() {
  echo_log "Cleaning previous configuration..."

  # Remove all dialplan files
  rm -f "$FS_CONF/dialplan/default"/*.xml 2>/dev/null || true
  rm -f "$FS_CONF/dialplan/public"/*.xml 2>/dev/null || true

  # Remove all directory files
  rm -f "$FS_CONF/directory/default"/*.xml 2>/dev/null || true
  rm -f "$FS_CONF/directory/default.xml" 2>/dev/null || true

  # Remove gateway files
  rm -rf "$FS_CONF/sip_profiles/external"/*.xml 2>/dev/null || true
  rm -rf "$FS_CONF/sip_profiles/internal"/*.xml 2>/dev/null || true

  # Remove profile files (we'll regenerate them)
  rm -f "$FS_CONF/sip_profiles/internal.xml" 2>/dev/null || true
  rm -f "$FS_CONF/sip_profiles/external.xml" 2>/dev/null || true

  # Create necessary directories
  mkdir -p "$FS_CONF"/{dialplan/{default,public},directory/default,sip_profiles/{internal,external},autoload_configs}

  echo_log "Configuration cleaned"
}

################################################################################
# Generate vars.xml
################################################################################

generate_vars() {
  echo_log "Generating vars.xml..."

  # Get values from JSON or ENV
  local var_domain var_ext_sip var_ext_rtp var_int_port var_ext_port
  local var_rtp_start var_rtp_end var_codec var_out_codec

  if [ "$USE_JSON_CONFIG" = true ]; then
    var_domain=$(get_json_value '.settings.fs_domain' "$FS_DOMAIN")
    var_ext_sip=$(get_json_value '.settings.external_sip_ip' "$EXTERNAL_SIP_IP")
    var_ext_rtp=$(get_json_value '.settings.external_rtp_ip' "$EXTERNAL_RTP_IP")
    var_int_port=$(get_json_value '.settings.internal_sip_port' "${INTERNAL_SIP_PORT:-5060}")
    var_ext_port=$(get_json_value '.settings.external_sip_port' "${EXTERNAL_SIP_PORT:-5080}")
    var_codec=$(get_json_value '.settings.codec_prefs' 'PCMU,PCMA,G729,opus')
    var_out_codec=$(get_json_value '.settings.outbound_codec_prefs' 'PCMU,PCMA,G729')
  else
    var_domain="$FS_DOMAIN"
    var_ext_sip="$EXTERNAL_SIP_IP"
    var_ext_rtp="$EXTERNAL_RTP_IP"
    var_int_port="${INTERNAL_SIP_PORT:-5060}"
    var_ext_port="${EXTERNAL_SIP_PORT:-5080}"
    var_codec="${CODEC_PREFS:-PCMU,PCMA,G729,opus}"
    var_out_codec="${OUTBOUND_CODEC_PREFS:-PCMU,PCMA,G729}"
  fi

  var_rtp_start="${RTP_START_PORT:-16384}"
  var_rtp_end="${RTP_END_PORT:-32768}"

  cat > "$FS_CONF/vars.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <!-- Global Variables -->
  <X-PRE-PROCESS cmd="set" data="domain=$var_domain"/>
  <X-PRE-PROCESS cmd="set" data="external_sip_ip=$var_ext_sip"/>
  <X-PRE-PROCESS cmd="set" data="external_rtp_ip=$var_ext_rtp"/>

  <!-- Network Settings -->
  <X-PRE-PROCESS cmd="set" data="internal_sip_port=$var_int_port"/>
  <X-PRE-PROCESS cmd="set" data="external_sip_port=$var_ext_port"/>

  <!-- RTP Port Range -->
  <X-PRE-PROCESS cmd="set" data="rtp_start_port=$var_rtp_start"/>
  <X-PRE-PROCESS cmd="set" data="rtp_end_port=$var_rtp_end"/>

  <!-- SIP Settings -->
  <X-PRE-PROCESS cmd="set" data="sip_tls_version=${SIP_TLS_VERSION:-tlsv1.2}"/>

  <!-- Codec Settings -->
  <X-PRE-PROCESS cmd="set" data="global_codec_prefs=$var_codec"/>
  <X-PRE-PROCESS cmd="set" data="outbound_codec_prefs=$var_out_codec"/>
</include>
EOF

  echo_log "vars.xml generated"
}

################################################################################
# Generate Event Socket Configuration
################################################################################

generate_event_socket() {
  echo_log "Generating event_socket.conf.xml..."

  # Determine ACL for ESL connections
  local esl_acl="loopback.auto"

  # If FS_ALLOWED_IPS is set to 0.0.0.0 or empty, allow all
  if [ "${FS_ALLOWED_IPS:-127.0.0.1}" = "0.0.0.0" ] || [ -z "$FS_ALLOWED_IPS" ]; then
    esl_acl="any_v4.auto"
    echo_log "  ESL ACL: any_v4.auto (all IPs allowed)"
  elif [ "$FS_ALLOWED_IPS" = "127.0.0.1" ]; then
    esl_acl="loopback.auto"
    echo_log "  ESL ACL: loopback.auto (localhost only)"
  else
    # Custom IP - we'll use any_v4 for simplicity, firewall should handle restrictions
    esl_acl="any_v4.auto"
    echo_log "  ESL ACL: any_v4.auto (custom IP: $FS_ALLOWED_IPS - use firewall for restrictions)"
  fi

  cat > "$FS_CONF/autoload_configs/event_socket.conf.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<configuration name="event_socket.conf" description="Socket Client">
  <settings>
    <param name="nat-map" value="false"/>
    <param name="listen-ip" value="::"/>
    <param name="listen-port" value="${FS_PORT:-8021}"/>
    <param name="password" value="${FS_PASS:-ClueCon}"/>
    <param name="apply-inbound-acl" value="$esl_acl"/>
  </settings>
</configuration>
EOF

  echo_log "event_socket.conf.xml generated"
}

################################################################################
# Generate Internal Profile (for authenticated users)
################################################################################

generate_internal_profile() {
  echo_log "Generating internal SIP profile..."

  # Determine ACL list and blind auth based on whether ACL_USERS is defined
  # blind_auth/blind_reg = false means FreeSWITCH requires valid user in directory
  # ACL_USERS are authenticated by IP via ACL, not by password
  local has_acl_users=false

  if [ "$USE_JSON_CONFIG" = true ]; then
    local acl_len
    acl_len=$(get_json_array_length '.acl_users')
    if [ "$acl_len" -gt 0 ]; then
      has_acl_users=true
    fi
  elif [ -n "$ACL_USERS" ]; then
    has_acl_users=true
  fi

  # Check for blacklist
  local has_blacklist=false
  if [ "$USE_JSON_CONFIG" = true ]; then
    local bl_len
    bl_len=$(jq -r '.security.blacklist | length // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)
    if [ "$bl_len" -gt 0 ]; then
      has_blacklist=true
    fi
  fi

  # Build ACL chain: blacklist first (to deny), then domains/acl_users (to allow)
  local inbound_acl=""
  local register_acl=""
  if [ "$has_blacklist" = true ]; then
    inbound_acl="blacklist,"
    register_acl="blacklist"
    echo_log "  Blacklist ACL enabled - blocked IPs will be rejected"
  fi

  if [ "$has_acl_users" = true ]; then
    inbound_acl="${inbound_acl}domains,acl_users"
    local blind_auth="false"
    local blind_reg="false"
  else
    inbound_acl="${inbound_acl}domains"
    local blind_auth="false"
    local blind_reg="false"
  fi

  echo_log "  Internal profile ACL chain: $inbound_acl"

  # Build register ACL line (only if blacklist exists)
  local register_acl_line=""
  if [ -n "$register_acl" ]; then
    register_acl_line="<param name=\"apply-register-acl\" value=\"$register_acl\"/>"
    echo_log "  Register ACL: $register_acl"
  fi

  cat > "$FS_CONF/sip_profiles/internal.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<profile name="internal">
  <settings>
    <!-- Network -->
    <param name="sip-ip" value="\$\${local_ip_v4}"/>
    <param name="ext-sip-ip" value="\$\${external_sip_ip}"/>
    <param name="sip-port" value="\$\${internal_sip_port}"/>

    <!-- RTP -->
    <param name="rtp-ip" value="\$\${local_ip_v4}"/>
    <param name="ext-rtp-ip" value="\$\${external_rtp_ip}"/>
    <param name="rtp-start-port" value="\$\${rtp_start_port}"/>
    <param name="rtp-end-port" value="\$\${rtp_end_port}"/>

    <!-- Security -->
    <param name="auth-calls" value="true"/>
    <param name="auth-all-packets" value="false"/>
    <param name="accept-blind-auth" value="$blind_auth"/>
    <param name="accept-blind-reg" value="$blind_reg"/>
    <!-- CRITICAL: Force username to match directory entry -->
    <!-- Without this, ANY password from directory may work for ANY username -->
    <param name="inbound-reg-force-matching-username" value="true"/>

    <!-- NAT Handling -->
    <param name="apply-nat-acl" value="rfc1918.auto"/>
    <param name="apply-inbound-acl" value="$inbound_acl"/>
    $register_acl_line
    <param name="local-network-acl" value="localnet.auto"/>

    <!-- NAT Traversal - CRITICAL: Fix audio for clients behind NAT -->
    <!-- Force rport: always use source IP/port from packet, not SIP headers -->
    <param name="NDLB-force-rport" value="safe"/>
    <!-- Store actual received IP in registration contact -->
    <param name="NDLB-received-in-nat-reg-contact" value="true"/>
    <!-- Fix RTP going to wrong IP: rewrite SDP with detected public IP -->
    <param name="NDLB-sendrecv-in-session" value="true"/>
    <!-- Force symmetric RTP: always send to where packets come from -->
    <param name="NDLB-connectile-dysfunction" value="true"/>
    <!-- Force media through FreeSWITCH - required for NAT traversal -->
    <param name="inbound-bypass-media" value="false"/>

    <!-- Registration -->
    <param name="force-register-domain" value="\$\${domain}"/>
    <param name="force-register-db-domain" value="\$\${domain}"/>
    <param name="force-subscription-domain" value="\$\${domain}"/>

    <!-- Context -->
    <param name="context" value="default"/>
    <param name="dialplan" value="XML"/>

    <!-- DTMF -->
    <param name="dtmf-type" value="rfc2833"/>
    <param name="dtmf-duration" value="2000"/>

    <!-- Codecs -->
    <param name="inbound-codec-prefs" value="\$\${global_codec_prefs}"/>
    <param name="outbound-codec-prefs" value="\$\${outbound_codec_prefs}"/>
    <param name="inbound-codec-negotiation" value="generous"/>

    <!-- SIP -->
    <param name="nonce-ttl" value="60"/>
    <param name="inbound-reg-force-matching-username" value="true"/>
    <param name="aggressive-nat-detection" value="true"/>
    <param name="disable-register" value="false"/>
    <param name="disable-transfer" value="false"/>
    <param name="manual-redirect" value="false"/>
    <!-- Custom User-Agent: hide FreeSWITCH identity -->
    <param name="user-agent-string" value="$SIP_USER_AGENT"/>

    <!-- Caller ID Passthrough - show original client info -->
    <param name="pass-callee-id" value="true"/>
    <param name="caller-id-type" value="rpid"/>

    <!-- Media - disable late negotiation to establish RTP earlier -->
    <param name="inbound-late-negotiation" value="false"/>
    <param name="inbound-zrtp-passthru" value="true"/>
    <!-- Force symmetric RTP for NAT -->
    <param name="enable-soa" value="true"/>

    <!-- RTP NAT Fix: Handle clients behind NAT properly -->
    <param name="rtp-autoflush-during-bridge" value="true"/>
    <param name="rtp-rewrite-timestamps" value="true"/>
    <param name="rtp-timeout-sec" value="300"/>
    <param name="rtp-hold-timeout-sec" value="1800"/>

    <!-- Debug -->
    <param name="debug" value="${SIP_DEBUG:-0}"/>
    <param name="sip-trace" value="${SIP_TRACE:-no}"/>
    <param name="log-auth-failures" value="true"/>
    <param name="log-level" value="info"/>
  </settings>
</profile>
EOF

  echo_log "Internal profile generated"
}

################################################################################
# Generate External Profile (for gateways and inbound calls without auth)
################################################################################

generate_external_profile() {
  echo_log "Generating external SIP profile..."

  # Check for blacklist
  local blacklist_acl=""
  if [ "$USE_JSON_CONFIG" = true ]; then
    local bl_len
    bl_len=$(jq -r '.security.blacklist | length // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)
    if [ "$bl_len" -gt 0 ]; then
      blacklist_acl='
    <!-- Blacklist ACL -->
    <param name="apply-inbound-acl" value="blacklist"/>'
      echo_log "  Blacklist ACL enabled for external profile"
    fi
  fi

  cat > "$FS_CONF/sip_profiles/external.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<profile name="external">
  <gateways>
    <!-- Gateways will be included here -->
    <X-PRE-PROCESS cmd="include" data="external/*.xml"/>
  </gateways>

  <settings>
    <!-- Network -->
    <param name="sip-ip" value="\$\${local_ip_v4}"/>
    <param name="ext-sip-ip" value="\$\${external_sip_ip}"/>
    <param name="sip-port" value="\$\${external_sip_port}"/>

    <!-- RTP -->
    <param name="rtp-ip" value="\$\${local_ip_v4}"/>
    <param name="ext-rtp-ip" value="\$\${external_rtp_ip}"/>
    <param name="rtp-start-port" value="\$\${rtp_start_port}"/>
    <param name="rtp-end-port" value="\$\${rtp_end_port}"/>

    <!-- Security -->
    <param name="auth-calls" value="false"/>
    <param name="auth-all-packets" value="false"/>
    <param name="accept-blind-auth" value="true"/>
    <param name="accept-blind-reg" value="true"/>

    <!-- NAT -->
    <param name="apply-nat-acl" value="rfc1918.auto"/>
    <param name="local-network-acl" value="localnet.auto"/>
$blacklist_acl
    <!-- Context -->
    <param name="context" value="public"/>
    <param name="dialplan" value="XML"/>

    <!-- DTMF -->
    <param name="dtmf-type" value="rfc2833"/>
    <param name="dtmf-duration" value="2000"/>

    <!-- Codecs -->
    <param name="inbound-codec-prefs" value="\$\${global_codec_prefs}"/>
    <param name="outbound-codec-prefs" value="\$\${outbound_codec_prefs}"/>
    <param name="inbound-codec-negotiation" value="generous"/>

    <!-- SIP -->
    <param name="aggressive-nat-detection" value="true"/>
    <!-- SECURITY: Disable registrations on external profile (port 5080) -->
    <!-- Gateways/trunks don't register TO us - we register TO them -->
    <!-- All user registrations must go through internal profile (port 5060) with auth -->
    <param name="disable-register" value="true"/>
    <param name="disable-transfer" value="false"/>
    <param name="manual-redirect" value="false"/>
    <!-- Custom User-Agent: hide FreeSWITCH identity -->
    <param name="user-agent-string" value="$SIP_USER_AGENT"/>

    <!-- Media -->
    <param name="inbound-late-negotiation" value="true"/>
    <param name="inbound-zrtp-passthru" value="true"/>

    <!-- Caller ID Passthrough - show original client info, not FreeSWITCH -->
    <param name="pass-callee-id" value="true"/>
    <param name="caller-id-type" value="rpid"/>

    <!-- Debug -->
    <param name="debug" value="${SIP_DEBUG:-0}"/>
    <param name="sip-trace" value="${SIP_TRACE:-no}"/>
    <param name="log-level" value="info"/>
  </settings>
</profile>
EOF

  echo_log "External profile generated"
}

################################################################################
# Generate Users (authenticated)
# Format: USERS="user1:password1:1001,user2:password2:1002"
################################################################################

generate_users() {
  echo_log "Generating users..."

  local user_count=0
  local outbound_caller_id

  # Get default outbound caller ID
  if [ "$USE_JSON_CONFIG" = true ]; then
    outbound_caller_id=$(get_json_value '.routes.outbound_caller_id' '')
  else
    outbound_caller_id="${OUTBOUND_CALLER_ID:-}"
  fi

  if [ "$USE_JSON_CONFIG" = true ]; then
    # Read from JSON config
    local users_len
    users_len=$(get_json_array_length '.users')

    if [ "$users_len" -eq 0 ]; then
      echo_log "No authenticated users in JSON config, skipping..."
      return
    fi

    for ((i=0; i<users_len; i++)); do
      local username password extension enabled

      username=$(jq -r ".users[$i].username // empty" "$CONFIG_FILE")
      password=$(jq -r ".users[$i].password // empty" "$CONFIG_FILE")
      extension=$(jq -r ".users[$i].extension // empty" "$CONFIG_FILE")
      enabled=$(jq -r ".users[$i].enabled // true" "$CONFIG_FILE")

      if [ "$enabled" != "true" ]; then
        echo_log "Skipping disabled user: $username"
        continue
      fi

      if [ -z "$username" ] || [ -z "$password" ]; then
        echo_log "WARNING: Invalid user at index $i (skipping)"
        continue
      fi

      extension="${extension:-$username}"
      local caller_id="${outbound_caller_id:-$extension}"

      echo_log "Creating user: $username (extension: $extension)"

      cat > "$FS_CONF/directory/default/$username.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <user id="$username" number-alias="$extension">
    <params>
      <param name="password" value="$password"/>
      <param name="vm-password" value="$password"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_number" value="$caller_id"/>
      <variable name="effective_caller_id_name" value="$username"/>
      <variable name="outbound_caller_id_number" value="$caller_id"/>
      <variable name="outbound_caller_id_name" value="$username"/>
      <!-- NAT Traversal - applied to ALL calls from this user -->
      <variable name="rtp_auto_adjust" value="true"/>
      <variable name="sip_comedia" value="true"/>
      <variable name="bypass_media" value="false"/>
      <variable name="sip_nat_detected" value="true"/>
    </variables>
  </user>
</include>
EOF

      user_count=$((user_count + 1))
    done
  else
    # Read from ENV
    if [ -z "$USERS" ]; then
      echo_log "No authenticated users defined, skipping..."
      return
    fi

    IFS=',' read -ra USER_ARRAY <<< "$USERS"

    for user_entry in "${USER_ARRAY[@]}"; do
      IFS=':' read -r username password extension caller_id <<< "$user_entry"

      if [ -z "$username" ] || [ -z "$password" ]; then
        echo_log "WARNING: Invalid user entry: $user_entry (skipping)"
        continue
      fi

      # Default extension to username if not provided
      extension="${extension:-$username}"

      # Default caller_id to OUTBOUND_CALLER_ID or extension
      if [ -z "$caller_id" ]; then
        caller_id="${OUTBOUND_CALLER_ID:-$extension}"
      fi

      echo_log "Creating user: $username (extension: $extension, caller_id: $caller_id)"

      cat > "$FS_CONF/directory/default/$username.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <user id="$username" number-alias="$extension">
    <params>
      <param name="password" value="$password"/>
      <param name="vm-password" value="$password"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_number" value="$caller_id"/>
      <variable name="effective_caller_id_name" value="$username"/>
      <variable name="outbound_caller_id_number" value="$caller_id"/>
      <variable name="outbound_caller_id_name" value="$username"/>
      <!-- NAT Traversal - applied to ALL calls from this user -->
      <variable name="rtp_auto_adjust" value="true"/>
      <variable name="sip_comedia" value="true"/>
      <variable name="bypass_media" value="false"/>
      <variable name="sip_nat_detected" value="true"/>
    </variables>
  </user>
</include>
EOF

      user_count=$((user_count + 1))
    done
  fi

  echo_log "Generated $user_count authenticated users"
}

################################################################################
# Generate ACL Users (no authentication, IP-based)
# Format: ACL_USERS="user1:192.168.1.100:1001:+4932221803986,user2:192.168.1.101:1002"
# Multiple IPs: ACL_USERS="user1:192.168.1.100|192.168.1.101|10.0.0.5:1001:+4932221803986"
# Caller ID is optional
################################################################################

generate_acl_users() {
  echo_log "Generating ACL configuration..."

  local acl_count=0
  local outbound_caller_id
  local has_acl_users=false
  local has_blacklist=false

  # Get default outbound caller ID and check for ACL users / blacklist
  if [ "$USE_JSON_CONFIG" = true ]; then
    outbound_caller_id=$(get_json_value '.routes.outbound_caller_id' '')
    local acl_len
    acl_len=$(get_json_array_length '.acl_users')
    if [ "$acl_len" -gt 0 ]; then
      has_acl_users=true
    fi
    # Check for blacklist
    local bl_len
    bl_len=$(jq -r '.security.blacklist | length // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)
    if [ "$bl_len" -gt 0 ]; then
      has_blacklist=true
    fi
  else
    outbound_caller_id="${OUTBOUND_CALLER_ID:-}"
    if [ -n "$ACL_USERS" ]; then
      has_acl_users=true
    fi
  fi

  if [ "$has_acl_users" = false ] && [ "$has_blacklist" = false ]; then
    echo_log "No ACL users or blacklist defined, skipping..."
    return
  fi

  # Create ACL configuration header
  cat > "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<configuration name="acl.conf" description="Network Lists">
  <network-lists>
    <list name="domains" default="deny">
      <node type="allow" domain="$${domain}"/>
    </list>
    <!-- ACL for IP-based authentication (no password required) -->
    <list name="acl_users" default="deny">
EOF

  if [ "$USE_JSON_CONFIG" = true ]; then
    # Read from JSON config
    local acl_len
    acl_len=$(get_json_array_length '.acl_users')

    for ((i=0; i<acl_len; i++)); do
      local username extension caller_id enabled

      username=$(jq -r ".acl_users[$i].username // empty" "$CONFIG_FILE")
      extension=$(jq -r ".acl_users[$i].extension // empty" "$CONFIG_FILE")
      caller_id=$(jq -r ".acl_users[$i].caller_id // empty" "$CONFIG_FILE")
      enabled=$(jq -r ".acl_users[$i].enabled // true" "$CONFIG_FILE")

      if [ "$enabled" != "true" ]; then
        echo_log "Skipping disabled ACL user: $username"
        continue
      fi

      if [ -z "$username" ]; then
        echo_log "WARNING: Invalid ACL user at index $i (skipping)"
        continue
      fi

      extension="${extension:-$username}"
      caller_id="${caller_id:-$outbound_caller_id}"
      caller_id="${caller_id:-$extension}"

      # Get IPs array
      local ips_json
      ips_json=$(jq -r ".acl_users[$i].ips | @json" "$CONFIG_FILE")
      local ip_count
      ip_count=$(jq -r ".acl_users[$i].ips | length // 0" "$CONFIG_FILE")

      echo_log "Creating ACL user: $username ($ip_count IPs, extension: $extension)"

      # Add each IP to ACL
      for ((j=0; j<ip_count; j++)); do
        local ip
        ip=$(jq -r ".acl_users[$i].ips[$j]" "$CONFIG_FILE")

        # If IP already contains /, use as-is (CIDR). Otherwise add /32 (single IP)
        if [[ "$ip" == *"/"* ]]; then
          local cidr="$ip"
        else
          local cidr="$ip/32"
        fi

        echo_log "  Adding IP to ACL: $cidr"
        cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<EOF
      <node type="allow" cidr="$cidr"/>
EOF
      done

      # Create user directory entry without password
      cat > "$FS_CONF/directory/default/$username.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <user id="$username" number-alias="$extension">
    <params>
      <param name="a1-hash" value="disabled"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_number" value="$caller_id"/>
      <variable name="effective_caller_id_name" value="$username"/>
      <variable name="outbound_caller_id_number" value="$caller_id"/>
      <variable name="outbound_caller_id_name" value="$username"/>
    </variables>
  </user>
</include>
EOF

      acl_count=$((acl_count + 1))
    done
  else
    # Read from ENV
    IFS=',' read -ra ACL_ARRAY <<< "$ACL_USERS"

    for acl_entry in "${ACL_ARRAY[@]}"; do
      IFS=':' read -r username ip_list extension caller_id <<< "$acl_entry"

      if [ -z "$username" ] || [ -z "$ip_list" ]; then
        echo_log "WARNING: Invalid ACL entry: $acl_entry (skipping)"
        continue
      fi

      extension="${extension:-$username}"

      # Default caller_id to OUTBOUND_CALLER_ID or extension
      if [ -z "$caller_id" ]; then
        caller_id="${OUTBOUND_CALLER_ID:-$extension}"
      fi

      # Parse multiple IPs separated by | (pipe)
      IFS='|' read -ra IP_ARRAY <<< "$ip_list"
      local ip_count=${#IP_ARRAY[@]}

      if [ $ip_count -gt 1 ]; then
        echo_log "Creating ACL user: $username ($ip_count IPs, extension: $extension, caller_id: $caller_id)"
      else
        echo_log "Creating ACL user: $username (IP: $ip_list, extension: $extension, caller_id: $caller_id)"
      fi

      # Add each IP to ACL (support both single IP and CIDR notation)
      for ip in "${IP_ARRAY[@]}"; do
        # If IP already contains /, use as-is (CIDR). Otherwise add /32 (single IP)
        if [[ "$ip" == *"/"* ]]; then
          local cidr="$ip"
        else
          local cidr="$ip/32"
        fi

        echo_log "  Adding IP to ACL: $cidr"

        # Add IP to common ACL list
        cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<EOF
      <node type="allow" cidr="$cidr"/>
EOF
      done

      # Create user directory entry without password (one user for all IPs)
      cat > "$FS_CONF/directory/default/$username.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <user id="$username" number-alias="$extension">
    <params>
      <param name="a1-hash" value="disabled"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_number" value="$caller_id"/>
      <variable name="effective_caller_id_name" value="$username"/>
      <variable name="outbound_caller_id_number" value="$caller_id"/>
      <variable name="outbound_caller_id_name" value="$username"/>
    </variables>
  </user>
</include>
EOF

      acl_count=$((acl_count + 1))
    done
  fi

  # Close ACL users list
  cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
    </list>
EOF

  # Add blacklist if present (from JSON config)
  local blacklist_count=0
  if [ "$USE_JSON_CONFIG" = true ]; then
    local bl_len
    bl_len=$(jq -r '.security.blacklist | length // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)

    if [ "$bl_len" -gt 0 ]; then
      echo_log "Adding blacklist ACL ($bl_len IPs)..."

      cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
    <!-- Blacklist - blocked IPs -->
    <list name="blacklist" default="allow">
EOF

      for ((i=0; i<bl_len; i++)); do
        local ip comment
        ip=$(jq -r ".security.blacklist[$i].ip // empty" "$CONFIG_FILE")

        if [ -n "$ip" ]; then
          # If IP already contains /, use as-is (CIDR). Otherwise add /32 (single IP)
          if [[ "$ip" == *"/"* ]]; then
            local cidr="$ip"
          else
            local cidr="$ip/32"
          fi

          comment=$(jq -r ".security.blacklist[$i].comment // empty" "$CONFIG_FILE")
          echo_log "  Blocking IP: $cidr ${comment:+($comment)}"

          cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<EOF
      <node type="deny" cidr="$cidr"/>
EOF
          blacklist_count=$((blacklist_count + 1))
        fi
      done

      cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
    </list>
EOF
      echo_log "Added $blacklist_count IPs to blacklist"
    fi
  fi

  # Close network-lists and configuration
  cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
  </network-lists>
</configuration>
EOF

  echo_log "Generated $acl_count ACL users"
}

################################################################################
# Generate Directory default.xml
################################################################################

generate_directory() {
  echo_log "Generating directory configuration..."

  cat > "$FS_CONF/directory/default.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <domain name="\$\${domain}">
    <params>
      <param name="dial-string" value="{^^:sip_invite_domain=\$\${domain}:presence_id=\${dialed_user}@\$\${domain}}{\${sofia_contact(\${dialed_user}@\$\${domain})}}"/>
      <param name="jsonrpc-allowed-methods" value="verto"/>
    </params>

    <variables>
      <variable name="record_stereo" value="true"/>
      <variable name="default_gateway" value="\$\${default_gateway}"/>
      <variable name="default_areacode" value="\$\${default_areacode}"/>
      <variable name="transfer_fallback_extension" value="operator"/>
    </variables>

    <groups>
      <group name="default">
        <users>
          <X-PRE-PROCESS cmd="include" data="default/*.xml"/>
        </users>
      </group>
    </groups>
  </domain>
</include>
EOF

  echo_log "Directory configuration generated"
}

################################################################################
# Generate Gateways
# Format: GATEWAYS="type:name:host:port:user:pass:register:transport:auth_user,..."
# Fields: type:name:host:port:username:password:register:transport:auth_user
# Types: sip (default), 3cx, pbx, nebenstelle
################################################################################

generate_gateways() {
  echo_log "Generating gateways..."

  # Clean up old gateway XML files to prevent duplicates
  local gw_dir="$FS_CONF/sip_profiles/external"
  if [ -d "$gw_dir" ]; then
    echo_log "Cleaning up old gateway files in $gw_dir..."
    rm -f "$gw_dir"/*.xml 2>/dev/null || true
  fi

  local gw_count=0

  if [ "$USE_JSON_CONFIG" = true ]; then
    # Read from JSON config
    local gateways_len
    gateways_len=$(get_json_array_length '.gateways')

    if [ "$gateways_len" -eq 0 ]; then
      echo_log "No gateways in JSON config, skipping..."
      return
    fi

    for ((i=0; i<gateways_len; i++)); do
      local gw_type gw_name gw_host gw_port gw_user gw_pass gw_register gw_transport gw_auth_user enabled

      gw_type=$(jq -r ".gateways[$i].type // \"sip\"" "$CONFIG_FILE")
      gw_name=$(jq -r ".gateways[$i].name // empty" "$CONFIG_FILE")
      gw_host=$(jq -r ".gateways[$i].host // empty" "$CONFIG_FILE")
      gw_port=$(jq -r ".gateways[$i].port // 5060" "$CONFIG_FILE")
      gw_user=$(jq -r ".gateways[$i].username // empty" "$CONFIG_FILE")
      gw_pass=$(jq -r ".gateways[$i].password // empty" "$CONFIG_FILE")
      gw_register=$(jq -r ".gateways[$i].register // true" "$CONFIG_FILE")
      gw_transport=$(jq -r ".gateways[$i].transport // \"udp\"" "$CONFIG_FILE")
      gw_auth_user=$(jq -r ".gateways[$i].auth_username // empty" "$CONFIG_FILE")
      enabled=$(jq -r ".gateways[$i].enabled // true" "$CONFIG_FILE")

      if [ "$enabled" != "true" ]; then
        echo_log "Skipping disabled gateway: $gw_name"
        continue
      fi

      if [ -z "$gw_name" ] || [ -z "$gw_host" ]; then
        echo_log "WARNING: Invalid gateway at index $i (skipping)"
        continue
      fi

      # If auth_user not provided, use username
      if [ -z "$gw_auth_user" ]; then
        gw_auth_user="$gw_user"
      fi

      echo_log "Creating gateway [$gw_type]: $gw_name ($gw_host:$gw_port, register: $gw_register)"

      # Write gateway XML
      _write_gateway_xml "$gw_name" "$gw_host" "$gw_port" "$gw_user" "$gw_pass" "$gw_register" "$gw_transport" "$gw_auth_user"

      gw_count=$((gw_count + 1))
    done
  else
    # Read from ENV
    if [ -z "$GATEWAYS" ]; then
      echo_log "No gateways defined, skipping..."
      return
    fi

    IFS=',' read -ra GW_ARRAY <<< "$GATEWAYS"

    for gw_entry in "${GW_ARRAY[@]}"; do
      IFS=':' read -r gw_type gw_name gw_host gw_port gw_user gw_pass gw_register gw_transport gw_auth_user <<< "$gw_entry"

      if [ -z "$gw_type" ] || [ -z "$gw_name" ] || [ -z "$gw_host" ]; then
        echo_log "WARNING: Invalid gateway entry: $gw_entry (skipping)"
        continue
      fi

      # Defaults
      gw_port="${gw_port:-5060}"
      gw_register="${gw_register:-true}"
      gw_transport="${gw_transport:-udp}"

      # If auth_user not provided, use username as auth_user (default behavior)
      if [ -z "$gw_auth_user" ]; then
        gw_auth_user="$gw_user"
      fi

      if [ -n "$gw_auth_user" ] && [ "$gw_auth_user" != "$gw_user" ]; then
        echo_log "Creating gateway [$gw_type]: $gw_name ($gw_host:$gw_port, user: $gw_user, auth: $gw_auth_user, register: $gw_register)"
      else
        echo_log "Creating gateway [$gw_type]: $gw_name ($gw_host:$gw_port, register: $gw_register)"
      fi

      # Write gateway XML
      _write_gateway_xml "$gw_name" "$gw_host" "$gw_port" "$gw_user" "$gw_pass" "$gw_register" "$gw_transport" "$gw_auth_user"

      gw_count=$((gw_count + 1))
    done
  fi

  echo_log "Generated $gw_count gateways"
}

# Helper function to write gateway XML
_write_gateway_xml() {
  local gw_name="$1"
  local gw_host="$2"
  local gw_port="$3"
  local gw_user="$4"
  local gw_pass="$5"
  local gw_register="$6"
  local gw_transport="$7"
  local gw_auth_user="$8"

  cat > "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <gateway name="$gw_name">
EOF

  # Add username and password only if provided
  if [ -n "$gw_user" ]; then
    # For 3CX and similar: if auth-username differs, use it in from-user
    local from_user="$gw_user"
    if [ -n "$gw_auth_user" ] && [ "$gw_auth_user" != "$gw_user" ]; then
      from_user="$gw_auth_user"
    fi

    cat >> "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
    <param name="username" value="$gw_user"/>
    <param name="from-user" value="$from_user"/>
EOF
  fi

  # Add auth-username if different from username (for providers like 3CX)
  if [ -n "$gw_auth_user" ] && [ "$gw_auth_user" != "$gw_user" ]; then
    cat >> "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
    <param name="auth-username" value="$gw_auth_user"/>
EOF
  fi

  if [ -n "$gw_pass" ]; then
    cat >> "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
    <param name="password" value="$gw_pass"/>
EOF
  fi

  # Add gateway parameters
  cat >> "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
    <param name="realm" value="$gw_host"/>
    <param name="from-domain" value="$gw_host"/>
    <param name="proxy" value="$gw_host:$gw_port"/>
    <param name="register" value="$gw_register"/>
    <param name="register-transport" value="$gw_transport"/>
    <param name="retry-seconds" value="30"/>
    <param name="expire-seconds" value="600"/>
    <param name="caller-id-in-from" value="false"/>
    <param name="extension-in-contact" value="true"/>
    <!-- contact-params: empty to keep Contact clean -->
    <param name="contact-params" value=""/>
  </gateway>
</include>
EOF
}

################################################################################
# Generate Local Extensions Dialplan (calls to local users)
# Matches extensions 1000-1999 and routes to registered users
################################################################################

generate_local_extensions_dialplan() {
  echo_log "Generating local extensions dialplan..."

  cat > "$FS_CONF/dialplan/default/00_local_extensions.xml" <<'EOF'
<!-- Local extension routing - included by default.xml wrapper -->

    <!-- Route calls to local extensions (1000-1999) -->
    <extension name="local_extensions">
      <condition field="destination_number" expression="^(1[0-9]{3})$">
        <!-- NAT Traversal: use real IP from SIP packets, not SDP -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="set" data="continue_on_fail=true"/>
        <!-- Lookup user by extension (number-alias) and get real username, then call -->
        <action application="set" data="target_user=${user_data(${destination_number}@$${domain} attr id)}"/>
        <action application="bridge" data="${sofia_contact(${target_user}@$${domain})}"/>
      </condition>
    </extension>
EOF

  echo_log "Local extensions dialplan generated"
}

################################################################################
# Generate User-based Outbound Routing
# Routes calls based on WHO is calling (not destination number)
# Format: OUTBOUND_USER_ROUTES="alice:provider1,bob:provider2,vapi1:provider3"
################################################################################

generate_user_outbound_routing() {
  echo_log "Generating user-based outbound routing..."

  local route_count=0
  local country_code

  # Get default country code
  if [ "$USE_JSON_CONFIG" = true ]; then
    country_code=$(get_json_value '.settings.default_country_code' '49')
  else
    country_code="${DEFAULT_COUNTRY_CODE:-49}"
  fi

  cat > "$FS_CONF/dialplan/default/000_user_routing.xml" <<'EOF'
<!-- User-based outbound routing - HIGHEST PRIORITY (processed before default gateway) -->
EOF

  if [ "$USE_JSON_CONFIG" = true ]; then
    # Read from JSON config
    local routes_len
    routes_len=$(get_json_array_length '.routes.user_routes')

    if [ "$routes_len" -eq 0 ]; then
      echo_log "No user-based outbound routes in JSON config"
      return
    fi

    for ((i=0; i<routes_len; i++)); do
      local username gateway

      username=$(jq -r ".routes.user_routes[$i].username // empty" "$CONFIG_FILE")
      gateway=$(jq -r ".routes.user_routes[$i].gateway // empty" "$CONFIG_FILE")

      if [ -z "$username" ] || [ -z "$gateway" ]; then
        echo_log "WARNING: Invalid user route at index $i (skipping)"
        continue
      fi

      echo_log "Creating user route: $username -> $gateway"
      _write_user_route_xml "$username" "$gateway" "$country_code"
      route_count=$((route_count + 1))
    done
  else
    # Read from ENV
    if [ -z "$OUTBOUND_USER_ROUTES" ]; then
      echo_log "No user-based outbound routes defined"
      return
    fi

    IFS=',' read -ra ROUTE_ARRAY <<< "$OUTBOUND_USER_ROUTES"

    for route_entry in "${ROUTE_ARRAY[@]}"; do
      IFS=':' read -r username gateway <<< "$route_entry"

      if [ -z "$username" ] || [ -z "$gateway" ]; then
        echo_log "WARNING: Invalid user route entry: $route_entry (skipping)"
        continue
      fi

      echo_log "Creating user route: $username -> $gateway"
      _write_user_route_xml "$username" "$gateway" "$country_code"
      route_count=$((route_count + 1))
    done
  fi

  echo_log "Generated $route_count user-based outbound routes"
}

# Helper function to write user route XML
_write_user_route_xml() {
  local username="$1"
  local gateway="$2"
  local country_code="$3"

  cat >> "$FS_CONF/dialplan/default/000_user_routing.xml" <<EOF

    <!-- User $username routes to gateway $gateway -->

    <!-- International format: +49... or 00... -->
    <extension name="user_${username}_international">
      <condition field="username" expression="^${username}\$"/>
      <condition field="destination_number" expression="^(\+|00)(.+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/\$1\$2"/>
      </condition>
    </extension>

    <!-- Country code format: 49... → +49... -->
    <extension name="user_${username}_with_country_code">
      <condition field="username" expression="^${username}\$"/>
      <condition field="destination_number" expression="^($country_code[1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/+\$1"/>
      </condition>
    </extension>

    <!-- National format: 0123... → +49123... -->
    <extension name="user_${username}_national">
      <condition field="username" expression="^${username}\$"/>
      <condition field="destination_number" expression="^0([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/+$country_code\$1"/>
      </condition>
    </extension>

    <!-- Default: add country code -->
    <extension name="user_${username}_default">
      <condition field="username" expression="^${username}\$"/>
      <condition field="destination_number" expression="^([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/+$country_code\$1"/>
      </condition>
    </extension>
EOF
}

################################################################################
# Generate Outbound Dialplan (user -> gateway)
# Format: OUTBOUND_ROUTES="pattern1:gateway1:prepend1,pattern2:gateway2:prepend2"
################################################################################

generate_outbound_dialplan() {
  echo_log "Generating outbound dialplan..."

  local default_gateway country_code
  local has_outbound_routes=false

  # Get settings from JSON or ENV
  if [ "$USE_JSON_CONFIG" = true ]; then
    default_gateway=$(get_json_value '.routes.default_gateway' '')
    country_code=$(get_json_value '.settings.default_country_code' '49')
    local outbound_len
    outbound_len=$(get_json_array_length '.routes.outbound')
    if [ "$outbound_len" -gt 0 ]; then
      has_outbound_routes=true
    fi
  else
    default_gateway="$DEFAULT_GATEWAY"
    country_code="${DEFAULT_COUNTRY_CODE:-49}"
    if [ -n "$OUTBOUND_ROUTES" ]; then
      has_outbound_routes=true
    fi
  fi

  cat > "$FS_CONF/dialplan/default/00_outbound.xml" <<'EOF'
<!-- Outbound dialplan rules - included by default.xml wrapper -->
EOF

  if [ "$has_outbound_routes" = true ]; then
    local route_count=0

    if [ "$USE_JSON_CONFIG" = true ]; then
      # Read from JSON config
      local outbound_len
      outbound_len=$(get_json_array_length '.routes.outbound')

      for ((i=0; i<outbound_len; i++)); do
        local pattern gateway prepend strip

        pattern=$(jq -r ".routes.outbound[$i].pattern // empty" "$CONFIG_FILE")
        gateway=$(jq -r ".routes.outbound[$i].gateway // empty" "$CONFIG_FILE")
        prepend=$(jq -r ".routes.outbound[$i].prepend // empty" "$CONFIG_FILE")
        strip=$(jq -r ".routes.outbound[$i].strip // empty" "$CONFIG_FILE")

        if [ -z "$pattern" ] || [ -z "$gateway" ]; then
          echo_log "WARNING: Invalid outbound route at index $i (skipping)"
          continue
        fi

        echo_log "Creating outbound route: $pattern -> $gateway"
        _write_outbound_route_xml "$pattern" "$gateway" "$prepend" "$strip" "$route_count"
        route_count=$((route_count + 1))
      done
    else
      # Read from ENV
      IFS=',' read -ra ROUTE_ARRAY <<< "$OUTBOUND_ROUTES"

      for route_entry in "${ROUTE_ARRAY[@]}"; do
        IFS=':' read -r pattern gateway prepend strip <<< "$route_entry"

        if [ -z "$pattern" ] || [ -z "$gateway" ]; then
          echo_log "WARNING: Invalid outbound route: $route_entry (skipping)"
          continue
        fi

        echo_log "Creating outbound route: $pattern -> $gateway"
        _write_outbound_route_xml "$pattern" "$gateway" "$prepend" "$strip" "$route_count"
        route_count=$((route_count + 1))
      done
    fi

    echo_log "Generated $route_count outbound routes"
  else
    # Default catch-all outbound route
    if [ -n "$default_gateway" ]; then
      echo_log "Creating default outbound route via $default_gateway"

      cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF

    <!-- Normalize international format: +49... or 00... -->
    <extension name="outbound_international">
      <condition field="destination_number" expression="^(\+|00)(.+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$default_gateway/\$1\$2"/>
      </condition>
    </extension>

    <!-- Numbers already with country code: 49123... → +49123... -->
    <extension name="outbound_with_country_code">
      <condition field="destination_number" expression="^($country_code[1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$default_gateway/+\$1"/>
      </condition>
    </extension>

    <!-- Normalize national format: 0123... → +49123... -->
    <extension name="outbound_national">
      <condition field="destination_number" expression="^0([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$default_gateway/+$country_code\$1"/>
      </condition>
    </extension>

    <!-- Fallback: no prefix, add country code -->
    <extension name="outbound_default">
      <condition field="destination_number" expression="^([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$default_gateway/+$country_code\$1"/>
      </condition>
    </extension>
EOF
    else
      echo_log "WARNING: No outbound routes or default gateway defined"
    fi
  fi

  echo_log "Outbound dialplan generated"
}

# Helper function to write outbound route XML
_write_outbound_route_xml() {
  local pattern="$1"
  local gateway="$2"
  local prepend="$3"
  local strip="$4"
  local route_count="$5"

  cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF

    <!-- Route: $pattern via $gateway -->
    <extension name="outbound_${gateway}_${route_count}">
      <condition field="destination_number" expression="^($pattern)\$">
EOF

  # Strip prefix if specified
  local dial_number="\$1"
  if [ -n "$strip" ]; then
    cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="stripped_number=\${regex(\$1|^$strip(.*)|\$1)}"/>
EOF
    dial_number="\${stripped_number}"
  fi

  # Add prepend if specified
  if [ -n "$prepend" ]; then
    cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <action application="set" data="final_number=$prepend$dial_number"/>
EOF
    dial_number="\${final_number}"
  fi

  cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <!-- NAT Traversal: ignore SDP address, use real IP from SIP packets -->
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="ignore_sdp_addr=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/$dial_number"/>
      </condition>
    </extension>
EOF
}

################################################################################
# Generate Inbound Dialplan (gateway -> extension)
# Format: INBOUND_ROUTES="gateway1:extension1,gateway2:extension2"
# Example: INBOUND_ROUTES="fritz-rt:1001,sipgate-rt:1002"
# Matches on 'gw=' parameter in SIP request URI or destination_number
################################################################################

generate_inbound_dialplan() {
  echo_log "Generating inbound dialplan..."

  local default_extension
  local has_inbound_routes=false

  # Get default extension from JSON or ENV
  if [ "$USE_JSON_CONFIG" = true ]; then
    default_extension=$(get_json_value '.routes.default_extension' '')
    local inbound_len
    inbound_len=$(get_json_array_length '.routes.inbound')
    if [ "$inbound_len" -gt 0 ]; then
      has_inbound_routes=true
    fi
  else
    default_extension="$DEFAULT_EXTENSION"
    if [ -n "$INBOUND_ROUTES" ]; then
      has_inbound_routes=true
    fi
  fi

  cat > "$FS_CONF/dialplan/public/00_inbound.xml" <<'EOF'
<!-- Inbound dialplan rules - included by public.xml wrapper -->
<!-- Routes match on 'gw=' parameter from SIP request URI (e.g., gw=fritz-rt) -->
EOF

  if [ "$has_inbound_routes" = true ]; then
    local route_count=0

    if [ "$USE_JSON_CONFIG" = true ]; then
      # Read from JSON config
      local inbound_len
      inbound_len=$(get_json_array_length '.routes.inbound')

      for ((i=0; i<inbound_len; i++)); do
        local gateway extension

        gateway=$(jq -r ".routes.inbound[$i].gateway // empty" "$CONFIG_FILE")
        extension=$(jq -r ".routes.inbound[$i].extension // empty" "$CONFIG_FILE")

        if [ -z "$gateway" ] || [ -z "$extension" ]; then
          echo_log "WARNING: Invalid inbound route at index $i (skipping)"
          continue
        fi

        echo_log "Creating inbound route: gateway $gateway -> extension $extension"

        # Look up gateway host from JSON gateways for registration-based matching
        local inbound_gw_host=""
        inbound_gw_host=$(jq -r ".gateways[] | select(.name == \"$gateway\") | .host // empty" "$CONFIG_FILE" 2>/dev/null | head -1)
        if [ -n "$inbound_gw_host" ]; then
          echo_log "  Found gateway host: $inbound_gw_host"
        fi

        _write_inbound_route_xml "$gateway" "$extension" "$inbound_gw_host"
        route_count=$((route_count + 1))
      done
    else
      # Read from ENV
      IFS=',' read -ra INBOUND_ARRAY <<< "$INBOUND_ROUTES"

      for inbound_entry in "${INBOUND_ARRAY[@]}"; do
        IFS=':' read -r gateway extension <<< "$inbound_entry"

        if [ -z "$gateway" ] || [ -z "$extension" ]; then
          echo_log "WARNING: Invalid inbound route: $inbound_entry (skipping)"
          continue
        fi

        echo_log "Creating inbound route: gateway $gateway -> extension $extension"

        # Look up gateway host from GATEWAYS variable for registration-based matching
        local inbound_gw_host=""
        if [ -n "$GATEWAYS" ]; then
          IFS=',' read -ra GW_LOOKUP_ARRAY <<< "$GATEWAYS"
          for gw_lookup_entry in "${GW_LOOKUP_ARRAY[@]}"; do
            IFS=':' read -r lookup_type lookup_name lookup_host lookup_rest <<< "$gw_lookup_entry"
            if [ "$lookup_name" = "$gateway" ]; then
              inbound_gw_host="$lookup_host"
              echo_log "  Found gateway host: $inbound_gw_host (type: $lookup_type)"
              break
            fi
          done
        fi

        _write_inbound_route_xml "$gateway" "$extension" "$inbound_gw_host"
        route_count=$((route_count + 1))
      done
    fi

    echo_log "Generated $route_count inbound routes"
  else
    # Default: forward all inbound to default extension
    if [ -n "$default_extension" ]; then
      # Check if default_extension is a gateway reference (format: gateway@gateway_name)
      if [[ "$default_extension" =~ ^gateway@(.+)$ ]]; then
        local gateway_name="${BASH_REMATCH[1]}"
        echo_log "Creating default inbound route to gateway $gateway_name"

        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Default inbound route to gateway -->
    <extension name="inbound_default">
      <condition field="destination_number" expression="^(.+)\$">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway_name/\$1"/>
      </condition>
    </extension>
EOF
      else
        echo_log "Creating default inbound route to extension $default_extension"

        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Default inbound route -->
    <extension name="inbound_default">
      <condition field="destination_number" expression="^(.+)\$">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="transfer" data="$default_extension XML default"/>
      </condition>
    </extension>
EOF
      fi
    else
      echo_log "WARNING: No inbound routes or default extension defined"
    fi
  fi

  echo_log "Inbound dialplan generated"
}

# Helper function to write inbound route XML
_write_inbound_route_xml() {
  local gateway="$1"
  local extension="$2"
  local inbound_gw_host="$3"

  local ext_name="inbound_${gateway}"

  # Check if extension is a gateway reference (format: gateway@gateway_name)
  if [[ "$extension" =~ ^gateway@(.+)$ ]]; then
    local out_gateway="${BASH_REMATCH[1]}"
    echo_log "  Routing to gateway: $out_gateway"

    cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Inbound: gateway $gateway -> outbound gateway $out_gateway -->
    <extension name="$ext_name">
      <condition field="\${sip_req_params}" expression="(^|;)gw=${gateway}($|;)">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="export" data="rtp_auto_adjust=true"/>
        <action application="export" data="sip_comedia=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$out_gateway/\${destination_number}"/>
      </condition>
    </extension>
EOF
  else
    # Regular extension transfer - first the gw= parameter match
    cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Inbound: gateway $gateway -> extension $extension (via gw= parameter) -->
    <extension name="$ext_name">
      <condition field="\${sip_req_params}" expression="(^|;)gw=${gateway}($|;)">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="transfer" data="$extension XML default"/>
      </condition>
    </extension>
EOF

    # Add registration-based matching if we found the gateway host
    if [ -n "$inbound_gw_host" ]; then
      echo_log "  Adding registration-based matching for host: $inbound_gw_host"
      cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Inbound: gateway $gateway -> extension $extension (via registered gateway) -->
    <!-- This handles calls from PBX systems (like 3CX) that send to registered contact without gw= param -->
    <!-- Matches on sip_from_host containing gateway host domain -->
    <extension name="${ext_name}_via_registration">
      <condition field="\${sip_from_host}" expression="$inbound_gw_host" break="on-false"/>
      <condition field="destination_number" expression="^(.+)$">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="log" data="INFO Inbound from registered gateway $gateway (host $inbound_gw_host) to extension $extension"/>
        <action application="transfer" data="$extension XML default"/>
      </condition>
    </extension>
EOF
    fi
  fi
}

################################################################################
# Create Dialplan Wrapper Files
################################################################################

create_dialplan_wrappers() {
  echo_log "Creating dialplan wrapper files..."

  # Create default.xml wrapper to include default/*.xml
  cat > "$FS_CONF/dialplan/default.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <context name="default">
    <X-PRE-PROCESS cmd="include" data="default/*.xml"/>
  </context>
</include>
EOF

  echo_log "Created /etc/freeswitch/dialplan/default.xml"

  # Create public.xml wrapper to include public/*.xml
  cat > "$FS_CONF/dialplan/public.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <context name="public">
    <X-PRE-PROCESS cmd="include" data="public/*.xml"/>
  </context>
</include>
EOF

  echo_log "Created /etc/freeswitch/dialplan/public.xml"
  echo_log "Dialplan wrapper files created successfully"
}

################################################################################
# Apply Configuration
################################################################################

apply_config() {
  echo_log "Applying configuration..."

  # Check if FreeSWITCH is running
  if ! pgrep -x "freeswitch" > /dev/null; then
    echo_log "FreeSWITCH is not running, skipping reload"
    return
  fi

  # Reload XML configuration
  if command -v fs_cli >/dev/null 2>&1; then
    echo_log "Reloading XML configuration..."
    fs_cli -x "reloadxml" || echo_log "WARNING: Failed to reload XML"

    echo_log "Rescanning SIP profiles..."
    fs_cli -x "sofia profile internal rescan" || echo_log "WARNING: Failed to rescan internal profile"
    fs_cli -x "sofia profile external rescan" || echo_log "WARNING: Failed to rescan external profile"

    # Restart profiles if requested
    if [ "$RESTART_PROFILES" = "true" ]; then
      echo_log "Restarting SIP profiles..."
      fs_cli -x "sofia profile internal restart reloadxml" || true
      fs_cli -x "sofia profile external restart reloadxml" || true
    fi

    sleep 2

    # Show status
    echo_log "SIP profile status:"
    fs_cli -x "sofia status" || true

    echo_log "Gateway registrations:"
    fs_cli -x "sofia status gateway" || true
  else
    echo_log "WARNING: fs_cli not found, cannot reload configuration"
  fi

  echo_log "Configuration applied"
}

################################################################################
# Summary
################################################################################

show_summary() {
  echo_log ""
  echo_log "=============================================="
  echo_log "FreeSWITCH Provisioning Complete"
  echo_log "=============================================="
  echo_log ""
  echo_log "Configuration directory: $FS_CONF"
  echo_log "Backup directory: $BACKUP_DIR"
  echo_log ""
  echo_log "Generated:"
  echo_log "  - vars.xml (global variables)"
  echo_log "  - internal.xml (authenticated users profile)"
  echo_log "  - external.xml (gateways and inbound profile)"
  echo_log "  - directory/default.xml (user directory)"
  echo_log "  - dialplan/default/00_outbound.xml (outbound routes)"
  echo_log "  - dialplan/public/00_inbound.xml (inbound routes)"
  echo_log ""
  echo_log "Next steps:"
  echo_log "1. Start FreeSWITCH: systemctl start freeswitch"
  echo_log "2. Check status: fs_cli -x 'sofia status'"
  echo_log "3. View registrations: fs_cli -x 'show registrations'"
  echo_log "4. View gateways: fs_cli -x 'sofia status gateway'"
  echo_log ""
}

################################################################################
# Generate Routing Config JSON
################################################################################

generate_routing_config_json() {
  echo_log "Generating routing config JSON..."

  local json_file="/var/lib/freeswitch/routing_config.json"

  # Start JSON
  echo '{' > "$json_file"

  # Users array
  echo '  "users": [' >> "$json_file"
  if [ -n "$USERS" ]; then
    local first_user=true
    IFS=',' read -ra USER_ARRAY <<< "$USERS"
    for user_entry in "${USER_ARRAY[@]}"; do
      IFS=':' read -r username password extension <<< "$user_entry"
      if [ -n "$username" ] && [ -n "$extension" ]; then
        if [ "$first_user" = true ]; then
          first_user=false
        else
          echo ',' >> "$json_file"
        fi
        printf '    {"username": "%s", "extension": "%s"}' "$username" "$extension" >> "$json_file"
      fi
    done
  fi
  echo '' >> "$json_file"
  echo '  ],' >> "$json_file"

  # Inbound routes array
  echo '  "inbound_routes": [' >> "$json_file"
  if [ -n "$INBOUND_ROUTES" ]; then
    local first_route=true
    IFS=',' read -ra INBOUND_ARRAY <<< "$INBOUND_ROUTES"
    for route in "${INBOUND_ARRAY[@]}"; do
      IFS=':' read -r gateway extension <<< "$route"
      if [ -n "$gateway" ] && [ -n "$extension" ]; then
        if [ "$first_route" = true ]; then
          first_route=false
        else
          echo ',' >> "$json_file"
        fi
        printf '    {"gateway": "%s", "extension": "%s"}' "$gateway" "$extension" >> "$json_file"
      fi
    done
  fi
  echo '' >> "$json_file"
  echo '  ],' >> "$json_file"

  # Outbound user routes array
  echo '  "outbound_user_routes": [' >> "$json_file"
  if [ -n "$OUTBOUND_USER_ROUTES" ]; then
    local first_route=true
    IFS=',' read -ra ROUTE_ARRAY <<< "$OUTBOUND_USER_ROUTES"
    for route in "${ROUTE_ARRAY[@]}"; do
      IFS=':' read -r username gateway <<< "$route"
      if [ -n "$username" ] && [ -n "$gateway" ]; then
        if [ "$first_route" = true ]; then
          first_route=false
        else
          echo ',' >> "$json_file"
        fi
        printf '    {"username": "%s", "gateway": "%s"}' "$username" "$gateway" >> "$json_file"
      fi
    done
  fi
  echo '' >> "$json_file"
  echo '  ],' >> "$json_file"

  # Gateways array
  echo '  "gateways": [' >> "$json_file"
  if [ -n "$GATEWAYS" ]; then
    local first_gw=true
    IFS=',' read -ra GW_ARRAY <<< "$GATEWAYS"
    for gw_entry in "${GW_ARRAY[@]}"; do
      # Format: type:name:host:port:user:pass:register:transport:auth_user
      IFS=':' read -r gw_type gw_name gw_host gw_port gw_user gw_pass gw_register gw_transport gw_auth_user <<< "$gw_entry"
      if [ -n "$gw_name" ]; then
        if [ "$first_gw" = true ]; then
          first_gw=false
        else
          echo ',' >> "$json_file"
        fi
        printf '    {"name": "%s", "type": "%s", "host": "%s"}' "$gw_name" "$gw_type" "$gw_host" >> "$json_file"
      fi
    done
  fi
  echo '' >> "$json_file"
  echo '  ],' >> "$json_file"

  # Defaults
  printf '  "default_gateway": "%s",\n' "${DEFAULT_GATEWAY:-}" >> "$json_file"
  printf '  "default_extension": "%s",\n' "${DEFAULT_EXTENSION:-}" >> "$json_file"
  printf '  "default_country_code": "%s"\n' "${DEFAULT_COUNTRY_CODE:-49}" >> "$json_file"

  echo '}' >> "$json_file"

  chmod 644 "$json_file"
  echo_log "Routing config saved to $json_file"

  # Also generate JS file for static landing page
  local js_file="/var/lib/freeswitch/routing_config.js"
  echo "// Auto-generated by provision.sh - $(date)" > "$js_file"
  echo "window.ROUTING_CONFIG = $(cat "$json_file");" >> "$js_file"
  chmod 644 "$js_file"
  echo_log "Routing config JS saved to $js_file"
}

################################################################################
# Main
################################################################################

main() {
  # Check if JSON config exists - must be done first
  check_json_config

  show_banner
  build_user_agent
  echo_log "Starting FreeSWITCH provisioning..."

  validate_config
  backup_config
  clean_config

  generate_vars
  generate_event_socket
  generate_internal_profile
  generate_external_profile
  generate_directory
  generate_users
  generate_acl_users
  generate_gateways
  generate_local_extensions_dialplan
  generate_user_outbound_routing
  generate_outbound_dialplan
  generate_inbound_dialplan
  create_dialplan_wrappers
  generate_routing_config_json

  apply_config
  show_summary

  echo_log "Provisioning completed successfully!"
}

main "$@"
