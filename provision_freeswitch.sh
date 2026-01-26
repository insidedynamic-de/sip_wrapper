#!/bin/sh

set -e

echo_ts() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

need() {
  VAR="$1"
  eval VAL=\$$VAR
  if [ -z "$VAL" ]; then
    echo "ENV $VAR is required" >&2
    exit 1
  fi
}

### ===== REQUIRED ENV =====
need SIP_DOMAIN
need SIP_USER
need SIP_PASSWORD

need PROVIDER_NAME
need PROVIDER_HOST
need PROVIDER_PORT
need PROVIDER_USERNAME
need PROVIDER_PASSWORD
need PROVIDER_TRANSPORT
need CALLER_ID

need VAPI_NAME
need VAPI_HOST
need VAPI_PORT
need VAPI_USERNAME
need VAPI_PASSWORD
need VAPI_TRANSPORT

need EXTERNAL_IP

FS_CONF=${FS_CONF:-/etc/freeswitch}
BACKUP_DIR=${BACKUP_DIR:-/etc/freeswitch-backups}
TS=$(date -u '+%Y%m%d-%H%M%S')

GW_DIR="$FS_CONF/sip_profiles/external/gateways"
DP_DEF="$FS_CONF/dialplan/default"
DP_PUB="$FS_CONF/dialplan/public"
DIR_DIR="$FS_CONF/directory"

### ===== BACKUP =====
echo_ts "Backup FreeSWITCH config"
mkdir -p "$BACKUP_DIR"
tar -C "$(dirname "$FS_CONF")" -czf "$BACKUP_DIR/freeswitch-$TS.tar.gz" "$(basename "$FS_CONF")"

### ===== CLEAN (only managed files) =====
echo_ts "Clean managed files"

rm -f \
  "$DIR_DIR/$SIP_DOMAIN.xml" \
  "$DIR_DIR/default.xml" \
  "$DP_DEF/00_outbound_to_provider.xml" \
  "$DP_PUB/00_inbound_to_vapi.xml" \
  "$GW_DIR/$PROVIDER_NAME.xml" \
  "$GW_DIR/$VAPI_NAME.xml"

mkdir -p "$GW_DIR" "$DP_DEF" "$DP_PUB" "$DIR_DIR"

### ===== DIRECTORY (domain + user) =====
echo_ts "Create directory domain + user"

cat > "$DIR_DIR/$SIP_DOMAIN.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="directory">
    <domain name="$SIP_DOMAIN">
      <groups>
        <group name="default">
          <users>
            <user id="$SIP_USER">
              <params>
                <param name="password" value="$SIP_PASSWORD"/>
              </params>
              <variables>
                <variable name="user_context" value="default"/>
                <variable name="effective_caller_id_number" value="$CALLER_ID"/>
                <variable name="effective_caller_id_name" value="$CALLER_ID"/>
              </variables>
            </user>
          </users>
        </group>
      </groups>
    </domain>
  </section>
</document>
EOF

cat > "$DIR_DIR/default.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="directory">
    <X-PRE-PROCESS cmd="include" data="$SIP_DOMAIN.xml"/>
  </section>
</document>
EOF

### ===== GATEWAY PROVIDER =====
echo_ts "Create provider gateway"

cat > "$GW_DIR/$PROVIDER_NAME.xml" <<EOF
<gateway name="$PROVIDER_NAME">
  <param name="username" value="$PROVIDER_USERNAME"/>
  <param name="password" value="$PROVIDER_PASSWORD"/>
  <param name="realm" value="$PROVIDER_HOST"/>
  <param name="proxy" value="$PROVIDER_HOST:$PROVIDER_PORT"/>
  <param name="from-user" value="$PROVIDER_USERNAME"/>
  <param name="from-domain" value="$PROVIDER_HOST"/>
  <param name="register" value="true"/>
  <param name="register-transport" value="$PROVIDER_TRANSPORT"/>
</gateway>
EOF

### ===== GATEWAY VAPI =====
echo_ts "Create VAPI gateway"

VAPI_REGISTER=${VAPI_REGISTER:-false}

cat > "$GW_DIR/$VAPI_NAME.xml" <<EOF
<gateway name="$VAPI_NAME">
  <param name="username" value="$VAPI_USERNAME"/>
  <param name="password" value="$VAPI_PASSWORD"/>
  <param name="realm" value="$VAPI_HOST"/>
  <param name="proxy" value="$VAPI_HOST:$VAPI_PORT"/>
  <param name="from-user" value="$VAPI_USERNAME"/>
  <param name="from-domain" value="$VAPI_HOST"/>
  <param name="register" value="$VAPI_REGISTER"/>
  <param name="register-transport" value="$VAPI_TRANSPORT"/>
</gateway>
EOF

### ===== OUTBOUND DIALPLAN =====
echo_ts "Create outbound dialplan (user -> provider)"

cat > "$DP_DEF/00_outbound_to_provider.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="dialplan">
    <context name="default">

      <extension name="outbound_to_provider">
        <condition field="destination_number" expression="^(.*)$">
          <action application="set" data="orig=\${destination_number}"/>
          <action application="set" data="num=\${regex(\${orig}|^00(.*)$|+%1)}"/>
          <action application="set" data="num=\${regex(\${num}|^0(.*)$|+49%1)}"/>

          <action application="set" data="effective_caller_id_number=$CALLER_ID"/>
          <action application="set" data="effective_caller_id_name=$CALLER_ID"/>

          <action application="export" data="sip_h_P-Preferred-Identity=&lt;sip:$CALLER_ID@$SIP_DOMAIN&gt;"/>
          <action application="export" data="sip_h_P-Asserted-Identity=&lt;sip:$CALLER_ID@$SIP_DOMAIN&gt;"/>

          <action application="bridge" data="sofia/gateway/$PROVIDER_NAME/\${num}"/>
        </condition>
      </extension>

    </context>
  </section>
</document>
EOF

### ===== INBOUND DIALPLAN =====
echo_ts "Create inbound dialplan (provider -> vapi)"

cat > "$DP_PUB/00_inbound_to_vapi.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="dialplan">
    <context name="public">

      <extension name="inbound_to_vapi">
        <condition field="destination_number" expression="^(.*)$">
          <action application="bridge" data="sofia/gateway/$VAPI_NAME/\${destination_number}"/>
        </condition>
      </extension>

    </context>
  </section>
</document>
EOF

### ===== RELOAD =====
echo_ts "Reload FreeSWITCH"
if command -v fs_cli >/dev/null 2>&1; then
  fs_cli -x reloadxml
  fs_cli -x "sofia profile external rescan"
fi

echo_ts "DONE"
