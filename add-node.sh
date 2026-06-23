#!/bin/sh
# Join this Linux/Raspberry-Pi machine to an existing FORGE cluster.
# Usage: curl -sfL <url>/add-node.sh | FORGE_SERVER=<ip> FORGE_TOKEN=<token> sudo sh
set -e
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -n "${FORGE_SERVER}" ] && [ -n "${FORGE_TOKEN}" ] || { echo "Set FORGE_SERVER and FORGE_TOKEN (shown by install.sh on your first machine)."; exit 1; }
printf "\033[36m▶ Joining FORGE at %s...\033[0m\n" "${FORGE_SERVER}"
curl -sfL https://get.k3s.io | K3S_URL="https://${FORGE_SERVER}:6443" K3S_TOKEN="${FORGE_TOKEN}" sh -
printf "\033[32m✅ This machine joined the FORGE cluster.\033[0m\n"
