# CRRT Prescriber Agent

> **Domain:** Nephrology & Renal Replacement Protocols
> **Reference Guidelines & Standards:** `KDIGO & KDOQI Clinical Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**CRRT Prescriber Agent** is an advanced analytical and computational platform implementing Continuous Renal Replacement Effluent & Regional Citrate Manager. It provides clinical decision support for CRRT dosing, anticoagulation protocols, and fluid balance management.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Calculation Engine (`crrt_mind.py`)

- **`calc_cvvh_prescribed_dose()`**: Calculate prescribed CVVH dose in mL/kg/hr
- **`calc_replacement_fluid_rate()`**: Calculate replacement fluid rate for CVVH
- **`calc_pre_post_dilution()`**: Adjust replacement fluid for pre-dilution vs post-dilution mode
- **`calc_cvvhd_clearance()`**: Calculate CVVHD clearance using the KoA approach
- **`calc_cvhdf_total_effluent()`**: Calculate total effluent volume for CVVHDF
- **`calc_crrt_ktv()`**: Calculate Kt/V dose adequacy metric
- **`calc_citrate_protocol()`**: Regional citrate anticoagulation protocol
- **`calc_heparin_protocol()`**: Systemic heparin anticoagulation protocol
- **`calc_fluid_balance()`**: Net fluid balance calculation
- **`prescribe_crrt()`**: Generate comprehensive CRRT prescription

### 🤖 Multi-Agent System (`crrt_prescriber_agent/`)

- **EffluentDoseCalculatorAgent**: Primary metric & baseline quality auditor
- **RegionalCitrateManagerAgent**: STAT kinetics & closed-loop escalation auditor
- **FilterTransmembranePressureAgent**: Biomarker & concordance triager
- **CRRTCoordinator**: Executive coordinator & air-gapped supervisory interface

### 🛡️ Enterprise Security (`agents/base.py`)

- **Zero-PHI Outbound Guard**: AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs for every evaluation
- **Path Traversal Protection**: Input validation for file operations

### 📊 Telemetry & Monitoring (`agents/metrics.py`)

- Prometheus-compatible metrics export
- Task processing latency tracking
- Alert tier counters (ROUTINE, ELEVATED, CRITICAL_STAT)

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/crrt-prescriber-agent.git
cd crrt-prescriber-agent

# Install dependencies (stdlib-only core, optional for full features)
pip install -e .

# For FastAPI server support:
pip install fastapi uvicorn

# For Pydantic models (agents module):
pip install pydantic
```

---

## 💻 CLI Quickstart & Usage

### Core Calculator (stdlib-only)
```bash
# CVVH dose calculation
python cli.py cvvh --effluent-ml 48000 --weight 80 --hours 24

# Replacement fluid rate
python cli.py replacement --dose 25 --weight 80

# CVVHD clearance
python cli.py cvvhd --dialysate-ml-hr 2000 --blood-flow-ml-min 200

# Full prescription
python cli.py prescribe --mode CVVH --weight 80 --dose 25 --anticoag citrate

# Citrate protocol
python cli.py citrate --blood-flow-ml-min 150

# Heparin protocol
python cli.py heparin --weight 80 --indication standard

# Fluid balance
python cli.py fluid --intake-ml 3000 --output-ml 500 --uf-ml 2500
```

### Multi-Agent System
```bash
# Run clinical audit
python crrt_prescriber_agent_app.py audit --case-id CASE-001 --primary 26.2 --secondary 12.5

# Batch process CSV
python crrt_prescriber_agent_app.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python crrt_prescriber_agent_app.py verify-audit

# Launch FastAPI server
python crrt_prescriber_agent_app.py serve --host 127.0.0.1 --port 8000
```

---

## 🧪 Testing & Verification

```bash
# Run all tests
pytest -v

# Run specific test modules
pytest test_crrt_mind.py -v
pytest tests/ -v
```

### Test Coverage
- **32 tests** for core calculation engine (`test_crrt_mind.py`)
- **3 tests** for multi-agent system (`tests/test_crrt_prescriber_agent.py`)
- **2 tests** for enrichment modules (`tests/test_enrichment.py`)

---

## 🐳 Container Deployment

```bash
docker build -t crrt-prescriber-agent .
docker run -p 8000:8000 crrt-prescriber-agent
```

---

## 🔒 Security Configuration

Set the audit secret key in production:

```bash
export AUDIT_SECRET_KEY="your-secure-random-key-here"
```

**Note:** Without `AUDIT_SECRET_KEY` set, a development-only fallback key is used with a runtime warning.

---

## 📐 Mathematical Formulation

```
CVVH Dose (mL/kg/hr) = Effluent Volume (mL) / (Body Weight (kg) × Time (hr))
CVVHD Clearance: K = Qd × (1 - e^(-KoA × Qd / Qb))
Pre-dilution: Effective = Replacement × Qb / (Qb + Replacement)
Kt/V = Effluent Volume (L) / Total Body Water (L)
```

---

## 📁 Project Structure

```
crrt-prescriber-agent/
├── crrt_mind.py                    # Core calculation engine (stdlib-only)
├── cli.py                          # CLI entry point for core calculator
├── crrt_prescriber_agent_app.py    # Multi-agent system entry point
├── crrt_prescriber_agent/          # Multi-agent package
│   ├── agents.py                   # Agent implementations
│   ├── cli.py                      # CLI with audit/batch/serve commands
│   ├── engine.py                   # Clinical domain engine
│   ├── models.py                   # Data models
│   └── server.py                   # FastAPI application factory
├── agents/                         # Enterprise security & workers
│   ├── base.py                     # PHI guard, HMAC audit trail
│   ├── models.py                   # Pydantic schemas
│   ├── workers.py                  # Specialized domain workers
│   ├── supervisor.py               # Supervisor orchestrator
│   ├── api.py                      # FastAPI REST endpoints
│   ├── metrics.py                  # Prometheus metrics
│   ├── learning.py                 # Bayesian calibration engine
│   ├── llm_factory.py              # LLM provider factory
│   └── streamer.py                 # WebSocket telemetry
├── enrichment.py                   # Feature enrichment modules
├── test_crrt_mind.py               # Core engine tests
├── tests/                          # Additional test suites
├── simulator.py                    # High-throughput stress testing
├── Dockerfile / docker-compose.yml # Container config
└── pyproject.toml                  # Project metadata
```

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
* **Path Traversal Protection:** Input validation for file operations in batch processing
* **Configurable Audit Key:** Environment variable `AUDIT_SECRET_KEY` for production deployments
* **FastAPI & Prometheus Telemetry:** REST endpoints and operational metrics (`/metrics`)
