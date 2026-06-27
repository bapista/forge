#!/usr/bin/env bash
# Enroll this node into FORGE-managed firewall. Usage: install-node.sh <node-name>
set -euo pipefail
NODE="${1:?usage: install-node.sh <node-name>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
sudo mkdir -p /etc/forge-firewall
sudo cp "$HERE/policy.json" "$HERE/forge_firewall.py" /etc/forge-firewall/
echo "$NODE" | sudo tee /etc/forge-firewall/node >/dev/null
sudo cp "$HERE/forge-firewall.service" "$HERE/forge-firewall.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now forge-firewall.timer
echo "[forge-fw] enrolled $NODE; running first reconcile…"
sudo systemctl start forge-firewall.service
