#!/usr/bin/env bash
# Serve the "Building Agentic AI with Amazon Bedrock AgentCore" slide app over
# HTTP so deck.html can fetch its decks.
# The reveal.js viewer loads decks/mN.json via fetch(), which browsers block
# under file:// — the bundled decks/mN.js fallback makes file:// work too, but
# serving over HTTP is the most reliable way to run it.
#
# Usage:  ./slides/serve.sh [PORT]     (default 8010)
set -euo pipefail
PORT="${1:-8010}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Free the port if something is already bound to it.
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT busy; freeing it."
  lsof -tiTCP:"$PORT" -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
  sleep 1
fi
echo "Serving $DIR at http://localhost:$PORT/"
echo "Open:  http://localhost:$PORT/index.html   (Ctrl-C to stop)"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIR"
