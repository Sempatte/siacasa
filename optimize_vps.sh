#!/bin/bash

echo "Optimizando VPS para SIACASA..."

# Configurar límites del sistema
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "root soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "root hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimizar parámetros de red
echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 1024" | sudo tee -a /etc/sysctl.conf
echo "net.core.netdev_max_backlog = 5000" | sudo tee -a /etc/sysctl.conf

# Aplicar cambios
sudo sysctl -p

# Optimizar memoria virtual
echo "vm.swappiness = 10" | sudo tee -a /etc/sysctl.conf
echo "vm.vfs_cache_pressure = 50" | sudo tee -a /etc/sysctl.conf

# Aplicar cambios
sudo sysctl -p

echo "Optimización completada."
