#!/bin/sh
set -eu

echo "[START] FreeSWITCH provisioning (sh)"

FS_CONF_DIR="${FS_CONF_DIR:-/etc/freeswitch}"

need() {
  k="$1"
  eval v=\${$k-}
  if [ "x$v" = "x" ]; then
    echo "Missing env: $k" >&2
    exit 1
  fi
}

# Required env vars
need SIP_USER
need SIP_PASSWORD
need SIP_DOMAIN
need PROVIDER_HOST
need PROVIDER_PORT
need PROVIDER_USERNAME
need PROVIDER_PASSWORD
need PROVIDER_TRANSPORT
need EXTERNAL_IP

DIR_DEFAULT="$FS_CONF_DIR/directory/default"
DP_DEFAULT="$FS_CONF_DIR/dialplan/default"
GW_DIR="$FS_CONF_DIR/sip_profiles/external"
VARS_XML="$FS_CONF_DIR/vars.xml"
VARS_LOCAL="$FS_CONF_DIR/vars_local.xml"

mkdir -p "$DIR_DEFAULT" "$DP_DEFAULT" "$GW_DIR"

# SAFE CLEANUP: remove only our generated files (not whole dialplan)
USER_XML="$DIR_DEFAULT/$SIP_USER.xml"
GW_XML="$GW_DIR/provider.xml"
DP_XML="$DP_DEFAULT/forward_$SIP_USER.xml"

rm -f "$USER_XML" "$GW_XML" "$DP_XML" "$VARS_LOCAL"

# 1) Create SIP user
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

# 2) Create Provider Gateway
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

# 3) Dialplan: calls to SIP_USER -> provider (NO <context> here)
cat > "$DP_XML" <<EOF
<include>
  <extension name="forward_${SIP_USER}_to_provider">
    <condition field="destination_number" expression="^${SIP_USER}\$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="bridge" data="sofia/gateway/provider/\${destination_number}"/>
    </condition>
  </extension>
</include>
EOF

# 4) external ip override
cat > "$VARS_LOCAL" <<EOF
<include>
  <X-PRE-PROCESS cmd="set" data="external_sip_ip=$EXTERNAL_IP"/>
  <X-PRE-PROCESS cmd="set" data="external_rtp_ip=$EXTERNAL_IP"/>
</include>
EOF

# 5) Ensure vars.xml includes vars_local.xml (POSIX sh + awk)
if [ -f "$VARS_XML" ]; then
  if grep -q "vars_local.xml" "$VARS_XML" 2>/dev/null; then
    echo "[INFO] vars_local.xml already included in vars.xml"
  else
    tmp="${VARS_XML}.tmp.$$"
    awk '
      { lines[NR]=$0 }
      END {
        if (NR < 1) exit 1
        for (i=1; i<NR; i++) print lines[i]
        print "  <!-- include local overrides -->"
        print "  <X-PRE-PROCESS cmd=\"include\" data=\"vars_local.xml\"/>"
        print lines[NR]
      }
    ' "$VARS_XML" > "$tmp" && mv "$tmp" "$VARS_XML"
    echo "[INFO] Added vars_local.xml include to vars.xml"
  fi
else
  echo "[WARN] vars.xml not found at $VARS_XML (skip include step)"
fi

# Final existence check
fail=0
for f in "$USER_XML" "$GW_XML" "$DP_XML" "$VARS_LOCAL"; do
  if [ -f "$f" ]; then
    echo "[OK] $f"
  else
    echo "[ERROR] missing: $f" >&2
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "[SUCCESS] All config files generated."
else
  echo "[FAIL] Some files missing."
fi

# Reload (optional)
if command -v fs_cli >/dev/null 2>&1; then
  fs_cli -x "reloadxml" >/dev/null 2>&1 || true
  fs_cli -x "sofia profile external restart" >/dev/null 2>&1 || true
fi

echo "[DONE]"
