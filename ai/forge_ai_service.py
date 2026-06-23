#!/usr/bin/env python3
"""FORGE AI service — exposes FORGE's full brain over HTTP, closing the learning loop.

It wraps forge_ai (brain + memory + per-node routing) and forge_learn (lessons), so:
  - the desktop chats with FORGE's *real* brain (memory + recalled lessons applied), and
  - every command the operator approves is POSTed back here and becomes a LESSON,
    which the brain then applies next time. command -> lesson -> better answer. Loop closed.

Stdlib only, no deps. Runs on the control-plane (or any node with Ollama + the memory).

Endpoints:
  GET  /api/health
  POST /api/chat    {question|messages, node?}     -> {response, persona, node}
  POST /api/learn   {node, cmd, exit_code, output}  (or {category,title,body,tags}) -> {lesson_id, stats}
  GET  /api/lessons -> {lessons, top}
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forge_ai      # noqa: E402
import forge_learn   # noqa: E402

PORT = 8099
MEM = forge_ai.ForgeMemory()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path.startswith("/api/health"):
            self._send(200, {"status": "healthy", "service": "forge-ai",
                             "skills": list(forge_ai.SKILLS), "personas": {k: v["persona"] for k, v in forge_ai.PERSONAS.items()}})
        elif self.path.startswith("/api/lessons"):
            self._send(200, forge_learn.stats())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            d = self._body()
        except Exception:
            return self._send(400, {"error": "bad json"})
        if self.path.startswith("/api/chat"):
            q = d.get("question") or (d.get("messages", [{}])[-1].get("content", "") if d.get("messages") else "")
            r = forge_ai.ask(q, node=d.get("node", "forge"), memory=MEM)
            self._send(200, {"response": r["answer"], "persona": r["persona"], "node": r["node"]})
        elif self.path.startswith("/api/learn"):
            if "cmd" in d:
                lid = forge_learn.learn_from_command(d.get("node", "?"), d.get("cmd", ""),
                                                     int(d.get("exit_code", 0) or 0), d.get("output", ""))
            else:
                lid = forge_learn.log(d.get("category", "ops"), d.get("title", ""), d.get("body", ""),
                                      float(d.get("signal", 0.6)), d.get("tags"), d.get("source", "desktop"))
            self._send(200, {"lesson_id": lid, "stats": forge_learn.stats()})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"FORGE AI service on :{PORT} — chat + memory + lessons + per-node routing")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
