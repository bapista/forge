# FORGE — architecture & design decisions

## Nodes

| Node | Role | Notes |
|---|---|---|
| **THE_CORE** | K3s control plane | etcd/datastore, scheduler, Argo CD, core services |
| **PAWN** | edge / on-device AI | low-power ARM with an NPU for on-device drafting |
| **ENVOY** | mail | self-hosted mail server (Aegis AI) |
| **CAVALRY** | compute | heavier x86 compute / model nodes |
| **TEMPLAR** | public gateway | hardened ingress + relay; the only public surface |

All nodes join a **private mesh (Tailscale)**; only TEMPLAR exposes a public surface. Real addresses are
kept out of this repo (see `inventory.example.ini`).

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
