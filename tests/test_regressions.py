"""Regressions for unit conversion, input handling, audit authenticity and web UI."""
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from agents.base import AuditTrail
from crrt_mind import (
    calc_cvvh_prescribed_dose,
    calc_cvhdf_total_effluent,
    calc_citrate_protocol,
    calc_crrt_ktv,
    calc_fluid_balance,
    calc_replacement_fluid_rate,
    prescribe_crrt,
)


def test_citrate_solution_conversion_is_liters_to_milliliters():
    # 150 mL/min blood = 9 L/h; 3 mmol/L blood => 27 mmol/h.
    # 27 mmol/h / 18 mmol/L solution = 1.5 L/h = 1500 mL/h.
    result = calc_citrate_protocol(150, citrate_concentration_mmol_l=18)
    assert result["citrate_dose_mmol_hr"] == 27.0
    assert result["citrate_infusion_ml_hr"] == 1500.0


def test_high_observed_dose_not_marked_inside_reference_range():
    result = calc_cvvh_prescribed_dose(30 * 80 * 24, 80, 24)
    assert result["prescribed_dose_ml_kg_hr"] == 30.0
    assert result["within_target"] is False


def test_predilution_compensation_solves_for_target_effective_rate():
    result = prescribe_crrt("CVVH", 80, desired_dose_ml_kg_hr=25,
                           blood_flow_rate_ml_min=200, dilution="pre", anticoagulation="none")
    nominal_rate = result["replacement_rate_ml_hr"]
    qb_ml_hr = 200 * 60
    effective_rate = nominal_rate * qb_ml_hr / (qb_ml_hr + nominal_rate)
    assert effective_rate / 80 == pytest.approx(25, abs=0.002)
    assert result["estimated_effective_dose_ml_kg_hr"] == pytest.approx(25, abs=0.02)
    assert result["dose_adequate"] is True


@pytest.mark.parametrize("action", [
    lambda: calc_cvvh_prescribed_dose(48000, float("nan"), 24),
    lambda: calc_cvvh_prescribed_dose(48000, 80, float("inf")),
    lambda: calc_replacement_fluid_rate(20, 80, 0),
    lambda: calc_cvhdf_total_effluent(1000, 1000, -1),
    lambda: calc_crrt_ktv(48000, 80, 0),
    lambda: calc_citrate_protocol(150, citrate_concentration_mmol_l=float("inf")),
    lambda: calc_fluid_balance(-100, 50, 0),
    lambda: prescribe_crrt("CVVH", 80, anticoagulation="unknown"),
    lambda: prescribe_crrt("CVVH", 80, dilution="invalid"),
    lambda: prescribe_crrt("CVVH", 80, desired_dose_ml_kg_hr=float("nan")),
    lambda: prescribe_crrt("CVVH", 80, desired_dose_ml_kg_hr=160, dilution="pre"),
])
def test_invalid_inputs_rejected(action):
    with pytest.raises(ValueError):
        action()


def test_hmac_validates_contents_not_only_chain_pointers():
    trail = AuditTrail(secret_key="test-key")
    trail.log("worker", "system", "event", {"value": 1})
    trail.log("worker", "system", "event", {"value": 2})
    assert trail.verify_integrity() is True

    # The public read API must not allow editing the underlying audit records.
    exported = trail.get_trail()
    exported[0]["actor"] = "tampered"
    assert trail.verify_integrity() is True

    trail.logs[0]["actor"] = "tampered"
    assert trail.verify_integrity() is False


def test_server_accepts_valid_audit_requests():
    from fastapi.testclient import TestClient
    from crrt_prescriber_agent.server import create_app

    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    response = client.post("/api/audit", json={
        "case_id": "SYNTH-CASE-01",
        "patient_synthetic_id": "SYNTH-01",
        "primary_metric": 22.0,
        "secondary_metric": 5.0,
        "status_flag": "NORMAL",
        "is_stat": False,
    })
    assert response.status_code == 200
    assert response.json()["total_alerts"] == 1


def test_pages_uses_real_arithmetic_and_valid_javascript():
    html = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert 'effluent / (weight * hours)' in html
    assert 'fetch(' not in html and 'Math.random' not in html
    assert 'HMAC_SHA256_' not in html and 'Air-Gapped Active' not in html
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    node = shutil.which("node")
    if node:
        proc = subprocess.run([node, "--check"], input=script, text=True, capture_output=True)
        assert proc.returncode == 0, proc.stderr


def test_batch_csv_boolean_strings_and_tsv(tmp_path):
    import csv
    from crrt_prescriber_agent.cli import main, parse_batch_boolean

    assert parse_batch_boolean("False") is False
    assert parse_batch_boolean("YES") is True
    with pytest.raises(ValueError):
        parse_batch_boolean("sometimes")
    source = tmp_path / "cases.tsv"
    destination = tmp_path / "result.csv"
    source.write_text(
        "case_id\tpatient_synthetic_id\tmetric_primary\tmetric_secondary\tstatus_flag\tis_stat\n"
        "SYN-1\tSYN-PT-1\t15\t5\tNORMAL\tfalse\n"
        "SYN-2\tSYN-PT-2\t15\t5\tNORMAL\ttrue\n",
        encoding="utf-8",
    )
    assert main(["batch", "--input", str(source), "--output", str(destination)]) == 0
    with destination.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["stat_critical_alerts"] == "0"
    assert rows[1]["stat_critical_alerts"] == "1"
