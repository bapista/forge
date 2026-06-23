# FORGE — organic auto-clustering

Run the **same** `install.sh` on every machine on the same Wi-Fi / LAN. No IP to copy, no token to paste — FORGE self-organizes.

## How it works
1. Each node browses **mDNS** (`_forge._tcp`) for an existing control-plane.
2. **Found** → it auto-joins as an agent (server IP + join token come from the mDNS record).
3. **None found** → an **election**: every node announces a candidacy (`_forge-elect._tcp`) carrying its IP; after a short random jitter the **lowest IP wins** and becomes the control-plane. The rest wait for it to come up, then join.
4. The control-plane runs a persistent announce (`forge-announce.service`) so machines that join *later* always find it.

That's the missing 10%: the K3s engine, the bundle, add-node and the Tailscale mesh already existed — this adds **automatic discovery + control-plane election** on top.

## Security
- **Default (trusted home LAN):** the control-plane auto-generates the K3s token and shares it in the mDNS TXT record. Anyone on that LAN could read it — acceptable at home.
- **Hardened:** set `FORGE_CLUSTER_SECRET=<passphrase>` on every node. The token is then your secret and is **never broadcast**.

## Scope & honest caveats
- mDNS works on **one L2 LAN/Wi-Fi** (not across subnets). Cross-network machines join via `add-node.sh` over **Tailscale/WireGuard**.
- The election is **jitter + lowest-IP**, not full consensus (Raft) — robust for a handful of home machines; powering on many nodes simultaneously on a noisy network is the edge case to validate.
- Heavy LLM inference stays **off** the cluster (Ollama/MLX on dedicated nodes), by design.

## Try it
```bash
# every machine, same command:
curl -sfL https://raw.githubusercontent.com/bapista/forge/main/install.sh | sudo sh
# hardened (set the same secret everywhere):
curl -sfL .../install.sh | FORGE_CLUSTER_SECRET="your-passphrase" sudo sh
```
