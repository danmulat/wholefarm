# Methodology registry

This repository is the working implementation for the whole farm greenhouse gas and soil carbon model for Ethiopia and Kenya.

## Core references

CAP2ER Level 2 defines the whole farm indicator structure and reporting scales.

CARBON AGRI defines the baseline and intervention accounting logic and five year project structure.

FAO GLEAM X is the livestock process reference. The source reference is pinned to commit 90e416197e89093c4f3a347b263ba805d33d4aac.

Verra VM0042 version 2.2 defines the improved agricultural land management accounting context.

VMD0053 version 2.1 is used for process model calibration, validation and uncertainty.

VT0014 version 1.0 is used for digital soil mapping alignment.

The Florida grazing SOC QRF repository is the digital SOC Python workflow reference. The environmental data are not transferred from Florida. Ethiopia and Kenya use local soil observations and regional environmental covariates.

RothC is the temporal SOC process model. The scientific workflow compares RothC only, QRF only and RothC guided machine learning before any hybrid model is considered operational.

## Soil depth

SOC quantification uses at least 30 cm. Shallower legacy observations may enter calibration or validation only when the model output represents at least 30 cm and the depth extrapolation method is documented.

## Livestock and manure loop

GLEAM cohort calculations are aggregated to the farm before global warming potential conversion. Raw enteric methane, manure methane, manure nitrous oxide, nitrogen excretion and volatile solids remain available for audit.

Manure recovery is a physical mass balance layer. Collection, nitrogen retention, field application, volatile solids recovery and carbon fraction are explicit scenario inputs. These flows can supply crop nitrogen and RothC farmyard manure carbon without hard coded recovery efficiencies.

## Soil greenhouse gases

The soil nitrous oxide module uses explicit nitrogen sources. Each source carries its own direct emission factor, volatilization fraction and leaching fraction. Indirect emission factors are also explicit. This keeps methodology specific factors outside the generic process code.

## SOC model separation

The QRF branch is the digital measurement and mapping branch.

The RothC branch is the temporal process branch.

The hybrid branch is research mode. It may add RothC simulated samples with a lower training weight, but held out spatial groups are removed from both measured and process training data during validation. Hybrid performance is evaluated only against held out measured SOC.

## Current coding status

Implemented components now include SOC stock and depth checks, QRF feature engineering and model training, RothC monthly pools, RothC guided machine learning validation, GLEAM cohort and farm aggregation, manure nutrient routing, source explicit soil nitrous oxide, whole farm scenario accounting, CAP2ER nitrogen indicators and CARBON AGRI accounting.

The next coding stage will connect RothC monthly scenarios directly to recovered manure and crop residue carbon inputs, add tree carbon calculations, add digital SOC prediction table and raster output utilities, and build the first end to end baseline versus intervention example for an East African mixed crop livestock farm.
