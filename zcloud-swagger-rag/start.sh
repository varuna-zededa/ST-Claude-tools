#!/bin/bash
# Start services needed for the Swagger RAG MCP server.
# Run once after each reboot before using Claude Code swagger tools.

echo "Starting Ollama..."
pgrep -x ollama > /dev/null || (ollama serve > /tmp/ollama.log 2>&1 & echo "  Ollama started (log: /tmp/ollama.log)")
sleep 1
pgrep -x ollama > /dev/null && echo "  Ollama is running" || echo "  WARNING: Ollama failed to start"

echo "Starting Qdrant..."
if docker ps --filter name=qdrant --filter status=running --format "{{.Names}}" | grep -q qdrant; then
    echo "  Qdrant already running"
else
    docker start qdrant && echo "  Qdrant started" || echo "  WARNING: Could not start Qdrant"
fi

echo ""
echo "Ready. The MCP server (server.py) starts automatically when Claude Code spawns it."
echo "To re-ingest swagger files:"
echo "  source ~/swagger-rag/venv/bin/activate"
echo "  python ~/swagger-rag/ingest.py /path/to/*.swagger.json"
