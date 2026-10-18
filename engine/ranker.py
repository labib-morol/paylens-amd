"""Deterministic Multi-Objective Card Ranker for PayLens.

Architecture Rule 1: CODE COMPUTES, MODEL EXPLAINS.
Ranking scores (impact * confidence * goal_weight) are computed purely in Python.
"""

import sys
from pathlib import Path
from typing import List

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.schema import RecommendationCard, RecommendationType, GoalWeights

PRESET_GOAL_WEIGHTS = {
    "Urgent Cash Recovery (High Cash)": GoalWeights(
        cash_now_weight=0.80, margin_protection_weight=0.10, stock_availability_weight=0.10
    ),
    "Protect Profit Margins (High Margin)": GoalWeights(
        cash_now_weight=0.15, margin_protection_weight=0.70, stock_availability_weight=0.15
    ),
    "Prevent Stockouts (High Inventory Cover)": GoalWeights(
        cash_now_weight=0.10, margin_protection_weight=0.20, stock_availability_weight=0.70
    ),
}


def get_applicable_weight(card: RecommendationCard, goal_weights: GoalWeights) -> float:
    """Determine the applicable goal weight based on recommendation category."""
    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        return goal_weights.cash_now_weight
    elif card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY:
        # Cash recovery with minor margin sensitivity
        return goal_weights.cash_now_weight
    elif card.rec_type == RecommendationType.STOCKOUT_RISK:
        # Driven by stock availability and margin protection
        return round(0.5 * goal_weights.stock_availability_weight + 0.5 * goal_weights.margin_protection_weight, 4)
    return goal_weights.cash_now_weight


def rank_cards(
    cards: List[RecommendationCard],
    goal_weights: GoalWeights,
) -> List[RecommendationCard]:
    """Score each card using impact * confidence * applicable_weight and sort descending."""
    scored_cards: List[RecommendationCard] = []

    for card in cards:
        weight = get_applicable_weight(card, goal_weights)
        score = round(card.impact_taka * card.confidence * weight, 2)
        card.ranking_score = score
        scored_cards.append(card)

    scored_cards.sort(key=lambda c: c.ranking_score, reverse=True)
    return scored_cards


__all__ = ["rank_cards", "get_applicable_weight", "PRESET_GOAL_WEIGHTS"]
