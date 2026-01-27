#!/bin/bash
################################################################################
# Диагностика проблемы с диалпланом FreeSWITCH
################################################################################

echo "=========================================="
echo "FreeSWITCH Dialplan Diagnostics"
echo "=========================================="
echo ""

# Check if container is running
echo "1. Container status:"
docker ps | grep freeswitch || { echo "Container not running!"; exit 1; }
echo ""

# Check dialplan files
echo "2. Checking dialplan files:"
echo "   Directory structure:"
docker exec freeswitch ls -la /etc/freeswitch/dialplan/ 2>/dev/null || echo "   ERROR: Cannot access dialplan directory"
echo ""

echo "   Default context files:"
docker exec freeswitch ls -la /etc/freeswitch/dialplan/default/ 2>/dev/null || echo "   ERROR: Cannot access default directory"
echo ""

echo "   Public context files:"
docker exec freeswitch ls -la /etc/freeswitch/dialplan/public/ 2>/dev/null || echo "   ERROR: Cannot access public directory"
echo ""

# Check main dialplan.xml
echo "3. Checking main dialplan.xml:"
docker exec freeswitch test -f /etc/freeswitch/dialplan.xml && {
  echo "   ✓ dialplan.xml exists"
  echo "   Content preview:"
  docker exec freeswitch head -20 /etc/freeswitch/dialplan.xml
} || {
  echo "   ✗ dialplan.xml NOT found!"
}
echo ""

# Check if dialplan includes the directories
echo "4. Checking if dialplan includes default/public contexts:"
docker exec freeswitch grep -A 5 "context.*default" /etc/freeswitch/dialplan.xml 2>/dev/null || {
  echo "   WARNING: No 'default' context include found in dialplan.xml"
}
echo ""

# Check provision-generated files
echo "5. Checking provision-generated dialplan files:"
echo "   User-to-user dialplan:"
docker exec freeswitch test -f /etc/freeswitch/dialplan/default/00_user_to_user.xml && {
  echo "   ✓ 00_user_to_user.xml exists"
} || {
  echo "   ✗ 00_user_to_user.xml NOT found"
}

echo "   Outbound dialplan:"
docker exec freeswitch test -f /etc/freeswitch/dialplan/default/00_outbound.xml && {
  echo "   ✓ 00_outbound.xml exists"
  docker exec freeswitch head -10 /etc/freeswitch/dialplan/default/00_outbound.xml
} || {
  echo "   ✗ 00_outbound.xml NOT found"
}

echo "   Inbound dialplan:"
docker exec freeswitch test -f /etc/freeswitch/dialplan/public/00_inbound.xml && {
  echo "   ✓ 00_inbound.xml exists"
} || {
  echo "   ✗ 00_inbound.xml NOT found"
}
echo ""

# Try to reload dialplan
echo "6. Reloading dialplan in FreeSWITCH:"
docker exec freeswitch fs_cli -x "reloadxml" 2>/dev/null && echo "   ✓ XML reloaded" || echo "   ✗ Failed to reload XML"
echo ""

# Show current dialplan status
echo "7. FreeSWITCH dialplan status:"
docker exec freeswitch fs_cli -x "xml_locate dialplan" 2>/dev/null | head -50

echo ""
echo "=========================================="
echo "Diagnostics complete"
echo "=========================================="
