#!/bin/sh
# Give this machine FORGE's own brain: pull the model set via Ollama, sized to its RAM.
set -e
RAM_GB=$(awk '/MemTotal/{printf "%d",$2/1024/1024}' /proc/meminfo 2>/dev/null || echo 8)
command -v ollama >/dev/null 2>&1 || { echo "installing Ollama (FORGE engine)..."; curl -sfL https://ollama.com/install.sh | sh >/dev/null 2>&1 || true; }
pull(){ echo "▶ FORGE model: $1"; ollama pull "$1" >/dev/null 2>&1 || true; }
pull llama3.2:1b
pull nomic-embed-text
if   [ "$RAM_GB" -ge 16 ]; then pull qwen2.5:7b-instruct; pull qwen2.5-coder:3b
elif [ "$RAM_GB" -ge 8  ]; then pull qwen2.5:3b-instruct; pull qwen2.5-coder:3b
else pull qwen2.5:1.5b; fi
echo "✅ FORGE brain ready (RAM ${RAM_GB}GB)."
