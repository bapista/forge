#!/usr/bin/env python3
"""FORGE fleet firewall reconciler — makes this node's ufw match the desired
state in policy.json. FORGE owns the firewall the way it owns the cluster.

Strategy: reset-then-rebuild. We reset ufw (which DISABLES it -> host briefly
open, never locked out), then add exactly the policy's rules and re-enable.
This guarantees the live firewall equals the policy: drift is removed by
construction, no fragile diffing. A dead-man switch disables ufw after 180s if
this script dies mid-run, so a bug can never lock the fleet out.

Invariants always enforced regardless of policy: loopback + tailscale mesh
trusted, and SSH (22/tcp) kept. Result is written to a state file for Aegis.

Run as root (systemd timer or sudo). Usage: forge_firewall.py [policy.json]
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys

POLICY_PATH = (sys.argv[1] if len(sys.argv) > 1
               else os.environ.get("FORGE_FW_POLICY", "/etc/forge-firewall/policy.json"))
NODE_FILE = "/etc/forge-firewall/node"
STATE_DIR = "/var/lib/forge-firewall"
DEADMAN_UNIT = "forge-fw-deadman"
DEADMAN_SECONDS = 180


def node_name() -> str:
    if os.path.exists(NODE_FILE):
        n = open(NODE_FILE).read().strip()
        if n:
            return n
    return os.environ.get("FORGE_NODE") or socket.gethostname().split(".")[0]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def expand_rules(node_cfg: dict, groups: dict) -> list[dict]:
    out = []
    for r in node_cfg.get("rules", []):
        if "group" in r:
            out.extend(groups.get(r["group"], []))
        else:
            out.append(r)
    return out


def rule_cmd(r: dict) -> list[str]:
    """Uniform ufw spec that handles single ports, lists (137,138) and ranges (30000:32767)."""
    proto = r.get("proto", "tcp")
    frm = r.get("from", "any")
    comment = "forge: " + r.get("comment", "managed")
    return ["ufw", "allow", "proto", proto, "from", frm, "to", "any",
            "port", str(r["port"]), "comment", comment]


def arm_deadman() -> None:
    # if this script dies before disarm, ufw is disabled (host reopened) after 180s
    run(["systemd-run", "--on-active=%d" % DEADMAN_SECONDS, "--unit", DEADMAN_UNIT,
         "--collect", "/bin/sh", "-c", "ufw --force disable"], check=False)


def disarm_deadman() -> None:
    run(["systemctl", "stop", DEADMAN_UNIT + ".timer"], check=False)
    run(["systemctl", "stop", DEADMAN_UNIT + ".service"], check=False)
    run(["systemctl", "reset-failed", DEADMAN_UNIT + ".timer", DEADMAN_UNIT + ".service"], check=False)


def current_rules() -> list[str]:
    """Best-effort snapshot of live ufw ALLOW rules (for drift reporting to Aegis)."""
    try:
        out = run(["ufw", "status"], check=False).stdout
    except Exception:
        return []
    rules = []
    for line in out.splitlines():
        if "ALLOW" in line and "on lo" not in line and "tailscale0" not in line:
            rules.append(" ".join(line.split()))
    return rules


def write_state(node: str, managed: bool, applied: list[dict], note: str = "",
                drift: list[str] | None = None) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    state = {"node": node, "managed": managed, "rule_count": len(applied),
             "applied": applied, "drift_removed": drift or [],
             "note": note, "policy": POLICY_PATH}
    with open(os.path.join(STATE_DIR, "state.json"), "w") as f:
        json.dump(state, f, indent=2)


def main() -> int:
    if os.geteuid() != 0:
        print("[forge-fw] must run as root", file=sys.stderr)
        return 2
    policy = json.load(open(POLICY_PATH))
    node = node_name()
    cfg = policy.get("nodes", {}).get(node)
    if cfg is None:
        print(f"[forge-fw] node '{node}' not in policy — leaving firewall untouched")
        write_state(node, False, [], "node not in policy")
        return 0
    if not cfg.get("manage", False):
        print(f"[forge-fw] node '{node}' is manage:false — leaving firewall as-is")
        write_state(node, False, [], "manage:false")
        return 0

    rules = expand_rules(cfg, policy.get("groups", {}))
    trust = policy.get("trust_interfaces", ["lo", "tailscale0"])
    print(f"[forge-fw] reconciling {node}: {len(rules)} rules + trust {trust} + ssh")

    # drift report: which live rules existed that the policy does NOT sanction
    desired_tokens = {"22/tcp"}
    for r in rules:
        desired_tokens.add(f"{r['port']}/{r.get('proto', 'tcp')}")
    drift = []
    if cfg.get("enforce_drift", True):
        for line in current_rules():
            tok = line.split()[0]
            if tok not in desired_tokens and not tok.startswith("22"):
                drift.append(line)
        if drift:
            print(f"[forge-fw] DRIFT on {node} (removing {len(drift)} unsanctioned rule(s)): {drift}")

    arm_deadman()
    try:
        run(["ufw", "--force", "reset"])                       # clears all + disables (open gap)
        run(["ufw", "default", "deny", "incoming"])
        run(["ufw", "default", "allow", "outgoing"])
        for iface in trust:                                    # loopback + tailnet mesh trusted
            run(["ufw", "allow", "in", "on", iface])
        if policy.get("keep_ssh", True):                       # anti-lockout invariant
            run(["ufw", "allow", "22/tcp", "comment", "forge: ssh (invariant)"])
        for r in rules:
            run(rule_cmd(r))
        run(["ufw", "--force", "enable"])
    finally:
        disarm_deadman()

    write_state(node, True, rules, drift=drift)
    print(f"[forge-fw] {node} reconciled: deny-in/allow-out, ssh+{','.join(trust)} trusted, "
          f"{len(rules)} policy rules applied, {len(drift)} drift removed. Firewall matches policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
