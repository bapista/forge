#!/bin/sh
# FORGE — organic auto-cluster installer.
#
# Run the SAME one command on every machine on the same Wi-Fi / LAN.
# FORGE discovers peers over mDNS, ELECTS one control-plane automatically,
# and the rest auto-join. No IP to copy, no token to paste.
#
#   curl -sfL https://raw.githubusercontent.com/bapista/forge/main/install.sh | sudo sh
#
# Re-running is safe (idempotent). Clients (Mac/Windows/phone) just open the dashboard.
# Cross-network joins (different LANs) still use add-node.sh over Tailscale.
set -e

REPO="${FORGE_REPO:-https://github.com/bapista/forge}"
REF="${FORGE_REF:-main}"
DASH_PORT=30888
SVC="_forge._tcp"
ELECT="_forge-elect._tcp"
# Optional: a pre-shared cluster secret. If set on every node, the join token is
# NEVER broadcast (more secure on an untrusted LAN). If unset, the control-plane
# auto-generates a token and shares it via mDNS — fine for a trusted home network.
SECRET="${FORGE_CLUSTER_SECRET:-}"

say() { printf "\033[36m▶ %s\033[0m\n" "$1"; }
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo:  curl -sfL <url> | sudo sh"; exit 1; }

# --- discovery deps (mDNS) ---
if ! command -v avahi-browse >/dev/null 2>&1; then
  say "Setting up network discovery (avahi)..."
  (apt-get update -qq && apt-get install -y avahi-daemon avahi-utils) >/dev/null 2>&1 \
    || echo "  (couldn't auto-install avahi — install 'avahi-utils' if discovery fails)"
fi

MYIP=$(hostname -I 2>/dev/null | awk '{print $1}')

discover_server() {            # echoes "IP TOKEN" of a live FORGE control-plane, or nothing
  line=$(avahi-browse -rtp "$SVC" 2>/dev/null | grep '^=' | head -1)
  [ -z "$line" ] && return 1
  ip=$(echo "$line"  | awk -F';' '{print $8}')
  tok=$(echo "$line" | grep -oE 'token=[A-Za-z0-9]+' | head -1 | cut -d= -f2)
  [ -n "$ip" ] && echo "$ip ${tok}"
}

# --- 1. Is a control-plane already on the network? -------------------------------
say "Looking for an existing FORGE cluster on your network..."
FOUND="$(discover_server || true)"

# --- 2. If not, hold an election (lowest IP wins) --------------------------------
ROLE=""
if [ -z "$FOUND" ]; then
  say "No cluster found — holding an election..."
  avahi-publish -s "forge-cand-${MYIP}" "$ELECT" 7000 "ip=${MYIP}" >/tmp/forge-cand.log 2>&1 &
  CPID=$!
  sleep "$(awk 'BEGIN{srand();print int(rand()*4)+4}')"     # 4–7s jitter so peers can announce
  CANDS=$( { avahi-browse -rtp "$ELECT" 2>/dev/null | grep '^=' | grep -oE 'ip=[0-9.]+' | cut -d= -f2; echo "$MYIP"; } \
           | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n | uniq )
  LOWEST=$(echo "$CANDS" | head -1)
  FOUND="$(discover_server || true)"          # did a CP appear during the election?
  kill "$CPID" 2>/dev/null || true
  if [ -z "$FOUND" ] && [ "$MYIP" = "$LOWEST" ]; then
    ROLE=server
  elif [ -z "$FOUND" ]; then
    say "Deferring to ${LOWEST} as control-plane — waiting for it to come up..."
    i=0; while [ -z "$FOUND" ] && [ "$i" -lt 40 ]; do sleep 3; FOUND="$(discover_server || true)"; i=$((i+1)); done
    ROLE=agent
  else
    ROLE=agent
  fi
else
  ROLE=agent
fi

# --- 3a. Become the control-plane ------------------------------------------------
if [ "$ROLE" = server ]; then
  say "This machine is the CONTROL PLANE. ⚙️"
  TOKEN="${SECRET:-$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')}"
  if ! command -v k3s >/dev/null 2>&1; then
    curl -sfL https://get.k3s.io | sh -s - server --write-kubeconfig-mode 644 --token "$TOKEN"
  fi
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
  say "Waiting for the node to come online..."
  until k3s kubectl get nodes 2>/dev/null | grep -q " Ready"; do sleep 3; done
  say "Deploying FORGE services..."
  k3s kubectl apply -k "${REPO}//bundle?ref=${REF}" 2>/dev/null || true

  # Announce ourselves so peers (now and later) auto-join. Token in TXT only if no SECRET.
  TXT="role=server"; [ -z "$SECRET" ] && TXT="$TXT token=$TOKEN"
  cat >/etc/systemd/system/forge-announce.service <<EOF
[Unit]
Description=FORGE control-plane mDNS announce
After=network-online.target k3s.service
Wants=network-online.target
[Service]
ExecStart=/usr/bin/avahi-publish -s FORGE $SVC 6443 $TXT
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable --now forge-announce.service 2>/dev/null \
    || avahi-publish -s FORGE "$SVC" 6443 $TXT >/dev/null 2>&1 &
  printf "\n\033[32m✅ FORGE control-plane is up.\033[0m\n\n"
  echo "   Dashboard (open from any device): http://${MYIP}:${DASH_PORT}"
  echo "   Other machines: run the SAME installer — they auto-join. Nothing to copy."

# --- 3b. Auto-join as an agent ---------------------------------------------------
else
  SERVER=$(echo "$FOUND" | awk '{print $1}')
  TOKEN="${SECRET:-$(echo "$FOUND" | awk '{print $2}')}"
  [ -n "$SERVER" ] && [ -n "$TOKEN" ] || { echo "Could not auto-discover the control-plane. Is one up on this LAN? (Or use add-node.sh.)"; exit 1; }
  say "Joining the FORGE cluster at ${SERVER}..."
  if ! command -v k3s >/dev/null 2>&1; then
    curl -sfL https://get.k3s.io | K3S_URL="https://${SERVER}:6443" K3S_TOKEN="${TOKEN}" sh -
  fi
  printf "\n\033[32m✅ This machine joined the FORGE cluster.\033[0m\n"
  echo "   Dashboard: http://${SERVER}:${DASH_PORT}"
fi
