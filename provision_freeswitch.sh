#!/usr/bin/env bash
set -euo pipefail

### ===== REQUIRE ENV =====
need() { [ -n "${!1:-}" ] || { echo "Missing env: $1"; exit 1; }; }

need SIP_USER
need SIP_PASSWORD
need SIP_DOMAIN

need PROVIDER_NAME
need PROVIDER_HOST
need PROVIDER_USERNAME
need PROVIDER_PASSWORD
need PROVIDER_REALM
need PROVIDER_TRANSPORT

need INBOUND_DID_CORE
need COUNTRY_CODE

USE_PPI="${USE_PPI:-0}"
DEFAULT_CID="${DEFAULT_CID:-$SIP_USER}"
PPI_DOMAIN="${PPI_DOMAIN:-$PROVIDER_REALM}"

### ===== PATHS =====
FS="/etc/freeswitch"
DIR_USER="$FS/directory/default/${SIP_USER}.xml"
GW_FILE="$FS/sip_profiles/external/${PROVIDER_NAME}.xml"
DP_OUT="$FS/dialplan/default/out_${SIP_USER}_to_${PROVIDER_NAME}.xml"
DP_IN="$FS/dialplan/public/in_${PROVIDER_NAME}_to_${SIP_USER}.xml"

### ===== BACKUP =====
TS="$(date +%Y%m%d-%H%M%S)"
BK="/var/backups/freeswitch-$TS"
mkdir -p "$BK"
cp -a "$FS" "$BK/"
echo "[OK] Backup -> $BK"

### ===== CLEAN OUR FILES =====
rm -f "$DIR_USER" "$GW_FILE" "$DP_OUT" "$DP_IN"

mkdir -p \
  "$FS/directory/default" \
  "$FS/sip_profiles/external" \
  "$FS/dialplan/default" \
  "$FS/dialplan/public"

### ===== USER =====
cat >"$DIR_USER" <<EOF
<include>
  <user id="${SIP_USER}">
    <params>
      <param name="password" value="${SIP_PASSWORD}"/>
    </params>
    <variables>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_number" value="${DEFAULT_CID}"/>
      <variable name="effective_caller_id_name" value="${SIP_USER}"/>
    </variables>
  </user>
</include>
EOF

### ===== GATEWAY =====
cat >"$GW_FILE" <<EOF
<include>
  <gateway name="${PROVIDER_NAME}">
    <param name="username" value="${PROVIDER_USERNAME}"/>
    <param name="password" value="${PROVIDER_PASSWORD}"/>
    <param name="realm" value="${PROVIDER_REALM}"/>
    <param name="proxy" value="${PROVIDER_HOST}"/>
    <param name="transport" value="${PROVIDER_TRANSPORT}"/>
    <param name="register" value="true"/>
    <param name="expire-seconds" value="600"/>
  </gateway>
</include>
EOF

### ===== OUTBOUND =====
PPI_BLOCK=""
if [ "$USE_PPI" = "1" ]; then
PPI_BLOCK=$(cat <<EOP
        <action application="export" data="sip_h_P-Preferred-Identity=<sip:${DEFAULT_CID}@${PPI_DOMAIN}>"/>
        <action application="export" data="sip_h_P-Asserted-Identity=<sip:${DEFAULT_CID}@${PPI_DOMAIN}>"/>
EOP
)
fi

cat >"$DP_OUT" <<EOF
<include>
  <context name="default">
    <extension name="out_${SIP_USER}_to_${PROVIDER_NAME}">
      <condition field="destination_number" expression="^(\\+${COUNTRY_CODE}\\d+|00${COUNTRY_CODE}\\d+|0\\d+)$">
        <action application="set" data="dst=\${destination_number}"/>
        <action application="set" data="dst=\${regex(\${dst}|^00${COUNTRY_CODE}(\\d+)\$|+${COUNTRY_CODE}%1)}"/>
        <action application="set" data="dst=\${regex(\${dst}|^0(\\d+)\$|+${COUNTRY_CODE}%1)}"/>
        <action application="set" data="effective_caller_id_number=${DEFAULT_CID}"/>
${PPI_BLOCK}
        <action application="bridge" data="sofia/gateway/${PROVIDER_NAME}/\${dst}"/>
      </condition>
    </extension>
  </context>
</include>
EOF

### ===== INBOUND =====
cat >"$DP_IN" <<EOF
<include>
  <context name="public">
    <extension name="in_${PROVIDER_NAME}_to_${SIP_USER}">
      <condition field="destination_number" expression="^(?:\\+${COUNTRY_CODE}|00${COUNTRY_CODE}|0)?(${INBOUND_DID_CORE})\$">
        <action application="bridge" data="user/${SIP_USER}"/>
      </condition>
    </extension>
  </context>
</include>
EOF

### ===== RELOAD =====
if command -v fs_cli >/dev/null; then
  fs_cli -x "reloadxml"
  fs_cli -x "sofia profile external rescan"
  fs_cli -x "sofia status gateway ${PROVIDER_NAME}"
fi

echo "[DONE] FreeSWITCH rebuilt from ENV"
