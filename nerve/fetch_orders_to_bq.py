import requests
import os
from dotenv import load_dotenv
from google.cloud import bigquery
from datetime import datetime

load_dotenv("nerve_agent/.env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
PROJECT_ID = "nerve-agent-496707"
DATASET_ID = "shopify"
TABLE_ID = "order"

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def fetch_all_orders():
    all_orders = []
    url = f"https://{SHOP_URL}/admin/api/2024-01/orders.json?status=any&limit=250"
    
    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        orders = data.get("orders", [])
        all_orders.extend(orders)
        print(f"Fetched {len(all_orders)} orders so far...")
        
        # Pagination
        link_header = response.headers.get("Link", "")
        if 'rel="next"' in link_header:
            next_url = [l.split(";")[0].strip("<>") for l in link_header.split(",") if 'rel="next"' in l]
            url = next_url[0] if next_url else None
        else:
            url = None
    
    return all_orders

def push_to_bigquery(orders):
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    rows = []
    for o in orders:
        rows.append({
            "id": str(o.get("id")),
            "created_at": o.get("created_at"),
            "financial_status": o.get("financial_status"),
            "total_price": float(o.get("total_price", 0)),
            "subtotal_price": float(o.get("subtotal_price", 0)),
            "currency": o.get("currency"),
            "order_number": o.get("order_number"),
        })
    
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print(f"Errors: {errors}")
    else:
        print(f"{len(rows)} orders pushed to BigQuery!")

if __name__ == "__main__":
    orders = fetch_all_orders()
    push_to_bigquery(orders)