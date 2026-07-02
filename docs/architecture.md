# FORGE — architecture & design decisions

## Nodes

Reference fleet (names are illustrative — yours can be anything):

| Node | Role | Notes |
|---|---|---|
| **olympus** | K3s control plane | etcd/datastore, scheduler, core services + storage hub (i7 · 64 GB ECC · Coral TPU) |
| **hermes** | worker — mail | self-hosted mail server (Aegis AI) — Raspberry Pi 5 |
| **talos** | worker — edge AI | Hailo-10H NPU (40 TOPS) · realtime CV / GenAI — Raspberry Pi 5 |
| **tuxedo** | dev / training | Ryzen AI workstation (kept off the critical path) |
| **gateway** | public gateway | hardened SMTP relay / ingress — the only public surface |

All nodes join a **private mesh (Tailscale / WireGuard)** — so they can live on different networks and still
form one cluster; only **gateway** exposes a public surface. Real addresses are kept out of this repo
(see `inventory.example.ini`).

## Why K3s

Lightweight, certified Kubernetes that runs well on mixed ARM64 + x86 hardware and small nodes — the
right fit for a heterogeneous self-hosted fleet, without the overhead of full kubeadm.

## Why GitOps (Argo CD, app-of-apps)

The cluster's desired state lives in Git. Argo CD continuously reconciles it: a push to `main` is the
only deployment mechanism, changes are reviewable and revertible, and the cluster self-heals toward the
declared state. The **app-of-apps** pattern (`clusters/forge/apps/root-app.yaml`) lets one root
Application manage all the others.

## The inference boundary (key decision)

LLM inference is intentionally **not** containerised:

- Model-serving is heavy and stateful; pod scheduling and rolling updates fight model load times.
- NPU (edge) and Apple-Silicon **MLX** acceleration aren't covered by standard K8s device scheduling.

So inference runs on **dedicated nodes** (Ollama on CPU/compute; MLX on Apple Silicon) and is exposed to
the cluster as a network service. Kubernetes orchestrates the **stateless services / control plane** —
APIs, gateways, mail pipeline, schedulers, observability — where it genuinely adds value.

## Roadmap rationale

Each layer is shippable on its own and maps to a concrete platform skill: IaC → GitOps → ingress/TLS →
observability → secrets → CI/CD → real workload. Built in the open, incrementally.
