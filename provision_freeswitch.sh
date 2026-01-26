#!/bin/sh
set -eu

echo "[START] FreeSWITCH wrapper provisioning (POSIX sh)"

FS_CONF_DIR="${FS_CONF_DIR:-/etc/freeswitch}"

need() {
  k="$1"
  eval v=\${$k-}
  if [ "x$v" = "x" ]; then
    echo "Missing env: $k" >&2
    exit 1
  fi
}

# ===== REQUIRED ENV =====
need SIP_USER
need SIP_PASSWORD
need SIP_DOMAIN

need PROVIDER_HOST
need PROVIDER_PORT
need PROVIDER_USERNAME
need PROVIDER_PASSWORD
need PROVIDER_TRANSPORT

need VAPI_HOST
need VAPI_PORT
need VAPI_USERNAME
need VAPI_PASSWORD
need VAPI_TRANSPORT
# optional but we treat as required with default:
VAPI_REGISTER="${VAPI_REGISTER:-false}"

need EXTERNAL_IP

# ===== PATHS =====
DIR_USERS="$FS_CONF_DIR/directory/default"

DP_ROOT="$FS_CONF_DIR/dialplan"
DP_DEFAULT="$DP_ROOT/default"
DP_PUBLIC="$DP_ROOT/public"
DEFAULT_CTX_XML="$DP_ROOT/default.xml"
PUBLIC_CTX_XML="$DP_ROOT/public.xml"

GW_DIR="$FS_CONF_DIR/sip_profiles/external"

DIALPLAN_CONF="$FS_CONF_DIR/dialplan.conf.xml"
VARS_XML="$FS_CONF_DIR/vars.xml"
VARS_LOCAL="$FS_CONF_DIR/vars_local.xml"

mkdir -p "$DIR_USERS" "$DP_DEFAULT" "$DP_PUBLIC" "$GW_DIR"

# ======================================================
# CLEANUP (users + dialplan rules + gateways), keep context skeleton files
# ======================================================
echo "[CLEANUP] Removing users, dialplan rules, gateways (keeping default/public context skeleton)"
rm -f "$DIR_USERS"/*.xml 2>/dev/null || true
rm -f "$DP_DEFAULT"/*.xml 2>/dev/null || true
rm -f "$DP_PUBLIC"/*.xml 2>/dev/null || true
rm -f "$GW_DIR"/*.xml 2>/dev/null || true
rm -f "$VARS_LOCAL" 2>/dev/null || true
echo "[CLEANUP] Done"

# ======================================================
# ENSURE DIALPLAN LOADER + CONTEXTS
# ======================================================
# dialplan.conf.xml must include dialplan/*.xml so default.xml/public.xml are loaded
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
else
  # if it includes default/*.xml directly, switch to dialplan/*.xml
  if grep -q 'data="default/\*\.xml"' "$DIALPLAN_CONF" 2>/dev/null; then
    tmp="${DIALPLAN_CONF}.tmp.$$"
    sed 's/data="default\/\*\.xml"/data="dialplan\/\*\.xml"/g' "$DIALPLAN_CONF" > "$tmp" && mv "$tmp" "$DIALPLAN_CONF"
  fi
fi

# default context skeleton
if [ ! -f "$DEFAULT_CTX_XML" ]; then
  cat > "$DEFAULT_CTX_XML" <<EOF
<include>
  <context name="default">
    <X-PRE-PROCESS cmd="include" data="default/*.xml"/>
  </context>
</include>
EOF
fi

# public context skeleton (incoming from external profile usually lands here)
if [ ! -f "$PUBLIC_CTX_XML" ]; then
  cat > "$PUBLIC_CTX_XML" <<EOF
<include>
  <context name="public">
    <X-PRE-PROCESS cmd="include" data="public/*.xml"/>
  </context>
</include>
EOF
fi

# ======================================================
# USER (internal registration)
# ======================================================
USER_XML="$DIR_USERS/$SIP_USER.xml"
cat > "$USER_XML" <<EOF
<include>
  <user id="$SIP_USER">
    <params>
      <param name="password" value="$SIP_PASSWORD"/>
      <param name="dial-string" value="{sip_invite_domain=$SIP_DOMAIN}sofia/internal/\${destination_number}@\${domain_name}"/>
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
# GATEWAYS (provider + vapi) under external profile
# ======================================================
GW_PROVIDER="$GW_DIR/gw_provider.xml"
cat > "$GW_PROVIDER" <<EOF
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

GW_VAPI="$GW_DIR/gw_vapi.xml"
cat > "$GW_VAPI" <<EOF
<include>
  <gateway name="vapi">
    <param name="proxy" value="$VAPI_HOST"/>
    <param name="port" value="$VAPI_PORT"/>
    <param name="username" value="$VAPI_USERNAME"/>
    <param name="password" value="$VAPI_PASSWORD"/>
    <param name="register" value="$VAPI_REGISTER"/>
    <param name="transport" value="$VAPI_TRANSPORT"/>
    <param name="caller-id-in-from" value="true"/>
    <param name="retry-seconds" value="30"/>
    <param name="expire-seconds" value="600"/>
  </gateway>
</include>
EOF

# ======================================================
# DIALPLAN RULES
# ======================================================

# OUTBOUND: calls FROM SIP_USER -> provider (send dialed number)
DP_OUT="$DP_DEFAULT/out_${SIP_USER}_to_provider.xml"
cat > "$DP_OUT" <<EOF
<include>
  <extension name="out_${SIP_USER}_to_provider">
    <condition field="caller_id_number" expression="^${SIP_USER}\$">
      <condition field="destination_number" expression="^(.+)\$">
        <action application="set" data="hangup_after_bridge=true"/>
        <action application="set" data="continue_on_fail=true"/>
        <action application="bridge" data="sofia/gateway/provider/\${destination_number}"/>
      </condition>
    </condition>
  </extension>
</include>
EOF

# INBOUND: anything coming into public -> vapi
# Use sip_req_user to preserve original called user/number from Request-URI.
DP_IN="$DP_PUBLIC/in_provider_to_vapi.xml"
cat > "$DP_IN" <<EOF
<include>
  <extension name="in_provider_to_vapi">
    <condition field="destination_number" expression="^(.+)\$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="bridge" data="sofia/gateway/vapi/\${sip_req_user}"/>
    </condition>
  </extension>
</include>
EOF

# ======================================================
# EXTERNAL IP (NAT)
# ======================================================
cat > "$VARS_LOCAL" <<EOF
<include>
  <X-PRE-PROCESS cmd="set" data="external_sip_ip=$EXTERNAL_IP"/>
  <X-PRE-PROCESS cmd="set" data="external_rtp_ip=$EXTERNAL_IP"/>
</include>
EOF

# include vars_local.xml in vars.xml
if [ -f "$VARS_XML" ] && ! grep -q "vars_local.xml" "$VARS_XML" 2>/dev/null; then
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
# RELOAD
# ======================================================
if command -v fs_cli >/dev/null 2>&1; then
  fs_cli -x "reloadxml" >/dev/null 2>&1 || true
  fs_cli -x "sofia profile external restart" >/dev/null 2>&1 || true
fi

echo "[FILES]"
for f in "$DIALPLAN_CONF" "$DEFAULT_CTX_XML" "$PUBLIC_CTX_XML" "$USER_XML" "$GW_PROVIDER" "$GW_VAPI" "$DP_OUT" "$DP_IN" "$VARS_LOCAL"; do
  if [ -f "$f" ]; then echo "[OK] $f"; else echo "[FAIL] $f" >&2; fi
done

echo "[DONE]"
