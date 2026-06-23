#!/bin/sh
# FORGE — organic auto-cluster installer.
#
# Run the SAME one command on every machine on the same Wi-Fi / LAN.
# FORGE installs Tailscale (WireGuard), joins the mesh, discovers peers over mDNS,
# ELECTS one control-plane automatically, and the rest auto-join. Nothing to copy.
#
#   curl -sfL https://raw.githubusercontent.com/bapista/forge/main/install.sh | sudo sh
#   # headless / pre-authed mesh:  ... | FORGE_TS_AUTHKEY=tskey-... sudo sh
#
# Re-running is safe (idempotent). Clients (Mac/Windows/phone) just open the dashboard.
set -e

REPO="${FORGE_REPO:-https://github.com/bapista/forge}"
REF="${FORGE_REF:-main}"
DASH_PORT=30888
SVC="_forge._tcp"
ELECT="_forge-elect._tcp"
SECRET="${FORGE_CLUSTER_SECRET:-}"          # optional pre-shared cluster secret (keeps token off mDNS)

say() { printf "\033[36m▶ %s\033[0m\n" "$1"; }
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo:  curl -sfL <url> | sudo sh"; exit 1; }

# --- deps: mDNS discovery + the mesh ---------------------------------------------
if ! command -v avahi-browse >/dev/null 2>&1; then
  say "Setting up network discovery (avahi)..."
  (apt-get update -qq && apt-get install -y avahi-daemon avahi-utils) >/dev/null 2>&1 || true
fi

# Tailscale (WireGuard) — the cluster runs over the mesh, so it works across networks.
setup_mesh() {
  if ! command -v tailscale >/dev/null 2>&1; then
    say "Installing Tailscale (WireGuard mesh)..."
    curl -fsSL https://tailscale.com/install.sh | sh >/dev/null 2>&1 \
      || echo "  (couldn't auto-install Tailscale — install it, then re-run)"
  fi
  if ! tailscale ip -4 >/dev/null 2>&1; then
    if [ -n "${FORGE_TS_AUTHKEY:-}" ]; then
      say "Joining your mesh..."
      tailscale up --authkey="$FORGE_TS_AUTHKEY" --hostname="forge-$(hostname -s 2>/dev/null || hostname)" >/dev/null 2>&1 || true
    else
      say "Tailscale needs a one-time login (or pass FORGE_TS_AUTHKEY to skip the prompt)."
      tailscale up --hostname="forge-$(hostname -s 2>/dev/null || hostname)" || true
    fi
  fi
  TSIP=$(tailscale ip -4 2>/dev/null | head -1)
  [ -n "$TSIP" ] && say "Mesh IP: ${TSIP}" || echo "  (no mesh IP yet — falling back to the LAN IP)"
}
setup_mesh

MYIP=$(hostname -I 2>/dev/null | awk '{print $1}')
NODEIP="${TSIP:-$MYIP}"                      # prefer the mesh IP for the cluster

discover_server() {            # echoes "MESH_IP TOKEN" of a live FORGE control-plane, or nothing
  line=$(avahi-browse -rtp "$SVC" 2>/dev/null | grep '^=' | head -1)
  [ -z "$line" ] && return 1
  ip=$(echo "$line"  | grep -oE 'ip=[0-9.]+' | head -1 | cut -d= -f2)   # server's mesh IP (from TXT)
  [ -z "$ip" ] && ip=$(echo "$line" | awk -F';' '{print $8}')          # fallback: announced address
  tok=$(echo "$line" | grep -oE 'token=[A-Za-z0-9]+' | head -1 | cut -d= -f2)
  [ -n "$ip" ] && echo "$ip ${tok}"
}

# --- 1. Is a control-plane already on the network? -------------------------------
say "Looking for an existing FORGE cluster..."
FOUND="$(discover_server || true)"

# --- 2. If not, elect one (lowest mesh IP wins) ----------------------------------
ROLE=""
if [ -z "$FOUND" ]; then
  say "No cluster found — holding an election..."
  avahi-publish -s "forge-cand-${NODEIP}" "$ELECT" 7000 "ip=${NODEIP}" >/tmp/forge-cand.log 2>&1 &
  CPID=$!
  sleep "$(awk 'BEGIN{srand();print int(rand()*4)+4}')"
  CANDS=$( { avahi-browse -rtp "$ELECT" 2>/dev/null | grep '^=' | grep -oE 'ip=[0-9.]+' | cut -d= -f2; echo "$NODEIP"; } \
           | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n | uniq )
  LOWEST=$(echo "$CANDS" | head -1)
  FOUND="$(discover_server || true)"
  kill "$CPID" 2>/dev/null || true
  if   [ -z "$FOUND" ] && [ "$NODEIP" = "$LOWEST" ]; then ROLE=server
  elif [ -z "$FOUND" ]; then
    say "Deferring to ${LOWEST} as control-plane — waiting..."
    i=0; while [ -z "$FOUND" ] && [ "$i" -lt 40 ]; do sleep 3; FOUND="$(discover_server || true)"; i=$((i+1)); done
    ROLE=agent
  else ROLE=agent; fi
else
  ROLE=agent
fi

# --- dry-run ---------------------------------------------------------------------
if [ -n "${FORGE_DRY_RUN:-}" ]; then
  printf "\n\033[33m[dry-run]\033[0m no changes made.\n"
  echo "  mesh IP:    ${NODEIP}"
  [ -n "${CANDS:-}" ]  && echo "  candidates: $(echo "$CANDS" | tr '\n' ' ')"
  [ -n "${LOWEST:-}" ] && echo "  lowest IP:  ${LOWEST}"
  [ "$ROLE" = server ] && echo "  decision:   WOULD become the CONTROL PLANE" \
                       || echo "  decision:   WOULD JOIN${FOUND:+ at $(echo "$FOUND" | awk '{print $1}')}"
  exit 0
fi

# --- 3a. Control-plane -----------------------------------------------------------
if [ "$ROLE" = server ]; then
  say "This machine is the CONTROL PLANE. ⚙️"
  TOKEN="${SECRET:-$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')}"
  K3S_ARGS="server --write-kubeconfig-mode 644 --token $TOKEN"
  [ -n "$TSIP" ] && K3S_ARGS="$K3S_ARGS --node-ip $TSIP --flannel-iface tailscale0"
  command -v k3s >/dev/null 2>&1 || curl -sfL https://get.k3s.io | sh -s - $K3S_ARGS
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
  say "Waiting for the node to come online..."
  until k3s kubectl get nodes 2>/dev/null | grep -q " Ready"; do sleep 3; done
  say "Deploying FORGE services..."
  k3s kubectl apply -k "${REPO}//bundle?ref=${REF}" 2>/dev/null || true
  say "Giving FORGE its own brain (Ollama models, sized to this machine)..."
  curl -sfL "${REPO}/raw/${REF}/ai/forge-models.sh" | sh 2>/dev/null || echo "  (skip — run ai/forge-models.sh later)"

  # Announce over mDNS with our MESH IP so peers join over Tailscale (works across networks).
  TXT="role=server ip=$NODEIP"; [ -z "$SECRET" ] && TXT="$TXT token=$TOKEN"
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
  printf "\n\033[32m✅ FORGE control-plane is up (on the mesh).\033[0m\n\n"
  echo "   Dashboard: http://${NODEIP}:${DASH_PORT}"
  echo "   Other machines: run the SAME installer — they auto-join over the mesh."

# --- 3b. Auto-join as an agent ---------------------------------------------------
else
  SERVER=$(echo "$FOUND" | awk '{print $1}')
  TOKEN="${SECRET:-$(echo "$FOUND" | awk '{print $2}')}"
  [ -n "$SERVER" ] && [ -n "$TOKEN" ] || { echo "Couldn't auto-discover the control-plane. (Try add-node.sh.)"; exit 1; }
  AGENT_ARGS=""; [ -n "$TSIP" ] && AGENT_ARGS="--node-ip $TSIP --flannel-iface tailscale0"
  say "Joining the FORGE cluster at ${SERVER} (over the mesh)..."
  command -v k3s >/dev/null 2>&1 || curl -sfL https://get.k3s.io | K3S_URL="https://${SERVER}:6443" K3S_TOKEN="${TOKEN}" sh -s - $AGENT_ARGS
  printf "\n\033[32m✅ This machine joined the FORGE cluster.\033[0m\n"
  echo "   Dashboard: http://${SERVER}:${DASH_PORT}"
fi
