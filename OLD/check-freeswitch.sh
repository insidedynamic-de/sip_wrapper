#!/bin/bash
################################################################################
# FreeSWITCH Status Check Script
# Запустите на Coolify сервере для проверки статуса FreeSWITCH
################################################################################

echo "=========================================="
echo "FreeSWITCH Status Check"
echo "=========================================="
echo ""

# Check if container is running
echo "1. Checking container status..."
if docker ps | grep -q freeswitch; then
  echo "   ✓ Container is running"
else
  echo "   ✗ Container is NOT running"
  echo ""
  echo "Container logs (last 20 lines):"
  docker logs freeswitch --tail 20
  exit 1
fi

echo ""

# Check FreeSWITCH process
echo "2. Checking FreeSWITCH process..."
if docker exec freeswitch pgrep -x freeswitch > /dev/null 2>&1; then
  echo "   ✓ FreeSWITCH process is running"
else
  echo "   ✗ FreeSWITCH process is NOT running"
  exit 1
fi

echo ""

# Wait for FreeSWITCH to fully start (if just started)
echo "3. Waiting for FreeSWITCH to initialize (10 seconds)..."
sleep 10

echo ""

# Check SIP profiles
echo "4. Checking SIP profiles..."
echo "----------------------------------------"
docker exec freeswitch fs_cli -x "sofia status" 2>/dev/null || {
  echo "   ✗ Cannot connect to FreeSWITCH CLI yet"
  echo "   FreeSWITCH is still starting up. Wait 30 seconds and try again."
  exit 0
}

echo ""

# Check gateways
echo "5. Checking SIP gateways (providers)..."
echo "----------------------------------------"
docker exec freeswitch fs_cli -x "sofia status gateway" 2>/dev/null

echo ""

# Check registrations
echo "6. Checking registrations..."
echo "----------------------------------------"
docker exec freeswitch fs_cli -x "show registrations" 2>/dev/null

echo ""

# Check calls
echo "7. Checking active calls..."
echo "----------------------------------------"
docker exec freeswitch fs_cli -x "show calls" 2>/dev/null

echo ""

# Show summary
echo "=========================================="
echo "Summary:"
echo "=========================================="

# Count gateways
GATEWAYS_UP=$(docker exec freeswitch fs_cli -x "sofia status gateway" 2>/dev/null | grep -c "State.*REGED" || echo "0")
GATEWAYS_TOTAL=$(docker exec freeswitch fs_cli -x "sofia status gateway" 2>/dev/null | grep -c "Name" || echo "0")

if [ "$GATEWAYS_TOTAL" -gt 0 ]; then
  echo "✓ Gateways: $GATEWAYS_UP/$GATEWAYS_TOTAL registered"
else
  echo "⚠ No gateways configured"
fi

# Count registered users
USERS_REGISTERED=$(docker exec freeswitch fs_cli -x "show registrations" 2>/dev/null | grep -c "^sofia" || echo "0")
echo "✓ Registered users: $USERS_REGISTERED"

# Count active calls
ACTIVE_CALLS=$(docker exec freeswitch fs_cli -x "show calls count" 2>/dev/null | grep -oP '\d+ total' | grep -oP '^\d+' || echo "0")
echo "✓ Active calls: $ACTIVE_CALLS"

echo ""
echo "=========================================="
echo "FreeSWITCH is operational!"
echo "=========================================="
