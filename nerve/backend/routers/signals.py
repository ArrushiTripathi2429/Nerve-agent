from fastapi import APIRouter
from google.cloud import bigquery
from datetime import date

router = APIRouter()
client = bigquery.Client(project="nerve-agent-496707")
DATASET = "nerve-agent-496707.nerve_data"

def serialize(row: dict) -> dict:
    return {
        k: v.isoformat() if hasattr(v, 'isoformat') else v
        for k, v in row.items()
    }

@router.get("/signals")
def get_all_signals():
    signals = {}

    # Zombie SKU
    zombie_query = f"""
        SELECT
            product_name, sku_id, inventory_units, unit_cost,
            inventory_units * unit_cost AS locked_capital,
            DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) AS days_since_sold
        FROM `{DATASET}.shopify_inventory`
        WHERE DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) >= 30
        ORDER BY locked_capital DESC
    """
    zombies = [serialize(dict(r)) for r in client.query(zombie_query).result()]
    total_locked = sum(z["locked_capital"] for z in zombies)
    signals["zombie_sku"] = {
        "status": "CRITICAL" if zombies else "HEALTHY",
        "severity": min(10, 5 + len(zombies) * 2) if zombies else 1,
        "total_locked_capital": round(total_locked, 2),
        "zombies": zombies,
        "alert": (
            f"🧟 {len(zombies)} dead SKUs — ₹{total_locked:,.0f} locked"
            if zombies else "No zombie SKUs"
        )
    }

    # Cash Cliff
    cash_query = f"""
        SELECT bank_balance, upcoming_payroll, upcoming_rent,
               upcoming_gst, pending_receivable, days_until_due, daily_burn_rate
        FROM `{DATASET}.cash_flow`
        ORDER BY date DESC LIMIT 1
    """
    cash_rows = [serialize(dict(r)) for r in client.query(cash_query).result()]
    if cash_rows:
        r = cash_rows[0]
        total_outflows = r["upcoming_payroll"] + r["upcoming_rent"] + r["upcoming_gst"]
        net_position = r["bank_balance"] + r["pending_receivable"] - total_outflows
        runway_days = int(r["bank_balance"] / r["daily_burn_rate"]) if r["daily_burn_rate"] > 0 else 999
        signals["cash_cliff"] = {
            "status": "CRITICAL" if net_position < 0 else "WARNING" if runway_days < 20 else "HEALTHY",
            "severity": 10 if net_position < 0 else 7 if runway_days < 20 else 2,
            "runway_days": runway_days,
            "net_position": round(net_position, 2),
            "bank_balance": r["bank_balance"],
            "daily_burn_rate": r["daily_burn_rate"],
            "total_outflows": total_outflows,
            "alert": f" {runway_days} days runway — Net: ₹{net_position:,.0f}"
        }

    # Margin Drift
    margin_query = f"""
        WITH recent AS (
            SELECT SUM(revenue) AS rev, SUM(cost_price) AS cost,
                   SUM(revenue * return_rate) AS returns
            FROM `{DATASET}.shopify_orders`
            WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        ),
        previous AS (
            SELECT SUM(revenue) AS rev, SUM(cost_price) AS cost,
                   SUM(revenue * return_rate) AS returns
            FROM `{DATASET}.shopify_orders`
            WHERE order_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        )
        SELECT
            ROUND((recent.rev - recent.cost - recent.returns) / NULLIF(recent.rev,0) * 100, 1) AS current_margin,
            ROUND((previous.rev - previous.cost - previous.returns) / NULLIF(previous.rev,0) * 100, 1) AS previous_margin
        FROM recent, previous
    """
    margin_rows = [dict(r) for r in client.query(margin_query).result()]
    if margin_rows:
        current = margin_rows[0]["current_margin"] or 0
        previous = margin_rows[0]["previous_margin"] or 0
        drift = current - previous
        signals["margin_drift"] = {
            "status": "CRITICAL" if drift < -15 else "WARNING" if drift < -8 else "HEALTHY",
            "severity": 9 if drift < -15 else 6 if drift < -8 else 2,
            "current_margin": current,
            "previous_margin": previous,
            "drift": round(drift, 1),
            "trigger_research": drift < -8,
            "alert": f" Margin: {previous}% → {current}% ({drift:+.1f}%)"
        }

    # Inventory Capital Collision
    collision_query = f"""
        WITH dead_stock AS (
            SELECT SUM(inventory_units * unit_cost) AS total_locked
            FROM `{DATASET}.shopify_inventory`
            WHERE DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) >= 30
        ),
        bills AS (
            SELECT SUM(amount) AS total_bills,
                   MIN(DATE_DIFF(due_date, CURRENT_DATE(), DAY)) AS nearest_days,
                   MIN(vendor_name) AS nearest_vendor,
                   MIN(amount) AS nearest_amount
            FROM `{DATASET}.quickbooks_payables`
            WHERE status = 'pending'
            AND due_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY)
        ),
        cash AS (
            SELECT bank_balance FROM `{DATASET}.cash_flow`
            ORDER BY date DESC LIMIT 1
        )
        SELECT d.total_locked, b.total_bills, b.nearest_days,
               b.nearest_vendor, b.nearest_amount, c.bank_balance
        FROM dead_stock d, bills b, cash c
    """
    collision_rows = [serialize(dict(r)) for r in client.query(collision_query).result()]
    if collision_rows and collision_rows[0]["total_locked"]:
        r = collision_rows[0]
        locked = r["total_locked"]
        bills = r["total_bills"]
        balance = r["bank_balance"]
        days = r["nearest_days"]
        signals["inventory_collision"] = {
            "status": "CRITICAL" if locked > balance * 0.5 and days < 20 else "WARNING" if locked > balance * 0.3 else "HEALTHY",
            "severity": 10 if locked > balance * 0.5 and days < 20 else 6 if locked > balance * 0.3 else 2,
            "locked_capital": round(locked, 2),
            "upcoming_bills": round(bills, 2),
            "nearest_due_days": days,
            "nearest_vendor": r["nearest_vendor"],
            "alert": f"₹{locked:,.0f} locked — ₹{r['nearest_amount']:,.0f} due in {days} days"
        }

    # Phantom Liability
    phantom_query = f"""
        SELECT platform, SUM(ad_cost) AS unbilled_amount,
               MIN(expected_charge_date) AS earliest_charge
        FROM `{DATASET}.ad_spend`
        WHERE unbilled = TRUE
        AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        GROUP BY platform
    """
    phantom_rows = [serialize(dict(r)) for r in client.query(phantom_query).result()]
    cash_bal_query = f"SELECT bank_balance FROM `{DATASET}.cash_flow` ORDER BY date DESC LIMIT 1"
    cash_bal = [dict(r) for r in client.query(cash_bal_query).result()]
    bank_balance = cash_bal[0]["bank_balance"] if cash_bal else 0
    total_unbilled = sum(r["unbilled_amount"] for r in phantom_rows)
    true_cash = bank_balance - total_unbilled
    signals["phantom_liability"] = {
        "status": "CRITICAL" if total_unbilled > bank_balance * 0.25 else "WARNING" if total_unbilled > bank_balance * 0.1 else "HEALTHY",
        "severity": 9 if total_unbilled > bank_balance * 0.25 else 5 if total_unbilled > bank_balance * 0.1 else 2,
        "total_unbilled": round(total_unbilled, 2),
        "bank_balance": bank_balance,
        "true_cash": round(true_cash, 2),
        "platforms": phantom_rows,
        "alert": f" Bank: ₹{bank_balance:,.0f} — True cash: ₹{true_cash:,.0f}"
    }

    return {"status": "success", "signals": signals}