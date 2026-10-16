"""One-Click Live Action Executor for PayLens Solo.

Dispatches approved actions through:
1. Evolus Business Workflow (dispute notice on connected AMD MI300X Gemma model)
2. Merchant notification webhook (Discord/Slack/REST if MERCHANT_WEBHOOK_URL is set)
3. Generates cryptographic execution receipt for the audit trail.
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from dotenv import load_dotenv

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.schema import RecommendationCard, RecommendationType, LeakSubType
from agent.evolus_bridge import trigger_dispute_workflow_via_evolus

load_dotenv()

MERCHANT_WEBHOOK_URL = os.getenv("MERCHANT_WEBHOOK_URL", "")


def execute_approved_action(
    card: RecommendationCard,
    tone: str = "Polite Reminder",
    edited_message_en: str = "",
    edited_message_bn: str = "",
) -> Dict[str, Any]:
    """Execute the approved action, dispatching to Evolus AI and merchant webhooks."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Trigger Evolus AI Workflow
    evolus_res = trigger_dispute_workflow_via_evolus(
        card=card,
        draft_message_en=edited_message_en or card.action_draft_en or "",
        draft_message_bn=edited_message_bn or card.action_draft_bn or "",
    )

    # 2. Channel Identification
    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        if card.leak_sub_type == LeakSubType.DISPATCHED_UNPAID:
            channel = "bKash / Nagad MFS Reconciliation Gateway"
        else:
            channel = "Steadfast Courier COD Dispute Portal + Evolus Workflow"
    elif card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY:
        channel = "WhatsApp Business API Automated Recovery Link"
    else:
        channel = "ERP Automated Purchase Order Requisition"

    # 3. Optional Merchant Webhook Dispatch (e.g. Discord / Slack / webhook.site)
    webhook_sent = False
    if MERCHANT_WEBHOOK_URL:
        try:
            webhook_payload = {
                "text": f"🚨 [PayLens Action Approved] {card.merchant_name} — {card.title}",
                "card_id": card.card_id,
                "impact_taka": card.impact_taka,
                "formula": card.formula_display,
                "channel": channel,
                "message": edited_message_en or card.action_draft_en,
                "receipt_id": evolus_res.get("receipt_id"),
            }
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(MERCHANT_WEBHOOK_URL, json=webhook_payload)
                webhook_sent = (resp.status_code < 300)
        except Exception:
            webhook_sent = False

    # 4. Generate Cryptographic Audit Receipt
    audit_str = f"{card.card_id}:{card.impact_taka}:{channel}:{timestamp_str}"
    audit_hash = hashlib.sha256(audit_str.encode()).hexdigest()[:12].upper()
    receipt_id = f"PAYLENS-TX-{audit_hash}"

    card.status = "APPROVED & DISPATCHED"
    card.execution_receipt_id = receipt_id

    return {
        "receipt_id": receipt_id,
        "evolus_receipt": evolus_res.get("receipt_id"),
        "channel": channel,
        "merchant_name": card.merchant_name,
        "entity_id": card.entity_id,
        "impact_taka": card.impact_taka,
        "recovered_taka_credited": card.impact_taka,
        "timestamp": timestamp_str,
        "new_status": "APPROVED & DISPATCHED",
        "webhook_dispatched": webhook_sent,
        "message_preview": edited_message_en or card.action_draft_en,
        "audit_hash": audit_hash,
    }
