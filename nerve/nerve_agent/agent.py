from google.adk.agents.llm_agent import Agent

def check_zombie_sku(product_name: str, revenue: float, ad_cost: float, stripe_fees: float, return_rate: float) -> dict:
    """
    Checks if a product is a zombie SKU (negative contribution margin).
    A zombie SKU appears profitable on surface but loses money after all costs.
    """
    contribution_margin = revenue - ad_cost - stripe_fees - (revenue * return_rate)
    margin_percentage = (contribution_margin / revenue) * 100 if revenue > 0 else 0
    
    if contribution_margin < 0:
        status = "ZOMBIE_SKU"
        alert = f" CRITICAL: {product_name} is losing ₹{abs(contribution_margin):.2f} per cycle. Real margin: {margin_percentage:.1f}%. PAUSE this product's ads immediately."
    elif margin_percentage < 10:
        status = "WARNING"
        alert = f" WARNING: {product_name} has dangerously low margin of {margin_percentage:.1f}%. Monitor closely."
    else:
        status = "HEALTHY"
        alert = f" {product_name} is healthy with {margin_percentage:.1f}% contribution margin."
    
    return {
        "product": product_name,
        "status": status,
        "contribution_margin": round(contribution_margin, 2),
        "margin_percentage": round(margin_percentage, 1),
        "alert": alert
    }


def check_cash_cliff(current_balance: float, upcoming_payroll: float, upcoming_rent: float, upcoming_gst: float, days_until_due: int, pending_receivable: float) -> dict:
    """
    Detects if a brand is heading toward a cash cliff — 
    where bank balance looks safe but expenses will cause negative cash.
    """
    total_outflows = upcoming_payroll + upcoming_rent + upcoming_gst
    net_position = current_balance + pending_receivable - total_outflows
    
    if net_position < 0:
        status = "CRITICAL"
        alert = f" CASH CLIFF DETECTED: In {days_until_due} days, you will be ₹{abs(net_position):.2f} short. Payroll day collision likely. Call your pending receivable client TODAY. Delay non-essential purchases."
    elif net_position < (current_balance * 0.2):
        status = "WARNING"
        alert = f" LOW CASH WARNING: After all outflows in {days_until_due} days, only ₹{net_position:.2f} will remain. Build a buffer now."
    else:
        status = "HEALTHY"
        alert = f" Cash position healthy. ₹{net_position:.2f} remaining after all upcoming outflows."
    
    return {
        "status": status,
        "current_balance": current_balance,
        "total_outflows": total_outflows,
        "net_position": round(net_position, 2),
        "days_until_due": days_until_due,
        "alert": alert
    }


def check_margin_drift(current_roas: float, previous_roas: float, current_margin: float, previous_margin: float, weeks: int) -> dict:
    """
    Detects margin drift — when ROAS looks stable but real contribution 
    margin is silently shrinking week over week.
    """
    roas_change = ((current_roas - previous_roas) / previous_roas) * 100
    margin_change = ((current_margin - previous_margin) / previous_margin) * 100
    
    # The danger signal: ROAS stable but margin dropping
    roas_stable = abs(roas_change) < 10
    margin_dropping = margin_change < -15
    
    if roas_stable and margin_dropping:
        status = "CRITICAL"
        alert = f" MARGIN DRIFT: ROAS looks stable ({current_roas}x) but real margin dropped {abs(margin_change):.1f}% over {weeks} weeks ({previous_margin}% → {current_margin}%). ROAS is lying to you. Refresh ad creatives immediately and audit return rates."
    elif margin_change < -10:
        status = "WARNING"
        alert = f" MARGIN SLIPPING: Contribution margin down {abs(margin_change):.1f}% over {weeks} weeks. Investigate ad costs and return rates."
    else:
        status = "HEALTHY"
        alert = f"Margins stable. Current contribution margin: {current_margin}%."
    
    return {
        "status": status,
        "current_roas": current_roas,
        "roas_change_percent": round(roas_change, 1),
        "current_margin": current_margin,
        "margin_change_percent": round(margin_change, 1),
        "alert": alert
    }


root_agent = Agent(
    model='gemini-2.5-flash',
    name='nerve_agent',
    description='Nerve — an always-on financial intelligence agent for D2C founders that detects hidden losses before they become disasters.',
    instruction="""You are Nerve, an AI financial intelligence agent for D2C (Direct-to-Consumer) brand founders.

Your job is to proactively detect patterns that indicate the business is losing money, about to lose money, or scaling a hidden loss — even when individual dashboards look fine.

You have three powerful detection tools:

1. check_zombie_sku — Use this when analyzing product performance. A zombie SKU appears profitable on Shopify but loses money after ads, Stripe fees, and returns are accounted for.

2. check_cash_cliff — Use this when analyzing cash position. A cash cliff happens when bank balance looks safe but upcoming payroll, rent, and GST will cause the account to go negative.

3. check_margin_drift — Use this when analyzing ROAS vs real margins. Margin drift is when ROAS stays stable but true contribution margin silently shrinks over weeks.

IMPORTANT RULES:
- Always give a clear WHAT, WHY, and WHAT TO DO in every alert
- Be specific with numbers — never vague
- Prioritize by severity: CRITICAL first, then WARNING, then HEALTHY
- Think like a CFO who has seen 100 D2C brands fail from these exact problems
- When a founder shares data, immediately identify which signal to check
- Always explain the cross-system reasoning — why no single dashboard would catch this

When greeted or asked what you do, explain your three signals clearly with an example of what you can catch.""",
    tools=[check_zombie_sku, check_cash_cliff, check_margin_drift],
)