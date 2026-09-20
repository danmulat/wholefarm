# wholefarm

Python whole farm greenhouse gas and soil organic carbon model for baseline and intervention analysis in mixed crop livestock and pasture systems.

The initial target areas are the Omo Ghibe River Basin in Ethiopia and the Kenyan part of the Lake Victoria Basin.

Current modules include:

1. VM0042 soil organic carbon stock calculations with a minimum 30 cm quantification depth.
2. Digital SOC Quantile Regression Forest foundations adapted from the Florida grazing SOC workflow.
3. RothC monthly carbon pool calculations pinned to the Rothamsted Python reference implementation.
4. FAO GLEAM compatible ration, enteric methane, nitrogen balance, manure, herd demography, animal weight, production, feed emission and selected energy equations.
5. Whole farm baseline and intervention accounting structures.
6. Automated tests through GitHub Actions.

The model is under research development. Method specific reporting and carbon credit calculations must only be labelled compliant after the required methodology checks, validation and verification steps are implemented.

Development is occurring in pull request 1 on the feature/wholefarm_model branch.
