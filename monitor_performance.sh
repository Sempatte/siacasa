#!/bin/bash

echo "=== MONITOREO DE RENDIMIENTO SIACASA ==="
echo "Fecha: $(date)"
echo ""

echo "=== MEMORIA ==="
free -h
echo ""

echo "=== CPU ==="
top -bn1 | grep "Cpu(s)"
echo ""

echo "=== PROCESOS PYTHON ==="
ps aux | grep python | grep -v grep
echo ""

echo "=== PUERTOS ACTIVOS ==="
netstat -tlnp | grep -E ":(3200|4545|4040)"
echo ""

echo "=== LOGS RECIENTES (últimas 5 líneas) ==="
tail -5 /home/sebas/projects/siacasa/siacasa/logs/bot-error.log
echo ""

echo "=== PM2 STATUS ==="
pm2 status
