from pathlib import Path

import pytest

from wholefarm.compliance import (
    load_compliance_modes,
    reporting_label,
    require_mode,
    validate_soc_branch_for_mode,
)

ROOT = Path(__file__).resolve().parents[1]


def test_compliance_modes_load_from_project_config() -> None:
    modes = load_compliance_modes(ROOT / "config" / "compliance_modes.yml")
    assert require_mode(modes, "research_hybrid_soc").is_research_only
    assert require_mode(modes, "verra_vt0014_dsm").is_methodology_pathway


def test_hybrid_soc_cannot_be_labelled_as_methodology_pathway() -> None:
    modes = load_compliance_modes(ROOT / "config" / "compliance_modes.yml")
    mode = require_mode(modes, "verra_vm0042_process")
    with pytest.raises(ValueError):
        validate_soc_branch_for_mode(mode, "hybrid")


def test_methodology_soc_branch_guards() -> None:
    modes = load_compliance_modes(ROOT / "config" / "compliance_modes.yml")
    process = require_mode(modes, "verra_vm0042_process")
    dsm = require_mode(modes, "verra_vt0014_dsm")

    validate_soc_branch_for_mode(process, "rothc")
    validate_soc_branch_for_mode(dsm, "qrf")

    with pytest.raises(ValueError):
        validate_soc_branch_for_mode(process, "qrf")
    with pytest.raises(ValueError):
        validate_soc_branch_for_mode(dsm, "rothc")


def test_reporting_label_preserves_research_status() -> None:
    modes = load_compliance_modes(ROOT / "config" / "compliance_modes.yml")
    assert reporting_label(require_mode(modes, "research_hybrid_soc")) == "research"