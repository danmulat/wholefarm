# wholefarm

Python whole farm greenhouse gas and soil organic carbon model for baseline and intervention analysis in mixed crop livestock and pasture systems.

The initial target areas are the Omo Ghibe River Basin in Ethiopia and the Kenyan part of the Lake Victoria Basin.

Current modules include:

1. VM0042 soil organic carbon stock calculations with a minimum 30 cm quantification depth.
2. Digital SOC Quantile Regression Forest foundations adapted from the Florida grazing SOC workflow.
3. RothC monthly carbon pool calculations pinned to the Rothamsted Python reference implementation.
4. A research mode RothC guided machine learning workflow that keeps measured and process simulated SOC records distinct during spatial validation.
5. FAO GLEAM compatible ration, enteric methane, nitrogen balance, manure, herd demography, animal weight, production, feed emission and selected energy equations.
6. Farm level aggregation of GLEAM cohort emissions, production, nitrogen excretion and volatile solids.
7. Explicit manure nitrogen and carbon recovery flows for connection to crop nutrient budgets and RothC carbon inputs.
8. Source explicit soil nitrous oxide accounting with direct, volatilization and leaching pathways.
9. Whole farm baseline and intervention accounting with SOC and tree carbon stock changes.
10. CAP2ER Level 2 indicator structures and selected public nitrogen equations.
11. CARBON AGRI project accounting equations kept separate from scientific process calculations.
12. Automated tests through GitHub Actions.

Feed emission factors may be incomplete in early farm datasets. The model marks that condition explicitly instead of treating missing factors as verified zero emissions.

The RothC guided machine learning module is research mode. It is not automatically a Verra methodology pathway. The operational model must first pass independent QRF, RothC and hybrid validation.

The model is under research development. Method specific reporting and carbon credit calculations must only be labelled compliant after the required methodology checks, validation and verification steps are implemented.

Development is occurring in pull request 1 on the feature/wholefarm_model branch.
