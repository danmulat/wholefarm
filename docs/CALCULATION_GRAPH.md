# Calculation graph

## Purpose

The model keeps physical process calculations separate from reporting and methodology accounting.

## Core sequence

1. Farm survey, livestock, land management, energy and soil observations enter the input validation layer.

2. Livestock records are converted to the pinned GLEAM cohort inputs.

3. GLEAM returns production, enteric methane, manure methane, manure nitrous oxide, nitrogen excretion and volatile solids.

4. Nitrogen excretion and volatile solids enter the manure recovery module.

5. Recovered manure nitrogen and recorded mineral or organic nitrogen enter managed soil nitrogen calculations using explicit emission factors.

6. Recovered manure carbon, crop residue carbon and plant carbon enter RothC.

7. Measured soil observations enter fixed depth and equivalent soil mass SOC stock calculations.

8. Environmental and management covariates enter digital SOC feature engineering.

9. Categorical covariates are target encoded within grouped training folds.

10. Digital SOC uses grouped outer validation, grouped inner feature selection and tuning, Random Forest mean prediction and Quantile Regression Forest uncertainty prediction.

11. Data spiking tests target only, target plus compatible legacy data and target plus all legacy data while removing all training records that overlap held out spatial groups.

12. Final digital SOC fitting uses fold consensus for selected features, Random Forest parameters and scaling settings.

13. Block prediction produces SOC mean, Q05 and Q95 surfaces. Farm and basin uncertainty aggregation remains separate from simple surface summaries.

14. RothC and digital SOC are validated independently.

15. Research mode may evaluate RothC guided machine learning after independent validation.

16. Tree biomass carbon is calculated separately from soil carbon.

17. Farm accounting combines greenhouse gas sources, soil carbon change and tree carbon change. Crop only farms are supported.

18. CAP2ER Level 2 organizes farm indicators.

19. CARBON AGRI applies baseline and intervention project accounting in its own reporting mode.

20. Methodology mode guards prevent research hybrid SOC outputs from being labelled as methodology pathway outputs.

21. Run provenance records the model commit, methodology versions and input file hashes.

## Main feedback loop

Livestock → manure nitrogen and carbon → crops and soil → feed production → livestock.

## SOC separation rule

Digital SOC estimates spatial stock and uncertainty.

RothC estimates temporal stock response to management.

The hybrid branch is research mode until independent validation and methodology review are complete.
