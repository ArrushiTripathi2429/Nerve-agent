from google.cloud import bigquery
import json

client = bigquery.Client(project="nerve-agent-496707")
dataset_id = "nerve_data"

# Create tables
tables = {
    "shopify_orders": [
        bigquery.SchemaField("order_id", "STRING"),
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("revenue", "FLOAT"),
        bigquery.SchemaField("return_rate", "FLOAT"),
        bigquery.SchemaField("order_date", "DATE"),
    ],
    "ad_spend": [
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("ad_cost", "FLOAT"),
        bigquery.SchemaField("platform", "STRING"),
        bigquery.SchemaField("date", "DATE"),
    ],
    "stripe_fees": [
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("stripe_fee", "FLOAT"),
        bigquery.SchemaField("date", "DATE"),
    ],
    "cash_flow": [
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("bank_balance", "FLOAT"),
        bigquery.SchemaField("upcoming_payroll", "FLOAT"),
        bigquery.SchemaField("upcoming_rent", "FLOAT"),
        bigquery.SchemaField("upcoming_gst", "FLOAT"),
        bigquery.SchemaField("pending_receivable", "FLOAT"),
        bigquery.SchemaField("days_until_due", "INTEGER"),
    ],
}

# Create tables in BigQuery
for table_name, schema in tables.items():
    table_ref = f"{client.project}.{dataset_id}.{table_name}"
    table = bigquery.Table(table_ref, schema=schema)
    try:
        client.create_table(table)
        print(f" Table created: {table_name}")
    except Exception as e:
        print(f" {table_name}: {e}")

# Seed Priya's brand data
rows_to_insert = {
    "shopify_orders": [
        {"order_id": "ORD001", "product_name": "Premium Leather Wallet", "revenue": 320000.0, "return_rate": 0.07, "order_date": "2026-05-01"},
        {"order_id": "ORD002", "product_name": "Canvas Tote Bag", "revenue": 180000.0, "return_rate": 0.02, "order_date": "2026-05-01"},
        {"order_id": "ORD003", "product_name": "Premium Leather Wallet", "revenue": 290000.0, "return_rate": 0.08, "order_date": "2026-04-01"},
        {"order_id": "ORD004", "product_name": "Canvas Tote Bag", "revenue": 160000.0, "return_rate": 0.02, "order_date": "2026-04-01"},
    ],
    "ad_spend": [
        {"product_name": "Premium Leather Wallet", "ad_cost": 250000.0, "platform": "Google", "date": "2026-05-01"},
        {"product_name": "Canvas Tote Bag", "ad_cost": 0.0, "platform": "None", "date": "2026-05-01"},
        {"product_name": "Premium Leather Wallet", "ad_cost": 180000.0, "platform": "Google", "date": "2026-04-01"},
    ],
    "stripe_fees": [
        {"product_name": "Premium Leather Wallet", "stripe_fee": 9600.0, "date": "2026-05-01"},
        {"product_name": "Canvas Tote Bag", "stripe_fee": 5400.0, "date": "2026-05-01"},
    ],
    "cash_flow": [
        {"date": "2026-05-18", "bank_balance": 800000.0, "upcoming_payroll": 500000.0, "upcoming_rent": 200000.0, "upcoming_gst": 150000.0, "pending_receivable": 50000.0, "days_until_due": 21},
    ],
}

# Insert rows
for table_name, rows in rows_to_insert.items():
    table_ref = f"{client.project}.{dataset_id}.{table_name}"
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print(f" Error inserting into {table_name}: {errors}")
    else:
        print(f" Data inserted: {table_name}")

print("\n Priya's brand data ready in BigQuery!")