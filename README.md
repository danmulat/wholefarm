# wholefarm

Python whole farm greenhouse gas and soil organic carbon model for baseline and intervention analysis in mixed crop livestock and pasture systems.

The initial target areas are the Omo Ghibe River Basin in Ethiopia and the Kenyan part of the Lake Victoria Basin.

Current modules include:

1. Measured SOC stock calculations at a minimum 30 cm quantification depth, with equivalent soil mass support for repeated profiles.
2. Digital SOC feature engineering, group aware categorical encoding, nested spatial validation, Random Forest mean prediction, Quantile Regression Forest uncertainty, fold consensus final fitting, block raster prediction and domain compatible data spiking.
3. RothC monthly carbon pool calculations pinned to the Rothamsted Python reference implementation.
4. A research mode RothC guided machine learning workflow that keeps measured and process simulated SOC records distinct during spatial validation.
5. FAO GLEAM compatible ration, enteric methane, nitrogen balance, manure, herd demography, animal weight, production, feed emission, energy, allocation and aggregation equations pinned to the requested source commit.
6. Farm level aggregation of GLEAM cohort emissions, production, nitrogen excretion and volatile solids.
7. Explicit manure nitrogen and carbon recovery flows for connection to crop nutrient budgets and RothC carbon inputs.
8. Source explicit soil nitrous oxide accounting with direct, volatilization and leaching pathways.
9. Validated farm survey schemas for soil, land management, livestock, ration, manure management and farm energy records.
10. Farm management aggregation, measured SOC profile adapters and explicit energy emissions with missing factor flags.
11. Whole farm baseline and intervention accounting for farms with or without livestock, including SOC and tree carbon stock changes.
12. CAP2ER Level 2 indicator structures and selected public nitrogen equations.
13. CARBON AGRI project accounting kept separate from scientific process calculations.
14. Methodology mode guards and run provenance records for MRV traceability.
15. Automated tests, a pinned GLEAM function coverage check and a synthetic whole farm integration example.

Feed and energy emission factors may be incomplete in early farm datasets. The model marks that condition explicitly instead of treating missing factors as verified zero emissions.

The RothC guided machine learning module is research mode. It is not automatically a Verra methodology pathway. The operational model must first pass independent QRF, RothC and hybrid validation.

The model is under research development. Method specific reporting and carbon credit calculations must only be labelled compliant after the required methodology checks, validation and verification steps are implemented.

Development is occurring in pull request 1 on the feature/wholefarm_model branch.
