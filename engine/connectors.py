"""Pluggable Global Payment-Rail Connectors for PayLens Solo.

Decouples fragmented local payment rails from the core accounting & reconciliation engine.
Maps raw export rows from Bangladesh MFS, Brazil Pix, India UPI, and Kenya M-Pesa
into PayLens's canonical DuckDB schema.
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


class MFSWalletConnector(PaymentRailConnector):
    rail_name = "bKash / Nagad MFS"
    country = "🇧🇩 Bangladesh"
    rail_type = "MOBILE_WALLET_MFS"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            amt = float(row.get("amount", 0.0))
            fee = round(amt * 0.015, 2)
            normalized.append({
                "rail_payment_id": f"RP-MFS-{row.get('trxID', i)}",
                "merchant_id": row.get("merchantId", "MERCH_01"),
                "rail_type": "MOBILE_WALLET_MFS",
                "provider": row.get("walletProvider", "bKash"),
                "transaction_ref": row.get("trxID", ""),
                "customer_phone": row.get("senderNumber", "")[-11:],
                "amount_taka": amt,
                "fee_taka": fee,
                "net_amount_taka": round(amt - fee, 2),
                "payment_timestamp": row.get("dateTime", "2026-10-15T12:00:00"),
                "status": "SUCCESS" if row.get("status") in ("COMPLETED", "SUCCESS") else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"trxID": "BKASH9928374", "walletProvider": "bKash", "senderNumber": "01711223344", "merchantId": "MERCH_01", "amount": 12500.0, "status": "COMPLETED", "dateTime": "2026-10-15T14:32:00"},
            {"trxID": "NAGAD1182736", "walletProvider": "Nagad", "senderNumber": "01822334455", "merchantId": "MERCH_01", "amount": 4200.0, "status": "COMPLETED", "dateTime": "2026-10-15T15:10:00"},
        ]


class PaymentGatewayConnector(PaymentRailConnector):
    rail_name = "SSLCommerz / Card Gateway"
    country = "🇧🇩 Bangladesh"
    rail_type = "PAYMENT_GATEWAY"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            amt = float(row.get("total_amount", 0.0))
            fee = round(amt * 0.025, 2)
            normalized.append({
                "rail_payment_id": f"RP-GW-{row.get('bank_tran_id', i)}",
                "merchant_id": row.get("store_id", "MERCH_01"),
                "rail_type": "PAYMENT_GATEWAY",
                "provider": "SSLCommerz",
                "transaction_ref": row.get("tran_id", ""),
                "customer_phone": row.get("cus_phone", "")[-11:],
                "amount_taka": amt,
                "fee_taka": fee,
                "net_amount_taka": round(amt - fee, 2),
                "payment_timestamp": row.get("tran_date", "2026-10-15T12:00:00"),
                "status": "SUCCESS" if row.get("status") == "VALID" else "FAILED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"tran_id": "SSL-TXN-88291", "bank_tran_id": "BT-99201", "store_id": "MERCH_01", "total_amount": 7600.0, "status": "VALID", "cus_phone": "01933445566", "tran_date": "2026-10-15T11:20:00"},
        ]


class CourierCODConnector(PaymentRailConnector):
    rail_name = "Steadfast / RedX COD Courier"
    country = "🇧🇩 Bangladesh"
    rail_type = "COURIER_COD"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            cod = float(row.get("cod_collected", 0.0))
            fee = float(row.get("delivery_charge", 120.0))
            expected = round(cod - fee, 2)
            actual = float(row.get("settled_amount", expected))
            normalized.append({
                "settlement_id": f"SETTLE-{row.get('consignment_id', i)}",
                "merchant_id": row.get("merchant_id", "MERCH_01"),
                "courier_name": row.get("courier", "Steadfast Courier"),
                "consignment_id": row.get("consignment_id", ""),
                "order_id": row.get("invoice_order_id", ""),
                "cod_collected_taka": cod,
                "courier_fee_taka": fee,
                "return_fee_taka": 0.0,
                "expected_net_payout_taka": expected,
                "actual_settled_taka": actual,
                "settlement_date": row.get("payout_date", "2026-10-15"),
                "dispute_status": "DISPUTED" if (expected - actual) > 5.0 else "SETTLED",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"consignment_id": "CONS-8001", "courier": "Steadfast Courier", "invoice_order_id": "ORD-COD-SHORT-1001", "merchant_id": "MERCH_01", "cod_collected": 7200.0, "delivery_charge": 130.0, "settled_amount": 5820.0, "payout_date": "2026-10-15"},
        ]


class BrazilPixConnector(PaymentRailConnector):
    rail_name = "Brazil Pix (Banco Central)"
    country = "🇧🇷 Brazil"
    rail_type = "INSTANT_PAYMENT_PIX"

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        normalized = []
        for i, row in enumerate(raw_data):
            val_brl = float(row.get("valor", 0.0))
            # Exchange rate to Taka for canonical comparison (1 BRL ~ 23 BDT)
            amt_taka = round(val_brl * 23.0, 2)
            normalized.append({
                "rail_payment_id": f"RP-PIX-{row.get('endToEndId', i)[:12]}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_BR"),
                "rail_type": "INSTANT_PAYMENT_PIX",
                "provider": "Banco Central Pix",
                "transaction_ref": row.get("endToEndId", ""),
                "customer_phone": row.get("chavePix", ""),
                "amount_taka": amt_taka,
                "fee_taka": 0.0,
                "net_amount_taka": amt_taka,
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
            amt_taka = round(val_inr * 1.45, 2)  # 1 INR ~ 1.45 BDT
            normalized.append({
                "rail_payment_id": f"RP-UPI-{row.get('npciTxnId', i)}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_IN"),
                "rail_type": "INSTANT_PAYMENT_UPI",
                "provider": "NPCI UPI Gateway",
                "transaction_ref": row.get("npciTxnId", ""),
                "customer_phone": row.get("payerVpa", ""),
                "amount_taka": amt_taka,
                "fee_taka": 0.0,
                "net_amount_taka": amt_taka,
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
            amt_taka = round(val_kes * 0.95, 2)  # 1 KES ~ 0.95 BDT
            normalized.append({
                "rail_payment_id": f"RP-MPESA-{row.get('MpesaReceiptNumber', i)}",
                "merchant_id": row.get("merchant_id", "MERCH_GLOBAL_KE"),
                "rail_type": "MOBILE_WALLET_MPESA",
                "provider": "Safaricom M-Pesa",
                "transaction_ref": row.get("MpesaReceiptNumber", ""),
                "customer_phone": str(row.get("PhoneNumber", ""))[-9:],
                "amount_taka": amt_taka,
                "fee_taka": round(amt_taka * 0.012, 2),
                "net_amount_taka": round(amt_taka * 0.988, 2),
                "payment_timestamp": "2026-10-15T14:30:00",
                "status": "SUCCESS",
            })
        return pd.DataFrame(normalized)

    def get_sample_raw_payload(self) -> List[Dict[str, Any]]:
        return [
            {"MpesaReceiptNumber": "NLJ7RT61SV", "PhoneNumber": 254712345678, "Amount": 3500.0, "TransactionDate": 20261015143000},
        ]


CONNECTOR_REGISTRY: Dict[str, PaymentRailConnector] = {
    "bd_mfs": MFSWalletConnector(),
    "bd_gateway": PaymentGatewayConnector(),
    "bd_courier_cod": CourierCODConnector(),
    "brazil_pix": BrazilPixConnector(),
    "india_upi": IndiaUPIConnector(),
    "kenya_mpesa": KenyaMPesaConnector(),
}
