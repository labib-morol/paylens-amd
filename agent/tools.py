"""OpenAI Tool Schemas and Execution Helpers for PayLens Solo.

Backed by DuckDB and engine/pipeline data sources.
Provides ground-truth retrieval tools for the Gemma agent on AMD Instinct.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _get_con(duckdb_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    if duckdb_path is None:
        duckdb_path = os.getenv("DUCKDB_PATH", os.path.join(ROOT_DIR, "data", "generated", "paylens.duckdb"))
    return duckdb.connect(duckdb_path, read_only=True)


def get_order(order_id: str, duckdb_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve complete order record by order ID."""
    con = _get_con(duckdb_path)
    try:
        df = con.execute("SELECT * FROM orders WHERE order_id = ?", [order_id]).df()
        if df.empty:
            return None
        row = df.iloc[0].to_dict()
        # Convert non-serializable objects
        return {k: (v if not hasattr(v, "isoformat") else v.isoformat()) for k, v in row.items()}
    finally:
        con.close()


def get_payments(
    merchant_id: str,
    phone: Optional[str] = None,
    transaction_ref: Optional[str] = None,
    duckdb_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve rail payment records matching merchant_id and optionally phone or transaction_ref."""
    con = _get_con(duckdb_path)
    try:
        query = "SELECT * FROM rail_payments WHERE merchant_id = ?"
        params: List[Any] = [merchant_id]

        if transaction_ref:
            query += " AND transaction_ref = ?"
            params.append(transaction_ref)
        elif phone:
            # Match on clean 11 digits
            clean_digits = "".join([c for c in phone if c.isdigit()])[-11:]
            query += " AND customer_phone LIKE ?"
            params.append(f"%{clean_digits}%")

        df = con.execute(query, params).df()
        return df.to_dict(orient="records")
    finally:
        con.close()


def get_settlement(
    consignment_id: Optional[str] = None,
    order_id: Optional[str] = None,
    duckdb_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve courier settlement details by consignment ID or order ID."""
    con = _get_con(duckdb_path)
    try:
        if consignment_id:
            df = con.execute("SELECT * FROM courier_settlements WHERE consignment_id = ?", [consignment_id]).df()
        elif order_id:
            df = con.execute("SELECT * FROM courier_settlements WHERE order_id = ?", [order_id]).df()
        else:
            return None

        if df.empty:
            return None
        row = df.iloc[0].to_dict()
        return {k: (v if not hasattr(v, "isoformat") else v.isoformat()) for k, v in row.items()}
    finally:
        con.close()


def get_forecast(
    merchant_id: str,
    sku: str,
    duckdb_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve inventory snapshot and demand summary for a SKU."""
    con = _get_con(duckdb_path)
    try:
        df = con.execute(
            """
            SELECT * FROM inventory_daily 
            WHERE merchant_id = ? AND sku = ? 
            ORDER BY snapshot_date ASC
            """,
            [merchant_id, sku],
        ).df()

        if df.empty:
            return None

        latest = df.iloc[-1].to_dict()
        recent_sales = df["units_sold_today"].tail(7).tolist()
        total_30d_sales = int(df["units_sold_today"].sum())

        return {
            "merchant_id": merchant_id,
            "sku": sku,
            "item_name": latest["item_name"],
            "category": latest["category"],
            "current_stock": int(latest["current_stock"]),
            "unit_cost_taka": float(latest["unit_cost_taka"]),
            "unit_retail_price_taka": float(latest["unit_retail_price_taka"]),
            "unit_margin_taka": float(latest["unit_margin_taka"]),
            "supplier_lead_time_days": int(latest["supplier_lead_time_days"]),
            "reorder_point_units": int(latest["reorder_point_units"]),
            "recent_7d_sales": recent_sales,
            "total_30d_sales": total_30d_sales,
            "snapshot_date": str(latest["snapshot_date"]),
        }
    finally:
        con.close()


# OpenAI Tool Definitions for Gemma Function Calling
OPENAI_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up an order by order_id to inspect amount, status, customer, and payment rail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g. ORD-1042"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payments",
            "description": "Search rail payment records by merchant ID and customer phone or transaction reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string", "description": "Merchant ID, e.g. MERCH_01"},
                    "phone": {"type": "string", "description": "Customer phone number to match"},
                    "transaction_ref": {"type": "string", "description": "Transaction reference string"},
                },
                "required": ["merchant_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_settlement",
            "description": "Retrieve courier settlement records to inspect collected COD, fees, expected net payout, and actual settled amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consignment_id": {"type": "string", "description": "Courier consignment ID, e.g. CONS-SHORT-8001"},
                    "order_id": {"type": "string", "description": "Associated order ID"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Retrieve SKU inventory status, lead times, margins, and sales velocity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string", "description": "Merchant ID"},
                    "sku": {"type": "string", "description": "Product SKU code"},
                },
                "required": ["merchant_id", "sku"],
            },
        },
    },
]


def execute_tool(name: str, arguments: Dict[str, Any], duckdb_path: Optional[str] = None) -> Any:
    """Execute a tool by name with provided arguments."""
    if name == "get_order":
        return get_order(arguments.get("order_id", ""), duckdb_path=duckdb_path)
    elif name == "get_payments":
        return get_payments(
            merchant_id=arguments.get("merchant_id", ""),
            phone=arguments.get("phone"),
            transaction_ref=arguments.get("transaction_ref"),
            duckdb_path=duckdb_path,
        )
    elif name == "get_settlement":
        return get_settlement(
            consignment_id=arguments.get("consignment_id"),
            order_id=arguments.get("order_id"),
            duckdb_path=duckdb_path,
        )
    elif name == "get_forecast":
        return get_forecast(
            merchant_id=arguments.get("merchant_id", ""),
            sku=arguments.get("sku", ""),
            duckdb_path=duckdb_path,
        )
    else:
        return {"error": f"Unknown tool: {name}"}
