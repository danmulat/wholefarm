from pathlib import Path

import pytest
import yaml

from wholefarm.registry import load_data_source_registry, load_variable_registry


ROOT = Path(__file__).resolve().parents[1]


def test_project_variable_registry_is_valid() -> None:
    registry = load_variable_registry(ROOT / "config" / "variables.yml")
    assert registry.version == 1
    assert registry.require("soc_g_kg")["role"] == "measured_soc_concentration"
    assert registry.require("enteric_ch4_kg")["unit"] == "kg_CH4"


def test_east_africa_data_source_registry_is_valid() -> None:
    registry = load_data_source_registry(
        ROOT / "config" / "data_sources_east_africa.yml"
    )
    assert registry.require("local_soc_measurements")["operational_priority"] == "required"
    assert registry.require("isda_soil")["truth_status"] == "not_primary_lab_truth"


def test_registry_validation_rejects_missing_fields(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text(
        yaml.safe_dump({"version": 1, "variables": {"x": {"unit": "kg"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_variable_registry(path)
