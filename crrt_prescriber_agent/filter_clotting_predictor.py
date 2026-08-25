"""
Predictive Filter Clotting Model for CRRT-Mind Agent.
ML-based prediction of CRRT filter lifespan using transmembrane pressure trends,
anticoagulation adequacy, and hemoconcentration markers.

Domain: Nephrology / ICU
Standard: KDIGO 2012 AKI & CRRT Practice Guidelines
"""
import math
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class FilterRiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    IMMINENT = "IMMINENT_FAILURE"


class AnticoagulationAdequacy(str, Enum):
    OPTIMAL = "OPTIMAL"
    SUBTHERAPEUTIC = "SUBTHERAPEUTIC"
    SUPRATHERAPEUTIC = "SUPRATHERAPEUTIC"
    NONE = "NO_ANTICOAGULATION"


@dataclass
class FilterPressureReading:
    """Time-stamped transmembrane pressure reading."""
    timestamp: datetime.datetime
    tmp_mmhg: float  # Transmembrane pressure
    access_pressure_mmhg: float
    return_pressure_mmhg: float
    effluent_pressure_mmhg: float


@dataclass
class FilterVitals:
    """Current filter operational parameters."""
    filter_age_hours: float
    blood_flow_rate_ml_min: float
    effluent_flow_rate_ml_hr: float
    hematocrit_percent: float
    platelet_count_k: float
    anticoagulation_type: str  # "citrate", "heparin", "none"
    post_filter_ica_mmol_l: float  # Post-filter ionized calcium (citrate)
    act_seconds: Optional[float] = None  # Activated clotting time (heparin)


@dataclass
class FilterClottingPrediction:
    """Output of the predictive filter clotting model."""
    prediction_id: str
    timestamp: str
    risk_level: FilterRiskLevel
    estimated_remaining_hours: float
    confidence_score: float  # 0.0 - 1.0
    contributing_factors: List[Dict[str, Any]]
    anticoagulation_adequacy: AnticoagulationAdequacy
    recommended_actions: List[str]
    tmp_trend_slope: float  # mmHg/hour
    filter_patency_score: float  # 0-100


class TransmembranePressureAnalyzer:
    """Analyzes TMP trends for early clotting detection."""

    # TMP thresholds (mmHg)
    TMP_BASELINE_MAX = 150.0
    TMP_WARNING = 200.0
    TMP_CRITICAL = 250.0
    TMP_RAPID_RISE_THRESHOLD = 20.0  # mmHg/hour

    @staticmethod
    def calculate_tmp(access_pressure: float, return_pressure: float,
                      effluent_pressure: float) -> float:
        """Calculate transmembrane pressure from component pressures."""
        return (access_pressure + return_pressure) / 2 - effluent_pressure

    @classmethod
    def analyze_tmp_trend(cls, readings: List[FilterPressureReading]) -> Dict[str, Any]:
        """Analyze TMP trend over time using linear regression."""
        if len(readings) < 2:
            return {"slope": 0.0, "r_squared": 0.0, "trend": "INSUFFICIENT_DATA"}

        tmps = [r.tmp_mmhg for r in readings]
        times = [(r.timestamp - readings[0].timestamp).total_seconds() / 3600.0
                 for r in readings]

        n = len(tmps)
        sum_x = sum(times)
        sum_y = sum(tmps)
        sum_xy = sum(t * tmp for t, tmp in zip(times, tmps))
        sum_x2 = sum(t ** 2 for t in times)
        sum_y2 = sum(tmp ** 2 for tmp in tmps)

        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return {"slope": 0.0, "r_squared": 0.0, "trend": "STABLE"}

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared
        ss_res = sum((tmp - (slope * t + intercept)) ** 2
                     for t, tmp in zip(times, tmps))
        mean_y = sum_y / n
        ss_tot = sum((tmp - mean_y) ** 2 for tmp in tmps)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        if slope > cls.TMP_RAPID_RISE_THRESHOLD:
            trend = "RAPID_RISE"
        elif slope > 5.0:
            trend = "RISING"
        elif slope > -5.0:
            trend = "STABLE"
        else:
            trend = "DECLINING"

        return {
            "slope": round(slope, 2),
            "intercept": round(intercept, 2),
            "r_squared": round(r_squared, 4),
            "trend": trend,
            "current_tmp": tmps[-1],
            "max_tmp": max(tmps),
        }


class AnticoagulationAssessor:
    """Assesses anticoagulation adequacy for filter patency."""

    # Citrate targets
    CITRATE_POST_FILTER_ICA_LOW = 0.20  # mmol/L
    CITRATE_POST_FILTER_ICA_HIGH = 0.40  # mmol/L

    # Heparin targets
    HEPARIN_ACT_LOW = 180.0  # seconds
    HEPARIN_ACT_HIGH = 220.0  # seconds

    @classmethod
    def assess_citrate(cls, post_filter_ica: float) -> Tuple[AnticoagulationAdequacy, str]:
        """Assess citrate anticoagulation adequacy."""
        if cls.CITRATE_POST_FILTER_ICA_LOW <= post_filter_ica <= cls.CITRATE_POST_FILTER_ICA_HIGH:
            return AnticoagulationAdequacy.OPTIMAL, "Post-filter iCa within target range (0.20-0.40 mmol/L)"
        elif post_filter_ica > cls.CITRATE_POST_FILTER_ICA_HIGH:
            return AnticoagulationAdequacy.SUBTHERAPEUTIC, (
                f"Post-filter iCa ({post_filter_ica:.2f}) above target - increase citrate rate"
            )
        else:
            return AnticoagulationAdequacy.SUPRATHERAPEUTIC, (
                f"Post-filter iCa ({post_filter_ica:.2f}) below target - decrease citrate rate, monitor for citrate toxicity"
            )

    @classmethod
    def assess_heparin(cls, act_seconds: float) -> Tuple[AnticoagulationAdequacy, str]:
        """Assess systemic heparin anticoagulation adequacy."""
        if cls.HEPARIN_ACT_LOW <= act_seconds <= cls.HEPARIN_ACT_HIGH:
            return AnticoagulationAdequacy.OPTIMAL, f"ACT ({act_seconds:.0f}s) within therapeutic range"
        elif act_seconds < cls.HEPARIN_ACT_LOW:
            return AnticoagulationAdequacy.SUBTHERAPEUTIC, f"ACT ({act_seconds:.0f}s) below target - increase heparin"
        else:
            return AnticoagulationAdequacy.SUPRATHERAPEUTIC, f"ACT ({act_seconds:.0f}s) above target - decrease heparin, bleeding risk"


class FilterClottingPredictor:
    """
    Main predictive model for CRRT filter clotting.
    Combines TMP trends, anticoagulation status, and hematologic markers
    to estimate remaining filter lifespan.
    """

    # Scoring weights
    WEIGHT_TMP_TREND = 0.35
    WEIGHT_TMP_ABSOLUTE = 0.20
    WEIGHT_ANTICOAGULATION = 0.20
    WEIGHT_HEMATOCRIT = 0.10
    WEIGHT_PLATELETS = 0.10
    WEIGHT_FILTER_AGE = 0.05

    # Expected filter lifespan
    EXPECTED_FILTER_HOURS = 72.0
    MAX_FILTER_HOURS = 96.0

    def __init__(self):
        self.tmp_analyzer = TransmembranePressureAnalyzer()
        self.anticoag_assessor = AnticoagulationAssessor()

    def predict(self, vitals: FilterVitals,
                pressure_readings: List[FilterPressureReading]) -> FilterClottingPrediction:
        """Generate filter clotting prediction."""
        import uuid
        factors = []
        risk_scores = []

        # 1. TMP Trend Analysis
        tmp_analysis = self.tmp_analyzer.analyze_tmp_trend(pressure_readings)
        tmp_trend_score = self._score_tmp_trend(tmp_analysis)
        risk_scores.append(("tmp_trend", tmp_trend_score, self.WEIGHT_TMP_TREND))
        factors.append({
            "factor": "TMP Trend",
            "value": f"{tmp_analysis['slope']:.1f} mmHg/hr",
            "trend": tmp_analysis["trend"],
            "risk_contribution": round(tmp_trend_score * self.WEIGHT_TMP_TREND, 2),
        })

        # 2. Absolute TMP
        current_tmp = tmp_analysis.get("current_tmp", 0)
        tmp_abs_score = self._score_tmp_absolute(current_tmp)
        risk_scores.append(("tmp_absolute", tmp_abs_score, self.WEIGHT_TMP_ABSOLUTE))
        factors.append({
            "factor": "Current TMP",
            "value": f"{current_tmp:.0f} mmHg",
            "risk_contribution": round(tmp_abs_score * self.WEIGHT_TMP_ABSOLUTE, 2),
        })

        # 3. Anticoagulation adequacy
        anticoag_score, anticoag_status, anticoag_msg = self._score_anticoagulation(vitals)
        risk_scores.append(("anticoagulation", anticoag_score, self.WEIGHT_ANTICOAGULATION))
        factors.append({
            "factor": "Anticoagulation",
            "type": vitals.anticoagulation_type,
            "adequacy": anticoag_status.value,
            "detail": anticoag_msg,
            "risk_contribution": round(anticoag_score * self.WEIGHT_ANTICOAGULATION, 2),
        })

        # 4. Hematocrit (hemoconcentration)
        hct_score = self._score_hematocrit(vitals.hematocrit_percent)
        risk_scores.append(("hematocrit", hct_score, self.WEIGHT_HEMATOCRIT))
        factors.append({
            "factor": "Hematocrit",
            "value": f"{vitals.hematocrit_percent:.1f}%",
            "risk_contribution": round(hct_score * self.WEIGHT_HEMATOCRIT, 2),
        })

        # 5. Platelet count
        plt_score = self._score_platelets(vitals.platelet_count_k)
        risk_scores.append(("platelets", plt_score, self.WEIGHT_PLATELETS))
        factors.append({
            "factor": "Platelet Count",
            "value": f"{vitals.platelet_count_k:.0f} K/uL",
            "risk_contribution": round(plt_score * self.WEIGHT_PLATELETS, 2),
        })

        # 6. Filter age
        age_score = self._score_filter_age(vitals.filter_age_hours)
        risk_scores.append(("filter_age", age_score, self.WEIGHT_FILTER_AGE))
        factors.append({
            "factor": "Filter Age",
            "value": f"{vitals.filter_age_hours:.1f} hours",
            "risk_contribution": round(age_score * self.WEIGHT_FILTER_AGE, 2),
        })

        # Composite risk score (0-100, higher = more risk)
        composite_risk = sum(score * weight for _, score, weight in risk_scores)
        composite_risk = min(100.0, max(0.0, composite_risk))

        # Determine risk level
        if composite_risk >= 80:
            risk_level = FilterRiskLevel.IMMINENT
        elif composite_risk >= 60:
            risk_level = FilterRiskLevel.HIGH
        elif composite_risk >= 35:
            risk_level = FilterRiskLevel.MODERATE
        else:
            risk_level = FilterRiskLevel.LOW

        # Estimate remaining hours
        remaining_hours = self._estimate_remaining_hours(
            composite_risk, vitals.filter_age_hours, tmp_analysis
        )

        # Filter patency score (inverse of risk)
        patency_score = max(0, 100 - composite_risk)

        # Confidence based on data quality
        confidence = self._calculate_confidence(pressure_readings, tmp_analysis)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_level, anticoag_status, vitals, tmp_analysis, remaining_hours
        )

        return FilterClottingPrediction(
            prediction_id=str(uuid.uuid4())[:8],
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            risk_level=risk_level,
            estimated_remaining_hours=round(remaining_hours, 1),
            confidence_score=round(confidence, 2),
            contributing_factors=factors,
            anticoagulation_adequacy=anticoag_status,
            recommended_actions=recommendations,
            tmp_trend_slope=tmp_analysis["slope"],
            filter_patency_score=round(patency_score, 1),
        )

    def _score_tmp_trend(self, analysis: Dict) -> float:
        slope = analysis["slope"]
        if slope > 30:
            return 100.0
        elif slope > 20:
            return 80.0
        elif slope > 10:
            return 50.0
        elif slope > 0:
            return 20.0
        return 5.0

    def _score_tmp_absolute(self, tmp: float) -> float:
        if tmp >= 250:
            return 100.0
        elif tmp >= 200:
            return 70.0
        elif tmp >= 150:
            return 40.0
        elif tmp >= 100:
            return 15.0
        return 5.0

    def _score_anticoagulation(self, vitals: FilterVitals) -> Tuple[float, AnticoagulationAdequacy, str]:
        if vitals.anticoagulation_type == "citrate":
            status, msg = self.anticoag_assessor.assess_citrate(vitals.post_filter_ica_mmol_l)
        elif vitals.anticoagulation_type == "heparin" and vitals.act_seconds:
            status, msg = self.anticoag_assessor.assess_heparin(vitals.act_seconds)
        else:
            return 80.0, AnticoagulationAdequacy.NONE, "No anticoagulation - high clotting risk"

        score_map = {
            AnticoagulationAdequacy.OPTIMAL: 10.0,
            AnticoagulationAdequacy.SUBTHERAPEUTIC: 70.0,
            AnticoagulationAdequacy.SUPRATHERAPEUTIC: 30.0,
        }
        return score_map.get(status, 50.0), status, msg

    def _score_hematocrit(self, hct: float) -> float:
        if hct >= 45:
            return 80.0
        elif hct >= 40:
            return 50.0
        elif hct >= 30:
            return 20.0
        return 10.0

    def _score_platelets(self, plt_k: float) -> float:
        if plt_k >= 400:
            return 70.0
        elif plt_k >= 250:
            return 40.0
        elif plt_k >= 150:
            return 20.0
        return 10.0

    def _score_filter_age(self, hours: float) -> float:
        if hours >= 72:
            return 90.0
        elif hours >= 48:
            return 60.0
        elif hours >= 24:
            return 30.0
        return 10.0

    def _estimate_remaining_hours(self, risk_score: float, filter_age: float,
                                  tmp_analysis: Dict) -> float:
        """Estimate remaining filter life in hours."""
        base_remaining = max(0, self.EXPECTED_FILTER_HOURS - filter_age)
        risk_factor = 1.0 - (risk_score / 100.0)
        slope_factor = max(0.1, 1.0 - (tmp_analysis["slope"] / 50.0))
        return base_remaining * risk_factor * slope_factor

    def _calculate_confidence(self, readings: List[FilterPressureReading],
                              tmp_analysis: Dict) -> float:
        """Calculate prediction confidence based on data quality."""
        if len(readings) < 3:
            return 0.3
        data_points_factor = min(1.0, len(readings) / 10.0)
        r2_factor = tmp_analysis["r_squared"]
        return 0.4 + 0.3 * data_points_factor + 0.3 * r2_factor

    def _generate_recommendations(self, risk_level: FilterRiskLevel,
                                  anticoag_status: AnticoagulationAdequacy,
                                  vitals: FilterVitals,
                                  tmp_analysis: Dict,
                                  remaining_hours: float) -> List[str]:
        """Generate actionable clinical recommendations."""
        recs = []

        if risk_level == FilterRiskLevel.IMMINENT:
            recs.append("URGENT: Prepare for immediate filter change - imminent clotting")
            recs.append("Ensure replacement filter circuit primed and ready")
        elif risk_level == FilterRiskLevel.HIGH:
            recs.append(f"Schedule filter change within {max(1, int(remaining_hours))}h")
            recs.append("Increase monitoring frequency to q1h TMP checks")
        elif risk_level == FilterRiskLevel.MODERATE:
            recs.append("Continue current protocol with q2h TMP monitoring")

        if anticoag_status == AnticoagulationAdequacy.SUBTHERAPEUTIC:
            if vitals.anticoagulation_type == "citrate":
                recs.append("Increase citrate infusion rate by 10-20% to achieve post-filter iCa 0.20-0.40 mmol/L")
            elif vitals.anticoagulation_type == "heparin":
                recs.append("Increase heparin infusion to achieve ACT 180-220 seconds")
        elif anticoag_status == AnticoagulationAdequacy.NONE:
            recs.append("Consider initiating regional citrate anticoagulation per KDIGO guidelines")

        if vitals.hematocrit_percent >= 45:
            recs.append("Hemoconcentration detected - consider volume resuscitation")

        if tmp_analysis["trend"] == "RAPID_RISE":
            recs.append("Rapid TMP rise detected - check for kinked lines and verify access flow")

        return recs
