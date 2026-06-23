"""FORGE AI — the cluster's own brain.

Memory structure is copied from Cipher (SQLite: memories / facts / sessions, with
cognitive modules + importance), so FORGE remembers what happens on the cluster.

FORGE is AI-powered with a FIXED skill set and routes each question to the AI that
lives on the relevant machine:
    tuxedo  -> NeuronAI      olympus -> Aegis AI      mac -> Cipher
FORGE also looks after its OWN health & safety, and is designed to survive the loss
of any single node (HA fallback) — see docs/AI.md.

This module is the foundation: the memory + identity + skills + per-node router are
real and runnable against the existing NeuronAI (:8001) / Cipher (:8000) bridges.
The Aegis endpoint, autonomous self-healing and leader-failover are later phases.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from pathlib import Path

# ── Per-node personas: who answers, and where ──────────────────────────────
# FORGE has no single "voice" — the AI resident on each machine answers for it.
PERSONAS: dict[str, dict] = {
    "tuxedo":  {"persona": "NeuronAI", "base": "http://tuxedo.local:8001",  "chat": "/api/chat", "shape": "messages"},
    "olympus": {"persona": "Aegis AI", "base": "http://olympus.local:8000", "chat": "/api/chat", "shape": "messages"},  # pending Aegis bridge
    "mac":     {"persona": "Cipher",   "base": "http://mac.local:8000",     "chat": "/api/chat", "shape": "messages"},
}
DEFAULT_NODE = "forge"   # FORGE answers with its OWN brain by default; personas are upgrades

# ── FORGE's OWN brain — local Ollama, zero external dependency ──────────────
import os
OLLAMA = os.environ.get("FORGE_OLLAMA", "http://localhost:11434")
FORGE_CHAT_MODEL = os.environ.get("FORGE_CHAT_MODEL", "qwen2.5:3b-instruct")  # see ai/models.yaml
_AI_DIR = Path(__file__).resolve().parent


def _identity_facts() -> str:
    try:
        return (_AI_DIR / "identity.md").read_text(encoding="utf-8")
    except Exception:
        return "FORGE is a sovereign, self-organizing AI cluster platform by Collab-Foundry."


def forge_system_prompt() -> str:
    """Ground FORGE on its identity + fixed skills (Cipher's _FACTS_EN pattern)."""
    skills = "; ".join(f"{k} ({v})" for k, v in SKILLS.items())
    return (
        "You are FORGE, the sovereign cluster operator, by Collab-Foundry.\n"
        "AUTHORITATIVE FACTS about yourself — never contradict these, they override your pretraining:\n"
        f"{_identity_facts()}\n"
        f"YOUR FIXED SKILLS (you do these and only these): {skills}.\n"
        "Answer briefly and plainly for a non-technical operator. When an action needs a shell command, "
        'propose exactly ONE command on its own line starting with "RUN:" — never claim you ran it; the '
        "operator approves and runs it. You never run destructive commands on your own."
    )


def forge_brain(question: str, system: str | None = None, model: str | None = None, timeout: float = 120.0) -> str:
    """FORGE's own voice via local Ollama — grounded on identity + skills + recalled LESSONS
    (self-learning, copied from Cipher). No external AI needed."""
    sys_p = system or forge_system_prompt()
    try:  # apply what FORGE has learned that's relevant to this question
        import forge_learn
        lb = forge_learn.lessons_block(query=question, k=4)
        if lb:
            sys_p = sys_p + "\n" + lb
    except Exception:
        pass
    body = json.dumps({"model": model or FORGE_CHAT_MODEL, "stream": False,
                       "messages": [{"role": "system", "content": sys_p},
                                    {"role": "user", "content": question}]}).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return (d.get("message") or {}).get("content", "") or "(no reply)"

# ── Fixed skills (FORGE's defined capabilities) ────────────────────────────
SKILLS: dict[str, str] = {
    "cluster-ops":  "inspect and operate the cluster (nodes, roles, joins)",
    "health-check": "read cluster health + the node's own liveness",
    "node-join":    "explain/trigger adding a machine (mDNS auto-join or add-node)",
    "diagnose":     "investigate a problem on a machine via the terminal tool",
    "terminal":     "propose a shell command for the user to approve, then run it",
    "explain":      "answer in plain language for a non-technical operator",
    "self-care":    "watch FORGE's own health & safety and raise issues",
}

# ── Memory — structure copied from Cipher (SQLite) ─────────────────────────
COGNITIVE_MODULES = ["self", "cluster", "nodes", "health", "security", "ops", "incidents", "operator"]


class ForgeMemory:
    """Cipher-modeled memory: episodic `memories`, durable `facts`, `sessions`."""

    def __init__(self, path: str = "~/.forge/forge_memory.db") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
              id INTEGER PRIMARY KEY, content TEXT, memory_type TEXT DEFAULT 'episodic',
              module TEXT DEFAULT 'cluster', importance REAL DEFAULT 0.5,
              source TEXT DEFAULT 'forge', ts REAL );
            CREATE INDEX IF NOT EXISTS idx_mod ON memories(module);
            CREATE TABLE IF NOT EXISTS facts ( key TEXT PRIMARY KEY, value TEXT, ts REAL );
            CREATE TABLE IF NOT EXISTS sessions ( id TEXT PRIMARY KEY, started REAL, note TEXT );
            """
        )
        self.db.commit()

    def remember(self, content: str, module: str = "cluster", importance: float = 0.5, source: str = "forge") -> None:
        self.db.execute(
            "INSERT INTO memories(content,memory_type,module,importance,source,ts) VALUES(?,?,?,?,?,?)",
            (content, "episodic", module, importance, source, time.time()),
        )
        self.db.commit()

    def recall(self, query: str, k: int = 5) -> list[str]:
        rows = self.db.execute(
            "SELECT content FROM memories WHERE content LIKE ? ORDER BY importance DESC, ts DESC LIMIT ?",
            (f"%{query}%", k),
        ).fetchall()
        return [r[0] for r in rows]

    def set_fact(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO facts(key,value,ts) VALUES(?,?,?)", (key, value, time.time()))
        self.db.commit()

    def get_fact(self, key: str) -> str | None:
        r = self.db.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return r[0] if r else None


# ── Router — send a question to the AI on the right machine ────────────────
def resident_for(node: str) -> dict:
    return PERSONAS.get(node, PERSONAS[DEFAULT_NODE])


def ask(question: str, node: str = DEFAULT_NODE, memory: ForgeMemory | None = None, timeout: float = 60.0) -> dict:
    """Answer `question`. node='forge' uses FORGE's OWN brain (local Ollama). A persona node
    (tuxedo/mac/olympus) routes to that machine's AI — and falls back to FORGE's brain if that
    bridge is down. So FORGE ALWAYS answers, with or without NeuronAI/Cipher/Aegis present."""
    if node == "forge" or node not in PERSONAS:
        try:
            answer, persona, ok = forge_brain(question, timeout=timeout), "FORGE", True
        except Exception as exc:
            answer, persona, ok = f"[FORGE brain (Ollama) unreachable: {exc}]", "FORGE", False
    else:
        p = resident_for(node)
        body = json.dumps({"messages": [{"role": "user", "content": question}]}).encode()
        req = urllib.request.Request(p["base"] + p["chat"], data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            answer, persona, ok = (data.get("response") or data.get("answer") or json.dumps(data)[:800]), p["persona"], True
        except Exception:
            try:  # persona bridge down -> FORGE's own brain takes over
                answer, persona, ok = forge_brain(question, timeout=timeout), f"FORGE (fallback for {p['persona']})", True
            except Exception as exc:
                answer, persona, ok = f"[{p['persona']} + FORGE brain unreachable: {exc}]", p["persona"], False
    if memory is not None:
        memory.remember(f"Q@{node}({persona}): {question} -> {str(answer)[:200]}", module="ops", importance=0.6)
    return {"node": node, "persona": persona, "ok": ok, "answer": answer}


# ── Guarded terminal tool — AI proposes, the OPERATOR approves ─────────────
_DESTRUCTIVE = ("rm ", "mkfs", "dd ", "shutdown", "reboot", ":(){", "> /dev", "drop ", "delete ", "kubectl delete")
READONLY_OK = ("uptime", "df", "free", "top", "kubectl get", "systemctl status", "cat ", "ls ", "ip ", "ping ")


def classify_command(cmd: str) -> str:
    c = cmd.strip().lower()
    if any(d in c for d in _DESTRUCTIVE):
        return "destructive"        # never auto-run — explicit approval required
    if c.startswith(READONLY_OK):
        return "readonly"           # safe to run on approval (or auto in read-only mode)
    return "mutating"               # requires approval


# ── Self health & safety ───────────────────────────────────────────────────
def self_health(memory: ForgeMemory | None = None) -> dict:
    """FORGE checks its own brain (memory reachable) + records it. The cluster's
    machine health comes from /api/cluster/nodes (the dashboard's Health tab)."""
    status = {"memory": False, "skills": list(SKILLS), "personas": {k: v["persona"] for k, v in PERSONAS.items()}}
    try:
        m = memory or ForgeMemory()
        m.set_fact("last_self_check", str(time.time()))
        status["memory"] = True
    except Exception:
        status["memory"] = False
    return status


if __name__ == "__main__":
    mem = ForgeMemory()
    print("FORGE AI online. self-health:", json.dumps(self_health(mem), indent=2))
    print("skills:", list(SKILLS))
