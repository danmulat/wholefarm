"""Source explicit soil nitrous oxide calculations for crop and pasture nitrogen.

Emission factors are supplied by the selected methodology or project data.
The module does not silently choose regional or IPCC default factors.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SoilNitrogenSource:
    name: str
    nitrogen_kg: float
    direct_ef_n2on_per_n: float
    volatilized_fraction: float = 0.0
    leached_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.nitrogen_kg < 0:
            raise ValueError("nitrogen_kg must be nonnegative")
        if self.direct_ef_n2on_per_n < 0:
            raise ValueError("direct emission factor must be nonnegative")
        if not 0.0 <= self.volatilized_fraction <= 1.0:
            raise ValueError("volatilized_fraction must be between zero and one")
        if not 0.0 <= self.leached_fraction <= 1.0:
            raise ValueError("leached_fraction must be between zero and one")


@dataclass(frozen=True)
class SoilN2OFactors:
    ef4_n2on_per_volatilized_n: float
    ef5_n2on_per_leached_n: float
    n2on_to_n2o: float = 44.0 / 28.0

    def __post_init__(self) -> None:
        if self.ef4_n2on_per_volatilized_n < 0:
            raise ValueError("EF4 must be nonnegative")
        if self.ef5_n2on_per_leached_n < 0:
            raise ValueError("EF5 must be nonnegative")
        if self.n2on_to_n2o <= 0:
            raise ValueError("N2O N conversion ratio must be positive")


@dataclass(frozen=True)
class SoilN2OResult:
    direct_n2o_kg: float
    volatilization_n2o_kg: float
    leaching_n2o_kg: float
    total_n2o_kg: float
    total_co2e_t: float
    nitrogen_applied_kg: float
    volatilized_n_kg: float
    leached_n_kg: float


def calculate_soil_n2o(
    sources: list[SoilNitrogenSource],
    factors: SoilN2OFactors,
    gwp_n2o: float = 273.0,
) -> SoilN2OResult:
    if not sources:
        raise ValueError("At least one nitrogen source is required")
    if gwp_n2o < 0:
        raise ValueError("gwp_n2o must be nonnegative")

    direct_n2on = sum(
        source.nitrogen_kg * source.direct_ef_n2on_per_n
        for source in sources
    )
    volatilized_n = sum(
        source.nitrogen_kg * source.volatilized_fraction
        for source in sources
    )
    leached_n = sum(
        source.nitrogen_kg * source.leached_fraction
        for source in sources
    )

    direct_n2o = direct_n2on * factors.n2on_to_n2o
    volatilization_n2o = (
        volatilized_n
        * factors.ef4_n2on_per_volatilized_n
        * factors.n2on_to_n2o
    )
    leaching_n2o = (
        leached_n
        * factors.ef5_n2on_per_leached_n
        * factors.n2on_to_n2o
    )
    total_n2o = direct_n2o + volatilization_n2o + leaching_n2o
    return SoilN2OResult(
        direct_n2o_kg=direct_n2o,
        volatilization_n2o_kg=volatilization_n2o,
        leaching_n2o_kg=leaching_n2o,
        total_n2o_kg=total_n2o,
        total_co2e_t=total_n2o / 1000.0 * gwp_n2o,
        nitrogen_applied_kg=sum(source.nitrogen_kg for source in sources),
        volatilized_n_kg=volatilized_n,
        leached_n_kg=leached_n,
    )
