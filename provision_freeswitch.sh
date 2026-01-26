#!/bin/sh
set -eu

echo "[START] FreeSWITCH provisioning (POSIX sh)"

FS_CONF_DIR="${FS_CONF_DIR:-/etc/freeswitch}"

need() {
  k="$1"
  eval v=\${$k-}
  if [ "x$v" = "x" ]; then
    echo "Missing env: $k" >&2
    exit 1
  fi
}

# ===== ENV =====
need SIP_USER
need SIP_PASSWORD
need SIP_DOMAIN
need PROVIDER_HOST
need PROVIDER_PORT
need PROVIDER_USERNAME
need PROVIDER_PASSWORD
need PROVIDER_TRANSPORT
need EXTERNAL_IP

# ===== PATHS =====
DIR_USERS="$FS_CONF_DIR/directory/default"
DP_ROOT="$FS_CONF_DIR/dialplan"
DP_DEFAULT="$DP_ROOT/default"
GW_DIR="$FS_CONF_DIR/sip_profiles/external"

DIALPLAN_CONF="$FS_CONF_DIR/dialplan.conf.xml"
DEFAULT_CTX_XML="$DP_ROOT/default.xml"
VARS_XML="$FS_CONF_DIR/vars.xml"
VARS_LOCAL="$FS_CONF_DIR/vars_local.xml"

mkdir -p "$DIR_USERS" "$DP_DEFAULT" "$GW_DIR"

# ======================================================
# CLEANUP (АГРЕССИВНО, НО БЕЗОПАСНО)
# ======================================================

echo "[CLEANUP] Removing ALL users, dialplans, gateways (keeping default context)"

# Users
rm -f "$DIR_USERS"/*.xml 2>/dev/null || true

# Dialplan extensions (НО НЕ default.xml)
rm -f "$DP_DEFAULT"/*.xml 2>/dev/null || true

# Gateways
rm -f "$GW_DIR"/*.xml 2>/dev/null || true

# Local vars
rm -f "$VARS_LOCAL" 2>/dev/null || true

echo "[CLEANUP] Done"

# ======================================================
# ENSURE DIALPLAN CORE STRUCTURE
# ======================================================

# dialplan.conf.xml
if [ ! -f "$DIALPLAN_CONF" ]; then
  cat > "$DIALPLAN_CONF" <<EOF
<configuration name="dialplan.conf" description="Dialplan Configuration">
  <settings>
    <param name="default_dialplan" value="XML"/>
    <param name="dialplan_directory" value="dialplan"/>
  </settings>
  <contexts>
    <X-PRE-PROCESS cmd="include" data="dialplan/*.xml"/>
  </contexts>
</configuration>
EOF
fi

# default context (CRITICAL)
if [ ! -f "$DEFAULT_CTX_XML" ]; then
  cat > "$DEFAULT_CTX_XML" <<EOF
<include>
  <context name="default">
    <X-PRE-PROCESS cmd="include" data="default/*.xml"/>
  </context>
</include>
EOF
fi

# ======================================================
# USER
# ======================================================

USER_XML="$DIR_USERS/$SIP_USER.xml"

cat > "$USER_XML" <<EOF
<include>
  <user id="$SIP_USER">
    <params>
      <param name="password" value="$SIP_PASSWORD"/>
      <param name="dial-string"
             value="{sip_invite_domain=$SIP_DOMAIN}sofia/internal/\${destination_number}@\${domain_name}"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_name" value="$SIP_USER"/>
      <variable name="effective_caller_id_number" value="$SIP_USER"/>
    </variables>
  </user>
</include>
EOF

# ======================================================
# PROVIDER GATEWAY
# ======================================================

GW_XML="$GW_DIR/provider.xml"

cat > "$GW_XML" <<EOF
<include>
  <gateway name="provider">
    <param name="proxy" value="$PROVIDER_HOST"/>
    <param name="port" value="$PROVIDER_PORT"/>
    <param name="username" value="$PROVIDER_USERNAME"/>
    <param name="password" value="$PROVIDER_PASSWORD"/>
    <param name="register" value="true"/>
    <param name="transport" value="$PROVIDER_TRANSPORT"/>
    <param name="caller-id-in-from" value="true"/>
    <param name="retry-seconds" value="30"/>
    <param name="expire-seconds" value="600"/>
  </gateway>
</include>
EOF

# ======================================================
# DIALPLAN: SIP_USER → PROVIDER
# ======================================================

DP_XML="$DP_DEFAULT/forward_$SIP_USER.xml"

cat > "$DP_XML" <<EOF
<include>
  <extension name="forward_${SIP_USER}_to_provider">
    <condition field="destination_number" expression="^${SIP_USER}\$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="bridge"
              data="sofia/gateway/provider/\${sip_req_user}"/>
    </condition>
  </extension>
</include>
EOF

# ======================================================
# EXTERNAL IP
# ======================================================

cat > "$VARS_LOCAL" <<EOF
<include>
  <X-PRE-PROCESS cmd="set" data="external_sip_ip=$EXTERNAL_IP"/>
  <X-PRE-PROCESS cmd="set" data="external_rtp_ip=$EXTERNAL_IP"/>
</include>
EOF

# include vars_local.xml in vars.xml
if [ -f "$VARS_XML" ] && ! grep -q vars_local.xml "$VARS_XML"; then
  tmp="${VARS_XML}.tmp.$$"
  awk '
    { l[NR]=$0 }
    END {
      for (i=1;i<NR;i++) print l[i]
      print "  <X-PRE-PROCESS cmd=\"include\" data=\"vars_local.xml\"/>"
      print l[NR]
    }
  ' "$VARS_XML" > "$tmp" && mv "$tmp" "$VARS_XML"
fi

# ======================================================
# FINAL CHECK
# ======================================================

echo "[CHECK]"
for f in "$USER_XML" "$GW_XML" "$DP_XML" "$DEFAULT_CTX_XML"; do
  if [ -f "$f" ]; then
    echo "[OK] $f"
  else
    echo "[FAIL] $f" >&2
  fi
done

# ======================================================
# RELOAD
# ======================================================

if command -v fs_cli >/dev/null 2>&1; then
  fs_cli -x reloadxml >/dev/null 2>&1 || true
  fs_cli -x "sofia profile external restart" >/dev/null 2>&1 || true
fi

echo "[DONE]"
