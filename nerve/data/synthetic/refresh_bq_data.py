"""
Run this script to refresh all BigQuery tables with current dates.
Usage: python refresh_bq_data.py
"""
from google.cloud import bigquery
from datetime import date, timedelta
import os, sys

# ── setup ──────────────────────────────────────────────────────────────────
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "nerve-agent-496707")
client = bigquery.Client(project="nerve-agent-496707")
DS = "nerve-agent-496707.nerve_data"
TODAY = date.today()

def insert(table: str, rows: list):
    errors = client.insert_rows_json(f"{DS}.{table}", rows)
    if errors:
        print(f"  ✗ {table}: {errors}")
    else:
        print(f"  ✓ {table}: {len(rows)} rows inserted")

def ensure_table(table: str, schema: list):
    table_ref = f"{DS}.{table}"
    tbl = bigquery.Table(table_ref, schema=schema)
    try:
        client.create_table(tbl)
        print(f"  + created {table}")
    except Exception:
        pass  # already exists

# ── ensure all required tables exist ────────────────────────────────────────
print("Ensuring tables exist...")

ensure_table("shopify_inventory", [
    bigquery.SchemaField("sku_id", "STRING"),
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("inventory_units", "INTEGER"),
    bigquery.SchemaField("unit_cost", "FLOAT"),
    bigquery.SchemaField("last_sold_date", "DATE"),
])

ensure_table("cash_flow", [
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("bank_balance", "FLOAT"),
    bigquery.SchemaField("upcoming_payroll", "FLOAT"),
    bigquery.SchemaField("upcoming_rent", "FLOAT"),
    bigquery.SchemaField("upcoming_gst", "FLOAT"),
    bigquery.SchemaField("pending_receivable", "FLOAT"),
    bigquery.SchemaField("days_until_due", "INTEGER"),
    bigquery.SchemaField("daily_burn_rate", "FLOAT"),
])

ensure_table("shopify_orders", [
    bigquery.SchemaField("order_id", "STRING"),
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("revenue", "FLOAT"),
    bigquery.SchemaField("cost_price", "FLOAT"),
    bigquery.SchemaField("return_rate", "FLOAT"),
    bigquery.SchemaField("order_date", "DATE"),
])

ensure_table("ad_spend", [
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("ad_cost", "FLOAT"),
    bigquery.SchemaField("platform", "STRING"),
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("unbilled", "BOOLEAN"),
    bigquery.SchemaField("expected_charge_date", "DATE"),
])

ensure_table("quickbooks_payables", [
    bigquery.SchemaField("vendor_name", "STRING"),
    bigquery.SchemaField("amount", "FLOAT"),
    bigquery.SchemaField("due_date", "DATE"),
    bigquery.SchemaField("status", "STRING"),
])

ensure_table("chat_sessions", [
    bigquery.SchemaField("session_id", "STRING"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
    bigquery.SchemaField("messages", "STRING"),
    bigquery.SchemaField("is_deleted", "BOOLEAN"),
])

print("\nInserting fresh data with today's dates...")

# ── shopify_inventory (zombie SKUs — not sold in 30+ days) ──────────────────
insert("shopify_inventory", [
    {
        "sku_id": "SKU001",
        "product_name": "Kundan Choker Set",
        "inventory_units": 24,
        "unit_cost": 4200.0,
        "last_sold_date": (TODAY - timedelta(days=45)).isoformat(),
    },
    {
        "sku_id": "SKU002",
        "product_name": "Polki Jhumka Pair",
        "inventory_units": 18,
        "unit_cost": 3100.0,
        "last_sold_date": (TODAY - timedelta(days=38)).isoformat(),
    },
    {
        "sku_id": "SKU003",
        "product_name": "Meenakari Bangles Set",
        "inventory_units": 30,
        "unit_cost": 1800.0,
        "last_sold_date": (TODAY - timedelta(days=60)).isoformat(),
    },
    {
        "sku_id": "SKU004",
        "product_name": "Pearl Choker Necklace",
        "inventory_units": 12,
        "unit_cost": 5500.0,
        "last_sold_date": (TODAY - timedelta(days=10)).isoformat(),  # healthy
    },
    {
        "sku_id": "SKU005",
        "product_name": "Gold Plated Maang Tikka",
        "inventory_units": 8,
        "unit_cost": 2400.0,
        "last_sold_date": (TODAY - timedelta(days=5)).isoformat(),   # healthy
    },
])

# ── cash_flow ────────────────────────────────────────────────────────────────
insert("cash_flow", [
    {
        "date": TODAY.isoformat(),
        "bank_balance": 320000.0,
        "upcoming_payroll": 85000.0,
        "upcoming_rent": 45000.0,
        "upcoming_gst": 32000.0,
        "pending_receivable": 28000.0,
        "days_until_due": 12,
        "daily_burn_rate": 11000.0,
    }
])

# ── shopify_orders (last 60 days — current + previous period for margin) ─────
recent_orders = []
prev_orders = []

products = [
    ("Kundan Choker Set", 8500, 4200),
    ("Polki Jhumka Pair", 6200, 3100),
    ("Pearl Choker Necklace", 11000, 5500),
    ("Gold Plated Maang Tikka", 4800, 2400),
    ("Bridal Jewellery Set", 22000, 9800),
]

# Recent 30 days — lower margin (CRITICAL drift)
for i, (name, rev, cost) in enumerate(products):
    for j in range(6):
        recent_orders.append({
            "order_id": f"ORD-R-{i}-{j}",
            "product_name": name,
            "revenue": float(rev),
            "cost_price": float(cost * 1.3),  # costs crept up = margin drift
            "return_rate": 0.12,
            "order_date": (TODAY - timedelta(days=j * 4 + 1)).isoformat(),
        })

# Previous 30-60 days — better margin
for i, (name, rev, cost) in enumerate(products):
    for j in range(6):
        prev_orders.append({
            "order_id": f"ORD-P-{i}-{j}",
            "product_name": name,
            "revenue": float(rev),
            "cost_price": float(cost),
            "return_rate": 0.05,
            "order_date": (TODAY - timedelta(days=31 + j * 4)).isoformat(),
        })

insert("shopify_orders", recent_orders + prev_orders)

# ── ad_spend (unbilled charges that will auto-hit) ───────────────────────────
insert("ad_spend", [
    {
        "product_name": "Kundan Choker Set",
        "ad_cost": 38000.0,
        "platform": "Meta",
        "date": (TODAY - timedelta(days=2)).isoformat(),
        "unbilled": True,
        "expected_charge_date": (TODAY + timedelta(days=3)).isoformat(),
    },
    {
        "product_name": "Polki Jhumka Pair",
        "ad_cost": 27000.0,
        "platform": "Google",
        "date": (TODAY - timedelta(days=3)).isoformat(),
        "unbilled": True,
        "expected_charge_date": (TODAY + timedelta(days=4)).isoformat(),
    },
    {
        "product_name": "Bridal Jewellery Set",
        "ad_cost": 15000.0,
        "platform": "Meta",
        "date": (TODAY - timedelta(days=1)).isoformat(),
        "unbilled": False,
        "expected_charge_date": (TODAY - timedelta(days=1)).isoformat(),
    },
])

# ── quickbooks_payables (upcoming vendor bills) ──────────────────────────────
insert("quickbooks_payables", [
    {
        "vendor_name": "Rajasthan Gems & Crafts",
        "amount": 95000.0,
        "due_date": (TODAY + timedelta(days=8)).isoformat(),
        "status": "pending",
    },
    {
        "vendor_name": "Mumbai Packaging Co.",
        "amount": 22000.0,
        "due_date": (TODAY + timedelta(days=14)).isoformat(),
        "status": "pending",
    },
    {
        "vendor_name": "Gold Wire Suppliers Ltd",
        "amount": 140000.0,
        "due_date": (TODAY + timedelta(days=21)).isoformat(),
        "status": "pending",
    },
])

print("\n✅ All tables refreshed with current dates!")
print(f"   Today: {TODAY}")
print("   Redeploy your backend or wait 30s for Cloud Run to pick up changes.")
