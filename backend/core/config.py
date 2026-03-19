"""Configuration loader — reads YAML config files into dicts."""

from pathlib import Path

import yaml

CONFIG_DIR = Path("config")


def load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config() -> dict:
    """Load and merge all configuration files."""
    settings = load_yaml("settings.yaml")
    streams = load_yaml("streams.yaml")
    instruments = load_yaml("instruments.yaml")

    settings["streams"] = streams
    settings["instruments"] = instruments
    return settings


def load_instruments() -> dict:
    return load_yaml("instruments.yaml")


def load_streams() -> dict:
    return load_yaml("streams.yaml")
