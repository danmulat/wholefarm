# Calculation graph

## Purpose

The model keeps physical process calculations separate from reporting and methodology accounting.

## Core sequence

1. Farm survey and soil observations enter the input validation layer.

2. Livestock records enter the GLEAM cohort chain.

3. GLEAM returns production, enteric methane, manure methane, manure nitrous oxide, nitrogen excretion and volatile solids.

4. Nitrogen excretion and volatile solids enter the manure recovery module.

5. Recovered manure nitrogen enters the crop and managed soil nitrogen calculation.

6. Recovered manure carbon enters RothC together with crop residue and plant carbon inputs.

7. Measured soil observations enter the digital SOC branch.

8. Environmental and management covariates enter feature engineering, spatial validation, Random Forest mean prediction and Quantile Regression Forest uncertainty prediction.

9. RothC and digital SOC are validated independently.

10. Research mode may evaluate RothC guided machine learning after independent validation.

11. Tree biomass carbon is calculated separately from soil carbon.

12. Farm accounting combines raw greenhouse gas sources, soil carbon change and tree carbon change.

13. CAP2ER Level 2 organizes farm indicators.

14. CARBON AGRI applies baseline and intervention project accounting in its own reporting mode.

15. Verra reporting modes expose only outputs allowed by the selected methodology pathway.

## Main feedback loop

Livestock → manure nitrogen and carbon → crops and soil → feed production → livestock.

## SOC separation rule

Digital SOC estimates spatial stock and uncertainty.

RothC estimates temporal stock response to management.

The hybrid branch is research mode until independent validation and methodology review are complete.
