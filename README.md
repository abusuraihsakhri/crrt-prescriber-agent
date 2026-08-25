# CRRT Prescriber Calculator

> **Nephrology / ICU** — Continuous Renal Replacement Therapy Dosing & Anticoagulation

## Overview

Real clinical calculator for CRRT prescription including CVVH, CVVHD, and CVVHDF modes with dose adequacy assessment, regional citrate and heparin anticoagulation protocols, and fluid balance calculations.

**References:** KDIGO 2012 AKI Guidelines, ADQI Consensus

## Formulas Implemented

| Calculator | Formula |
|:-----------|:--------|
| **CVVH Dose** | Prescribed dose = Effluent volume / (Weight × Time) |
| **Replacement Rate** | Rate (mL/hr) = Desired dose × Body weight |
| **Pre/Post Dilution** | Pre-dilution adjustment: Qb / (Qb + Qr) |
| **CVVHD Clearance** | K = Qd × (1 - e^(-KoA × Qd / Qb)) |
| **CVVHDF Effluent** | Total = Replacement rate + Dialysate rate |
| **CRRT Kt/V** | Kt/V = Effluent (L) / (0.6 × Weight) |
| **Citrate Protocol** | Citrate dose = Qb × 3.0 mmol/hr, Ca replacement |
| **Heparin Protocol** | Load 30-50 U/kg, maintain 5-10 U/kg/hr |
| **Fluid Balance** | Net = Intake - Output - UF |

## CLI Usage

```bash
# CVVH prescribed dose
python crrt_mind.py cvvh --effluent-ml 48000 --weight 80

# Replacement fluid rate
python crrt_mind.py replacement --dose 25 --weight 80

# CVVHD clearance
python crrt_mind.py cvvhd --dialysate-ml-hr 2000

# CVVHDF total effluent
python crrt_mind.py cvvhdf --replacement-ml-hr 1000 --dialysate-ml-hr 1000

# CRRT Kt/V
python crrt_mind.py ktv --effluent-ml 48000 --weight 80

# Citrate anticoagulation protocol
python crrt_mind.py citrate --blood-flow-ml-min 150

# Heparin protocol
python crrt_mind.py heparin --weight 80

# Fluid balance
python crrt_mind.py fluid --intake-ml 3000 --output-ml 500 --uf-ml 2000

# Full CRRT prescription
python crrt_mind.py prescribe --mode CVVH --weight 80 --dose 25 --anticoag citrate
```

## Python API

```python
from crrt_mind import (calc_cvvh_prescribed_dose, calc_cvvhd_clearance,
                        calc_cvhdf_total_effluent, calc_crrt_ktv,
                        calc_citrate_protocol, prescribe_crrt)

# CVVH dose check
result = calc_cvvh_prescribed_dose(effluent_volume_ml=48000, body_weight_kg=80)
print(result["prescribed_dose_ml_kg_hr"])  # 25.0
print(result["within_target"])  # True

# Full prescription
rx = prescribe_crrt(mode="CVVH", body_weight_kg=80, desired_dose_ml_kg_hr=25)
```

## Dose Targets (KDIGO)

| Parameter | Target |
|:----------|:-------|
| Effluent dose | 20-25 mL/kg/hr |
| CRRT Kt/V (daily) | ≥ 0.65 |
| Post-filter iCa (citrate) | 0.25-0.40 mmol/L |
| Systemic iCa (citrate) | 1.0-1.2 mmol/L |

## License

MIT License.
