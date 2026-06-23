# FORGE bundle — the apps deployed on your cluster

`install.sh` deploys everything here via `kubectl apply -k bundle/`.

| Module | Status | What it is |
|---|---|---|
| **dashboard** | ✅ live | the app launcher on `:30888` — tiles + live cluster status |
| **NeuronAI** | 🔌 wired (tile) | offline multi-persona AI; links to the NeuronAI app. Full in-cluster packaging is the next step. |
| **Aegis AI** | ⏳ next | sovereign mail server + AI reply engine |
| **Cipher** | ⏳ next | Apple-Silicon AI workspace (client-side) |

## How modules plug in
Each app is a folder of manifests added to `kustomization.yaml`. The dashboard discovers them as tiles.
The cluster strip reuses the canonical **`/api/cluster/nodes`** fleet API — the same endpoint NeuronAI's
and Cipher's machine views already use, so the fleet is one source of truth across all three.

> Naming: **"Cluster" = machines** (this fleet). NeuronAI's model backends are **"Tiers" (A/B)** — a
> separate concept, deliberately not called "cluster".
