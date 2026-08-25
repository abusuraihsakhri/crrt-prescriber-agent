#!/usr/bin/env python3
"""
CRRT Prescriber: Continuous Renal Replacement Therapy Calculator

Real implementations for:
- CVVH (Continuous Venovenous Hemofiltration) dose calculation
- CVVHD (Continuous Venovenous Hemodialysis) clearance
- CVVHDF (Combined) total effluent
- Dose adequacy (Kt/V for CRRT)
- Anticoagulation: Citrate (regional) and Heparin protocols
- Fluid balance calculation

References: KDIGO 2012 AKI Guidelines, ADQI consensus
Stdlib only.
"""

import argparse
import json
import math
import sys
from typing import Dict, Any, Optional


# ---------------------------------------------------------------------------
# CVVH - Continuous Venovenous Hemofiltration
# ---------------------------------------------------------------------------

def calc_cvvh_prescribed_dose(effluent_volume_ml: float, body_weight_kg: float,
                               time_hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate prescribed CVVH dose in mL/kg/hr.

    Args:
        effluent_volume_ml: Total effluent volume in mL over the time period
        body_weight_kg: Patient dry weight in kg
        time_hours: Duration in hours (default 24)

    Returns:
        Dict with prescribed_dose_ml_kg_hr, within_target, recommendation
    """
    if body_weight_kg <= 0:
        raise ValueError("Body weight must be positive")
    if time_hours <= 0:
        raise ValueError("Time must be positive")
    if effluent_volume_ml < 0:
        raise ValueError("Effluent volume cannot be negative")

    dose = effluent_volume_ml / (body_weight_kg * time_hours)

    if dose < 20:
        within_target = False
        recommendation = "Below KDIGO minimum (20 mL/kg/hr). Increase effluent volume."
    elif dose <= 25:
        within_target = True
        recommendation = "Within acceptable range (20-25 mL/kg/hr per KDIGO)."
    elif dose <= 35:
        within_target = True
        recommendation = "Higher dose range (25-35 mL/kg/hr). Monitor for nutrient losses."
    else:
        within_target = False
        recommendation = "Excessive dose (>35 mL/kg/hr). Risk of electrolyte wasting and drug removal."

    return {
        "mode": "CVVH",
        "prescribed_dose_ml_kg_hr": round(dose, 2),
        "effluent_volume_ml": effluent_volume_ml,
        "body_weight_kg": body_weight_kg,
        "time_hours": time_hours,
        "target_range": "20-25 mL/kg/hr (KDIGO)",
        "within_target": within_target,
        "recommendation": recommendation,
    }


def calc_replacement_fluid_rate(desired_dose_ml_kg_hr: float, body_weight_kg: float,
                                 time_hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate replacement fluid rate for CVVH.

    Replacement fluid rate (mL/hr) = (Desired dose × Body weight × time) / time
                                    = Desired dose × Body weight

    Args:
        desired_dose_ml_kg_hr: Target dose in mL/kg/hr
        body_weight_kg: Patient weight in kg
        time_hours: Duration (not used in rate calc but included for context)

    Returns:
        Dict with replacement_rate_ml_hr, total_volume_ml
    """
    if desired_dose_ml_kg_hr <= 0:
        raise ValueError("Desired dose must be positive")
    if body_weight_kg <= 0:
        raise ValueError("Body weight must be positive")

    rate = desired_dose_ml_kg_hr * body_weight_kg
    total = rate * time_hours

    return {
        "replacement_rate_ml_hr": round(rate, 1),
        "total_volume_ml": round(total, 1),
        "desired_dose_ml_kg_hr": desired_dose_ml_kg_hr,
        "body_weight_kg": body_weight_kg,
        "time_hours": time_hours,
    }


def calc_pre_post_dilution(replacement_rate_ml_hr: float, blood_flow_rate_ml_hr: float,
                            mode: str = "post") -> Dict[str, Any]:
    """
    Adjust replacement fluid for pre-dilution vs post-dilution mode.

    Pre-dilution: Effective dose = Replacement rate × Qb / (Qb + Replacement rate)
    Post-dilution: Effective dose = Replacement rate (no adjustment needed)

    Sieving coefficient assumed = 1.0 for small solutes (urea, creatinine)

    Args:
        replacement_rate_ml_hr: Replacement fluid rate in mL/hr
        blood_flow_rate_ml_hr: Blood flow rate in mL/hr (typically 150-250 mL/min × 60)
        mode: "pre" or "post"

    Returns:
        Dict with effective_dose, dilution_mode, adjustment_factor
    """
    if replacement_rate_ml_hr < 0:
        raise ValueError("Replacement rate cannot be negative")
    if blood_flow_rate_ml_hr <= 0:
        raise ValueError("Blood flow rate must be positive")

    if mode == "pre":
        # Pre-dilution reduces effective concentration
        adjustment_factor = blood_flow_rate_ml_hr / (blood_flow_rate_ml_hr + replacement_rate_ml_hr)
        effective_rate = replacement_rate_ml_hr * adjustment_factor
    elif mode == "post":
        adjustment_factor = 1.0
        effective_rate = replacement_rate_ml_hr
    else:
        raise ValueError("Mode must be 'pre' or 'post'")

    return {
        "dilution_mode": mode,
        "replacement_rate_ml_hr": replacement_rate_ml_hr,
        "blood_flow_rate_ml_hr": blood_flow_rate_ml_hr,
        "adjustment_factor": round(adjustment_factor, 4),
        "effective_replacement_rate_ml_hr": round(effective_rate, 1),
        "note": ("Pre-dilution reduces solute concentration at filter, "
                 "requiring ~20-30% higher nominal rate to achieve same clearance."
                 if mode == "pre" else "Post-dilution: full replacement rate is effective."),
    }


# ---------------------------------------------------------------------------
# CVVHD - Continuous Venovenous Hemodialysis
# ---------------------------------------------------------------------------

def calc_cvvhd_clearance(dialysate_flow_rate_ml_hr: float, koa: float = 600.0,
                          blood_flow_rate_ml_min: float = 200.0,
                          time_hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate CVVHD clearance using the KoA approach.

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
    """
    if dialysate_flow_rate_ml_hr < 0:
        raise ValueError("Dialysate flow rate cannot be negative")
    if blood_flow_rate_ml_min <= 0:
        raise ValueError("Blood flow rate must be positive")
    if koa <= 0:
        raise ValueError("KoA must be positive")

    qd_ml_min = dialysate_flow_rate_ml_hr / 60.0
    qb = blood_flow_rate_ml_min

    # Clearance formula: K = Qd × (1 - e^(-KoA × Qd / Qb))
    exponent = -koa * qd_ml_min / qb
    clearance_ml_min = qd_ml_min * (1 - math.exp(exponent))

    clearance_ml_hr = clearance_ml_min * 60.0
    total_clearance_ml = clearance_ml_hr * time_hours

    # Kt (total clearance over time)
    kt = total_clearance_ml

    return {
        "mode": "CVVHD",
        "dialysate_flow_rate_ml_hr": dialysate_flow_rate_ml_hr,
        "dialysate_flow_rate_ml_min": round(qd_ml_min, 2),
        "blood_flow_rate_ml_min": blood_flow_rate_ml_min,
        "koa": koa,
        "clearance_ml_min": round(clearance_ml_min, 2),
        "clearance_ml_hr": round(clearance_ml_hr, 1),
        "total_clearance_ml": round(total_clearance_ml, 1),
        "time_hours": time_hours,
    }


# ---------------------------------------------------------------------------
# CVVHDF - Combined
# ---------------------------------------------------------------------------

def calc_cvhdf_total_effluent(replacement_rate_ml_hr: float,
                               dialysate_flow_rate_ml_hr: float,
                               time_hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate total effluent volume for CVVHDF.

    Total effluent = Replacement fluid volume + Dialysate volume

    Args:
        replacement_rate_ml_hr: Replacement fluid rate in mL/hr
        dialysate_flow_rate_ml_hr: Dialysate flow rate in mL/hr
        time_hours: Duration in hours

    Returns:
        Dict with total effluent and dose
    """
    if replacement_rate_ml_hr < 0:
        raise ValueError("Replacement rate cannot be negative")
    if dialysate_flow_rate_ml_hr < 0:
        raise ValueError("Dialysate flow rate cannot be negative")

    total_effluent_hr = replacement_rate_ml_hr + dialysate_flow_rate_ml_hr
    total_effluent = total_effluent_hr * time_hours

    return {
        "mode": "CVVHDF",
        "replacement_rate_ml_hr": replacement_rate_ml_hr,
        "dialysate_flow_rate_ml_hr": dialysate_flow_rate_ml_hr,
        "total_effluent_rate_ml_hr": total_effluent_hr,
        "total_effluent_ml": round(total_effluent, 1),
        "time_hours": time_hours,
    }


# ---------------------------------------------------------------------------
# Dose Adequacy - Kt/V for CRRT
# ---------------------------------------------------------------------------

def calc_crrt_ktv(total_effluent_ml: float, body_weight_kg: float,
                   time_hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate Kt/V for CRRT.

    For CRRT, Kt/V ≈ (Effluent volume) / (Vd)
    where Vd = 0.6 × body_weight_kg (Watson estimate for total body water)

    Daily Kt/V = Effluent volume (L) / Vd (L)
    Weekly Kt/V = Daily Kt/V × 7

    Target: Daily Kt/V ≥ 0.65 (equivalent to effluent dose ≥ 20 mL/kg/hr)

    Args:
        total_effluent_ml: Total effluent volume in mL
        body_weight_kg: Patient weight in kg
        time_hours: Duration in hours

    Returns:
        Dict with Kt/V values and adequacy assessment
    """
    if body_weight_kg <= 0:
        raise ValueError("Body weight must be positive")
    if total_effluent_ml < 0:
        raise ValueError("Effluent volume cannot be negative")

    # Total body water (Watson formula simplified)
    vd_liters = 0.6 * body_weight_kg

    kt_total_liters = total_effluent_ml / 1000.0
    ktv_period = kt_total_liters / vd_liters

    # Normalize to daily
    hours_per_day = 24.0
    daily_ktv = ktv_period * (hours_per_day / time_hours) if time_hours > 0 else 0
    weekly_ktv = daily_ktv * 7

    adequate = daily_ktv >= 0.65

    return {
        "total_effluent_ml": total_effluent_ml,
        "body_weight_kg": body_weight_kg,
        "vd_liters": round(vd_liters, 1),
        "ktv_for_period": round(ktv_period, 3),
        "daily_ktv": round(daily_ktv, 3),
        "weekly_ktv": round(weekly_ktv, 3),
        "time_hours": time_hours,
        "target_daily_ktv": 0.65,
        "adequate": adequate,
        "recommendation": ("Dose is adequate." if adequate
                           else "Dose below target. Increase effluent volume."),
    }


# ---------------------------------------------------------------------------
# Anticoagulation Protocols
# ---------------------------------------------------------------------------

def calc_citrate_protocol(blood_flow_rate_ml_min: float,
                           citrate_concentration_mmol_l: float = 18.0,
                           target_ionized_calcium_mmol_l: float = 0.35,
                           duration_hours: float = 24.0) -> Dict[str, Any]:
    """
    Regional citrate anticoagulation protocol.

    Citrate infusion rate (mL/hr) = (Blood flow rate × citrate dose factor)
    Target post-filter iCa: 0.25-0.40 mmol/L (typically 0.35)

    Citrate dose = Qb × 3.0 (mmol citrate per liter of blood)
    Citrate infusion rate = Citrate dose / citrate_concentration × 60

    Calcium replacement: 10% CaCl2 or Ca-gluconate to maintain systemic iCa 1.0-1.2 mmol/L

    Args:
        blood_flow_rate_ml_min: Blood flow rate in mL/min
        citrate_concentration_mmol_l: Citrate solution concentration (mmol/L)
        target_ionized_calcium_mmol_l: Target post-filter iCa
        duration_hours: Treatment duration

    Returns:
        Dict with citrate dosing parameters
    """
    if blood_flow_rate_ml_min <= 0:
        raise ValueError("Blood flow rate must be positive")
    if citrate_concentration_mmol_l <= 0:
        raise ValueError("Citrate concentration must be positive")

    # Citrate dose: approximately 3 mmol per liter of blood processed
    qblood_l_hr = (blood_flow_rate_ml_min * 60) / 1000.0
    citrate_dose_mmol_hr = qblood_l_hr * 3.0

    # Citrate infusion rate
    citrate_infusion_ml_hr = (citrate_dose_mmol_hr / citrate_concentration_mmol_l) * 60.0

    # Calcium replacement (approximate: 1 mmol Ca per 3 mmol citrate chelated)
    # Assuming ~60-70% citrate is chelated systemically
    calcium_replacement_mmol_hr = citrate_dose_mmol_hr * 0.65 / 3.0

    # 10% CaCl2: 100 mg/mL = 1.36 mEq/mL = 0.68 mmol/mL Ca2+
    # 10% Ca-gluconate: 100 mg/mL = 0.465 mEq/mL = 0.223 mmol/mL Ca2+
    cacl2_rate_ml_hr = calcium_replacement_mmol_hr / 0.68
    cagluconate_rate_ml_hr = calcium_replacement_mmol_hr / 0.223

    return {
        "protocol": "Regional Citrate Anticoagulation (RCA)",
        "blood_flow_rate_ml_min": blood_flow_rate_ml_min,
        "citrate_concentration_mmol_l": citrate_concentration_mmol_l,
        "citrate_dose_mmol_hr": round(citrate_dose_mmol_hr, 1),
        "citrate_infusion_ml_hr": round(citrate_infusion_ml_hr, 1),
        "target_post_filter_ica_mmol_l": target_ionized_calcium_mmol_l,
        "calcium_replacement_mmol_hr": round(calcium_replacement_mmol_hr, 2),
        "cacl2_10pct_rate_ml_hr": round(cacl2_rate_ml_hr, 1),
        "cagluconate_10pct_rate_ml_hr": round(cagluconate_rate_ml_hr, 1),
        "monitoring": "Check post-filter iCa q4-6h, systemic iCa q6-8h",
        "duration_hours": duration_hours,
    }


def calc_heparin_protocol(body_weight_kg: float, indication: str = "standard") -> Dict[str, Any]:
    """
    Systemic heparin anticoagulation for CRRT.

    Loading dose: 30-50 units/kg
    Maintenance: 5-10 units/kg/hr
    Target aPTT: 1.5-2.0× baseline (45-60 seconds typically)

    Args:
        body_weight_kg: Patient weight in kg
        indication: "standard" or "high_risk" (lower doses)

    Returns:
        Dict with heparin dosing
    """
    if body_weight_kg <= 0:
        raise ValueError("Body weight must be positive")

    if indication == "high_risk":
        loading_dose_units_kg = 30.0
        maintenance_units_kg_hr = 5.0
    else:
        loading_dose_units_kg = 50.0
        maintenance_units_kg_hr = 10.0

    loading_dose = loading_dose_units_kg * body_weight_kg
    maintenance_rate = maintenance_units_kg_hr * body_weight_kg

    return {
        "protocol": "Systemic Heparin Anticoagulation",
        "indication": indication,
        "body_weight_kg": body_weight_kg,
        "loading_dose_units": round(loading_dose, 0),
        "loading_dose_units_per_kg": loading_dose_units_kg,
        "maintenance_rate_units_hr": round(maintenance_rate, 1),
        "maintenance_units_per_kg_hr": maintenance_units_kg_hr,
        "target_aptt_seconds": "45-60 (1.5-2.0x baseline)",
        "monitoring": "Check aPTT q6h, adjust by 10-20% per protocol",
    }


# ---------------------------------------------------------------------------
# Fluid Balance
# ---------------------------------------------------------------------------

def calc_fluid_balance(fluid_intake_ml: float, fluid_output_ml: float,
                       ultrafiltration_ml: float = 0.0,
                       hours: float = 24.0) -> Dict[str, Any]:
    """
    Calculate net fluid balance for CRRT patient.

    Net balance = Intake - Output - Ultrafiltration
    Hourly rate = Net balance / hours

    Args:
        fluid_intake_ml: Total fluid intake (IV, oral, meds) in mL
        fluid_output_ml: Total output (urine, drain) in mL
        ultrafiltration_ml: CRRT ultrafiltration volume in mL
        hours: Time period in hours

    Returns:
        Dict with fluid balance details
    """
    if hours <= 0:
        raise ValueError("Hours must be positive")

    net_balance = fluid_intake_ml - fluid_output_ml - ultrafiltration_ml
    hourly_rate = net_balance / hours

    if net_balance > 500:
        status = "positive_balance"
        recommendation = "Fluid overload risk. Consider increasing ultrafiltration."
    elif net_balance < -500:
        status = "negative_balance"
        recommendation = "Significant fluid deficit. Consider reducing ultrafiltration."
    else:
        status = "balanced"
        recommendation = "Fluid balance within acceptable range."

    return {
        "fluid_intake_ml": fluid_intake_ml,
        "fluid_output_ml": fluid_output_ml,
        "ultrafiltration_ml": ultrafiltration_ml,
        "net_balance_ml": round(net_balance, 1),
        "hourly_balance_ml_hr": round(hourly_rate, 1),
        "hours": hours,
        "status": status,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Comprehensive CRRT Prescription
# ---------------------------------------------------------------------------

def prescribe_crrt(mode: str, body_weight_kg: float,
                   desired_dose_ml_kg_hr: float = 25.0,
                   blood_flow_rate_ml_min: float = 200.0,
                   dilution: str = "post",
                   anticoagulation: str = "citrate",
                   time_hours: float = 24.0,
                   koa: float = 600.0) -> Dict[str, Any]:
    """
    Generate a comprehensive CRRT prescription.

    Args:
        mode: "CVVH", "CVVHD", or "CVVHDF"
        body_weight_kg: Patient dry weight
        desired_dose_ml_kg_hr: Target effluent dose (20-35 mL/kg/hr)
        blood_flow_rate_ml_min: Blood flow rate (150-250 mL/min)
        dilution: "pre" or "post"
        anticoagulation: "citrate", "heparin", or "none"
        time_hours: Treatment duration
        koa: KoA for CVVHD/CVVHDF dialyzer

    Returns:
        Complete prescription dict
    """
    if body_weight_kg <= 0:
        raise ValueError("Body weight must be positive")
    if mode not in ("CVVH", "CVVHD", "CVVHDF"):
        raise ValueError("Mode must be CVVH, CVVHD, or CVVHDF")

    blood_flow_rate_ml_hr = blood_flow_rate_ml_min * 60.0
    prescription = {"mode": mode, "body_weight_kg": body_weight_kg, "time_hours": time_hours}

    if mode == "CVVH":
        repl = calc_replacement_fluid_rate(desired_dose_ml_kg_hr, body_weight_kg, time_hours)
        if dilution == "pre":
            adj = calc_pre_post_dilution(repl["replacement_rate_ml_hr"],
                                          blood_flow_rate_ml_hr, "pre")
            # Increase nominal rate to compensate for pre-dilution
            adjusted_rate = repl["replacement_rate_ml_hr"] / adj["adjustment_factor"]
            prescription["replacement_rate_ml_hr"] = round(adjusted_rate, 1)
            prescription["dilution"] = "pre-dilution (adjusted)"
        else:
            prescription["replacement_rate_ml_hr"] = repl["replacement_rate_ml_hr"]
            prescription["dilution"] = "post-dilution"

        effluent_ml = prescription["replacement_rate_ml_hr"] * time_hours
        prescription["effluent_volume_ml"] = round(effluent_ml, 1)

    elif mode == "CVVHD":
        dialysate_rate = desired_dose_ml_kg_hr * body_weight_kg
        prescription["dialysate_flow_rate_ml_hr"] = round(dialysate_rate, 1)
        clearance = calc_cvvhd_clearance(dialysate_rate, koa, blood_flow_rate_ml_min, time_hours)
        prescription["clearance_ml_min"] = clearance["clearance_ml_min"]
        prescription["effluent_volume_ml"] = round(dialysate_rate * time_hours, 1)

    elif mode == "CVVHDF":
        # Split dose: 50% replacement, 50% dialysate
        total_rate = desired_dose_ml_kg_hr * body_weight_kg
        half_rate = total_rate / 2.0
        prescription["replacement_rate_ml_hr"] = round(half_rate, 1)
        prescription["dialysate_flow_rate_ml_hr"] = round(half_rate, 1)
        effluent = calc_cvhdf_total_effluent(half_rate, half_rate, time_hours)
        prescription["effluent_volume_ml"] = effluent["total_effluent_ml"]

    # Dose adequacy
    dose = calc_cvvh_prescribed_dose(prescription["effluent_volume_ml"],
                                      body_weight_kg, time_hours)
    prescription["prescribed_dose_ml_kg_hr"] = dose["prescribed_dose_ml_kg_hr"]
    prescription["dose_adequate"] = dose["within_target"]

    ktv = calc_crrt_ktv(prescription["effluent_volume_ml"], body_weight_kg, time_hours)
    prescription["daily_ktv"] = ktv["daily_ktv"]

    # Anticoagulation
    if anticoagulation == "citrate":
        prescription["anticoagulation"] = calc_citrate_protocol(blood_flow_rate_ml_min)
    elif anticoagulation == "heparin":
        prescription["anticoagulation"] = calc_heparin_protocol(body_weight_kg)
    else:
        prescription["anticoagulation"] = {"protocol": "None", "note": "No anticoagulation"}

    return prescription


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="crrt-prescriber",
        description="CRRT Prescriber: Continuous Renal Replacement Therapy Calculator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # CVVH dose
    p_cvvh = sub.add_parser("cvvh", help="Calculate CVVH prescribed dose")
    p_cvvh.add_argument("--effluent-ml", type=float, required=True, help="Total effluent volume (mL)")
    p_cvvh.add_argument("--weight", type=float, required=True, help="Body weight (kg)")
    p_cvvh.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    # Replacement fluid rate
    p_repl = sub.add_parser("replacement", help="Calculate replacement fluid rate")
    p_repl.add_argument("--dose", type=float, required=True, help="Desired dose (mL/kg/hr)")
    p_repl.add_argument("--weight", type=float, required=True, help="Body weight (kg)")
    p_repl.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    # CVVHD clearance
    p_cvvhd = sub.add_parser("cvvhd", help="Calculate CVVHD clearance")
    p_cvvhd.add_argument("--dialysate-ml-hr", type=float, required=True, help="Dialysate flow (mL/hr)")
    p_cvvhd.add_argument("--blood-flow-ml-min", type=float, default=200.0, help="Blood flow (mL/min)")
    p_cvvhd.add_argument("--koa", type=float, default=600.0, help="KoA coefficient")
    p_cvvhd.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    # CVVHDF
    p_cvhdf = sub.add_parser("cvvhdf", help="Calculate CVVHDF total effluent")
    p_cvhdf.add_argument("--replacement-ml-hr", type=float, required=True, help="Replacement rate (mL/hr)")
    p_cvhdf.add_argument("--dialysate-ml-hr", type=float, required=True, help="Dialysate rate (mL/hr)")
    p_cvhdf.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    # Kt/V
    p_ktv = sub.add_parser("ktv", help="Calculate CRRT Kt/V")
    p_ktv.add_argument("--effluent-ml", type=float, required=True, help="Total effluent (mL)")
    p_ktv.add_argument("--weight", type=float, required=True, help="Body weight (kg)")
    p_ktv.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    # Citrate
    p_cit = sub.add_parser("citrate", help="Citrate anticoagulation protocol")
    p_cit.add_argument("--blood-flow-ml-min", type=float, required=True, help="Blood flow (mL/min)")
    p_cit.add_argument("--citrate-conc", type=float, default=18.0, help="Citrate concentration (mmol/L)")

    # Heparin
    p_hep = sub.add_parser("heparin", help="Heparin anticoagulation protocol")
    p_hep.add_argument("--weight", type=float, required=True, help="Body weight (kg)")
    p_hep.add_argument("--indication", choices=["standard", "high_risk"], default="standard")

    # Fluid balance
    p_fluid = sub.add_parser("fluid", help="Fluid balance calculation")
    p_fluid.add_argument("--intake-ml", type=float, required=True, help="Total intake (mL)")
    p_fluid.add_argument("--output-ml", type=float, required=True, help="Total output (mL)")
    p_fluid.add_argument("--uf-ml", type=float, default=0.0, help="Ultrafiltration (mL)")
    p_fluid.add_argument("--hours", type=float, default=24.0, help="Hours")

    # Full prescription
    p_rx = sub.add_parser("prescribe", help="Generate full CRRT prescription")
    p_rx.add_argument("--mode", choices=["CVVH", "CVVHD", "CVVHDF"], required=True)
    p_rx.add_argument("--weight", type=float, required=True, help="Body weight (kg)")
    p_rx.add_argument("--dose", type=float, default=25.0, help="Desired dose (mL/kg/hr)")
    p_rx.add_argument("--blood-flow", type=float, default=200.0, help="Blood flow (mL/min)")
    p_rx.add_argument("--dilution", choices=["pre", "post"], default="post")
    p_rx.add_argument("--anticoag", choices=["citrate", "heparin", "none"], default="citrate")
    p_rx.add_argument("--hours", type=float, default=24.0, help="Duration (hours)")

    args = parser.parse_args(argv)

    if args.command == "cvvh":
        result = calc_cvvh_prescribed_dose(args.effluent_ml, args.weight, args.hours)
    elif args.command == "replacement":
        result = calc_replacement_fluid_rate(args.dose, args.weight, args.hours)
    elif args.command == "cvvhd":
        result = calc_cvvhd_clearance(args.dialysate_ml_hr, args.koa,
                                       args.blood_flow_ml_min, args.hours)
    elif args.command == "cvvhdf":
        result = calc_cvhdf_total_effluent(args.replacement_ml_hr,
                                            args.dialysate_ml_hr, args.hours)
    elif args.command == "ktv":
        result = calc_crrt_ktv(args.effluent_ml, args.weight, args.hours)
    elif args.command == "citrate":
        result = calc_citrate_protocol(args.blood_flow_ml_min, args.citrate_conc)
    elif args.command == "heparin":
        result = calc_heparin_protocol(args.weight, args.indication)
    elif args.command == "fluid":
        result = calc_fluid_balance(args.intake_ml, args.output_ml, args.uf_ml, args.hours)
    elif args.command == "prescribe":
        result = prescribe_crrt(args.mode, args.weight, args.dose, args.blood_flow,
                                 args.dilution, args.anticoag, args.hours)
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
