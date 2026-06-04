import stripe
import random
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\hp\Desktop\Nerve\nerve\nerve_agent\.env")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

names = ["Rahul Sharma", "Priya Singh", "Amit Kumar", "Neha Gupta", "Rohan Verma"]
products = ["Kundan Necklace", "Polki Earrings", "Bridal Choker", "Gold Jhumka", "Meenakari Bangle"]

for i in range(50):
    # Customer banao
    customer = stripe.Customer.create(
        email=f"user{i}@testmail.com",
        name=random.choice(names),
        source="tok_visa"  # ← yahan attach karo customer mein
    )

    # Ab charge karo
    stripe.Charge.create(
        amount=random.randint(500, 5000),
        currency="usd",
        customer=customer.id,  # source hata do yahan se
        metadata={
            "order_id": f"ORD_{i+1:03d}",
            "product": random.choice(products),
            "quantity": random.randint(1, 5)
        }
    )
    print(f"Created ORD_{i+1:03d}")

print(" Done! 50 dummy orders ready.")