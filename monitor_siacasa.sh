#!/bin/bash

while true; do
  clear
  echo "════════════════════════════════════════"
  echo "   MONITOR SIACASA - $(date '+%H:%M:%S')"
  echo "════════════════════════════════════════"
  
  # Memoria general
  echo "💾 MEMORIA GENERAL:"
  free -h | grep -E "(total|Mem|Swap)"
  echo ""
  
  # Procesos Python específicos
  echo "🐍 PROCESOS PYTHON (SIACASA):"
  ps aux | grep python | grep -v grep | awk '{printf "%-20s %s %s %s\n", $11, $3"%", $4"%", $6"KB"}'
  echo ""
  
  # PM2 Status
  echo "⚙️  PM2 STATUS:"
  pm2 jlist | jq -r '.[] | "\(.name): \(.pm2_env.status) - CPU: \(.monit.cpu)% - Mem: \(.monit.memory/1024/1024 | floor)MB"' 2>/dev/null || echo "PM2 no disponible"
  echo ""
  
  # Puertos activos
  echo "🌐 PUERTOS ACTIVOS:"
  netstat -tlnp 2>/dev/null | grep -E ":(3200|4545|4040|80)" | awk '{print $4 " -> " $7}'
  
  sleep 3
done
