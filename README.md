# FORGE — your own sovereign AI platform, in one command

[![validate](https://github.com/bapista/forge/actions/workflows/ci.yml/badge.svg)](https://github.com/bapista/forge/actions/workflows/ci.yml)
&nbsp;![Runs on](https://img.shields.io/badge/runs%20on-Linux%20%26%20Raspberry%20Pi-326CE5)
&nbsp;![No cloud](https://img.shields.io/badge/cloud-none-1d9e75)
&nbsp;![License](https://img.shields.io/badge/License-MIT-green)

Turn a few Linux or Raspberry Pi machines into **your own private AI platform** — on your hardware, in
your home or office, with **no cloud and no subscription**. One command to start. Open it from any
device. Add more machines when you want more power.

> Sovereign by default: your data, your models, your machines. Part of
> [Collab-Foundry](https://collab-foundry.com.au) — ethical, humanity-first technology for everyone.

## Get started — one machine, one command

On a Linux box or Raspberry Pi:

```bash
curl -sfL https://raw.githubusercontent.com/bapista/forge/main/install.sh | sudo sh
```
*(A friendlier `get.collab-foundry.com.au` shortcut is on the way.)*

That's it. FORGE installs itself and prints a link like `http://192.168.1.50:30888`.
**Open that link from any device** — your Mac, your phone, your laptop — and FORGE is there.

> Clients can be **anything** (Mac, Windows, Linux, phone). Only the *cluster* machines need to be
> Linux/Pi — they do the work; everything else just connects.

## Grow it — add a machine when you want more

Got a second Pi or mini-PC? The first machine prints an `add-node` command. Run it on the new box:

```bash
curl -sfL https://raw.githubusercontent.com/bapista/forge/main/add-node.sh | FORGE_SERVER=<ip> FORGE_TOKEN=<token> sudo sh
```

The new machine joins your cluster and shares the load. No reconfiguration, no downtime.

## Why FORGE

- **Easy.** One command. No Kubernetes knowledge needed — the complexity is hidden.
- **Sovereign.** Runs entirely on your machines. No hyperscaler, no data leaving home.
- **Yours to grow.** Start on one machine; add nodes as you need capacity.
- **Open.** MIT-licensed; inspect and own every line.

## What's inside

| | |
|---|---|
| `install.sh` | the one-command installer (sets up the engine + the FORGE apps) |
| `add-node.sh` | join another Linux/Pi machine to your cluster |
| `bundle/` | the FORGE apps that get deployed (starting with the dashboard) |
| `advanced/` | for engineers — the full GitOps build (Argo CD, Helm, cert-manager, observability) |

Under the hood FORGE uses **K3s** (lightweight Kubernetes) as its engine — but you never have to touch
it. *Real AI services (chat, mail, assistants) plug into `bundle/` as they ship.*

## For engineers — the advanced path

FORGE is built the way a production platform should be. The full **GitOps** version (Argo CD app-of-apps,
Helm-managed cert-manager + Let's Encrypt, ingress-nginx, kube-prometheus-stack observability,
sealed-secrets, CI-validated manifests, Ansible provisioning) lives in [`advanced/`](advanced/) — see
[`docs/architecture.md`](docs/architecture.md). The simple installer above is the friendly face on top of it.

## About

Built by **Bapista Khan** — AI Systems Engineer, Sydney 🇦🇺 —
as part of [Collab-Foundry](https://collab-foundry.com.au)'s sovereign-AI work (Aegis AI · NeuronAI · Cipher).
[bapistakhan.com](https://bapistakhan.com) · [LinkedIn](https://www.linkedin.com/in/bapista-khan)

_MIT licensed._
