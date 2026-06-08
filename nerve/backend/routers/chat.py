from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
import requests
import os
import json
import asyncio
import uuid
from datetime import datetime, timezone
from google.cloud import bigquery

from dotenv import load_dotenv
import pathlib

load_dotenv(pathlib.Path(__file__).parent.parent / ".env")

router = APIRouter()

# Vertex AI client — uses Cloud Run service account (no API key needed)
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

from routers.signals import get_all_signals as _get_cached_signals

def get_financial_signals() -> dict:
    try:
        data = _get_cached_signals()
        signals = data.get("signals", {})
        # Extract the most useful numbers for the agent
        return {
            "zombie_skus": signals.get("zombie_sku", {}).get("zombies", [])[:5],
            "cash_flow": {
                "bank_balance": signals.get("cash_cliff", {}).get("bank_balance", 0),
                "runway_days": signals.get("cash_cliff", {}).get("runway_days", 0),
                "daily_burn_rate": signals.get("cash_cliff", {}).get("daily_burn_rate", 0),
            },
            "margin": {
                "current_margin": signals.get("margin_drift", {}).get("current_margin", 0),
                "previous_margin": signals.get("margin_drift", {}).get("previous_margin", 0),
                "drift": signals.get("margin_drift", {}).get("drift", 0),
            },
            "phantom_liability": {
                "total_unbilled": signals.get("phantom_liability", {}).get("total_unbilled", 0),
                "true_cash": signals.get("phantom_liability", {}).get("true_cash", 0),
            },
            "summary": {
                "silent_killer_score": None,
                "zombie_locked_capital": signals.get("zombie_sku", {}).get("total_locked_capital", 0),
                "upcoming_bills": signals.get("inventory_collision", {}).get("upcoming_bills", 0),
            }
        }
    except Exception as e:
        return {"error": str(e)}


def get_shopify_products() -> dict:
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
            "message": f"Price updated to ₹{new_price} for '{product.get('title', product_id)}'"
        }
    except Exception as e:
        return {"error": str(e)}


def unpublish_product(product_id: str) -> dict:
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
                    "discount_percent": types.Schema(type=types.Type.NUMBER, description="Discount percentage e.g. 20 for 20%")
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
When you take an action, confirm exactly what changed.
You remember the full conversation history — refer to it when relevant."""


# ─── BIGQUERY SESSION HELPERS ─────────────────────────────────

def get_session(session_id: str) -> dict | None:
    query = f"""
        SELECT session_id, title, created_at, updated_at, messages, is_deleted
        FROM `{DATASET}.chat_sessions`
        WHERE session_id = '{session_id}'
        ORDER BY updated_at DESC
        LIMIT 1
    """
    rows = list(bq_client.query(query).result())
    if not rows:
        return None
    row = dict(rows[0])
    if row.get("is_deleted"):
        return None
    row["messages"] = row["messages"] if isinstance(row["messages"], list) else (json.loads(row["messages"]) if row["messages"] else [])
    return row

def save_session(session_id: str, title: str, messages: list, created_at: str = None):
    now = datetime.now(timezone.utc).isoformat()
    created = created_at or now
    rows = [{
        "session_id": session_id,
        "title": title,
        "created_at": created,
        "updated_at": now,
        "messages": json.dumps(messages),
        "is_deleted": False
    }]
    # Insert new version — get_session always fetches latest by updated_at
    errors = bq_client.insert_rows_json(f"{DATASET}.chat_sessions", rows)
    if errors:
        print(f"BQ insert errors: {errors}")


def list_sessions() -> list:
    query = f"""
        WITH latest AS (
            SELECT session_id, title, created_at, updated_at, is_deleted,
                   ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY updated_at DESC) AS rn
            FROM `{DATASET}.chat_sessions`
        )
        SELECT session_id, title, created_at, updated_at
        FROM latest
        WHERE rn = 1 AND (is_deleted IS NULL OR is_deleted = FALSE)
        ORDER BY updated_at DESC
        LIMIT 50
    """
    return [dict(r) for r in bq_client.query(query).result()]


def generate_title(message: str) -> str:
    """Generate short title from the first message — no API call needed."""
    words = message.strip().split()
    title = " ".join(words[:6])
    return (title + "...") if len(words) > 6 else title


# ─── REQUEST MODELS ───────────────────────────────────────────

class NewSessionRequest(BaseModel):
    first_message: str = ""

class ChatRequest(BaseModel):
    message: str
    session_id: str


# ─── SESSION ENDPOINTS ────────────────────────────────────────

@router.post("/chat/sessions/new")
def new_session(req: NewSessionRequest):
    session_id = str(uuid.uuid4())
    title = generate_title(req.first_message) if req.first_message else "New Chat"
    now = datetime.now(timezone.utc).isoformat()
    save_session(session_id, title, [], created_at=now)
    return {"session_id": session_id, "title": title}


@router.get("/chat/sessions")
def get_sessions():
    sessions = list_sessions()
    # Convert timestamps to string
    for s in sessions:
        for k in ["created_at", "updated_at"]:
            if hasattr(s[k], "isoformat"):
                s[k] = s[k].isoformat()
    return {"sessions": sessions}


@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str):
    # Insert a "deleted" marker row
    rows = [{
        "session_id": session_id,
        "title": "__deleted__",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": "[]",
        "is_deleted": True
    }]
    bq_client.insert_rows_json(f"{DATASET}.chat_sessions", rows)
    return {"status": "deleted", "session_id": session_id}

@router.get("/chat/sessions/{session_id}")
def get_session_messages(session_id: str):
    session = get_session(session_id)
    if not session:
        return {"session_id": session_id, "messages": [], "title": ""}
    for k in ["created_at", "updated_at"]:
        if hasattr(session.get(k), "isoformat"):
            session[k] = session[k].isoformat()
    return session


# ─── STREAMING CHAT ENDPOINT ──────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        # Load session from BQ
        session = get_session(req.session_id)
        if not session:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Session not found'})}\n\n"
            return

        history = session["messages"]
        title = session["title"]
        created_at = session["created_at"]
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        # Build messages for Gemini
        messages = []
        for h in history:
            messages.append(types.Content(
                role=h["role"],
                parts=[types.Part(text=h["content"])]
            ))

        # Add current user message
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=req.message)]
        ))

        actions_taken = []
        final_reply = ""

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
            function_calls = [p for p in parts if p.function_call]

            if not function_calls:
                # Stream final text — send in chunks for low latency
                final_text = "".join(p.text for p in parts if p.text)
                final_reply = final_text
                # Send in ~5-word chunks for snappy appearance
                words = final_text.split(" ")
                chunk_size = 4
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size]) + " "
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.02)

                if actions_taken:
                    yield f"data: {json.dumps({'type': 'actions', 'actions': actions_taken})}\n\n"

                yield "data: [DONE]\n\n"
                break

            # Execute tool calls
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

        # Save updated history to BQ
        updated_history = history + [
            {"role": "user", "content": req.message},
            {"role": "model", "content": final_reply}
        ]
        save_session(req.session_id, title, updated_history, created_at=str(created_at))

    return StreamingResponse(generate(), media_type="text/event-stream")