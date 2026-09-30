"""Load user defaults from a YAML config file."""

import os
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Config keys and the CLI options they provide defaults for, per command
CONFIG_OPTIONS = {
    "output_dir": {"transcribe": "output_dir", "summarize": "output_dir"},
    "openai_model": {"summarize": "openai_model", "report": "openai_model"},
    "whisper_model": {"transcribe": "model", "summarize": "model"},
    "device": {"transcribe": "device", "summarize": "device"},
}


def default_config_path() -> Path:
    """Return the config file path, honouring YTT_CONFIG and XDG_CONFIG_HOME.

    Returns:
        Path to config.yml (may not exist)
    """
    if env_path := os.getenv("YTT_CONFIG"):
        return Path(env_path).expanduser()
    config_home = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "yt-transcribe" / "config.yml"


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the config file.

    Args:
        path: Path to config.yml

    Returns:
        Dict of recognised settings (empty if the file doesn't exist)

    Raises:
        ValueError: If the file isn't valid YAML or isn't a mapping
    """
    if not path.exists():
        logger.debug(f"No config file at {path}")
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain key: value pairs")

    config = {}
    for key, value in data.items():
        if key not in CONFIG_OPTIONS:
            logger.warning(f"Ignoring unknown config key '{key}' in {path}")
            continue
        if value is None:
            continue
        config[key] = Path(str(value)).expanduser() if key == "output_dir" else str(value)

    logger.debug(f"Loaded config from {path}: {config}")
    return config


def build_default_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Translate config settings into a Click default_map.

    Args:
        config: Settings returned by load_config

    Returns:
        Mapping of command name to {option name: default value}
    """
    default_map: dict[str, dict[str, Any]] = {}
    for key, value in config.items():
        for command, option in CONFIG_OPTIONS[key].items():
            default_map.setdefault(command, {})[option] = value
    return default_map
