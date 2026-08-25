import pytest
import math
from crrt_mind import (
    calc_cvvh_prescribed_dose,
    calc_replacement_fluid_rate,
    calc_pre_post_dilution,
    calc_cvvhd_clearance,
    calc_cvhdf_total_effluent,
    calc_crrt_ktv,
    calc_citrate_protocol,
    calc_heparin_protocol,
    calc_fluid_balance,
    prescribe_crrt,
    main,
)


# --- CVVH Prescribed Dose ---

def test_cvvh_dose_standard():
    """80kg patient, 48L effluent in 24h = 25 mL/kg/hr"""
    r = calc_cvvh_prescribed_dose(48000, 80, 24)
    assert r["prescribed_dose_ml_kg_hr"] == 25.0
    assert r["within_target"] is True


def test_cvvh_dose_low():
    """Below minimum target: 30000/(80*24) = 15.625"""
    r = calc_cvvh_prescribed_dose(30000, 80, 24)
    assert abs(r["prescribed_dose_ml_kg_hr"] - 15.63) < 0.02
    assert r["within_target"] is False


def test_cvvh_dose_high():
    """Excessive dose"""
    r = calc_cvvh_prescribed_dose(72000, 80, 24)
    assert r["prescribed_dose_ml_kg_hr"] == 37.5
    assert r["within_target"] is False


def test_cvvh_dose_boundary_20():
    """Exactly at lower boundary"""
    r = calc_cvvh_prescribed_dose(38400, 80, 24)
    assert r["prescribed_dose_ml_kg_hr"] == 20.0
    assert r["within_target"] is True


def test_cvvh_dose_invalid_weight():
    with pytest.raises(ValueError):
        calc_cvvh_prescribed_dose(48000, 0, 24)


# --- Replacement Fluid Rate ---

def test_replacement_rate():
    """25 mL/kg/hr × 80kg = 2000 mL/hr"""
    r = calc_replacement_fluid_rate(25, 80)
    assert r["replacement_rate_ml_hr"] == 2000.0
    assert r["total_volume_ml"] == 48000.0


def test_replacement_rate_custom_hours():
    r = calc_replacement_fluid_rate(30, 70, 12)
    assert r["replacement_rate_ml_hr"] == 2100.0
    assert r["total_volume_ml"] == 25200.0


# --- Pre/Post Dilution ---

def test_post_dilution_no_adjustment():
    r = calc_pre_post_dilution(2000, 12000, "post")
    assert r["adjustment_factor"] == 1.0
    assert r["effective_replacement_rate_ml_hr"] == 2000.0


def test_pre_dilution_reduces_effective():
    r = calc_pre_post_dilution(2000, 12000, "pre")
    assert r["adjustment_factor"] < 1.0
    assert r["effective_replacement_rate_ml_hr"] < 2000.0


def test_pre_dilution_factor():
    """Qb/(Qb+Qr) = 12000/14000 = 0.8571"""
    r = calc_pre_post_dilution(2000, 12000, "pre")
    expected = 12000 / (12000 + 2000)
    assert abs(r["adjustment_factor"] - expected) < 0.001


# --- CVVHD Clearance ---

def test_cvvhd_clearance():
    r = calc_cvvhd_clearance(2000, 600, 200, 24)
    assert r["mode"] == "CVVHD"
    assert r["clearance_ml_min"] > 0
    assert r["total_clearance_ml"] > 0


def test_cvvhd_clearance_zero_flow():
    r = calc_cvvhd_clearance(0, 600, 200, 24)
    assert r["clearance_ml_min"] == 0.0


def test_cvvhd_clearance_increases_with_qd():
    r1 = calc_cvvhd_clearance(1000, 600, 200, 24)
    r2 = calc_cvvhd_clearance(2000, 600, 200, 24)
    assert r2["clearance_ml_min"] > r1["clearance_ml_min"]


# --- CVVHDF ---

def test_cvhdf_total_effluent():
    r = calc_cvhdf_total_effluent(1000, 1000, 24)
    assert r["total_effluent_rate_ml_hr"] == 2000
    assert r["total_effluent_ml"] == 48000


def test_cvhdf_asymmetric():
    r = calc_cvhdf_total_effluent(1500, 500, 12)
    assert r["total_effluent_ml"] == 24000


# --- CRRT Kt/V ---

def test_crrt_ktv():
    """48L effluent, 80kg: Vd=48L, Kt/V=1.0"""
    r = calc_crrt_ktv(48000, 80, 24)
    assert r["daily_ktv"] == 1.0
    assert r["vd_liters"] == 48.0


def test_crrt_ktv_adequate():
    r = calc_crrt_ktv(48000, 70, 24)
    assert r["daily_ktv"] > 0.65
    assert r["adequate"] is True


def test_crrt_ktv_inadequate():
    r = calc_crrt_ktv(20000, 80, 24)
    assert r["adequate"] is False


# --- Citrate Protocol ---

def test_citrate_protocol():
    r = calc_citrate_protocol(150)
    assert r["citrate_infusion_ml_hr"] > 0
    assert r["calcium_replacement_mmol_hr"] > 0
    assert r["protocol"] == "Regional Citrate Anticoagulation (RCA)"


def test_citrate_protocol_higher_flow():
    r1 = calc_citrate_protocol(100)
    r2 = calc_citrate_protocol(200)
    assert r2["citrate_dose_mmol_hr"] > r1["citrate_dose_mmol_hr"]


# --- Heparin Protocol ---

def test_heparin_standard():
    r = calc_heparin_protocol(80, "standard")
    assert r["loading_dose_units"] == 4000
    assert r["maintenance_rate_units_hr"] == 800


def test_heparin_high_risk():
    r = calc_heparin_protocol(80, "high_risk")
    assert r["loading_dose_units"] == 2400
    assert r["maintenance_rate_units_hr"] == 400


# --- Fluid Balance ---

def test_fluid_balance_balanced():
    r = calc_fluid_balance(3000, 500, 2500, 24)
    assert r["net_balance_ml"] == 0
    assert r["status"] == "balanced"


def test_fluid_balance_positive():
    r = calc_fluid_balance(5000, 500, 2000, 24)
    assert r["net_balance_ml"] == 2500
    assert r["status"] == "positive_balance"


def test_fluid_balance_negative():
    r = calc_fluid_balance(1000, 500, 2000, 24)
    assert r["net_balance_ml"] == -1500
    assert r["status"] == "negative_balance"


# --- Full Prescription ---

def test_prescribe_cvvh():
    r = prescribe_crrt("CVVH", 80, 25, 200, "post", "citrate", 24)
    assert r["mode"] == "CVVH"
    assert r["prescribed_dose_ml_kg_hr"] == 25.0
    assert r["dose_adequate"] is True
    assert r["daily_ktv"] > 0


def test_prescribe_cvvhd():
    r = prescribe_crrt("CVVHD", 80, 25, 200, "post", "heparin", 24)
    assert r["mode"] == "CVVHD"
    assert "dialysate_flow_rate_ml_hr" in r


def test_prescribe_cvhdf():
    r = prescribe_crrt("CVVHDF", 80, 25, 200, "post", "none", 24)
    assert r["mode"] == "CVVHDF"
    assert "replacement_rate_ml_hr" in r
    assert "dialysate_flow_rate_ml_hr" in r


def test_prescribe_pre_dilution():
    r = prescribe_crrt("CVVH", 80, 25, 200, "pre", "none", 24)
    assert "pre-dilution" in r["dilution"]


# --- CLI ---

def test_cli_cvvh():
    assert main(["cvvh", "--effluent-ml", "48000", "--weight", "80"]) == 0


def test_cli_prescribe():
    assert main(["prescribe", "--mode", "CVVH", "--weight", "80"]) == 0


def test_cli_fluid():
    assert main(["fluid", "--intake-ml", "3000", "--output-ml", "500"]) == 0
