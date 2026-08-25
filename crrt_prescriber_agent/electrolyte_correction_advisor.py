"""
Electrolyte Correction Advisor for CRRT-Mind Agent.
Automated potassium/phosphate/magnesium replacement dosing based on
CRRT clearance rates and serum levels.

Domain: Nephrology / ICU
Standard: KDIGO 2012 AKI & CRRT Practice Guidelines
"""
import datetime
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class SeverityLevel(str, Enum):
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class ReplacementUrgency(str, Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"
    EMERGENT = "EMERGENT"


@dataclass
class ElectrolytePanel:
    """Current serum electrolyte values."""
    timestamp: datetime.datetime
    potassium: float  # mEq/L (normal 3.5-5.0)
    sodium: float  # mEq/L (normal 135-145)
    magnesium: float  # mg/dL (normal 1.7-2.2)
    phosphate: float  # mg/dL (normal 2.5-4.5)
    ionized_calcium: float  # mg/dL (normal 4.5-5.3)
    total_calcium: float  # mg/dL
    albumin: float  # g/dL
    chloride: float  # mEq/L


@dataclass
class CRRTParameters:
    """CRRT operational parameters affecting clearance."""
    modality: str  # "CVVH", "CVVHD", "CVVHDF"
    effluent_flow_rate_ml_hr: float
    blood_flow_rate_ml_min: float
    replacement_fluid_rate_ml_hr: float
    replacement_fluid_potassium: float  # mEq/L in replacement fluid
    replacement_fluid_magnesium: float  # mEq/L
    replacement_fluid_phosphate: float  # mg/dL
    patient_weight_kg: float
    hours_on_crrt: float


@dataclass
class ReplacementOrder:
    """Recommended electrolyte replacement order."""
    electrolyte: str
    current_level: float
    target_range: Tuple[float, float]
    severity: SeverityLevel
    urgency: ReplacementUrgency
    dose: str
    route: str
    rate: str
    monitoring_interval_hours: float
    rationale: str
    expected_correction: float  # Expected change per dose
    max_daily_dose: str
    safety_notes: List[str]


@dataclass
class ElectrolyteCorrectionPlan:
    """Complete electrolyte correction plan."""
    plan_id: str
    timestamp: str
    electrolyte_status: Dict[str, str]
    replacement_orders: List[ReplacementOrder]
    crrt_adjustments: List[Dict[str, Any]]
    fluid_recommendations: List[str]
    safety_alerts: List[Dict[str, Any]]
    reassessment_hours: float


class ElectrolyteCorrectionAdvisor:
    """
    Automated electrolyte replacement advisor for CRRT patients.
    Accounts for CRRT clearance when calculating replacement doses.
    """

    # Normal ranges
    K_NORMAL = (3.5, 5.0)
    MG_NORMAL = (1.7, 2.2)
    PHOS_NORMAL = (2.5, 4.5)
    ICA_NORMAL = (4.5, 5.3)

    # Critical thresholds
    K_CRITICAL_LOW = 2.5
    K_CRITICAL_HIGH = 6.0
    MG_CRITICAL_LOW = 1.0
    PHOS_CRITICAL_LOW = 1.0

    # CRRT clearance factors (fraction of replacement needed)
    CVVH_K_CLEARANCE_FACTOR = 0.7
    CVVHD_K_CLEARANCE_FACTOR = 0.6
    CVVHDF_K_CLEARANCE_FACTOR = 0.65

    def __init__(self):
        self._history: List[ElectrolytePanel] = []

    def generate_correction_plan(self, labs: ElectrolytePanel,
                                  crrt_params: CRRTParameters) -> ElectrolyteCorrectionPlan:
        """Generate comprehensive electrolyte correction plan."""
        import uuid
        self._history.append(labs)
        orders = []
        crrt_adjustments = []
        fluid_recs = []
        safety_alerts = []
        status = {}

        # 1. Potassium assessment and replacement
        k_order, k_alerts = self._assess_potassium(labs, crrt_params)
        if k_order:
            orders.append(k_order)
        safety_alerts.extend(k_alerts)
        status["potassium"] = self._classify_level(labs.potassium, self.K_NORMAL)

        # 2. Magnesium assessment and replacement
        mg_order, mg_alerts = self._assess_magnesium(labs, crrt_params)
        if mg_order:
            orders.append(mg_order)
        safety_alerts.extend(mg_alerts)
        status["magnesium"] = self._classify_level(labs.magnesium, self.MG_NORMAL)

        # 3. Phosphate assessment and replacement
        phos_order, phos_alerts = self._assess_phosphate(labs, crrt_params)
        if phos_order:
            orders.append(phos_order)
        safety_alerts.extend(phos_alerts)
        status["phosphate"] = self._classify_level(labs.phosphate, self.PHOS_NORMAL)

        # 4. Calcium assessment
        ca_order = self._assess_calcium(labs)
        if ca_order:
            orders.append(ca_order)
        status["ionized_calcium"] = self._classify_level(labs.ionized_calcium, self.ICA_NORMAL)

        # 5. CRRT fluid adjustments
        crrt_adjustments = self._recommend_crrt_adjustments(labs, crrt_params)

        # 6. Fluid recommendations
        fluid_recs = self._generate_fluid_recommendations(labs, crrt_params)

        # Reassessment interval
        if any(o.urgency in (ReplacementUrgency.STAT, ReplacementUrgency.EMERGENT) for o in orders):
            reassess = 2.0
        elif any(o.urgency == ReplacementUrgency.URGENT for o in orders):
            reassess = 4.0
        else:
            reassess = 6.0

        return ElectrolyteCorrectionPlan(
            plan_id=str(uuid.uuid4())[:8],
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            electrolyte_status=status,
            replacement_orders=orders,
            crrt_adjustments=crrt_adjustments,
            fluid_recommendations=fluid_recs,
            safety_alerts=safety_alerts,
            reassessment_hours=reassess,
        )

    def _assess_potassium(self, labs: ElectrolytePanel,
                          crrt: CRRTParameters) -> Tuple[Optional[ReplacementOrder], List[Dict]]:
        alerts = []
        k = labs.potassium

        if k >= self.K_CRITICAL_HIGH:
            alerts.append({
                "type": "HYPERKALEMIA_CRITICAL",
                "severity": "CRITICAL",
                "message": f"Potassium {k:.1f} mEq/L - cardiac monitoring, emergent treatment required",
            })
            return None, alerts  # Hyperkalemia handled by emergency protocol

        if k >= self.K_NORMAL[1]:
            return None, alerts  # Mild hyperkalemia - adjust CRRT

        if k < self.K_CRITICAL_LOW:
            alerts.append({
                "type": "HYPOKALEMIA_CRITICAL",
                "severity": "CRITICAL",
                "message": f"Potassium {k:.1f} mEq/L - cardiac arrest risk, emergent central replacement",
            })
            urgency = ReplacementUrgency.EMERGENT
            severity = SeverityLevel.CRITICAL
        elif k < 3.0:
            urgency = ReplacementUrgency.STAT
            severity = SeverityLevel.SEVERE
        elif k < 3.3:
            urgency = ReplacementUrgency.URGENT
            severity = SeverityLevel.MODERATE
        elif k < self.K_NORMAL[0]:
            urgency = ReplacementUrgency.ROUTINE
            severity = SeverityLevel.MILD
        else:
            return None, alerts

        # Calculate replacement accounting for CRRT clearance
        deficit = self.K_NORMAL[0] - k
        clearance_factor = self._get_clearance_factor(crrt.modality)
        # CRRT clears ~0.6-0.7 of administered K, so need higher doses
        dose_meq = deficit * crrt.patient_weight_kg * 0.4 * (1 + clearance_factor)
        dose_meq = max(10, min(200, dose_meq))

        if k < 3.0:
            route = "CENTRAL IV"
            rate = f"{dose_meq:.0f} mEq over 2-4 hours via central line"
        else:
            route = "IV or ENTERAL"
            rate = f"{dose_meq:.0f} mEq over 4-6 hours"

        return ReplacementOrder(
            electrolyte="Potassium",
            current_level=k,
            target_range=self.K_NORMAL,
            severity=severity,
            urgency=urgency,
            dose=f"{dose_meq:.0f} mEq",
            route=route,
            rate=rate,
            monitoring_interval_hours=2.0 if k < 3.0 else 4.0,
            rationale=f"K+ {k:.1f} mEq/L, deficit ~{deficit:.1f} mEq/L, CRRT clearance factor {clearance_factor:.1f}",
            expected_correction=round(dose_meq / (crrt.patient_weight_kg * 0.4), 1),
            max_daily_dose="400 mEq/day (with cardiac monitoring)",
            safety_notes=[
                "Central line required for concentrations > 40 mEq/L",
                "ECG monitoring during rapid replacement",
                "Recheck K+ after each 40 mEq administered",
            ],
        ), alerts

    def _assess_magnesium(self, labs: ElectrolytePanel,
                          crrt: CRRTParameters) -> Tuple[Optional[ReplacementOrder], List[Dict]]:
        alerts = []
        mg = labs.magnesium

        if mg >= self.MG_NORMAL[1]:
            return None, alerts

        if mg < self.MG_CRITICAL_LOW:
            alerts.append({
                "type": "HYPOMAGNESEMIA_CRITICAL",
                "severity": "CRITICAL",
                "message": f"Magnesium {mg:.1f} mg/dL - arrhythmia risk, emergent replacement",
            })
            urgency = ReplacementUrgency.EMERGENT
            severity = SeverityLevel.CRITICAL
        elif mg < 1.4:
            urgency = ReplacementUrgency.URGENT
            severity = SeverityLevel.MODERATE
        elif mg < self.MG_NORMAL[0]:
            urgency = ReplacementUrgency.ROUTINE
            severity = SeverityLevel.MILD
        else:
            return None, alerts

        deficit = self.MG_NORMAL[0] - mg
        clearance_factor = self._get_clearance_factor(crrt.modality)
        dose_g = deficit * crrt.patient_weight_kg * 0.3 * (1 + clearance_factor * 0.5)
        dose_g = max(1, min(8, dose_g))

        return ReplacementOrder(
            electrolyte="Magnesium",
            current_level=mg,
            target_range=self.MG_NORMAL,
            severity=severity,
            urgency=urgency,
            dose=f"{dose_g:.1f} g MgSO4",
            route="IV",
            rate=f"{dose_g:.1f} g over {2 if dose_g > 4 else 1} hours",
            monitoring_interval_hours=4.0,
            rationale=f"Mg {mg:.1f} mg/dL, CRRT clearance factor {clearance_factor:.1f}",
            expected_correction=round(dose_g / (crrt.patient_weight_kg * 0.3), 2),
            max_daily_dose="12 g MgSO4/day IV",
            safety_notes=[
                "Monitor deep tendon reflexes if Mg > 4 mg/dL",
                "Adjust for renal function if not on CRRT",
                "Concurrent hypokalemia often present - check K+",
            ],
        ), alerts

    def _assess_phosphate(self, labs: ElectrolytePanel,
                          crrt: CRRTParameters) -> Tuple[Optional[ReplacementOrder], List[Dict]]:
        alerts = []
        phos = labs.phosphate

        if phos >= self.PHOS_NORMAL[1]:
            return None, alerts

        if phos < self.PHOS_CRITICAL_LOW:
            alerts.append({
                "type": "HYPOPHOSPHATEMIA_CRITICAL",
                "severity": "CRITICAL",
                "message": f"Phosphate {phos:.1f} mg/dL - respiratory failure risk, emergent IV replacement",
            })
            urgency = ReplacementUrgency.EMERGENT
            severity = SeverityLevel.CRITICAL
        elif phos < 1.5:
            urgency = ReplacementUrgency.STAT
            severity = SeverityLevel.SEVERE
        elif phos < 2.0:
            urgency = ReplacementUrgency.URGENT
            severity = SeverityLevel.MODERATE
        elif phos < self.PHOS_NORMAL[0]:
            urgency = ReplacementUrgency.ROUTINE
            severity = SeverityLevel.MILD
        else:
            return None, alerts

        deficit = self.PHOS_NORMAL[0] - phos
        clearance_factor = self._get_clearance_factor(crrt.modality)
        # Phosphate replacement in mmol
        dose_mmol = deficit * crrt.patient_weight_kg * 0.3 * (1 + clearance_factor * 0.6)
        dose_mmol = max(10, min(100, dose_mmol))

        if phos < 1.5:
            route = "IV (sodium phosphate or potassium phosphate)"
            rate = f"{dose_mmol:.0f} mmol over 4-6 hours"
        else:
            route = "ORAL (sodium phosphate or potassium phosphate)"
            rate = f"{dose_mmol:.0f} mmol PO divided TID"

        return ReplacementOrder(
            electrolyte="Phosphate",
            current_level=phos,
            target_range=self.PHOS_NORMAL,
            severity=severity,
            urgency=urgency,
            dose=f"{dose_mmol:.0f} mmol",
            route=route,
            rate=rate,
            monitoring_interval_hours=6.0 if phos >= 1.5 else 4.0,
            rationale=f"Phos {phos:.1f} mg/dL, CRRT clearance factor {clearance_factor:.1f}",
            expected_correction=round(dose_mmol / (crrt.patient_weight_kg * 0.3), 1),
            max_daily_dose="150 mmol/day IV",
            safety_notes=[
                "IV phosphate: max rate 7.5 mmol/hr to avoid hypocalcemia",
                "Monitor calcium during IV phosphate replacement",
                "CRRT patients: consider phosphate in replacement fluid",
            ],
        ), alerts

    def _assess_calcium(self, labs: ElectrolytePanel) -> Optional[ReplacementOrder]:
        ica = labs.ionized_calcium
        if ica < 3.5:
            return ReplacementOrder(
                electrolyte="Ionized Calcium",
                current_level=ica,
                target_range=self.ICA_NORMAL,
                severity=SeverityLevel.SEVERE,
                urgency=ReplacementUrgency.STAT,
                dose="Calcium gluconate 2g IV",
                route="IV (central preferred)",
                rate="2g over 20 minutes, then 1-2g/hr infusion",
                monitoring_interval_hours=2.0,
                rationale=f"iCa {ica:.1f} mg/dL critically low",
                expected_correction=0.5,
                max_daily_dose="15g calcium gluconate/day",
                safety_notes=["ECG monitoring during rapid infusion"],
            )
        return None

    def _recommend_crrt_adjustments(self, labs: ElectrolytePanel,
                                     crrt: CRRTParameters) -> List[Dict[str, Any]]:
        adjustments = []
        if labs.potassium < 3.5:
            adjustments.append({
                "parameter": "Replacement fluid potassium",
                "current": f"{crrt.replacement_fluid_potassium:.0f} mEq/L",
                "recommended": "Increase to 4.0 mEq/L",
                "rationale": "Reduce CRRT K+ clearance to prevent worsening hypokalemia",
            })
        if labs.magnesium < 1.7:
            adjustments.append({
                "parameter": "Replacement fluid magnesium",
                "current": f"{crrt.replacement_fluid_magnesium:.1f} mEq/L",
                "recommended": "Increase to 2.0 mEq/L",
                "rationale": "Supplement Mg in replacement fluid to offset CRRT clearance",
            })
        return adjustments

    def _generate_fluid_recommendations(self, labs: ElectrolytePanel,
                                         crrt: CRRTParameters) -> List[str]:
        recs = []
        if labs.potassium < 3.5 and labs.magnesium < 1.7:
            recs.append("Consider potassium and magnesium-enriched replacement fluid")
        if labs.phosphate < 2.0:
            recs.append("Consider phosphate-supplemented replacement fluid (Phoxilium)")
        return recs

    def _get_clearance_factor(self, modality: str) -> float:
        mod = modality.upper()
        if mod == "CVVH":
            return self.CVVH_K_CLEARANCE_FACTOR
        elif mod == "CVVHD":
            return self.CVVHD_K_CLEARANCE_FACTOR
        elif mod == "CVVHDF":
            return self.CVVHDF_K_CLEARANCE_FACTOR
        return 0.65

    def _classify_level(self, value: float, normal_range: Tuple[float, float]) -> str:
        if normal_range[0] <= value <= normal_range[1]:
            return "NORMAL"
        elif value < normal_range[0]:
            return "LOW"
        return "HIGH"
