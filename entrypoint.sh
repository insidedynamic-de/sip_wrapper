#!/bin/sh
set -e

# Копируем шаблоны как есть
cp /templates/internal.xml.tpl /etc/freeswitch/sip_profiles/internal.xml
cp /templates/external.xml.tpl /etc/freeswitch/sip_profiles/external.xml
cp /templates/provider.xml.tpl /etc/freeswitch/sip_profiles/provider.xml
cp /templates/default.xml.tpl /etc/freeswitch/dialplan/default.xml

# Запускаем FreeSWITCH
exec /usr/local/freeswitch/bin/freeswitch -nonat -nf
