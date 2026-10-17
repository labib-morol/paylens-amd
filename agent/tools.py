"""OpenAI Tool Schemas and Execution Helpers for PayLens.

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
            clean_digits = "".join([c for c in phone if c.isdigit()])[-10:]
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
    """Retrieve carrier settlement details by consignment ID or order ID."""
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

        margin = latest.get("unit_margin_usd", latest.get("unit_margin_taka", 0.0))
        cost = latest.get("unit_cost_usd", latest.get("unit_cost_taka", 0.0))
        price = latest.get("unit_retail_price_usd", latest.get("unit_retail_price_taka", 0.0))
        lead_time = latest.get("supplier_lead_time_days", 7)
        curr_stock = latest.get("current_stock", 0)
        reorder_point = int(latest.get("reorder_point_units", lead_time * 10))

        return {
            "merchant_id": merchant_id,
            "sku": sku,
            "item_name": str(latest.get("item_name", sku)),
            "category": str(latest.get("category", "General")),
            "current_stock": int(curr_stock),
            "unit_cost_usd": float(cost),
            "unit_retail_price_usd": float(price),
            "unit_margin_usd": float(margin),
            "supplier_lead_time_days": int(lead_time),
            "reorder_point_units": reorder_point,
            "recent_7d_sales": recent_sales,
            "total_30d_sales": total_30d_sales,
            "snapshot_date": str(latest.get("snapshot_date", "")),
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
                "properties": {"order_id": {"type": "string", "description": "e.g. ORD-1042"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payments",
            "description": "Look up payment rail settlement records for a merchant by transaction ref or customer phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string"},
                    "transaction_ref": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["merchant_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_settlement",
            "description": "Look up carrier COD remittance details by consignment ID or order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consignment_id": {"type": "string"},
                    "order_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Retrieve 30-day sales history, current stock, and lead time for a SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string"},
                    "sku": {"type": "string"},
                },
                "required": ["merchant_id", "sku"],
            },
        },
    },
]


def execute_tool(name: str, arguments: Dict[str, Any], duckdb_path: Optional[str] = None) -> Any:
    """Execute a function call by name with provided arguments."""
    if name == "get_order":
        return get_order(arguments.get("order_id", ""), duckdb_path)
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
        raise ValueError(f"Unknown tool name: {name}")
