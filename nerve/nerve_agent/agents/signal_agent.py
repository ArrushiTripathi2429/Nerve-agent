from google.adk.agents.llm_agent import Agent
from google.cloud import bigquery
from datetime import date

client = bigquery.Client(project="nerve-agent-496707")
DATASET = "nerve-agent-496707.nerve_data"

def serialize_row(row: dict) -> dict:
    """Convert BigQuery date/datetime objects to strings for JSON serialization."""
    result = {}
    for k, v in row.items():
        if hasattr(v, 'isoformat'):  # date, datetime, time sab cover hoga
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = serialize_row(v)
        elif isinstance(v, list):
            result[k] = [serialize_row(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result

# SIGNAL 1: ZOMBIE SKU

def detect_zombie_skus() -> dict:
    """
    Detects zombie SKUs — products sitting in inventory
    with zero sales for 30+ days.
    """
    query = f"""
        SELECT
            i.product_name,
            i.sku_id,
            i.inventory_units,
            i.unit_cost,
            i.last_sold_date,
            i.inventory_units * i.unit_cost AS locked_capital,
            DATE_DIFF(CURRENT_DATE(), i.last_sold_date, DAY) AS days_since_sold
        FROM `{DATASET}.shopify_inventory` i
        WHERE DATE_DIFF(CURRENT_DATE(), i.last_sold_date, DAY) >= 30
        ORDER BY locked_capital DESC
    """
    results = client.query(query).result()
    zombies = [serialize_row(dict(row)) for row in results]

    if not zombies:
        return {"status": "HEALTHY", "severity": 1, "zombies": [],
                "alert": "No zombie SKUs detected."}

    total_locked = sum(z["locked_capital"] for z in zombies)
    worst = zombies[0]
    severity = min(10, 5 + len(zombies) * 2)

    return {
        "status": "CRITICAL",
        "severity": severity,
        "zombies": zombies,
        "total_locked_capital": round(total_locked, 2),
        "alert": (
            f" ZOMBIE SKU DETECTED: {len(zombies)} dead SKUs found. "
            f"₹{total_locked:,.0f} locked in unselling inventory. "
            f"Worst offender: '{worst['product_name']}' — "
            f"{worst['days_since_sold']} days without a single sale, "
            f"₹{worst['locked_capital']:,.0f} trapped."
        )
    }

# SIGNAL 2: CASH CLIFF

def detect_cash_cliff() -> dict:
    """
    Detects if brand is heading toward cash cliff —
    calculates true runway in days.
    """
    query = f"""
        SELECT
            bank_balance,
            upcoming_payroll,
            upcoming_rent,
            upcoming_gst,
            pending_receivable,
            days_until_due,
            daily_burn_rate
        FROM `{DATASET}.cash_flow`
        ORDER BY date DESC
        LIMIT 1
    """
    results = client.query(query).result()
    row = [serialize_row(dict(r)) for r in results]

    if not row:
        return {"status": "UNKNOWN", "severity": 5, "alert": "No cash flow data found."}

    r = row[0]
    total_outflows = r["upcoming_payroll"] + r["upcoming_rent"] + r["upcoming_gst"]
    net_position = r["bank_balance"] + r["pending_receivable"] - total_outflows
    runway_days = int(r["bank_balance"] / r["daily_burn_rate"]) if r["daily_burn_rate"] > 0 else 999

    if net_position < 0:
        severity = 10
        status = "CRITICAL"
        alert = (
            f" CASH CLIFF: In {r['days_until_due']} days you will be "
            f"₹{abs(net_position):,.0f} SHORT. "
            f"Runway: only {runway_days} days at current burn rate of "
            f"₹{r['daily_burn_rate']:,.0f}/day. "
            f"Call receivables TODAY. Delay non-essential purchases immediately."
        )
    elif runway_days < 20:
        severity = 7
        status = "WARNING"
        alert = (
            f"LOW RUNWAY: Only {runway_days} days of cash left at current burn. "
            f"Net position after outflows: ₹{net_position:,.0f}. Act now."
        )
    else:
        severity = 2
        status = "HEALTHY"
        alert = f" Cash healthy. {runway_days} days runway. Net after outflows: ₹{net_position:,.0f}."

    return {
        "status": status,
        "severity": severity,
        "runway_days": runway_days,
        "net_position": round(net_position, 2),
        "bank_balance": r["bank_balance"],
        "total_outflows": total_outflows,
        "daily_burn_rate": r["daily_burn_rate"],
        "alert": alert
    }

# SIGNAL 3: MARGIN DRIFT

def detect_margin_drift() -> dict:
    """
    Detects silent margin erosion by comparing
    last 30 days vs previous 30 days.
    """
    query = f"""
        WITH recent AS (
            SELECT
                SUM(revenue) AS total_revenue,
                SUM(cost_price) AS total_cost,
                SUM(revenue * return_rate) AS total_returns
            FROM `{DATASET}.shopify_orders`
            WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        ),
        previous AS (
            SELECT
                SUM(revenue) AS total_revenue,
                SUM(cost_price) AS total_cost,
                SUM(revenue * return_rate) AS total_returns
            FROM `{DATASET}.shopify_orders`
            WHERE order_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        )
        SELECT
            ROUND((recent.total_revenue - recent.total_cost - recent.total_returns) / NULLIF(recent.total_revenue, 0) * 100, 1) AS current_margin,
            ROUND((previous.total_revenue - previous.total_cost - previous.total_returns) / NULLIF(previous.total_revenue, 0) * 100, 1) AS previous_margin
        FROM recent, previous
    """
    results = client.query(query).result()
    row = [dict(r) for r in results]

    if not row:
        return {"status": "UNKNOWN", "severity": 5, "alert": "Insufficient data for margin drift."}

    current = row[0]["current_margin"] or 0
    previous = row[0]["previous_margin"] or 0
    drift = current - previous

    if drift < -15:
        severity = 9
        status = "CRITICAL"
        alert = (
            f" MARGIN DRIFT CRITICAL: Margin collapsed from {previous}% → {current}% "
            f"({abs(drift):.1f}% drop in 30 days). "
            f"Your ROAS dashboard is hiding this. Audit ad creatives and return rates NOW."
        )
    elif drift < -8:
        severity = 6
        status = "WARNING"
        alert = (
            f" MARGIN SLIPPING: {previous}% → {current}% over 30 days. "
            f"Monitor ad costs and supplier pricing."
        )
    else:
        severity = 2
        status = "HEALTHY"
        alert = f"Margins stable at {current}%."

    return {
        "status": status,
        "severity": severity,
        "current_margin": current,
        "previous_margin": previous,
        "drift": round(drift, 1),
        "alert": alert,
        "trigger_research": drift < -8
    }

# SIGNAL 4: INVENTORY-CAPITAL COLLISION
def detect_inventory_capital_collision() -> dict:
    """
    Detects when cash is locked in dead stock
    AND a large payment is due soon — collision!
    """
    query = f"""
        WITH dead_stock AS (
            SELECT
                SUM(inventory_units * unit_cost) AS total_locked_value
            FROM `{DATASET}.shopify_inventory`
            WHERE DATE_DIFF(CURRENT_DATE(), last_sold_date, DAY) >= 30
        ),
        upcoming_bills AS (
            SELECT
                invoice_id,
                vendor_name,
                amount,
                due_date,
                category,
                DATE_DIFF(due_date, CURRENT_DATE(), DAY) AS days_until_due
            FROM `{DATASET}.quickbooks_payables`
            WHERE status = 'pending'
            AND due_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY)
            ORDER BY due_date ASC
        ),
        cash AS (
            SELECT bank_balance
            FROM `{DATASET}.cash_flow`
            ORDER BY date DESC LIMIT 1
        )
        SELECT
            d.total_locked_value,
            c.bank_balance,
            SUM(b.amount) AS total_upcoming_bills,
            MIN(b.days_until_due) AS nearest_due_days,
            MIN(b.vendor_name) AS nearest_vendor,
            MIN(b.amount) AS nearest_amount
        FROM dead_stock d, cash c, upcoming_bills b
        GROUP BY d.total_locked_value, c.bank_balance
    """
    results = client.query(query).result()
    row = [serialize_row(dict(r)) for r in results]

    if not row or not row[0]["total_locked_value"]:
        return {"status": "HEALTHY", "severity": 1,
                "alert": "No inventory-capital collision risk detected."}

    r = row[0]
    locked = r["total_locked_value"]
    bills = r["total_upcoming_bills"]
    balance = r["bank_balance"]
    days = r["nearest_due_days"]

    if locked > (balance * 0.5) and days < 20:
        severity = 10
        status = "CRITICAL"
        alert = (
            f" INVENTORY-CAPITAL COLLISION: ₹{locked:,.0f} locked in dead stock. "
            f"₹{r['nearest_amount']:,.0f} due to {r['nearest_vendor']} in {days} days. "
            f"True liquid cash: ₹{balance - bills:,.0f}. "
            f"NERVE RECOMMENDS: Run flash 40% discount on dead SKUs to free cash NOW."
        )
    elif locked > (balance * 0.3):
        severity = 6
        status = "WARNING"
        alert = (
            f" CAPITAL LOCKED: ₹{locked:,.0f} in slow inventory. "
            f"Upcoming bills: ₹{bills:,.0f}. Consider discounting slow SKUs."
        )
    else:
        severity = 2
        status = "HEALTHY"
        alert = " Inventory-capital position healthy."

    return {
        "status": status,
        "severity": severity,
        "locked_capital": round(locked, 2),
        "upcoming_bills": round(bills, 2),
        "nearest_due_days": days,
        "alert": alert
    }

# SIGNAL 5: PHANTOM LIABILITY

def detect_phantom_liability() -> dict:
    """
    Detects hidden ad debt — unbilled Meta/Google spend
    that hasn't hit the bank account yet.
    """
    query = f"""
        SELECT
            platform,
            SUM(ad_cost) AS unbilled_amount,
            COUNT(*) AS transactions,
            MIN(expected_charge_date) AS earliest_charge
        FROM `{DATASET}.ad_spend`
        WHERE unbilled = TRUE
        AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        GROUP BY platform
    """
    results = client.query(query).result()
    rows = [serialize_row(dict(r)) for r in results]

    cash_query = f"""
        SELECT bank_balance FROM `{DATASET}.cash_flow`
        ORDER BY date DESC LIMIT 1
    """
    cash_result = client.query(cash_query).result()
    cash_row = [serialize_row(dict(r)) for r in cash_result]
    bank_balance = cash_row[0]["bank_balance"] if cash_row else 0

    if not rows:
        return {"status": "HEALTHY", "severity": 1,
                "alert": "No phantom liabilities detected."}

    total_unbilled = sum(r["unbilled_amount"] for r in rows)
    true_cash = bank_balance - total_unbilled
    earliest = min(r["earliest_charge"] for r in rows)

    if total_unbilled > (bank_balance * 0.25):
        severity = 9
        status = "CRITICAL"
        alert = (
            f" PHANTOM DEBT ALERT: Bank shows ₹{bank_balance:,.0f} but "
            f"₹{total_unbilled:,.0f} in unbilled Meta/Google ads will "
            f"auto-charge by {earliest}. "
            f"TRUE available cash: ₹{true_cash:,.0f}. "
            f"You are NOT as safe as your bank account looks."
        )
    elif total_unbilled > (bank_balance * 0.1):
        severity = 5
        status = "WARNING"
        alert = (
            f" HIDDEN AD DEBT: ₹{total_unbilled:,.0f} unbilled. "
            f"True cash: ₹{true_cash:,.0f}."
        )
    else:
        severity = 2
        status = "HEALTHY"
        alert = f"Ad liabilities low. True cash: ₹{true_cash:,.0f}."

    return {
        "status": status,
        "severity": severity,
        "total_unbilled": round(total_unbilled, 2),
        "bank_balance": bank_balance,
        "true_cash": round(true_cash, 2),
        "platforms": rows,
        "alert": alert
    }

# SIGNAL DETECTIVE AGENT

signal_detective_agent = Agent(
    model="gemini-2.5-flash",
    name="signal_detective_agent",
    description="Detects all 5 financial warning signals from BigQuery data.",
    instruction="""You are the Signal Detective — a specialist financial analyst for D2C brands.

Run ALL 5 detection tools every time you are called:
1. detect_zombie_skus
2. detect_cash_cliff
3. detect_margin_drift
4. detect_inventory_capital_collision
5. detect_phantom_liability

After running all tools:
- Summarize findings clearly
- List CRITICAL signals first
- Note any dangerous COMBINATIONS (e.g., Zombie SKU + Cash Cliff together)
- Return structured results for the Orchestrator to calculate Silent Killer Score
- If margin_drift trigger_research is True, flag it for Research Agent

Be surgical and specific with numbers. Think like a CFO.""",
    tools=[
        detect_zombie_skus,
        detect_cash_cliff,
        detect_margin_drift,
        detect_inventory_capital_collision,
        detect_phantom_liability,
    ],
)