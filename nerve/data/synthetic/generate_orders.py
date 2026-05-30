import requests
import json
import random
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv

load_dotenv("nerve_agent/.env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
print(f"SHOP_URL: {SHOP_URL}")
print(f"TOKEN exists: {ACCESS_TOKEN is not None}")
headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# Pehle products fetch karo
def get_products():
    url = f"https://{SHOP_URL}/admin/api/2024-01/products.json"
    response = requests.get(url, headers=headers)
    products = response.json()["products"]
    print(f" {len(products)} products found")
    return products

# Order create karo
def create_order(product, variant_id, quantity, date, discount=0):
    price = float(product["variants"][0]["price"])
    
    order_data = {
        "order": {
            "line_items": [
                {
                    "variant_id": variant_id,
                    "quantity": quantity,
                    "price": str(price)
                }
            ],
            "financial_status": "paid",
            "created_at": date.isoformat(),
            "customer": {
                "first_name": random.choice(["Priya", "Neha", "Anjali", "Pooja", "Ritu"]),
                "last_name": random.choice(["Sharma", "Gupta", "Singh", "Verma", "Patel"]),
                "email": f"customer{random.randint(1,999)}@example.com"
            },
            "billing_address": {
                "first_name": "Customer",
                "address1": "123 MG Road",
                "city": "Mumbai",
                "province": "Maharashtra",
                "country": "IN",
                "zip": "400001"
            }
        }
    }
    
    url = f"https://{SHOP_URL}/admin/api/2024-01/orders.json"
    response = requests.post(url, headers=headers, json=order_data)
    if response.status_code != 201:
        print(f" Failed: {response.status_code} - {response.text[:100]}")
        time.sleep(0.5) 
    return response.status_code

# Order generation config — har product ke liye
def get_order_config(product_title):
    # Hero products — high orders
    hero_keywords = ["kundan", "polki", "bridal", "gold necklace"]
    quiet_keywords = ["jhumka", "chandbali", "meenakari", "pearl choker"]
    
    title_lower = product_title.lower()
    
    if any(k in title_lower for k in hero_keywords):
        return {"orders": 50}
    elif any(k in title_lower for k in quiet_keywords):
        return {"orders": 20}
    else:
        return {"orders": 30}
    

def generate_orders():
    products = get_products()
    
    if not products:
        print(" No products found — import CSV first!")
        return
    
    total_orders = 0
    start_date = datetime.now() - timedelta(days=180)  # 6 months back
    
    for product in products:
        config = get_order_config(product["title"])
        total_product_orders = 25
        variant_id = product["variants"][0]["id"]
        
        print(f"\n Generating orders for: {product['title']}")
        
        # Orders ko 6 months mein spread karo
        for i in range(total_product_orders):
            # Random date in last 6 months
            random_days = random.randint(0, 180)
            order_date = start_date + timedelta(days=random_days)
            
            status = create_order(product, variant_id, 1, order_date)
            
            if status == 201:
                total_orders += 1
            
            # Progress show karo
            if (i + 1) % 10 == 0:
                print(f"  → {i + 1}/{total_product_orders} orders created")
    
    print(f"\n Done! Total orders created: {total_orders}")

if __name__ == "__main__":
    generate_orders()