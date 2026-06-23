#!/bin/sh
# FORGE — your own sovereign AI platform, in one command.
# Turns this Linux/Raspberry-Pi machine into a FORGE node and deploys the platform.
# Re-running is safe (idempotent). Clients (Mac/Windows/phone) just open the dashboard.
set -e

REPO="${FORGE_REPO:-https://github.com/bapista/forge}"
REF="${FORGE_REF:-main}"
DASH_PORT=30888

say() { printf "\033[36m▶ %s\033[0m\n" "$1"; }

[ "$(id -u)" -eq 0 ] || { echo "Please run with sudo:  curl -sfL <url> | sudo sh"; exit 1; }

say "Installing FORGE on this machine..."

# 1) K3s — the lightweight engine (installed once, hidden from you afterwards)
if ! command -v k3s >/dev/null 2>&1; then
  say "Setting up the platform engine (K3s)..."
  curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
fi
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

say "Waiting for the node to come online..."
until k3s kubectl get nodes 2>/dev/null | grep -q " Ready"; do sleep 3; done

# 2) Deploy the FORGE app bundle straight from the repo (no extra tools)
say "Deploying FORGE services..."
k3s kubectl apply -k "${REPO}//bundle?ref=${REF}"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)

printf "\n\033[32m✅ FORGE is running.\033[0m\n\n"
echo   "   Open the dashboard from ANY device on your network:"
echo   "      http://${IP}:${DASH_PORT}"
echo   ""
echo   "   Add another Linux/Pi machine to grow your cluster — run this on it:"
echo   "      curl -sfL ${REPO}/raw/${REF}/add-node.sh | FORGE_SERVER=${IP} FORGE_TOKEN=${TOKEN} sudo sh"
echo   ""
