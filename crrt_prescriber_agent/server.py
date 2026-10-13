"""
FastAPI REST Application & Webhooks for CRRT-Mind: Continuous Renal Replacement Therapy Effluent & Citrate Anticoagulation Agent.
"""
from typing import Dict, Any, Optional
from .models import ClinicalCasePayload
from .agents import CRRTCoordinator

coordinator = CRRTCoordinator()

def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel, FiniteFloat, Field

        app = FastAPI(
            title="CRRT-Mind: Continuous Renal Replacement Therapy Effluent & Citrate Anticoagulation Agent",
            description="Calculates prescribed vs delivered effluent dose (20-25 mL/kg/h), post-filter ionized calcium targets, and systemic calcium chloride replacement.",
            version="2.0.0-PRO",
        )

        class AuditRequest(BaseModel):
            # Never fabricate patient measurements or a STAT flag from an empty request.
            case_id: str = Field(..., min_length=1, max_length=128)
            patient_synthetic_id: str = Field(..., min_length=1, max_length=128)
            primary_metric: FiniteFloat = Field(..., description="Observed delivered effluent dose (mL/kg/h); educational reference comparison")
            secondary_metric: FiniteFloat = Field(..., description="Synthetic secondary score; no clinically validated threshold")
            status_flag: str = Field(..., min_length=1, max_length=128)
            is_stat: bool = False
            clinical_notes: str = Field(default="", max_length=4000)
            biomarkers: Dict[str, Any] = Field(default_factory=dict)

        class ChatRequest(BaseModel):
            query: str = Field(..., min_length=1, max_length=2000)

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "crrt-prescriber-agent", "domain": "Nephrology / ICU", "version": "2.0.0-PRO"}

        @app.post("/api/audit")
        def api_audit(req: AuditRequest):
            payload = ClinicalCasePayload(
                case_id=req.case_id,
                patient_synthetic_id=req.patient_synthetic_id,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_flag=req.status_flag,
                is_stat=req.is_stat,
                clinical_notes=req.clinical_notes,
                biomarkers=req.biomarkers,
            )
            return coordinator.process_case(payload)

        @app.post("/api/chat")
        def api_chat(req: ChatRequest):
            return {"response": coordinator.query_supervisory_chat(req.query)}

        return app
    except ImportError:
        return None
