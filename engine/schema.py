"""Pydantic v2 schemas for PayLens.

Architecture Rule 1: CODE COMPUTES, AMD GPU MODEL EXPLAINS.
All mathematical computations, matching logic, and forecasts are strictly deterministic.
The LLM only explains and drafts actions, verified by numeric regex grounding.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class RecommendationType(str, Enum):
    PAYMENT_LEAKAGE = "PAYMENT_LEAKAGE"
    FAILED_PAYMENT_RECOVERY = "FAILED_PAYMENT_RECOVERY"
    STOCKOUT_RISK = "STOCKOUT_RISK"


class LeakSubType(str, Enum):
    DISPATCHED_UNPAID = "DISPATCHED_UNPAID"
    SETTLEMENT_SHORTFALL = "SETTLEMENT_SHORTFALL"
    NONE = "NONE"


class ExecutionSource(str, Enum):
    LIVE_GOOGLE_GEMMA4 = "LIVE_GOOGLE_GEMMA4"
    LIVE_AMD_MI300X_VLLM = "LIVE_AMD_MI300X_VLLM"
    LIVE_AMD_TOKENFACTORY = "LIVE_AMD_TOKENFACTORY"
    LOCAL_DETERMINISTIC_FALLBACK = "LOCAL_DETERMINISTIC_FALLBACK"


class GoalWeights(BaseModel):
    """Business priorities that dynamically drive recommendation card ranking.

    Normalized so that cash_now_weight + margin_protection_weight + stock_availability_weight == 1.0.
    """
    cash_now_weight: float = Field(default=0.5, ge=0.0)
    margin_protection_weight: float = Field(default=0.3, ge=0.0)
    stock_availability_weight: float = Field(default=0.2, ge=0.0)
    rationale: str = Field(default="Balanced operating posture")

    @model_validator(mode="after")
    def normalize_weights(self) -> "GoalWeights":
        total = self.cash_now_weight + self.margin_protection_weight + self.stock_availability_weight
        if total <= 0:
            self.cash_now_weight = 1.0 / 3.0
            self.margin_protection_weight = 1.0 / 3.0
            self.stock_availability_weight = 1.0 / 3.0
        else:
            self.cash_now_weight = round(self.cash_now_weight / total, 4)
            self.margin_protection_weight = round(self.margin_protection_weight / total, 4)
            self.stock_availability_weight = round(1.0 - self.cash_now_weight - self.margin_protection_weight, 4)
        return self


class EvidenceRow(BaseModel):
    """Deterministic audit trail linking a recommendation to raw database records."""
    source_table: str
    row_id: str
    summary: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    numbers: List[float] = Field(default_factory=list)


class RecommendationCard(BaseModel):
    """Autonomous audit & action card for merchant decision-makers."""
    card_id: str
    merchant_id: str
    merchant_name: str
    rec_type: RecommendationType
    leak_sub_type: LeakSubType = LeakSubType.NONE
    entity_id: str
    title: str = ""
    impact_usd: float = Field(default=0.0)
    confidence: float
    formula_display: str
    allowed_numbers: List[float] = Field(default_factory=list)
    evidence_rows: List[EvidenceRow] = Field(default_factory=list)
    stl_anomaly_context: Optional[Dict[str, Any]] = None
    ranking_score: float = 0.0

    # Explanation & Action (populated deterministically or by AMD Gemma LLM with strict grounding)
    explanation_en: Optional[str] = ""
    action_draft_en: Optional[str] = ""
    action_type: str = ""

    # Legacy/multi-lingual compatibility properties
    explanation_bn: Optional[str] = ""
    action_draft_bn: Optional[str] = ""

    # Grounding telemetry
    grounding_passed: bool = False
    grounding_retries: int = 0
    grounding_status: str = "NOT_APPLICABLE_OFFLINE"  # PASSED, RETRIED_PASSED, TEMPLATE_FALLBACK, or NOT_APPLICABLE_OFFLINE
    status: str = "PENDING"
    execution_receipt_id: Optional[str] = None

    # AMD GPU & Google Gemma Telemetry & Tool-Calling Trace
    execution_source: str = ExecutionSource.LOCAL_DETERMINISTIC_FALLBACK.value
    http_latency_ms: float = 0.0
    inference_latency_ms: float = 0.0
    endpoint_used: Optional[str] = None
    used_template_fallback: bool = False
    model_name: str = "google/gemma-4-31B-it"
    tool_calls_trace: List[Dict[str, Any]] = Field(default_factory=list)
    grounding_trace: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def impact_taka(self) -> float:
        """Alias for backward-compatibility with existing scripts."""
        return self.impact_usd

    @impact_taka.setter
    def impact_taka(self, val: float):
        self.impact_usd = val

    @property
    def score(self) -> float:
        return self.ranking_score

    @score.setter
    def score(self, val: float):
        self.ranking_score = val

    @property
    def impact_formula(self) -> str:
        return self.formula_display

    @impact_formula.setter
    def impact_formula(self, val: str):
        self.formula_display = val

    @property
    def action_draft(self) -> Optional[str]:
        return self.action_draft_en

    @action_draft.setter
    def action_draft(self, val: Optional[str]):
        self.action_draft_en = val

    @property
    def evidence(self) -> List[Dict[str, Any]]:
        return [row.model_dump() if hasattr(row, 'model_dump') else row for row in self.evidence_rows]
