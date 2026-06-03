#!/bin/bash
# Inject MemoryHub memories at Claude Code session start.
# Stdout is added to the conversation context before the first prompt.
# Exits 0 silently on any failure -- the session starts normally and
# the MCP server remains available as a fallback.

set -euo pipefail

API_KEY_FILE="$HOME/.config/memoryhub/api-key"
[ -f "$API_KEY_FILE" ] || exit 0

API_KEY=$(tr -d '\n' < "$API_KEY_FILE")
[ -n "$API_KEY" ] || exit 0
export MEMORYHUB_API_KEY="$API_KEY"

if [ -z "${MEMORYHUB_URL:-}" ]; then
  CONFIG_FILE="$HOME/.config/memoryhub/config.json"
  if [ -f "$CONFIG_FILE" ]; then
    MEMORYHUB_URL=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('url',''))" "$CONFIG_FILE" 2>/dev/null) || true
  fi
fi
[ -n "${MEMORYHUB_URL:-}" ] || exit 0
export MEMORYHUB_URL

MEMORYHUB_BIN="${CLAUDE_PROJECT_DIR:-$PWD}/memoryhub-cli/.venv/bin/memoryhub"
if ! [ -x "$MEMORYHUB_BIN" ]; then
  MEMORYHUB_BIN=$(command -v memoryhub 2>/dev/null) || exit 0
fi

PROJECT_ID=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")

"$MEMORYHUB_BIN" search \
  "project context architecture preferences decisions workflow" \
  --project-id "$PROJECT_ID" \
  --output compact \
  --max 20 2>/dev/null || exit 0
