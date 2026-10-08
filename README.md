# CRRT Prescriber Agent

CRRT effluent-dose and fluid-balance calculations, an experimental Python audit framework, and a browser-based educational worksheet. The clinical calculations are **illustrative** and have not been established as validated medical devices or autonomous prescribing protocols.

## Browser worksheet

The static interface in [`web/index.html`](web/index.html) calculates:

- **Observed effluent dose** = collected effluent (mL) / [body weight (kg) × observation duration (h)]
- **Net fluid balance** = intake − non-CRRT output − net patient fluid removal by CRRT

It runs entirely in the browser, does not contact an API, and does not store input data. Example measurements are prefilled. The browser uses JavaScript; it does **not** run the Python engine or pretend to provide signed audits. GitHub Pages deployment is configured in `.github/workflows/pages.yml`.

The KDIGO 2012 reference interval of **20–25 mL/kg/h refers to delivered effluent in adults with AKI**, not a universal prescribed pump rate. Effluent does not directly prove solute clearance, and the worksheet does not account for circuit downtime, anticoagulation or clinical individualization.

## Python features

`crrt_mind.py` provides CVVH effluent calculations, replacement-flow estimation, predilution approximation, CVVHD illustrative clearance, CVVHDF flow aggregation, simplified Kt/V, citrate and heparin arithmetic, and fluid balance. Additional research-oriented modules implement synthetic-case audits and exploratory citrate/electrolyte/filter evaluation.

**Important limitations:** Citrate and heparin functions are arithmetic models, not patient-specific treatment instructions. Some formulas and thresholds are simplifications that require independent specialist verification before any clinical use. Never copy calculated anticoagulant rates into clinical orders without a locally approved protocol. Do not enter identifiable patient data.

## Installation and usage

Requires Python 3.10–3.12 for the tested CI configurations (package metadata permits Python 3.9+).

```bash
git clone https://github.com/abusuraihsakhri/crrt-prescriber-agent.git
cd crrt-prescriber-agent
python -m pip install -e ".[api,dev]"
python cli.py cvvh --effluent-ml 48000 --weight 80 --hours 24
python cli.py fluid --intake-ml 3000 --output-ml 500 --uf-ml 2500
python cli.py prescribe --mode CVVH --weight 80 --dose 25 --anticoag none
python crrt_prescriber_agent_app.py audit --case-id SYN-CASE-01
python -m pytest -q
```

To open the browser worksheet locally, open `web/index.html` in a modern browser. No server, dependencies or external assets are needed.

## Optional API and Docker

```bash
python crrt_prescriber_agent_app.py serve --host 127.0.0.1 --port 8000
# Alternative synthetic-task worker API:
uvicorn agents.api:app --host 127.0.0.1 --port 8000
```

Both expose `/health` and `/api/audit`, **but they use different request schemas and rule sets**. The `agents.api` service also exposes `/metrics` as JSON (not Prometheus exposition text). The APIs have no built-in authentication or production-grade patient-data controls; bind to localhost for evaluation and do not expose them publicly with real health data.

For Docker Compose, configure a high-entropy key before starting:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

The audit trail is held **in process memory only**. HMAC-SHA256 signatures and chaining detect modification of retained records when verified with the same key, but do not provide durable retention, external anchoring, complete PHI detection, or regulatory compliance. When no audit key is set for direct Python use, an ephemeral development key is generated with a warning. Never commit production secrets.

## Testing and deployment

GitHub Actions runs dependency installation, `pip check`, Python compilation and pytest against Python 3.10, 3.11 and 3.12. Regression tests cover core calculations, citrate units, predilution, invalid measurements, batch flags, HMAC verification, API requests and the static worksheet script. GitHub Pages publishes the `web/` directory after changes to `master`.

## Technology, privacy and license

- Python 3 with standard-library calculation routines; Pydantic and optional FastAPI/Uvicorn for the synthetic audit framework
- Standalone HTML, CSS and JavaScript for the browser worksheet; no Pyodide required
- Chromium, Firefox and Safari-compatible modern browser APIs; automated cross-browser testing is not included
- Browser calculations do not store or transmit input; server-side processing is separate and may retain synthetic case identifiers in process memory
- [MIT License](LICENSE)

Clinical reference: [KDIGO AKI guideline summary, Part 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4056805/). Use professional judgment, institutional protocols and independently validated calculations for patient care.
