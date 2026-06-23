# FORGE — a sovereign, self-hosted K3s platform

A five-node, GitOps-managed Kubernetes platform running entirely on my own hardware — Raspberry Pis,
small x86 compute, and a hardened public gateway, linked over a private mesh. Built to run sovereign,
offline-first AI services with **no hyperscaler dependency**, and engineered the way a production
platform should be: declarative, observable, and reproducible from code.

> Status: building in the open. Layers ship incrementally — see the roadmap below.

## What this repository demonstrates

| Discipline | How it's shown here |
|---|---|
| **Infrastructure as Code** | The whole cluster is provisioned from `infra/ansible/` — no click-ops. |
| **GitOps** | Argo CD reconciles cluster state from `apps/` via an app-of-apps. Push to `main` → cluster converges. |
| **Kubernetes** | Multi-arch (ARM64 + x86) K3s, namespaces, workloads, resource limits. |
| **Networking & TLS** | Ingress + cert-manager + Let's Encrypt (Layer 3). |
| **Observability** | Prometheus + Grafana + Loki dashboards and alerts (Layer 4). |
| **Secrets hygiene** | No plaintext secrets in Git — sealed/external-secrets (Layer 5); strict `.gitignore`. |
| **CI/CD** | GitHub Actions build multi-arch images → registry → Argo CD auto-deploys (Layer 6). |

## Architecture

```
                       Internet
                          │
                  ┌───────▼────────┐
                  │    TEMPLAR      │  hardened public gateway (ARM)
                  └───────┬────────┘
                          │  private mesh (Tailscale)
        ┌─────────────────┼───────────────────────────┐
        │                 │                            │
 ┌──────▼──────┐   ┌──────▼──────┐             ┌───────▼──────┐
 │  THE_CORE   │   │    PAWN     │             │   CAVALRY    │
 │ control     │   │ edge NPU /  │             │ compute /    │
 │ plane       │   │ on-device AI│             │ model nodes  │
 └─────────────┘   └─────────────┘             └──────────────┘
        │
 ┌──────▼──────┐
 │   ENVOY     │  self-hosted mail (Aegis AI)
 └─────────────┘

K3s control plane = THE_CORE · agents = PAWN, ENVOY, CAVALRY, TEMPLAR
```

**Design rule — inference stays off Kubernetes.** LLM inference (Ollama on CPU/compute nodes,
Apple-Silicon MLX) does **not** run as pods — model-serving doesn't fit pod scheduling and NPU/Apple
hardware isn't standard K8s. K3s runs the **services / control plane**; inference lives on dedicated
nodes and is *exposed* to the cluster. This is a deliberate platform decision, not a limitation.

## Repository layout

```
infra/ansible/          Layer 1 — IaC: provision K3s across all nodes
clusters/forge/         Layer 2 — GitOps: Argo CD bootstrap + app-of-apps
apps/                   Workloads reconciled by Argo CD (start: podinfo demo)
docs/architecture.md    Topology + design decisions
Makefile                provision / bootstrap / diff / lint
```

## Quick start

```bash
# Layer 1 — provision the cluster (fill in your own inventory.ini first)
cp infra/ansible/inventory.example.ini infra/ansible/inventory.ini
make provision

# Layer 2 — install Argo CD and hand control to GitOps
make bootstrap

# From here, everything is GitOps: edit a manifest, push to main,
# and Argo CD converges the cluster. `make diff` previews changes.
```

## Roadmap

- [x] Layer 1 — **IaC** (Ansible provisioning of K3s)
- [x] Layer 2 — **GitOps** (Argo CD app-of-apps + first workload)
- [ ] Layer 3 — Ingress + TLS (cert-manager + Let's Encrypt)
- [ ] Layer 4 — Observability (Prometheus + Grafana + Loki)
- [ ] Layer 5 — Secrets management (sealed-secrets / external-secrets)
- [ ] Layer 6 — CI/CD (GitHub Actions, multi-arch images)
- [ ] Layer 7 — Deploy a NeuronAI / Aegis API service through the pipeline

## Security

No secrets live in this repository. The K3s join token, kubeconfig and any credentials are supplied at
runtime (environment / vault) and excluded by `.gitignore`; Layer 5 introduces sealed/external-secrets so
even encrypted secrets are handled the right way. Example inventory uses placeholder addresses only.

## About

Built by **Bapista Khan** — AI Systems Engineer, Sydney 🇦🇺.
Part of the [Collab-Foundry](https://collab-foundry.com.au) sovereign-AI work (Aegis AI · NeuronAI · Cipher).
[bapistakhan.com](https://bapistakhan.com) · [LinkedIn](https://www.linkedin.com/in/bapista-khan)

_MIT licensed._
