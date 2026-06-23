# FORGE — your own sovereign AI platform, in one command

[![validate](https://github.com/bapista/forge/actions/workflows/ci.yml/badge.svg)](https://github.com/bapista/forge/actions/workflows/ci.yml)
&nbsp;![Runs on](https://img.shields.io/badge/runs%20on-Linux%20%26%20Raspberry%20Pi-326CE5)
&nbsp;![No cloud](https://img.shields.io/badge/cloud-none-1d9e75)
&nbsp;![License](https://img.shields.io/badge/License-AGPL--3.0-green)

Turn a few Linux or Raspberry Pi machines into **your own private AI platform** — on your hardware, in
your home or office, with **no cloud and no subscription**. One command to start. Open it from any
device. Add more machines when you want more power.

> Sovereign by default: your data, your models, your machines. Part of
> [Collab-Foundry](https://collab-foundry.com.au) — ethical, humanity-first technology for everyone.

## Get started — run the SAME command on every machine

On each Linux box or Raspberry Pi on the same Wi-Fi / LAN:

```bash
curl -sfL https://raw.githubusercontent.com/bapista/forge/main/install.sh | sudo sh
```
*(A friendlier `get.collab-foundry.com.au` shortcut is on the way.)*

**That's it — FORGE self-organizes.** The machines discover each other over your network (mDNS),
**automatically elect one control-plane**, and the rest auto-join. No IP to copy, no token to paste.
The control-plane prints a link like `http://192.168.1.50:30888` — **open it from any device** (Mac,
phone, laptop). See [docs/ORGANIC.md](docs/ORGANIC.md) for how the election works.

> Clients can be **anything** (Mac, Windows, Linux, phone). Only the *cluster* machines need to be
> Linux/Pi — they do the work; everything else just connects.

## Grow it — just run it again

Add a machine later? Run the **same** installer on it — it auto-joins the existing cluster. Nothing to copy.

**Across different networks** (not the same LAN)? Join over Tailscale with explicit details:
```bash
curl -sfL https://raw.githubusercontent.com/bapista/forge/main/add-node.sh | FORGE_SERVER=<tailscale-ip> FORGE_TOKEN=<token> sudo sh
```

## Why FORGE

- **Easy.** One command. No Kubernetes knowledge needed — the complexity is hidden.
- **Sovereign.** Runs entirely on your machines. No hyperscaler, no data leaving home.
- **Yours to grow.** Start on one machine; add nodes as you need capacity.
- **Open & share-alike.** AGPL-3.0 licensed; inspect and own every line — use it freely, but share your contributions back.

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

> Reference fleet (Tailscale/WireGuard mesh): **olympus** (control-plane) · **hermes** (mail, Pi 5) ·
> **talos** (Hailo NPU edge AI, Pi 5) · **tuxedo** (dev) · **templar** (gateway). Node names are yours to choose.

FORGE is built the way a production platform should be. The full **GitOps** version (Argo CD app-of-apps,
Helm-managed cert-manager + Let's Encrypt, ingress-nginx, kube-prometheus-stack observability,
sealed-secrets, CI-validated manifests, Ansible provisioning) lives in [`advanced/`](advanced/) — see
[`docs/architecture.md`](docs/architecture.md). The simple installer above is the friendly face on top of it.

## About

Built by **Bapista Khan** — AI Systems Engineer, Sydney 🇦🇺 —
as part of [Collab-Foundry](https://collab-foundry.com.au)'s sovereign-AI work (Aegis AI · NeuronAI · Cipher).
[bapistakhan.com](https://bapistakhan.com) · [LinkedIn](https://www.linkedin.com/in/bapista-khan)

_AGPL-3.0 licensed — use freely, share contributions back, keep attribution. (Releases v0.1.0–v0.3.0 remain MIT.) See [NOTICE](NOTICE)._
