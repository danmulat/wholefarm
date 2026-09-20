"""CAP2ER Level 2 indicator structure from the supplied 2022 methodology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IndicatorStatus = Literal["computed", "not_computable", "not_applicable"]


@dataclass(frozen=True)
class IndicatorValue:
    name: str
    category: str
    value: float | str | None = None
    unit: str | None = None
    status: IndicatorStatus = "not_computable"
    source_note: str | None = None


LEVEL2_INDICATORS: tuple[tuple[str, str], ...] = (
    ("air_water_quality", "Ammonia emissions"),
    ("air_water_quality", "Leaching"),
    ("air_water_quality", "Eutrophication and acidification"),
    ("nitrogen", "Nitrogen balance"),
    ("nitrogen", "Nitrogen efficiency"),
    ("water", "Water consumption for irrigation"),
    ("biodiversity", "Areas of Ecological Interest"),
    ("biodiversity", "Crop diversity"),
    ("soil", "Soil cover"),
    ("soil", "Tillage intensity"),
    ("soil", "Legumes"),
    ("carbon_storage", "Carbon storage"),
    ("nutritional_performance", "Number of people fed"),
    ("autonomy", "Protein autonomy"),
    ("autonomy", "Dependence on mineral nitrogen"),
    ("economic", "EBITDA to gross product"),
    ("economic", "Income per manpower"),
    ("economic", "Unit production cost"),
    ("working_conditions", "Satisfaction level"),
    ("climate_change", "GHG emissions"),
    ("energy", "Fossil energy consumption"),
    ("energy", "Renewable energy production"),
    ("plant_protection", "Treatment Frequency Index"),
    ("plant_protection", "Untreated areas"),
)


def empty_level2_report() -> dict[str, IndicatorValue]:
    """Return every public Level 2 indicator without inventing missing calculations."""

    return {
        name: IndicatorValue(name=name, category=category)
        for category, name in LEVEL2_INDICATORS
    }


def merge_level2_results(
    computed: dict[str, IndicatorValue],
) -> dict[str, IndicatorValue]:
    report = empty_level2_report()
    unknown = set(computed).difference(report)
    if unknown:
        raise ValueError(f"Unknown CAP2ER Level 2 indicators: {sorted(unknown)}")
    report.update(computed)
    return report
