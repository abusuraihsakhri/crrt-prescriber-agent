# CRRT Prescriber Agent

> **Domain:** Nephrology & Renal Replacement Protocols  
> **Reference Guidelines & Standards:** `KDIGO & KDOQI Clinical Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**CRRT Prescriber Agent** is an advanced analytical and computational platform implementing Continuous Renal Replacement Effluent & Regional Citrate Manager.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`calc_cvvh_prescribed_dose()`**: Calculate prescribed CVVH dose in mL/kg/hr.

Args:
    effluent_volume_ml: Total effluent volume in mL over the time period
    body_weight_kg: Patient dry weight in kg
    time_hours: Duration in hours (default 24)

Returns:
    Dict with prescribed_dose_ml_kg_hr, within_target, recommendation
- **`calc_replacement_fluid_rate()`**: Calculate replacement fluid rate for CVVH.

Replacement fluid rate (mL/hr) = (Desired dose × Body weight × time) / time
                                = Desired dose × Body weight

Args:
    desired_dose_ml_kg_hr: Target dose in mL/kg/hr
    body_weight_kg: Patient weight in kg
    time_hours: Duration (not used in rate calc but included for context)

Returns:
    Dict with replacement_rate_ml_hr, total_volume_ml
- **`calc_pre_post_dilution()`**: Adjust replacement fluid for pre-dilution vs post-dilution mode.

Pre-dilution: Effective dose = Replacement rate × Qb / (Qb + Replacement rate)
Post-dilution: Effective dose = Replacement rate (no adjustment needed)

Sieving coefficient assumed = 1.0 for small solutes (urea, creatinine)

Args:
    replacement_rate_ml_hr: Replacement fluid rate in mL/hr
    blood_flow_rate_ml_hr: Blood flow rate in mL/hr (typically 150-250 mL/min × 60)
    mode: "pre" or "post"

Returns:
    Dict with effective_dose, dilution_mode, adjustment_factor
- **`calc_cvvhd_clearance()`**: Calculate CVVHD clearance using the KoA approach.

K = Qd × (1 - e^(-KoA × Qd / Qb))
where:
    K = clearance (mL/min)
    Qd = dialysate flow rate (mL/min)
    Qb = blood flow rate (mL/min)
    KoA = mass transfer area coefficient (default 600 for urea)

Args:
    dialysate_flow_rate_ml_hr: Dialysate flow in mL/hr
    koa: Mass transfer area coefficient (default 600 for urea)
    blood_flow_rate_ml_min: Blood flow in mL/min
    time_hours: Treatment duration in hours

Returns:
    Dict with clearance values
- **`calc_cvhdf_total_effluent()`**: Calculate total effluent volume for CVVHDF.

Total effluent = Replacement fluid volume + Dialysate volume

Args:
    replacement_rate_ml_hr: Replacement fluid rate in mL/hr
    dialysate_flow_rate_ml_hr: Dialysate flow rate in mL/hr
    time_hours: Duration in hours

Returns:
    Dict with total effluent and dose

---

## 📐 Mathematical Formulation & Logic

```text
  Calculate prescribed CVVH dose in mL/kg/hr.
  Calculate replacement fluid rate for CVVH.
  Calculate CVVHD clearance using the KoA approach.
  Clearance formula: K = Qd × (1 - e^(-KoA × Qd / Qb))
  Calculate total effluent volume for CVVHDF.
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --input data.csv
```

### Parameter Reference
- `--interactive`: Launch guided terminal interactive wizard.
- `--input <path>`: Evaluate input from JSON or CSV specification.
- `--json`: Output deterministic structured results in JSON format.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t crrt-prescriber-agent .
docker run -p 8000:8000 crrt-prescriber-agent
```
