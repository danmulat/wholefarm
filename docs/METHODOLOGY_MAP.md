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

RothC is the temporal SOC process model. The final hybrid design will compare RothC only, QRF only and RothC guided machine learning before selecting the operational SOC model.

## Soil depth

SOC quantification uses at least 30 cm. Shallower legacy observations may enter calibration or validation only when the model output represents at least 30 cm and the depth extrapolation method is documented.

## Current coding status

The repository currently contains the first VM0042 SOC stock functions, digital SOC feature engineering, first GLEAM compatible equations, whole farm scenario accounting and reference tests.

The next coding stage will add GLEAM herd demography, weights, energy requirements, feed intake, production allocation and feed emission aggregation. It will then connect manure carbon and nitrogen flows to crops and RothC.
