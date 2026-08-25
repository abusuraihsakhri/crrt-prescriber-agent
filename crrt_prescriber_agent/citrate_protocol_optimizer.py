"""
Automated Citrate Protocol Optimization for CRRT-Mind Agent.
Dynamic citrate infusion rate adjustment based on post-filter iCa trending
with metabolic alkalosis prevention.

Domain: Nephrology / ICU
Standard: KDIGO 2012 AKI & CRRT Practice Guidelines
"""
import datetime
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class CitrateStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    ACCUMULATION_RISK = "CITRATE_ACCUMULATION_RISK"
    SUBTHERAPEUTIC_FILTER = "SUBTHERAPEUTIC_FILTER_ANTICOAG"
    METABOLIC_ALKALOSIS_RISK = "METABOLIC_ALKALOSIS_RISK"
    ADJUSTMENT_IN_PROGRESS = "ADJUSTMENT_IN_PROGRESS"


class AcidBaseStatus(str, Enum):
    NORMAL = "NORMAL"
    METABOLIC_ALKALOSIS = "METABOLIC_ALKALOSIS"
    METABOLIC_ACIDOSIS = "METABOLIC_ACIDOSIS"
    CITRATE_LOCK = "CITRATE_LOCK_ACIDOSIS"


@dataclass
class CitrateLabPanel:
    """Lab values relevant to citrate anticoagulation management."""
    timestamp: datetime.datetime
    post_filter_ica: float  # mmol/L (target 0.20-0.40)
    systemic_ica: float  # mmol/L (target 1.00-1.20)
    systemic_total_calcium: float  # mg/dL
    ionized_calcium_systemic: float  # mg/dL
    bicarbonate: float  # mEq/L
    ph: Optional[float] = None
    lactate: Optional[float] = None  # mmol/L
    anion_gap: Optional[float] = None
    sodium: float = 140.0  # mEq/L
    chloride: float = 100.0  # mEq/L


@dataclass
class CitrateInfusionState:
    """Current citrate infusion parameters."""
    citrate_rate_ml_hr: float
    citrate_concentration_mmol_l: float  # Typically trisodium citrate 133 mmol/L
    calcium_chloride_rate_ml_hr: float
    calcium_chloride_concentration_mmol_l: float  # Typically CaCl2 10% = 680 mmol/L
    blood_flow_rate_ml_min: float
    effluent_flow_rate_ml_hr: float
    patient_weight_kg: float


@dataclass
class CitrateOptimizationResult:
    """Output of citrate protocol optimization."""
    optimization_id: str
    timestamp: str
    current_status: CitrateStatus
    acid_base_status: AcidBaseStatus
    recommended_citrate_rate_ml_hr: float
    recommended_calcium_chloride_rate_ml_hr: float
    rate_change_percent: float
    target_post_filter_ica: Tuple[float, float]
    target_systemic_ica: Tuple[float, float]
    bicarbonate_trend: str
    safety_alerts: List[Dict[str, Any]]
    rationale: List[str]
    next_check_hours: float


class CitrateProtocolOptimizer:
    """
    Dynamic citrate protocol optimizer for CRRT.
    Adjusts citrate and calcium replacement rates based on serial lab monitoring.
    """

    # Target ranges
    POST_FILTER_ICA_LOW = 0.20  # mmol/L
    POST_FILTER_ICA_HIGH = 0.40  # mmol/L
    POST_FILTER_ICA_TARGET = 0.30  # mmol/L
    SYSTEMIC_ICA_LOW = 1.00  # mmol/L
    SYSTEMIC_ICA_HIGH = 1.20  # mmol/L
    SYSTEMIC_ICA_TARGET = 1.10  # mmol/L

    # Bicarbonate thresholds
    BICARB_HIGH = 30.0  # mEq/L - alkalosis risk
    BICARB_LOW = 20.0  # mEq/L - acidosis risk
    BICARB_CRITICAL_HIGH = 35.0

    # Calcium ratio (total Ca / ionized Ca) for citrate accumulation detection
    CA_RATIO_ACCUMULATION_THRESHOLD = 2.5

    # Maximum rate adjustments per cycle
    MAX_RATE_CHANGE_PERCENT = 20.0

    def __init__(self):
        self._history: List[CitrateLabPanel] = []

    def optimize(self, labs: CitrateLabPanel,
                 current_state: CitrateInfusionState) -> CitrateOptimizationResult:
        """Generate optimized citrate protocol recommendations."""
        import uuid
        self._history.append(labs)
        safety_alerts = []
        rationale = []

        # 1. Assess post-filter iCa
        pf_ica_status, pf_ica_msg = self._assess_post_filter_ica(labs.post_filter_ica)

        # 2. Assess systemic iCa for citrate accumulation
        sys_ica_status, sys_ica_msg = self._assess_systemic_ica(labs.systemic_ica)

        # 3. Assess acid-base / bicarbonate for alkalosis
        acid_base, ab_msg = self._assess_acid_base(labs)

        # 4. Check for citrate accumulation (total Ca / iCa ratio)
        ca_ratio = labs.systemic_total_calcium / (labs.systemic_ica * 4.0) if labs.systemic_ica > 0 else 0
        accumulation_risk = ca_ratio > self.CA_RATIO_ACCUMULATION_THRESHOLD

        # 5. Determine citrate rate adjustment
        citrate_adjustment = self._calculate_citrate_adjustment(
            labs.post_filter_ica, current_state, accumulation_risk, acid_base
        )

        # 6. Determine calcium chloride adjustment
        calcium_adjustment = self._calculate_calcium_replacement(
            labs.systemic_ica, current_state, accumulation_risk
        )

        # 7. Determine overall status
        if accumulation_risk:
            status = CitrateStatus.ACCUMULATION_RISK
            safety_alerts.append({
                "type": "CITRATE_ACCUMULATION",
                "severity": "HIGH",
                "message": f"Ca/iCa ratio ({ca_ratio:.1f}) suggests citrate accumulation. Consider reducing or stopping citrate.",
            })
            rationale.append(f"Total Ca/iCa ratio {ca_ratio:.1f} > {self.CA_RATIO_ACCUMULATION_THRESHOLD} threshold")
        elif acid_base == AcidBaseStatus.METABOLIC_ALKALOSIS:
            status = CitrateStatus.METABOLIC_ALKALOSIS_RISK
            safety_alerts.append({
                "type": "METABOLIC_ALKALOSIS",
                "severity": "MODERATE",
                "message": f"Bicarbonate {labs.bicarbonate:.1f} mEq/L - citrate metabolism contributing to alkalosis.",
            })
        elif labs.post_filter_ica < self.POST_FILTER_ICA_LOW:
            status = CitrateStatus.SUBTHERAPEUTIC_FILTER
        elif labs.post_filter_ica > self.POST_FILTER_ICA_HIGH:
            status = CitrateStatus.SUBTHERAPEUTIC_FILTER
        else:
            status = CitrateStatus.OPTIMAL

        # Calculate new rates
        new_citrate_rate = current_state.citrate_rate_ml_hr * (1 + citrate_adjustment / 100.0)
        new_calcium_rate = current_state.calcium_chloride_rate_ml_hr * (1 + calcium_adjustment / 100.0)

        # Safety bounds
        new_citrate_rate = max(0, min(new_citrate_rate, current_state.blood_flow_rate_ml_min * 1.5))
        new_calcium_rate = max(0, new_calcium_rate)

        rate_change = citrate_adjustment

        # Bicarbonate trend
        bicarb_trend = self._assess_bicarbonate_trend()

        # Next check interval
        if status in (CitrateStatus.ACCUMULATION_RISK, CitrateStatus.SUBTHERAPEUTIC_FILTER):
            next_check = 2.0
        elif status == CitrateStatus.METABOLIC_ALKALOSIS_RISK:
            next_check = 4.0
        else:
            next_check = 6.0

        rationale.append(pf_ica_msg)
        rationale.append(sys_ica_msg)
        rationale.append(ab_msg)

        return CitrateOptimizationResult(
            optimization_id=str(uuid.uuid4())[:8],
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            current_status=status,
            acid_base_status=acid_base,
            recommended_citrate_rate_ml_hr=round(new_citrate_rate, 1),
            recommended_calcium_chloride_rate_ml_hr=round(new_calcium_rate, 1),
            rate_change_percent=round(rate_change, 1),
            target_post_filter_ica=(self.POST_FILTER_ICA_LOW, self.POST_FILTER_ICA_HIGH),
            target_systemic_ica=(self.SYSTEMIC_ICA_LOW, self.SYSTEMIC_ICA_HIGH),
            bicarbonate_trend=bicarb_trend,
            safety_alerts=safety_alerts,
            rationale=rationale,
            next_check_hours=next_check,
        )

    def _assess_post_filter_ica(self, ica: float) -> Tuple[str, str]:
        if self.POST_FILTER_ICA_LOW <= ica <= self.POST_FILTER_ICA_HIGH:
            return "IN_TARGET", f"Post-filter iCa {ica:.2f} mmol/L within target (0.20-0.40)"
        elif ica < self.POST_FILTER_ICA_LOW:
            return "LOW", f"Post-filter iCa {ica:.2f} below target - citrate may be excessive"
        else:
            return "HIGH", f"Post-filter iCa {ica:.2f} above target - insufficient anticoagulation"

    def _assess_systemic_ica(self, ica: float) -> Tuple[str, str]:
        if self.SYSTEMIC_ICA_LOW <= ica <= self.SYSTEMIC_ICA_HIGH:
            return "IN_TARGET", f"Systemic iCa {ica:.2f} mmol/L within target (1.00-1.20)"
        elif ica < self.SYSTEMIC_ICA_LOW:
            return "LOW", f"Systemic iCa {ica:.2f} below target - increase CaCl2 replacement"
        else:
            return "HIGH", f"Systemic iCa {ica:.2f} above target - decrease CaCl2 replacement"

    def _assess_acid_base(self, labs: CitrateLabPanel) -> Tuple[AcidBaseStatus, str]:
        if labs.bicarbonate >= self.BICARB_CRITICAL_HIGH:
            return AcidBaseStatus.METABOLIC_ALKALOSIS, (
                f"Severe metabolic alkalosis (HCO3 {labs.bicarbonate:.1f}) - reduce citrate rate"
            )
        elif labs.bicarbonate >= self.BICARB_HIGH:
            return AcidBaseStatus.METABOLIC_ALKALOSIS, (
                f"Metabolic alkalosis developing (HCO3 {labs.bicarbonate:.1f}) - monitor closely"
            )
        elif labs.bicarbonate <= self.BICARB_LOW:
            if labs.anion_gap and labs.anion_gap > 16:
                return AcidBaseStatus.CITRATE_LOCK, (
                    f"High anion gap acidosis (AG {labs.anion_gap:.1f}) with low HCO3 - consider citrate lock"
                )
            return AcidBaseStatus.METABOLIC_ACIDOSIS, (
                f"Metabolic acidosis (HCO3 {labs.bicarbonate:.1f}) - assess underlying cause"
            )
        return AcidBaseStatus.NORMAL, f"Acid-base status normal (HCO3 {labs.bicarbonate:.1f})"

    def _calculate_citrate_adjustment(self, post_filter_ica: float,
                                       state: CitrateInfusionState,
                                       accumulation_risk: bool,
                                       acid_base: AcidBaseStatus) -> float:
        """Calculate percentage adjustment to citrate rate."""
        if accumulation_risk:
            return -self.MAX_RATE_CHANGE_PERCENT

        if acid_base == AcidBaseStatus.METABOLIC_ALKALOSIS:
            return -10.0

        # PID-like controller for post-filter iCa
        error = post_filter_ica - self.POST_FILTER_ICA_TARGET
        proportional = error * 100  # Scale factor

        # Clamp adjustment
        return max(-self.MAX_RATE_CHANGE_PERCENT,
                   min(self.MAX_RATE_CHANGE_PERCENT, proportional))

    def _calculate_calcium_replacement(self, systemic_ica: float,
                                        state: CitrateInfusionState,
                                        accumulation_risk: bool) -> float:
        """Calculate percentage adjustment to calcium chloride rate."""
        if accumulation_risk:
            return -30.0  # Reduce calcium to lower total Ca/iCa ratio

        error = self.SYSTEMIC_ICA_TARGET - systemic_ica
        return max(-self.MAX_RATE_CHANGE_PERCENT,
                   min(self.MAX_RATE_CHANGE_PERCENT, error * 80))

    def _assess_bicarbonate_trend(self) -> str:
        """Assess bicarbonate trend from history."""
        if len(self._history) < 2:
            return "INSUFFICIENT_DATA"
        recent = self._history[-1].bicarbonate
        previous = self._history[-2].bicarbonate
        delta = recent - previous
        if delta > 2:
            return "RISING"
        elif delta < -2:
            return "FALLING"
        return "STABLE"
