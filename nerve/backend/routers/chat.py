from fastapi import APIRouter
from pydantic import BaseModel
from google.cloud import bigquery
from google import genai
from google.genai import types
import requests
import os
import json

router = APIRouter()

# Vertex AI client
ai_client = genai.Client(
    vertexai=True,
    project="nerve-agent-496707",
    location="us-central1"
)

bq_client = bigquery.Client(project="nerve-agent-496707")
DATASET = "nerve-agent-496707.nerve_data"

SHOPIFY_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}

# ─── TOOL FUNCTIONS ───────────────────────────────────────────

def get_financial_signals() -> dict:
    """Fetch all financial signals from BigQuery"""
    try:
        zombie_query = f"""
            SELECT product_name, sku_id, inventory_units, unit_cost,
                   inventory_units * unit_cost AS locked_capital,
                   DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) AS days_since_sold
            FROM `{DATASET}.shopify_inventory`
            WHERE DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) >= 30
            ORDER BY locked_capital DESC LIMIT 5
        """
        zombies = [dict(r) for r in bq_client.query(zombie_query).result()]

        cash_query = f"""
            SELECT bank_balance, upcoming_payroll, upcoming_rent,
                   upcoming_gst, pending_receivable, daily_burn_rate
            FROM `{DATASET}.cash_flow`
            ORDER BY date DESC LIMIT 1
        """
        cash = [dict(r) for r in bq_client.query(cash_query).result()]

        margin_query = f"""
            WITH recent AS (
                SELECT SUM(revenue) AS rev, SUM(cost_price) AS cost
                FROM `{DATASET}.shopify_orders`
                WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            ),
            previous AS (
                SELECT SUM(revenue) AS rev, SUM(cost_price) AS cost
                FROM `{DATASET}.shopify_orders`
                WHERE order_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
                    AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            )
            SELECT
                ROUND((recent.rev - recent.cost) / NULLIF(recent.rev,0) * 100, 1) AS current_margin,
                ROUND((previous.rev - previous.cost) / NULLIF(previous.rev,0) * 100, 1) AS previous_margin
            FROM recent, previous
        """
        margin = [dict(r) for r in bq_client.query(margin_query).result()]

        return {
            "zombie_skus": zombies,
            "cash_flow": cash[0] if cash else {},
            "margin": margin[0] if margin else {}
        }
    except Exception as e:
        return {"error": str(e)}


def get_shopify_products() -> dict:
    """Fetch all products from Shopify"""
    try:
        url = f"https://{SHOPIFY_URL}/admin/api/2024-01/products.json?limit=20"
        res = requests.get(url, headers=SHOPIFY_HEADERS)
        products = res.json().get("products", [])
        return {
            "products": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "status": p["status"],
                    "price": p["variants"][0]["price"] if p["variants"] else "N/A",
                    "inventory": p["variants"][0].get("inventory_quantity", 0) if p["variants"] else 0
                }
                for p in products
            ]
        }
    except Exception as e:
        return {"error": str(e)}


def update_product_price(product_id: str, new_price: float) -> dict:
    """Update price of a Shopify product"""
    try:
        url = f"https://{SHOPIFY_URL}/admin/api/2024-01/products/{product_id}.json"
        res = requests.get(url, headers=SHOPIFY_HEADERS)
        product = res.json().get("product", {})
        variants = product.get("variants", [])

        for variant in variants:
            variant_url = f"https://{SHOPIFY_URL}/admin/api/2024-01/variants/{variant['id']}.json"
            requests.put(variant_url, headers=SHOPIFY_HEADERS, json={
                "variant": {"id": variant["id"], "price": str(new_price)}
            })

        return {
            "success": True,
            "message": f"Price updated to ₹{new_price} for product {product.get('title', product_id)}"
        }
    except Exception as e:
        return {"error": str(e)}


def unpublish_product(product_id: str) -> dict:
    """Unpublish a zombie SKU from Shopify"""
    try:
        url = f"https://{SHOPIFY_URL}/admin/api/2024-01/products/{product_id}.json"
        res = requests.put(url, headers=SHOPIFY_HEADERS, json={
            "product": {"id": product_id, "status": "draft"}
        })
        product = res.json().get("product", {})
        return {
            "success": True,
            "message": f"Product '{product.get('title', product_id)}' unpublished successfully"
        }
    except Exception as e:
        return {"error": str(e)}


def apply_discount(product_id: str, discount_percent: float) -> dict:
    """Apply discount to a Shopify product"""
    try:
        url = f"https://{SHOPIFY_URL}/admin/api/2024-01/products/{product_id}.json"
        res = requests.get(url, headers=SHOPIFY_HEADERS)
        product = res.json().get("product", {})
        variants = product.get("variants", [])

        updated = []
        for variant in variants:
            original_price = float(variant.get("price", 0))
            new_price = round(original_price * (1 - discount_percent / 100), 2)
            variant_url = f"https://{SHOPIFY_URL}/admin/api/2024-01/variants/{variant['id']}.json"
            requests.put(variant_url, headers=SHOPIFY_HEADERS, json={
                "variant": {"id": variant["id"], "price": str(new_price)}
            })
            updated.append({"variant": variant["id"], "old_price": original_price, "new_price": new_price})

        return {
            "success": True,
            "message": f"{discount_percent}% discount applied to '{product.get('title', product_id)}'",
            "price_changes": updated
        }
    except Exception as e:
        return {"error": str(e)}


# ─── TOOL DEFINITIONS ─────────────────────────────────────────

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_financial_signals",
            description="Fetch current financial signals from BigQuery — zombie SKUs, cash flow, margin drift",
            parameters=types.Schema(type=types.Type.OBJECT, properties={})
        ),
        types.FunctionDeclaration(
            name="get_shopify_products",
            description="Get all products from Shopify store with their prices and inventory",
            parameters=types.Schema(type=types.Type.OBJECT, properties={})
        ),
        types.FunctionDeclaration(
            name="update_product_price",
            description="Update the price of a specific Shopify product",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.STRING, description="Shopify product ID"),
                    "new_price": types.Schema(type=types.Type.NUMBER, description="New price in INR")
                },
                required=["product_id", "new_price"]
            )
        ),
        types.FunctionDeclaration(
            name="unpublish_product",
            description="Unpublish/draft a zombie SKU product from Shopify store",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.STRING, description="Shopify product ID to unpublish")
                },
                required=["product_id"]
            )
        ),
        types.FunctionDeclaration(
            name="apply_discount",
            description="Apply a percentage discount to a Shopify product",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.STRING, description="Shopify product ID"),
                    "discount_percent": types.Schema(type=types.Type.NUMBER, description="Discount percentage (e.g. 20 for 20%)")
                },
                required=["product_id", "discount_percent"]
            )
        )
    ])
]

TOOL_MAP = {
    "get_financial_signals": get_financial_signals,
    "get_shopify_products": get_shopify_products,
    "update_product_price": update_product_price,
    "unpublish_product": unpublish_product,
    "apply_discount": apply_discount
}

SYSTEM_PROMPT = """You are Nerve, an autonomous D2C financial intelligence agent for a jewellery brand.

You have access to real business data via tools. When a user asks about financial health or requests an action:
1. First fetch relevant data using tools
2. Analyze the situation
3. Take action if requested (update prices, unpublish products, apply discounts)
4. Report what you did clearly

Always be concise, actionable, and specific with numbers.
When you take an action, confirm exactly what changed."""

# ─── CHAT ENDPOINT ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list = []


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = []

    # Add history
    for h in req.history:
        messages.append(types.Content(
            role=h["role"],
            parts=[types.Part(text=h["content"])]
        ))

    # Add current message
    messages.append(types.Content(
        role="user",
        parts=[types.Part(text=req.message)]
    ))

    actions_taken = []

    # Agentic loop
    while True:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOLS,
                temperature=0.3
            )
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts

        # Check for function calls
        function_calls = [p for p in parts if p.function_call]

        if not function_calls:
            # Final text response
            final_text = "".join(p.text for p in parts if p.text)
            return {
                "reply": final_text,
                "actions_taken": actions_taken,
                "refresh_dashboard": len(actions_taken) > 0
            }

        # Execute tool calls
        tool_results = []
        for part in function_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args)

            fn = TOOL_MAP.get(fn_name)
            result = fn(**fn_args) if fn else {"error": f"Unknown tool: {fn_name}"}

            if fn_name in ["update_product_price", "unpublish_product", "apply_discount"]:
                actions_taken.append({"tool": fn_name, "args": fn_args, "result": result})

            tool_results.append(types.Part(
                function_response=types.FunctionResponse(
                    name=fn_name,
                    response=result
                )
            ))

        # Add model response + tool results to messages
        messages.append(candidate.content)
        messages.append(types.Content(role="user", parts=tool_results))

        from fastapi.responses import StreamingResponse
import asyncio

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        messages = []
        for h in req.history:
            messages.append(types.Content(
                role=h["role"],
                parts=[types.Part(text=h["content"])]
            ))
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=req.message)]
        ))

        actions_taken = []

        while True:
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=TOOLS,
                    temperature=0.3
                )
            )

            candidate = response.candidates[0]
            parts = candidate.content.parts
            function_calls = [p for p in parts if p.function_call]

            if not function_calls:
                final_text = "".join(p.text for p in parts if p.text)
                # Word by word stream
                words = final_text.split(" ")
                for word in words:
                    yield f"data: {json.dumps({'type': 'text', 'content': word + ' '})}\n\n"
                    await asyncio.sleep(0.04)
                if actions_taken:
                    yield f"data: {json.dumps({'type': 'actions', 'actions': actions_taken})}\n\n"
                yield "data: [DONE]\n\n"
                break

            tool_results = []
            for part in function_calls:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                fn = TOOL_MAP.get(fn_name)
                result = fn(**fn_args) if fn else {"error": f"Unknown tool: {fn_name}"}

                if fn_name in ["update_product_price", "unpublish_product", "apply_discount"]:
                    actions_taken.append({"tool": fn_name, "args": fn_args, "result": result})
                    yield f"data: {json.dumps({'type': 'action_progress', 'tool': fn_name, 'result': result})}\n\n"

                tool_results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fn_name,
                        response=result
                    )
                ))

            messages.append(candidate.content)
            messages.append(types.Content(role="user", parts=tool_results))

    return StreamingResponse(generate(), media_type="text/event-stream")