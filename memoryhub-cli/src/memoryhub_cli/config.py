"""Configuration management for MemoryHub CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "memoryhub"
CONFIG_FILE = CONFIG_DIR / "config.json"
API_KEY_FILE = CONFIG_DIR / "api-key"


def load_config() -> dict:
    """Load config from disk. Returns empty dict if not found."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict) -> None:
    """Save config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
    CONFIG_FILE.chmod(0o600)


def get_api_key() -> str | None:
    """Resolve API key from env var, key file, or config.

    Precedence: MEMORYHUB_API_KEY env var > ~/.config/memoryhub/api-key file
    > api_key in config.json.
    """
    key = os.environ.get("MEMORYHUB_API_KEY", "").strip()
    if key:
        return key

    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text().strip()
        if key:
            return key

    return load_config().get("api_key") or None


def get_server_url() -> str | None:
    """Resolve server URL from env var or config."""
    url = os.environ.get("MEMORYHUB_URL", "").strip()
    if url:
        return url
    return load_config().get("url") or None


def get_connection_params() -> dict:
    """Get OAuth connection parameters, preferring env vars over config file.

    Required keys: url, auth_url, client_id, client_secret.
    """
    config = load_config()
    return {
        "url": os.environ.get("MEMORYHUB_URL", config.get("url", "")),
        "auth_url": os.environ.get("MEMORYHUB_AUTH_URL", config.get("auth_url", "")),
        "client_id": os.environ.get("MEMORYHUB_CLIENT_ID", config.get("client_id", "")),
        "client_secret": os.environ.get(
            "MEMORYHUB_CLIENT_SECRET", config.get("client_secret", "")
        ),
    }
