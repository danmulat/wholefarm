"""Methodology and research mode guards for model outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ComplianceMode:
    name: str
    status: str
    settings: dict[str, Any]

    @property
    def is_research_only(self) -> bool:
        return self.status in {"research", "research_only"}

    @property
    def is_methodology_pathway(self) -> bool:
        return self.status in {"methodology_pathway", "methodology_accounting"}


def load_compliance_modes(path: str | Path) -> dict[str, ComplianceMode]:
    source = Path(path)
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("modes"), dict):
        raise ValueError("Compliance configuration requires a modes mapping")

    result: dict[str, ComplianceMode] = {}
    for name, settings in data["modes"].items():
        if not isinstance(settings, dict):
            raise TypeError(f"Compliance mode must be a mapping: {name}")
        status = settings.get("status")
        if not isinstance(status, str) or not status:
            raise ValueError(f"Compliance mode requires a status: {name}")
        result[name] = ComplianceMode(
            name=name,
            status=status,
            settings=dict(settings),
        )
    return result


def require_mode(
    modes: dict[str, ComplianceMode],
    name: str,
) -> ComplianceMode:
    if name not in modes:
        raise KeyError(f"Unknown compliance mode: {name}")
    return modes[name]


def validate_soc_branch_for_mode(
    mode: ComplianceMode,
    soc_branch: str,
) -> None:
    """Prevent research SOC outputs from being presented as methodology outputs."""

    if soc_branch not in {"qrf", "rothc", "hybrid"}:
        raise ValueError("soc_branch must be qrf, rothc or hybrid")

    if soc_branch == "hybrid" and mode.is_methodology_pathway:
        raise ValueError(
            "Hybrid SOC is research mode and cannot be labelled as a methodology pathway"
        )

    expected_measurement = mode.settings.get("soc_measurement")
    expected_temporal = mode.settings.get("soc_temporal")

    if mode.name == "verra_vt0014_dsm" and soc_branch != expected_measurement:
        raise ValueError("VT0014 DSM mode requires the configured SOC measurement branch")

    if mode.name == "verra_vm0042_process" and soc_branch != expected_temporal:
        raise ValueError("VM0042 process mode requires the configured SOC temporal branch")


def reporting_label(mode: ComplianceMode) -> str:
    if mode.is_research_only:
        return "research"
    if mode.status == "methodology_accounting":
        return "methodology_accounting"
    if mode.status == "methodology_pathway":
        return "methodology_pathway"
    return mode.status
