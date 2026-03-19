"""Configuration loader — reads YAML config files into dicts."""

import json
from pathlib import Path

import yaml

CONFIG_DIR = Path("config")


def load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _deep_set(d: dict, key: str, value):
    """Set a value in a nested dict using dot-notation key."""
    parts = key.split(".")
    for part in parts[:-1]:
        if part not in d or not isinstance(d[part], dict):
            d[part] = {}
        d = d[part]
    d[parts[-1]] = value


def _apply_overrides(config: dict, overrides: dict) -> dict:
    """Apply dot-notation overrides to a config dict."""
    for key, value in overrides.items():
        _deep_set(config, key, value)
    return config


def load_config(db=None) -> dict:
    """Load and merge all configuration files, then apply SQLite overrides."""
    settings = load_yaml("settings.yaml")
    streams = load_yaml("streams.yaml")
    instruments = load_yaml("instruments.yaml")

    settings["streams"] = streams
    settings["instruments"] = instruments

    # Apply overrides from JSON file (written by Vercel direct config save)
    json_overrides_path = Path("data/config_overrides.json")
    if json_overrides_path.exists():
        try:
            with open(json_overrides_path) as f:
                json_overrides = json.load(f)
            if json_overrides:
                _apply_overrides(settings, json_overrides)
        except Exception:
            pass

    # Apply overrides from database (takes precedence over JSON file)
    if db is not None:
        overrides = db.get_config_overrides()
        if overrides:
            _apply_overrides(settings, overrides)
    else:
        # Try to load overrides from the default database
        try:
            from backend.core.database import Database
            _db = Database("data/sentinel.db")
            overrides = _db.get_config_overrides()
            if overrides:
                _apply_overrides(settings, overrides)
            _db.close()
        except Exception:
            pass

    return settings


def get_effective_config(db=None) -> dict:
    """Get the full effective config (YAML + overrides)."""
    return load_config(db=db)


def save_config_overrides(overrides: dict, db=None):
    """Save a dict of dot-notation key-value pairs as config overrides."""
    if db is None:
        from backend.core.database import Database
        db = Database("data/sentinel.db")
        should_close = True
    else:
        should_close = False

    for key, value in overrides.items():
        db.set_config_override(key, value)

    if should_close:
        db.close()


def load_instruments() -> dict:
    return load_yaml("instruments.yaml")


def load_streams() -> dict:
    return load_yaml("streams.yaml")
