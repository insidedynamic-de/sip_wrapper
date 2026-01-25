#!/bin/sh
set -e

# Создать директории, если их нет
mkdir -p /etc/freeswitch/sip_profiles
mkdir -p /etc/freeswitch/dialplan

# Копируем шаблоны как есть
cp /templates/internal.xml.tpl /etc/freeswitch/sip_profiles/internal.xml
cp /templates/external.xml.tpl /etc/freeswitch/sip_profiles/external.xml
cp /templates/provider.xml.tpl /etc/freeswitch/sip_profiles/provider.xml
cp /templates/default.xml.tpl /etc/freeswitch/dialplan/default.xml

# Запускаем FreeSWITCH
exec /usr/local/freeswitch/bin/freeswitch -nonat -nf
