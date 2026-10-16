"""Pluggable Global Payment-Rail Connectors for PayLens Solo.

Decouples fragmented regional and global payment rails from the core accounting & reconciliation engine.
Maps raw export rows from Stripe, PayPal, DHL/FedEx COD, Brazil Pix, India UPI, Kenya M-Pesa,
and Bangladesh MFS into PayLens's canonical DuckDB schema.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
import pandas as pd


class PaymentRailConnector(ABC):
    """Abstract interface for multi-rail normalization."""

    @property
    @abstractmethod
    def rail_name(self) -> str:
        pass

    @property
    @abstractmethod
    def country(self) -> str:
        pass

    @property
    @abstractmethod
    def rail_type(self) -> str:
        pass

    @abstractmethod
    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transforms raw vendor payload into canonical DuckDB schema."""
        pass

    @abstractmethod
    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        """Returns sample raw payload for UI inspection."""
        pass


class StripeGatewayConnector(PaymentRailConnector):
    rail_name = "Stripe Gateway (Global)"
    country = "🌐 Global / US / EU"
    rail_type = "PAYMENT_GATEWAY"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            amt = float(row.get("amount", 0.0)) / 100.0 if row.get("amount", 0) > 1000 else float(row.get("amount", 0.0))
            fee = round(amt * 0.029 + 0.30, 2)
            normalized.append({
                "rail_payment_id": f"RP-STRIPE-{row.get('id', i)[-8:]}",
                "merchant_id": row.get("metadata", {}).get("merchant_id", "MERCH_01"),
                "rail_type": "PAYMENT_GATEWAY",
                "provider": "Stripe",
                "transaction_ref": row.get("id", ""),
                "customer_email": row.get("billing_details", {}).get("email", row.get("customer_email", "")),
                "customer_phone": row.get("billing_details", {}).get("phone", row.get("customer_phone", "")),
                "amount_usd": amt,
                "amount_taka": amt,
                "fee_usd": fee,
                "net_amount_usd": round(amt - fee, 2),
                "payment_timestamp": row.get("created_at", "2026-10-15T12:00:00Z"),
                "status": "SUCCESS" if row.get("status") == "succeeded" else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"id": "ch_3Nabc123XYZ", "amount": 27500, "currency": "usd", "status": "succeeded", "customer_email": "sophia.chen@gmail.com", "customer_phone": "+1-415-555-0182", "created_at": "2026-10-15T14:22:00Z", "metadata": {"merchant_id": "MERCH_01"}},
            {"id": "ch_3Ndef456UVW", "amount": 9500, "currency": "usd", "status": "succeeded", "customer_email": "lucas.muller@outlook.com", "customer_phone": "+1-212-555-0199", "created_at": "2026-10-15T15:10:00Z", "metadata": {"merchant_id": "MERCH_01"}},
        ]


class PayPalWalletConnector(PaymentRailConnector):
    rail_name = "PayPal Commerce Platform"
    country = "🌐 Global / US / EU"
    rail_type = "DIGITAL_WALLET"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            amt = float(row.get("amount", {}).get("value", row.get("amount_value", 0.0)))
            fee = round(amt * 0.0349 + 0.49, 2)
            normalized.append({
                "rail_payment_id": f"RP-PP-{row.get('id', i)[-8:]}",
                "merchant_id": row.get("custom_id", "MERCH_02"),
                "rail_type": "DIGITAL_WALLET",
                "provider": "PayPal",
                "transaction_ref": row.get("id", ""),
                "customer_email": row.get("payer", {}).get("email_address", row.get("payer_email", "")),
                "customer_phone": row.get("payer", {}).get("phone", row.get("payer_phone", "")),
                "amount_usd": amt,
                "amount_taka": amt,
                "fee_usd": fee,
                "net_amount_usd": round(amt - fee, 2),
                "payment_timestamp": row.get("create_time", "2026-10-15T12:00:00Z"),
                "status": "SUCCESS" if row.get("status") == "COMPLETED" else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"id": "PAYPAL-99201928", "status": "COMPLETED", "amount_value": 480.0, "currency": "USD", "payer_email": "alex.vance@gmail.com", "custom_id": "MERCH_02", "create_time": "2026-10-15T16:45:00Z"},
        ]


class DHLCourierCODConnector(PaymentRailConnector):
    rail_name = "DHL Express Commercial COD"
    country = "🌐 Global / International"
    rail_type = "COURIER_COD"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            cod = float(row.get("cod_amount_collected", 0.0))
            fee = float(row.get("dhl_handling_fee", 24.0))
            expected = round(cod - fee, 2)
            actual = float(row.get("net_remittance", expected))
            normalized.append({
                "settlement_id": f"SETTLE-DHL-{row.get('waybill_number', i)[-6:]}",
                "merchant_id": row.get("merchant_account", "MERCH_02"),
                "courier_name": "DHL Express",
                "consignment_id": row.get("waybill_number", ""),
                "order_id": row.get("customer_reference", ""),
                "cod_collected_usd": cod,
                "courier_fee_usd": fee,
                "expected_net_payout_usd": expected,
                "actual_settled_usd": actual,
                "shortfall_usd": round(max(0.0, expected - actual), 2),
                "settlement_date": row.get("remittance_date", "2026-10-15"),
                "dispute_status": "DISPUTED" if (expected - actual) > 5.0 else "SETTLED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"waybill_number": "DHL-AWB-8839201", "customer_reference": "ORD-COD-SHORT-3143", "merchant_account": "MERCH_02", "cod_amount_collected": 850.0, "dhl_handling_fee": 44.0, "net_remittance": 686.0, "remittance_date": "2026-10-15"},
        ]


class BrazilPixConnector(PaymentRailConnector):
    rail_name = "Brazil Pix (Banco Central)"
    country = "🇧🇷 Brazil"
    rail_type = "INSTANT_PAYMENT_PIX"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            val_brl = float(row.get("valor", 0.0))
            amt_usd = round(val_brl * 0.18, 2)  # 1 BRL ~ 0.18 USD
            normalized.append({
                "rail_payment_id": f"RP-PIX-{row.get('endToEndId', i)[:12]}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_BR"),
                "rail_type": "INSTANT_PAYMENT_PIX",
                "provider": "Banco Central Pix",
                "transaction_ref": row.get("endToEndId", ""),
                "customer_phone": row.get("chavePix", ""),
                "amount_usd": amt_usd,
                "amount_taka": amt_usd,
                "fee_usd": 0.0,
                "net_amount_usd": amt_usd,
                "payment_timestamp": row.get("horario", "2026-10-15T12:00:00Z"),
                "status": "SUCCESS" if row.get("status", "CONCLUIDA") == "CONCLUIDA" else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"endToEndId": "E00038166202610151200", "chavePix": "+5511999887766", "valor": 350.0, "status": "CONCLUIDA", "horario": "2026-10-15T12:00:00Z"},
            {"endToEndId": "E00038166202610151201", "chavePix": "+5521988776655", "valor": 120.0, "status": "CONCLUIDA", "horario": "2026-10-15T12:15:00Z"},
        ]


class IndiaUPIConnector(PaymentRailConnector):
    rail_name = "India UPI (NPCI Protocol)"
    country = "🇮🇳 India"
    rail_type = "INSTANT_PAYMENT_UPI"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            val_inr = float(row.get("txnAmount", 0.0))
            amt_usd = round(val_inr * 0.012, 2)  # 1 INR ~ 0.012 USD
            normalized.append({
                "rail_payment_id": f"RP-UPI-{row.get('npciTxnId', i)}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_IN"),
                "rail_type": "INSTANT_PAYMENT_UPI",
                "provider": "NPCI UPI Gateway",
                "transaction_ref": row.get("npciTxnId", ""),
                "customer_phone": row.get("payerVpa", ""),
                "amount_usd": amt_usd,
                "amount_taka": amt_usd,
                "fee_usd": 0.0,
                "net_amount_usd": amt_usd,
                "payment_timestamp": row.get("txnDate", "2026-10-15T12:00:00"),
                "status": "SUCCESS" if row.get("status") == "SUCCESS" else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"npciTxnId": "UPI-IND-88392019", "payerVpa": "customer@okhdfcbank", "merchantVpa": "store@icici", "txnAmount": 4200.0, "status": "SUCCESS", "txnDate": "2026-10-15T14:10:00"},
        ]


class KenyaMPesaConnector(PaymentRailConnector):
    rail_name = "Kenya M-Pesa (Safaricom Daraja)"
    country = "🇰🇪 Kenya"
    rail_type = "MOBILE_WALLET_MPESA"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            val_kes = float(row.get("Amount", 0.0))
            amt_usd = round(val_kes * 0.0078, 2)  # 1 KES ~ 0.0078 USD
            normalized.append({
                "rail_payment_id": f"RP-MPESA-{row.get('MpesaReceiptNumber', i)}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_KE"),
                "rail_type": "MOBILE_WALLET_MPESA",
                "provider": "Safaricom M-Pesa",
                "transaction_ref": row.get("MpesaReceiptNumber", ""),
                "customer_phone": str(row.get("PhoneNumber", ""))[-9:],
                "amount_usd": amt_usd,
                "amount_taka": amt_usd,
                "fee_usd": round(amt_usd * 0.012, 2),
                "net_amount_usd": round(amt_usd * 0.988, 2),
                "payment_timestamp": "2026-10-15T14:30:00",
                "status": "SUCCESS",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"MpesaReceiptNumber": "NLJ7RT61SV", "PhoneNumber": 254712345678, "Amount": 3500.0, "TransactionDate": 20261015143000},
        ]


class MFSWalletConnector(PaymentRailConnector):
    rail_name = "bKash / Nagad MFS (Bangladesh)"
    country = "🇧🇩 Bangladesh"
    rail_type = "MOBILE_WALLET_MFS"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            amt_bdt = float(row.get("amount", 0.0))
            amt_usd = round(amt_bdt / 120.0, 2)
            fee_usd = round(amt_usd * 0.015, 2)
            normalized.append({
                "rail_payment_id": f"RP-MFS-{row.get('trxID', i)}",
                "merchant_id": row.get("merchantId", "MERCH_01"),
                "rail_type": "MOBILE_WALLET_MFS",
                "provider": row.get("walletProvider", "bKash"),
                "transaction_ref": row.get("trxID", ""),
                "customer_phone": row.get("senderNumber", "")[-11:],
                "amount_usd": amt_usd,
                "amount_taka": amt_bdt,
                "fee_usd": fee_usd,
                "net_amount_usd": round(amt_usd - fee_usd, 2),
                "payment_timestamp": row.get("dateTime", "2026-10-15T12:00:00"),
                "status": "SUCCESS" if row.get("status") in ("COMPLETED", "SUCCESS") else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"trxID": "BKASH9928374", "walletProvider": "bKash", "senderNumber": "01711223344", "merchantId": "MERCH_01", "amount": 12500.0, "status": "COMPLETED", "dateTime": "2026-10-15T14:32:00"},
        ]


CONNECTOR_REGISTRY: Dict[str, PaymentRailConnector] = {
    "stripe_gateway": StripeGatewayConnector(),
    "paypal_wallet": PayPalWalletConnector(),
    "dhl_fedex_cod": DHLCourierCODConnector(),
    "brazil_pix": BrazilPixConnector(),
    "india_upi": IndiaUPIConnector(),
    "kenya_mpesa": KenyaMPesaConnector(),
    "bd_mfs": MFSWalletConnector(),
}
