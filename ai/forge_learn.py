"""FORGE self-learning — copied from Cipher's lessons.py.

FORGE files short LESSONS from what happens on the cluster (a command that worked, a join that
failed, a recurring health issue), recalls the relevant ones before it acts, and lets noisy
lessons fade (times_surfaced). Lightweight continual learning: FORGE gets better with use.

Flow:  log(...)  →  recall(question/tags)  →  the brain applies them  →  noisy lessons fade.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB = Path("~/.forge/forge_lessons.db").expanduser()
_DB.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB))
    c.row_factory = sqlite3.Row
    return c


def _init() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS lessons (
              id TEXT PRIMARY KEY, category TEXT NOT NULL, title TEXT NOT NULL,
              body TEXT DEFAULT '', signal REAL DEFAULT 0.5, source TEXT DEFAULT '',
              tags TEXT DEFAULT '[]', created_at TEXT, last_relevant_at TEXT,
              times_surfaced INTEGER DEFAULT 0, active INTEGER DEFAULT 1 );
            CREATE INDEX IF NOT EXISTS l_sig ON lessons(signal DESC);
            """
        )
        c.commit()


_init()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(category: str, title: str, body: str = "", signal: float = 0.5,
        tags: list[str] | None = None, source: str = "") -> str | None:
    """File a lesson. Dedupes on (category, title) — re-logging bumps its signal."""
    cat = (category or "general").strip().lower()[:40] or "general"
    title = (title or "").strip()[:240]
    if not title:
        return None
    body = (body or "").strip()[:8000]
    sig = max(0.0, min(1.0, float(signal)))
    tj = json.dumps(sorted({(t or "").strip().lower() for t in (tags or []) if t}))
    now = _now()
    with _conn() as c:
        ex = c.execute("SELECT * FROM lessons WHERE category=? AND title=? AND active=1", (cat, title)).fetchone()
        if ex:
            c.execute("UPDATE lessons SET signal=?, body=?, tags=?, last_relevant_at=? WHERE id=?",
                      (min(1.0, ex["signal"] + 0.05), body or ex["body"], tj, now, ex["id"]))
            c.commit()
            return ex["id"]
        lid = "l_" + secrets.token_hex(6)
        c.execute("INSERT INTO lessons(id,category,title,body,signal,source,tags,created_at,last_relevant_at)"
                  " VALUES(?,?,?,?,?,?,?,?,?)", (lid, cat, title, body, sig, source, tj, now, now))
        c.commit()
        return lid


def recall(query: str = "", tags: list[str] | None = None, k: int = 5) -> list[dict]:
    """Most relevant lessons (tag overlap + text match + signal), strongest first; bump surfaced."""
    q = (query or "").lower()
    # significant query words (>3 chars, skip stopwords) — word overlap, not whole-string match
    _STOP = {"what", "when", "where", "which", "your", "this", "that", "with", "from", "have",
             "does", "should", "could", "would", "about", "into", "line", "answer", "tell"}
    qwords = {w.strip("?.,:;!`'\"") for w in q.split() if len(w) > 3} - _STOP
    want = {(t or "").lower() for t in (tags or []) if t}
    with _conn() as c:
        rows = c.execute("SELECT * FROM lessons WHERE active=1 ORDER BY signal DESC, created_at DESC LIMIT 200").fetchall()
        scored = []
        for r in rows:
            tg = set(json.loads(r["tags"] or "[]"))
            text = (r["title"] + " " + (r["body"] or "")).lower()
            hit_tag = bool(want & tg)
            word_hits = sum(1 for w in qwords if w in text)   # how many query words land in the lesson
            if hit_tag or word_hits or not (want or qwords):
                scored.append((len(want & tg) * 2 + word_hits + r["signal"], r))
        scored.sort(key=lambda x: -x[0])
        top = [r for _, r in scored[:k]]
        for r in top:
            c.execute("UPDATE lessons SET times_surfaced=times_surfaced+1, last_relevant_at=? WHERE id=?", (_now(), r["id"]))
        c.commit()
        return [{"title": r["title"], "body": r["body"], "signal": r["signal"], "category": r["category"]} for r in top]


def lessons_block(query: str = "", tags: list[str] | None = None, k: int = 4) -> str:
    """The recalled lessons formatted for FORGE's system prompt (so it applies what it learned)."""
    ls = recall(query, tags, k)
    if not ls:
        return ""
    return "WHAT YOU'VE LEARNED ON THIS CLUSTER (apply these):\n" + "\n".join(
        f"- {l['title']}" + (f": {l['body'][:160]}" if l["body"] else "") for l in ls)


def learn_from_command(node: str, cmd: str, exit_code: int, output: str = "") -> str | None:
    """After a terminal command runs, file a lesson from the outcome — this is how FORGE learns from doing."""
    ok = exit_code == 0
    cat = "ops-success" if ok else "ops-failure"
    title = f"on {node}: `{cmd[:80]}` {'works' if ok else 'failed ('+str(exit_code)+')'}"
    body = (output or "").strip()[:400]
    tags = [node, "command", "success" if ok else "failure"]
    return log(cat, title, body, signal=0.6 if ok else 0.7, tags=tags, source="terminal")


def stats() -> dict:
    with _conn() as c:
        n = c.execute("SELECT COUNT(*) FROM lessons WHERE active=1").fetchone()[0]
        top = c.execute("SELECT title, signal, times_surfaced FROM lessons WHERE active=1 ORDER BY signal DESC LIMIT 5").fetchall()
    return {"lessons": n, "top": [dict(r) for r in top]}


if __name__ == "__main__":
    # seed a few real bootstrap lessons so FORGE starts with operational knowledge
    log("cluster", "talos can be false-offline on its LAN IP — probe its Tailscale IP",
        "talos left the LAN; it's reachable on the Tailscale/WireGuard mesh. The node-liveness probe must check both.",
        signal=0.8, tags=["talos", "offline", "tailscale", "health"], source="seed")
    log("cluster", "single control-plane is a single point of failure",
        "olympus is the only etcd control-plane. Add a 2nd/3rd for HA so FORGE survives a node loss.",
        signal=0.7, tags=["olympus", "control-plane", "ha", "security"], source="seed")
    log("ops", "never run destructive commands without operator approval",
        "rm/dd/mkfs/kubectl delete must always be proposed and approved, never auto-run.",
        signal=0.9, tags=["safety", "terminal", "destructive"], source="seed")
    print("FORGE self-learning ready:", json.dumps(stats(), indent=2))
