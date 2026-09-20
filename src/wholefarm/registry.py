"""YAML registries for variables, data sources and methodology metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Registry:
    version: int
    entries: dict[str, dict[str, Any]]

    def require(self, name: str) -> dict[str, Any]:
        if name not in self.entries:
            raise KeyError(f"Registry entry not found: {name}")
        return self.entries[name]


def _load_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    with source.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError("Registry YAML root must be a mapping")
    return data


def load_variable_registry(path: str | Path) -> Registry:
    data = _load_yaml(path)
    if "version" not in data or "variables" not in data:
        raise ValueError("Variable registry requires version and variables")
    entries = data["variables"]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Variable registry must contain variable entries")
    for name, item in entries.items():
        if not isinstance(item, dict):
            raise TypeError(f"Variable entry must be a mapping: {name}")
        required = {"module", "unit", "scale", "required", "role"}
        missing = required.difference(item)
        if missing:
            raise ValueError(f"Variable {name} is missing fields: {sorted(missing)}")
    return Registry(version=int(data["version"]), entries=entries)


def load_data_source_registry(path: str | Path) -> Registry:
    data = _load_yaml(path)
    if "version" not in data or "sources" not in data:
        raise ValueError("Data source registry requires version and sources")
    entries = data["sources"]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Data source registry must contain source entries")
    for name, item in entries.items():
        if not isinstance(item, dict):
            raise TypeError(f"Data source entry must be a mapping: {name}")
        required = {
            "category",
            "geography",
            "role",
            "operational_priority",
            "verification_status",
        }
        missing = required.difference(item)
        if missing:
            raise ValueError(f"Data source {name} is missing fields: {sorted(missing)}")
    return Registry(version=int(data["version"]), entries=entries)