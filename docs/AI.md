# FORGE AI — architecture

FORGE is AI-powered: it has memory, a fixed skill set, a per-node persona router, self-health, and
HA fallback. A non-technical operator just installs it and *talks* to it; FORGE does the rest.

## Per-node personas (no single voice)
Each machine answers with the AI that lives on it:

| Node | Persona | Bridge |
|---|---|---|
| **tuxedo** | NeuronAI | `:8001/api/chat` ✅ exists |
| **olympus** | Aegis AI | `:8000/api/chat` ⏳ pending |
| **mac** (client) | Cipher | `:8000/api/chat` ✅ exists |

`forge_ai.ask(question, node)` routes to the right bridge. Ask FORGE on olympus → Aegis answers; on the
Mac → Cipher answers; on the Tuxedo → NeuronAI answers.

## Memory (copied from Cipher)
`ForgeMemory` (in `ai/forge_ai.py`) mirrors Cipher's structure — SQLite `memories` (episodic, with
`module` + `importance`), `facts` (durable key/value), `sessions`, plus cognitive modules
(`self/cluster/nodes/health/security/ops/incidents/operator`). FORGE remembers what happens on the cluster.

## Fixed skills
`cluster-ops · health-check · node-join · diagnose · terminal · explain · self-care`. Fixed, not open-ended
— FORGE is an operator, not a general chatbot.

## The terminal tool (guarded — this is the safety line)
The AI **proposes**, the operator **approves**:
- **read-only** (`df`, `uptime`, `kubectl get …`) → safe to run on approval.
- **mutating** → requires approval.
- **destructive** (`rm`, `dd`, `kubectl delete`, …) → never auto-run; explicit approval only.
- every AI-run command is logged to memory (`incidents`/`ops`).
`classify_command()` enforces this. Prompt-injection and hallucinated commands are contained by approval.

## Self health & safety
`self_health()` checks FORGE's own brain (memory reachable, skills/personas loaded) and records a
heartbeat; machine health comes from `/api/cluster/nodes` (the dashboard Health & Security tab). FORGE
flags problems instead of failing silently.

## HA fallback — surviving a node loss
Goal: **if olympus (control-plane) dies, FORGE keeps running on another machine.**
- **Cluster layer:** today it's a *single* etcd control-plane (the Health tab flags this). HA = promote a
  second machine to control-plane (k3s embedded-etcd supports 3-node HA). When the AEGIS GPU node + more
  nodes join, run 3 servers → no single point of failure.
- **AI layer:** the FORGE AI runs on **every** node (a small agent), and the **active brain = whoever is
  the current control-plane**, discovered via the same mDNS/k3s the cluster uses. Lose olympus → a
  surviving node becomes control-plane → its resident AI becomes the active FORGE brain. Memory is
  replicated (etcd / a synced SQLite) so nothing is lost.

## Build phases
1. ✅ **Foundation** (this commit): memory (Cipher-modeled) + identity + fixed skills + per-node router +
   guarded terminal classifier + self-health — runnable against NeuronAI/Cipher today.
2. ⏳ **Chat tab in the FORGE app** → `ask()` per node, with the AI proposing approve-to-run commands.
3. ⏳ **Aegis bridge on olympus** (so olympus answers as Aegis).
4. ⏳ **Autonomous self-care** (scheduled health checks → alerts/auto-remediation within the guardrails).
5. ⏳ **HA**: 3-node control-plane + replicated memory + AI-brain failover.
