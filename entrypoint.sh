#!/bin/bash
set -euo pipefail

# Fail fast on missing required env vars
: "${SIP_USER:?SIP_USER is required}"
: "${SIP_PASSWORD:?SIP_PASSWORD is required}"
: "${SIP_DOMAIN:?SIP_DOMAIN is required}"
: "${PROVIDER_HOST:?PROVIDER_HOST is required}"
: "${PROVIDER_PORT:?PROVIDER_PORT is required}"
: "${PROVIDER_TRANSPORT:=udp}"

FS_CONF_DIR="/freeswitch"
TEMPLATE_DIR="/templates"

mkdir -p "$FS_CONF_DIR/sip_profiles" "$FS_CONF_DIR/dialplan"

# Render XML configs from templates
render_template() {
  local template=$1
  local output=$2
  envsubst < "$TEMPLATE_DIR/$template" > "$output"
}

render_template "internal.xml.tpl" "$FS_CONF_DIR/sip_profiles/internal.xml"
render_template "external.xml.tpl" "$FS_CONF_DIR/sip_profiles/external.xml"
render_template "provider.xml.tpl" "$FS_CONF_DIR/sip_profiles/provider.xml"
render_template "default.xml.tpl" "$FS_CONF_DIR/dialplan/default.xml"

# Symlink config dirs for FreeSWITCH
ln -sf "$FS_CONF_DIR/sip_profiles" /etc/freeswitch/sip_profiles
ln -sf "$FS_CONF_DIR/dialplan" /etc/freeswitch/dialplan

# Start FreeSWITCH in foreground, log to stdout
exec freeswitch -nonat -nf -c
