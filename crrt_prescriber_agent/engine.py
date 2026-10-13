"""
Clinical Algorithmic Engine & Guideline Rules for CRRT-Mind: Continuous Renal Replacement Therapy Effluent & Citrate Anticoagulation Agent.
Domain: Nephrology / ICU
Standard: KDIGO 2012 AKI & CRRT Practice Guidelines
"""
import math
from typing import Dict, Any, List, Optional
from .models import ClinicalCasePayload, AgentAlert, UrgencyLevel, ClinicalIntegrityStatus


class ClinicalDomainEngine:
    GUIDELINE = "KDIGO 2012 AKI & CRRT Practice Guidelines"
    PRIMARY_BASELINE_LIMIT = 20.0
    UPPER_REFERENCE_LIMIT = 25.0
    SECONDARY_ALERT_LIMIT = 10.0

    @classmethod
    def evaluate_primary_index(cls, value: float) -> Optional[Dict[str, Any]]:
        # The caller must supply an observed, delivered effluent dose in mL/kg/h.
        # This is a reference comparison, not a patient-specific treatment decision.
        if value < cls.PRIMARY_BASELINE_LIMIT:
            return {
                "title": "Delivered Effluent Below Reference Interval",
                "finding": f"Observed dose ({value:.2f} mL/kg/h) is below the KDIGO 2012 delivered-effluent reference interval (20–25 mL/kg/h) for adults with AKI.",
                "recommendation": "Review the measured delivery, interruptions, and clinical context with the treating team.",
            }
        if value > cls.UPPER_REFERENCE_LIMIT:
            return {
                "title": "Delivered Effluent Above Reference Interval",
                "finding": f"Observed dose ({value:.2f} mL/kg/h) is above the KDIGO 2012 delivered-effluent reference interval (20–25 mL/kg/h) for adults with AKI.",
                "recommendation": "Review the measured delivery and clinical context; no automatic prescription change is implied.",
            }
        return None

    @classmethod
    def evaluate_secondary_kinetics(cls, value: float, is_stat: bool) -> Optional[Dict[str, Any]]:
        if value > cls.SECONDARY_ALERT_LIMIT or is_stat:
            return {
                "title": "Synthetic Secondary Score Flag",
                "finding": f"Demonstration-only secondary score ({value:.2f}), STAT={is_stat}; the threshold is not a validated clinical alarm.",
                "recommendation": "Manually review the synthetic case flag; do not use this rule to determine clinical escalation.",
            }
        return None

    @classmethod
    def evaluate_biomarker_concordance(cls, status_flag: str, biomarkers: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        status_upper = str(status_flag).upper()
        if "DISCORDANT" in status_upper or "EQUIVOCAL" in status_upper:
            return {
                "title": "Synthetic Status Flag Requires Review",
                "finding": f"Case status '{status_flag}' was marked for manual review; this is not a KDIGO biomarker criterion.",
                "recommendation": "Review the source status in the demonstration case. No confirmatory test or treatment is inferred.",
            }
        return None
