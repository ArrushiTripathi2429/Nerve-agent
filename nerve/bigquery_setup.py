from google.cloud import bigquery
import pandas as pd
from datetime import date, timedelta
import random

client = bigquery.Client(project="nerve-agent-496707")
dataset_id = "nerve-agent-496707.nerve_data"


# 1A. shopify_orders — add quantity, cost_price, inventory_level
shopify_orders_schema = [
    bigquery.SchemaField("order_id", "STRING"),
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("revenue", "FLOAT"),
    bigquery.SchemaField("return_rate", "FLOAT"),
    bigquery.SchemaField("order_date", "DATE"),
    bigquery.SchemaField("quantity", "INTEGER"),        # NEW
    bigquery.SchemaField("cost_price", "FLOAT"),        # NEW — margin calculation
    bigquery.SchemaField("category", "STRING"),         # NEW
]

# 1B. ad_spend — add unbilled column
ad_spend_schema = [
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("ad_cost", "FLOAT"),
    bigquery.SchemaField("platform", "STRING"),
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("unbilled", "BOOLEAN"),        # NEW — Phantom Liability
    bigquery.SchemaField("expected_charge_date", "DATE"), # NEW
]

# 1C. cash_flow — add daily_burn_rate
cash_flow_schema = [
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("bank_balance", "FLOAT"),
    bigquery.SchemaField("upcoming_payroll", "FLOAT"),
    bigquery.SchemaField("upcoming_rent", "FLOAT"),
    bigquery.SchemaField("upcoming_gst", "FLOAT"),
    bigquery.SchemaField("pending_receivable", "FLOAT"),
    bigquery.SchemaField("days_until_due", "INTEGER"),
    bigquery.SchemaField("daily_burn_rate", "FLOAT"),   # NEW
]

# 1D. stripe_fees — keep same
stripe_fees_schema = [
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("stripe_fee", "FLOAT"),
    bigquery.SchemaField("date", "DATE"),
]

# ─────────────────────────────────────────
# STEP 2: NEW TABLES
# ─────────────────────────────────────────

# 2A. shopify_inventory
shopify_inventory_schema = [
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("sku_id", "STRING"),
    bigquery.SchemaField("inventory_units", "INTEGER"),
    bigquery.SchemaField("unit_cost", "FLOAT"),         # cost per unit
    bigquery.SchemaField("last_sold_date", "DATE"),     # Zombie SKU detection
    bigquery.SchemaField("category", "STRING"),
]

# 2B. quickbooks_payables
quickbooks_payables_schema = [
    bigquery.SchemaField("invoice_id", "STRING"),
    bigquery.SchemaField("vendor_name", "STRING"),
    bigquery.SchemaField("amount", "FLOAT"),
    bigquery.SchemaField("due_date", "DATE"),
    bigquery.SchemaField("category", "STRING"),         # payroll, raw_material, rent
    bigquery.SchemaField("status", "STRING"),           # pending, paid
]

# ─────────────────────────────────────────
# STEP 3: DELETE OLD + CREATE NEW TABLES
# ─────────────────────────────────────────

tables_to_create = {
    "shopify_orders": shopify_orders_schema,
    "ad_spend": ad_spend_schema,
    "cash_flow": cash_flow_schema,
    "stripe_fees": stripe_fees_schema,
    "shopify_inventory": shopify_inventory_schema,
    "quickbooks_payables": quickbooks_payables_schema,
}

print("Creating tables...")
for table_name, schema in tables_to_create.items():
    table_ref = f"{dataset_id}.{table_name}"
    
    # Delete if exists
    client.delete_table(table_ref, not_found_ok=True)
    print(f"  Deleted old {table_name}")
    
    # Create new
    table = bigquery.Table(table_ref, schema=schema)
    client.create_table(table)
    print(f"  Created {table_name} ")

# ─────────────────────────────────────────
# STEP 4: INJECT SYNTHETIC DATA
# ─────────────────────────────────────────

today = date.today()

# ── 4A. shopify_orders ──
print("\nInjecting shopify_orders...")
products = [
    ("Classic Tan Wallet", 899, 420, "wallets"),
    ("Black Leather Belt", 1299, 580, "belts"),
    ("Canvas Backpack", 2499, 1100, "bags"),
    ("Minimalist Watch", 4999, 2100, "accessories"),
    ("Tan Wallet Pro", 1199, 560, "wallets"),  # Another zombie
]

orders_rows = []
for i in range(120):
    prod = random.choice(products[:3])  # Only first 3 sell — last 2 are zombies
    order_date = today - timedelta(days=random.randint(1, 60))
    qty = random.randint(1, 5)
    orders_rows.append({
        "order_id": f"ORD-{1000+i}",
        "product_name": prod[0],
        "revenue": prod[1] * qty,
        "return_rate": round(random.uniform(0.05, 0.18), 2),
        "order_date": order_date.isoformat(),
        "quantity": qty,
        "cost_price": prod[2] * qty,
        "category": prod[3],
    })

errors = client.insert_rows_json(f"{dataset_id}.shopify_orders", orders_rows)
print(f"  shopify_orders: {len(orders_rows)} rows {'✅' if not errors else errors}")

# ── 4B. shopify_inventory ──
print("Injecting shopify_inventory...")
inventory_rows = [
    # Zombie SKUs — no sales in 45+ days
    {
        "product_name": "Classic Tan Wallet",
        "sku_id": "SKU-TW-001",
        "inventory_units": 200,
        "unit_cost": 420.0,
        "last_sold_date": (today - timedelta(days=47)).isoformat(),  # ZOMBIE
        "category": "wallets",
    },
    {
        "product_name": "Tan Wallet Pro",
        "sku_id": "SKU-TW-002",
        "inventory_units": 85,
        "unit_cost": 560.0,
        "last_sold_date": (today - timedelta(days=52)).isoformat(),  # ZOMBIE
        "category": "wallets",
    },
    # Healthy SKUs
    {
        "product_name": "Black Leather Belt",
        "sku_id": "SKU-BL-001",
        "inventory_units": 45,
        "unit_cost": 580.0,
        "last_sold_date": (today - timedelta(days=2)).isoformat(),
        "category": "belts",
    },
    {
        "product_name": "Canvas Backpack",
        "sku_id": "SKU-CB-001",
        "inventory_units": 30,
        "unit_cost": 1100.0,
        "last_sold_date": (today - timedelta(days=1)).isoformat(),
        "category": "bags",
    },
    {
        "product_name": "Minimalist Watch",
        "sku_id": "SKU-MW-001",
        "inventory_units": 15,
        "unit_cost": 2100.0,
        "last_sold_date": today.isoformat(),
        "category": "accessories",
    },
]

errors = client.insert_rows_json(f"{dataset_id}.shopify_inventory", inventory_rows)
print(f"  shopify_inventory: {len(inventory_rows)} rows {'✅' if not errors else errors}")

# ── 4C. ad_spend ──
print("Injecting ad_spend...")
ad_rows = []
for i in range(30):
    spend_date = today - timedelta(days=i)
    is_unbilled = i < 7  # Last 7 days unbilled — Phantom Liability trigger
    ad_rows.append({
        "product_name": random.choice(["Classic Tan Wallet", "Black Leather Belt", "Canvas Backpack"]),
        "ad_cost": round(random.uniform(8000, 32000), 2),
        "platform": random.choice(["Meta", "Google"]),
        "date": spend_date.isoformat(),
        "unbilled": is_unbilled,
        "expected_charge_date": (spend_date + timedelta(days=7)).isoformat(),
    })

errors = client.insert_rows_json(f"{dataset_id}.ad_spend", ad_rows)
print(f"  ad_spend: {len(ad_rows)} rows {'✅' if not errors else errors}")

# ── 4D. cash_flow ──
print("Injecting cash_flow...")
cash_rows = []
for i in range(30):
    cash_date = today - timedelta(days=i)
    # Declining balance — Cash Cliff trigger
    balance = 500000 - (i * 0) + random.uniform(-5000, 5000)
    cash_rows.append({
        "date": cash_date.isoformat(),
        "bank_balance": round(500000 - (29 - i) * 8500, 2),  # Declining!
        "upcoming_payroll": 120000.0,
        "upcoming_rent": 45000.0,
        "upcoming_gst": 28000.0,
        "pending_receivable": round(random.uniform(20000, 60000), 2),
        "days_until_due": random.randint(5, 18),
        "daily_burn_rate": round(random.uniform(7000, 10000), 2),
    })

errors = client.insert_rows_json(f"{dataset_id}.cash_flow", cash_rows)
print(f"  cash_flow: {len(cash_rows)} rows {'✅' if not errors else errors}")

# ── 4E. quickbooks_payables ──
print("Injecting quickbooks_payables...")
payables_rows = [
    {
        "invoice_id": "INV-001",
        "vendor_name": "RawMat Suppliers Pvt Ltd",
        "amount": 300000.0,
        "due_date": (today + timedelta(days=14)).isoformat(),  # 14 days — COLLISION
        "category": "raw_material",
        "status": "pending",
    },
    {
        "invoice_id": "INV-002",
        "vendor_name": "Warehouse Logistics Co",
        "amount": 85000.0,
        "due_date": (today + timedelta(days=8)).isoformat(),
        "category": "logistics",
        "status": "pending",
    },
    {
        "invoice_id": "INV-003",
        "vendor_name": "Office Rent",
        "amount": 45000.0,
        "due_date": (today + timedelta(days=5)).isoformat(),
        "category": "rent",
        "status": "pending",
    },
    {
        "invoice_id": "INV-004",
        "vendor_name": "Packaging Supplies",
        "amount": 62000.0,
        "due_date": (today + timedelta(days=20)).isoformat(),
        "category": "packaging",
        "status": "pending",
    },
]

errors = client.insert_rows_json(f"{dataset_id}.quickbooks_payables", payables_rows)
print(f"  quickbooks_payables: {len(payables_rows)} rows {'✅' if not errors else errors}")

# ── 4F. stripe_fees ──
print("Injecting stripe_fees...")
stripe_rows = []
for i in range(30):
    stripe_rows.append({
        "product_name": random.choice(["Classic Tan Wallet", "Black Leather Belt", "Canvas Backpack"]),
        "stripe_fee": round(random.uniform(200, 1200), 2),
        "date": (today - timedelta(days=i)).isoformat(),
    })

errors = client.insert_rows_json(f"{dataset_id}.stripe_fees", stripe_rows)
print(f"  stripe_fees: {len(stripe_rows)} rows {'' if not errors else errors}")

print("\n ALL DONE! BigQuery setup complete.")
print("\nSignals that will trigger:")
print("   Zombie SKU — Classic Tan Wallet (47 days), Tan Wallet Pro (52 days)")
print("   Cash Cliff — Balance declining, ~12 days runway")
print("   Inventory-Capital Collision — ₹3,50,000 dead stock vs ₹3,00,000 due in 14 days")
print("   Phantom Liability — ₹1,80,000 unbilled Meta/Google ads")
print("   Margin Drift — Check shopify_orders cost vs revenue trend")