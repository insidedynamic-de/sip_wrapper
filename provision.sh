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

  # Required variables
  require_env "FS_DOMAIN"
  require_env "EXTERNAL_SIP_IP"
  require_env "EXTERNAL_RTP_IP"

  # At least one user or gateway should be defined
  if [ -z "$USERS" ] && [ -z "$GATEWAYS" ]; then
    error_exit "At least one USER or GATEWAY must be defined"
  fi

  echo_log "Configuration validated"
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

  cat > "$FS_CONF/vars.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <!-- Global Variables -->
  <X-PRE-PROCESS cmd="set" data="domain=$FS_DOMAIN"/>
  <X-PRE-PROCESS cmd="set" data="external_sip_ip=$EXTERNAL_SIP_IP"/>
  <X-PRE-PROCESS cmd="set" data="external_rtp_ip=$EXTERNAL_RTP_IP"/>

  <!-- Network Settings -->
  <X-PRE-PROCESS cmd="set" data="internal_sip_port=${INTERNAL_SIP_PORT:-5060}"/>
  <X-PRE-PROCESS cmd="set" data="external_sip_port=${EXTERNAL_SIP_PORT:-5080}"/>

  <!-- RTP Port Range -->
  <X-PRE-PROCESS cmd="set" data="rtp_start_port=${RTP_START_PORT:-16384}"/>
  <X-PRE-PROCESS cmd="set" data="rtp_end_port=${RTP_END_PORT:-32768}"/>

  <!-- SIP Settings -->
  <X-PRE-PROCESS cmd="set" data="sip_tls_version=${SIP_TLS_VERSION:-tlsv1.2}"/>

  <!-- Codec Settings -->
  <X-PRE-PROCESS cmd="set" data="global_codec_prefs=${CODEC_PREFS:-PCMU,PCMA,G729,opus}"/>
  <X-PRE-PROCESS cmd="set" data="outbound_codec_prefs=${OUTBOUND_CODEC_PREFS:-PCMU,PCMA,G729}"/>
</include>
EOF

  echo_log "vars.xml generated"
}

################################################################################
# Generate Internal Profile (for authenticated users)
################################################################################

generate_internal_profile() {
  echo_log "Generating internal SIP profile..."

  # Determine ACL list and blind auth based on whether ACL_USERS is defined
  if [ -n "$ACL_USERS" ]; then
    local inbound_acl="domains,acl_users"
    local blind_auth="true"
    local blind_reg="true"
  else
    local inbound_acl="domains"
    local blind_auth="false"
    local blind_reg="false"
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

    <!-- NAT Handling -->
    <param name="apply-nat-acl" value="rfc1918.auto"/>
    <param name="apply-inbound-acl" value="$inbound_acl"/>
    <param name="local-network-acl" value="localnet.auto"/>

    <!-- NAT Traversal - CRITICAL: Fix audio for clients behind NAT -->
    <!-- Force rport: always use source IP/port from packet, not SIP headers -->
    <param name="NDLB-force-rport" value="safe"/>
    <!-- Store actual received IP in registration contact -->
    <param name="NDLB-received-in-nat-reg-contact" value="true"/>
    <!-- Fix RTP going to wrong IP: rewrite SDP with detected public IP -->
    <param name="NDLB-sendrecv-in-session" value="true"/>
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

    <!-- Media -->
    <param name="inbound-late-negotiation" value="true"/>
    <param name="inbound-zrtp-passthru" value="true"/>

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
    <param name="disable-register" value="false"/>
    <param name="disable-transfer" value="false"/>
    <param name="manual-redirect" value="false"/>

    <!-- Media -->
    <param name="inbound-late-negotiation" value="true"/>
    <param name="inbound-zrtp-passthru" value="true"/>

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
  if [ -z "$USERS" ]; then
    echo_log "No authenticated users defined, skipping..."
    return
  fi

  echo_log "Generating users..."

  local user_count=0
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
  <user id="$username">
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
    </variables>
  </user>
</include>
EOF

    user_count=$((user_count + 1))
  done

  echo_log "Generated $user_count authenticated users"
}

################################################################################
# Generate ACL Users (no authentication, IP-based)
# Format: ACL_USERS="user1:192.168.1.100:1001:+4932221803986,user2:192.168.1.101:1002"
# Caller ID is optional
################################################################################

generate_acl_users() {
  if [ -z "$ACL_USERS" ]; then
    echo_log "No ACL users defined, skipping..."
    return
  fi

  echo_log "Generating ACL users..."

  # Create ACL configuration
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

  local acl_count=0
  IFS=',' read -ra ACL_ARRAY <<< "$ACL_USERS"

  for acl_entry in "${ACL_ARRAY[@]}"; do
    IFS=':' read -r username ip extension caller_id <<< "$acl_entry"

    if [ -z "$username" ] || [ -z "$ip" ]; then
      echo_log "WARNING: Invalid ACL entry: $acl_entry (skipping)"
      continue
    fi

    extension="${extension:-$username}"

    # Default caller_id to OUTBOUND_CALLER_ID or extension
    if [ -z "$caller_id" ]; then
      caller_id="${OUTBOUND_CALLER_ID:-$extension}"
    fi

    echo_log "Creating ACL user: $username (IP: $ip, extension: $extension, caller_id: $caller_id)"

    # Add to ACL (support both single IP and CIDR notation)
    # If IP already contains /, use as-is (CIDR). Otherwise add /32 (single IP)
    if [[ "$ip" == *"/"* ]]; then
      local cidr="$ip"
    else
      local cidr="$ip/32"
    fi

    # Add IP to common ACL list
    cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<EOF
      <node type="allow" cidr="$cidr"/>
EOF

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

  # Close ACL users list and configuration
  cat >> "$FS_CONF/autoload_configs/acl.conf.xml" <<'EOF'
    </list>
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
# Format: GATEWAYS="gw1:provider.com:5060:username:password:true:udp:+4932221803986,gw2:..."
# Fields: name:host:port:username:password:register:transport:caller_id (caller_id is optional)
################################################################################

generate_gateways() {
  if [ -z "$GATEWAYS" ]; then
    echo_log "No gateways defined, skipping..."
    return
  fi

  echo_log "Generating gateways..."

  local gw_count=0
  IFS=',' read -ra GW_ARRAY <<< "$GATEWAYS"

  for gw_entry in "${GW_ARRAY[@]}"; do
    IFS=':' read -r gw_name gw_host gw_port gw_user gw_pass gw_register gw_transport gw_auth_user <<< "$gw_entry"

    if [ -z "$gw_name" ] || [ -z "$gw_host" ]; then
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
      echo_log "Creating gateway: $gw_name ($gw_host:$gw_port, user: $gw_user, auth: $gw_auth_user, register: $gw_register)"
    else
      echo_log "Creating gateway: $gw_name ($gw_host:$gw_port, register: $gw_register)"
    fi

    cat > "$FS_CONF/sip_profiles/external/$gw_name.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<include>
  <gateway name="$gw_name">
EOF

    # Add username and password only if provided
    if [ -n "$gw_user" ]; then
      # For 3CX and similar: if auth-username differs, use it in from-user
      # This ensures the From header matches the authentication username
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
  </gateway>
</include>
EOF

    gw_count=$((gw_count + 1))
  done

  echo_log "Generated $gw_count gateways"
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
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="set" data="continue_on_fail=true"/>
        <action application="bridge" data="sofia/internal/${destination_number}@${domain_name}"/>
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
  if [ -z "$OUTBOUND_USER_ROUTES" ]; then
    echo_log "No user-based outbound routes defined, skipping..."
    return
  fi

  echo_log "Generating user-based outbound routing..."

  cat > "$FS_CONF/dialplan/default/000_user_routing.xml" <<'EOF'
<!-- User-based outbound routing - HIGHEST PRIORITY (processed before default gateway) -->
EOF

  local route_count=0
  IFS=',' read -ra ROUTE_ARRAY <<< "$OUTBOUND_USER_ROUTES"

  for route_entry in "${ROUTE_ARRAY[@]}"; do
    IFS=':' read -r username gateway <<< "$route_entry"

    if [ -z "$username" ] || [ -z "$gateway" ]; then
      echo_log "WARNING: Invalid user route entry: $route_entry (skipping)"
      continue
    fi

    echo_log "Creating user route: $username -> $gateway"

    # Get default country code for number normalization
    local country_code="${DEFAULT_COUNTRY_CODE:-49}"

    cat >> "$FS_CONF/dialplan/default/000_user_routing.xml" <<EOF

    <!-- User $username routes to gateway $gateway -->

    <!-- International format: +49... or 00... -->
    <extension name="user_${username}_international">
      <condition field="username" expression="^${username}\$"/>
      <condition field="destination_number" expression="^(\+|00)(.+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
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
        <action application="set" data="rtp_auto_adjust=true"/>
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
        <action application="set" data="rtp_auto_adjust=true"/>
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
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/+$country_code\$1"/>
      </condition>
    </extension>
EOF

    route_count=$((route_count + 1))
  done

  echo_log "Generated $route_count user-based outbound routes"
}

################################################################################
# Generate Outbound Dialplan (user -> gateway)
# Format: OUTBOUND_ROUTES="pattern1:gateway1:prepend1,pattern2:gateway2:prepend2"
################################################################################

generate_outbound_dialplan() {
  echo_log "Generating outbound dialplan..."

  cat > "$FS_CONF/dialplan/default/00_outbound.xml" <<'EOF'
<!-- Outbound dialplan rules - included by default.xml wrapper -->
EOF

  if [ -n "$OUTBOUND_ROUTES" ]; then
    local route_count=0
    IFS=',' read -ra ROUTE_ARRAY <<< "$OUTBOUND_ROUTES"

    for route_entry in "${ROUTE_ARRAY[@]}"; do
      IFS=':' read -r pattern gateway prepend strip <<< "$route_entry"

      if [ -z "$pattern" ] || [ -z "$gateway" ]; then
        echo_log "WARNING: Invalid outbound route: $route_entry (skipping)"
        continue
      fi

      echo_log "Creating outbound route: $pattern -> $gateway"

      cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF

    <!-- Route: $pattern via $gateway -->
    <extension name="outbound_${gateway}_${route_count}">
      <condition field="destination_number" expression="^($pattern)\$">
EOF

      # Strip prefix if specified
      if [ -n "$strip" ]; then
        cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="stripped_number=\${regex(\$1|^$strip(.*)|\$1)}"/>
EOF
        local dial_number="\${stripped_number}"
      else
        local dial_number="\$1"
      fi

      # Add prepend if specified
      if [ -n "$prepend" ]; then
        cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <action application="set" data="final_number=$prepend$dial_number"/>
EOF
        dial_number="\${final_number}"
      fi

      cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway/$dial_number"/>
      </condition>
    </extension>
EOF

      route_count=$((route_count + 1))
    done

    echo_log "Generated $route_count outbound routes"
  else
    # Default catch-all outbound route
    if [ -n "$DEFAULT_GATEWAY" ]; then
      echo_log "Creating default outbound route via $DEFAULT_GATEWAY"

      # Get default country code (default: 49 for Germany)
      local country_code="${DEFAULT_COUNTRY_CODE:-49}"

      cat >> "$FS_CONF/dialplan/default/00_outbound.xml" <<EOF

    <!-- Normalize international format: +49... or 00... -->
    <extension name="outbound_international">
      <condition field="destination_number" expression="^(\+|00)(.+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$DEFAULT_GATEWAY/\$1\$2"/>
      </condition>
    </extension>

    <!-- Numbers already with country code: 49123... → +49123... -->
    <extension name="outbound_with_country_code">
      <condition field="destination_number" expression="^($country_code[1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$DEFAULT_GATEWAY/+\$1"/>
      </condition>
    </extension>

    <!-- Normalize national format: 0123... → +49123... -->
    <extension name="outbound_national">
      <condition field="destination_number" expression="^0([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$DEFAULT_GATEWAY/+$country_code\$1"/>
      </condition>
    </extension>

    <!-- Fallback: no prefix, add country code -->
    <extension name="outbound_default">
      <condition field="destination_number" expression="^([1-9][0-9]+)\$">
        <action application="set" data="effective_caller_id_number=\${outbound_caller_id_number}"/>
        <action application="set" data="effective_caller_id_name=\${outbound_caller_id_name}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$DEFAULT_GATEWAY/+$country_code\$1"/>
      </condition>
    </extension>
EOF
    else
      echo_log "WARNING: No outbound routes or default gateway defined"
    fi
  fi

  echo_log "Outbound dialplan generated"
}

################################################################################
# Generate Inbound Dialplan (DID -> user)
# Format: INBOUND_ROUTES="DID1:extension1,DID2:extension2,*:1000"
################################################################################

generate_inbound_dialplan() {
  echo_log "Generating inbound dialplan..."

  cat > "$FS_CONF/dialplan/public/00_inbound.xml" <<'EOF'
<!-- Inbound dialplan rules - included by public.xml wrapper -->
EOF

  if [ -n "$INBOUND_ROUTES" ]; then
    local route_count=0
    IFS=',' read -ra INBOUND_ARRAY <<< "$INBOUND_ROUTES"

    for inbound_entry in "${INBOUND_ARRAY[@]}"; do
      IFS=':' read -r did extension <<< "$inbound_entry"

      if [ -z "$did" ] || [ -z "$extension" ]; then
        echo_log "WARNING: Invalid inbound route: $inbound_entry (skipping)"
        continue
      fi

      echo_log "Creating inbound route: DID $did -> extension $extension"

      # Handle wildcard DID
      if [ "$did" = "*" ]; then
        local condition_field="destination_number"
        local condition_expr="^(.+)\$"
        local ext_name="inbound_catchall"
      else
        local condition_field="destination_number"
        local condition_expr="^($did)\$"
        local ext_name="inbound_${did}"
      fi

      # Check if extension is a gateway reference (format: gateway@gateway_name)
      if [[ "$extension" =~ ^gateway@(.+)$ ]]; then
        local gateway_name="${BASH_REMATCH[1]}"
        echo_log "  Routing to gateway: $gateway_name"

        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Inbound: $did -> gateway $gateway_name -->
    <extension name="$ext_name">
      <condition field="$condition_field" expression="$condition_expr">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway_name/\$1"/>
      </condition>
    </extension>
EOF
      else
        # Regular extension transfer
        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Inbound: $did -> extension $extension -->
    <extension name="$ext_name">
      <condition field="$condition_field" expression="$condition_expr">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="transfer" data="$extension XML default"/>
      </condition>
    </extension>
EOF
      fi

      route_count=$((route_count + 1))
    done

    echo_log "Generated $route_count inbound routes"
  else
    # Default: forward all inbound to default extension
    if [ -n "$DEFAULT_EXTENSION" ]; then
      # Check if DEFAULT_EXTENSION is a gateway reference (format: gateway@gateway_name)
      if [[ "$DEFAULT_EXTENSION" =~ ^gateway@(.+)$ ]]; then
        local gateway_name="${BASH_REMATCH[1]}"
        echo_log "Creating default inbound route to gateway $gateway_name"

        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Default inbound route to gateway -->
    <extension name="inbound_default">
      <condition field="destination_number" expression="^(.+)\$">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="set" data="rtp_auto_adjust=true"/>
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="bridge" data="sofia/gateway/$gateway_name/\$1"/>
      </condition>
    </extension>
EOF
      else
        echo_log "Creating default inbound route to extension $DEFAULT_EXTENSION"

        cat >> "$FS_CONF/dialplan/public/00_inbound.xml" <<EOF

    <!-- Default inbound route -->
    <extension name="inbound_default">
      <condition field="destination_number" expression="^(.+)\$">
        <action application="set" data="domain_name=\$\${domain}"/>
        <action application="transfer" data="$DEFAULT_EXTENSION XML default"/>
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
# Main
################################################################################

main() {
  echo_log "Starting FreeSWITCH provisioning..."

  validate_config
  backup_config
  clean_config

  generate_vars
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

  apply_config
  show_summary

  echo_log "Provisioning completed successfully!"
}

main "$@"
