from google.adk.agents.llm_agent import Agent
import json

def generate_alert_payload(
    signals: str,
    silent_killer_score: int,
    founder_email: str = "founder@nervehq.in"
) -> dict:
    """
    Generates structured alert payload with
    Guardrail action buttons for the frontend.
    """
    signals_data = json.loads(signals) if isinstance(signals, str) else signals

    actions = []

    # Auto-generate actions based on signals
    for signal in signals_data:
        if signal.get("status") == "CRITICAL":
            name = signal.get("name", "")
            if "zombie" in name.lower():
                actions.append({
                    "id": "pause_zombie_ads",
                    "label": "⏸ Pause Zombie SKU Ads",
                    "description": "Pause all ad spend on non-performing SKUs",
                    "webhook": "/api/execute/pause-ads",
                    "severity": "CRITICAL"
                })
                actions.append({
                    "id": "flash_discount",
                    "label": " Apply 40% Flash Discount",
                    "description": "Liquidate dead stock with flash sale",
                    "webhook": "/api/execute/flash-discount",
                    "severity": "CRITICAL"
                })
            if "cash" in name.lower():
                actions.append({
                    "id": "send_receivable_reminder",
                    "label": " Send Receivable Reminder",
                    "description": "Auto-send payment reminder to pending clients",
                    "webhook": "/api/execute/send-reminder",
                    "severity": "CRITICAL"
                })
            if "phantom" in name.lower():
                actions.append({
                    "id": "reduce_ad_budget",
                    "label": " Reduce Ad Budget 30%",
                    "description": "Reduce Meta/Google ad spend to prevent overdraft",
                    "webhook": "/api/execute/reduce-ads",
                    "severity": "WARNING"
                })

    # Email content
    critical_count = sum(1 for s in signals_data if s.get("status") == "CRITICAL")
    warning_count = sum(1 for s in signals_data if s.get("status") == "WARNING")

    email_subject = (
        f"NERVE ALERT: {critical_count} Critical Signals — Silent Killer Score {silent_killer_score}/100"
        if critical_count > 0
        else f" Nerve Daily Digest — Score {silent_killer_score}/100"
    )

    email_body = f"""
While you were away, Nerve detected {critical_count} critical and {warning_count} warning signals.

Silent Killer Score: {silent_killer_score}/100
{" CRITICAL — Immediate action required" if silent_killer_score > 60 else "WARNING — Monitor closely" if silent_killer_score > 30 else " HEALTHY"}

Signals detected:
""" + "\n".join([f"• {s.get('alert', '')}" for s in signals_data])

    return {
        "status": "ALERT_READY",
        "email_subject": email_subject,
        "email_body": email_body,
        "founder_email": founder_email,
        "silent_killer_score": silent_killer_score,
        "guardrail_actions": actions,
        "critical_count": critical_count,
        "warning_count": warning_count
    }


def calculate_silent_killer_score(signals: str) -> dict:
    """
    Calculates the Silent Killer Score (0-100)
    from all 5 signal severities with cross-signal bonuses.
    """
    signals_data = json.loads(signals) if isinstance(signals, str) else signals

    weights = {
        "zombie_sku": 0.20,
        "cash_cliff": 0.30,
        "margin_drift": 0.20,
        "inventory_collision": 0.15,
        "phantom_liability": 0.15,
    }

    severities = {}
    for signal in signals_data:
        name = signal.get("name", "").lower()
        severity = signal.get("severity", 1)
        for key in weights:
            if key.split("_")[0] in name:
                severities[key] = severity
                break

    # Base score
    base_score = sum(
        severities.get(k, 1) * w * 10
        for k, w in weights.items()
    )

    # Cross-signal bonus — dangerous combinations
    bonus = 0
    has_zombie = severities.get("zombie_sku", 0) > 5
    has_cash = severities.get("cash_cliff", 0) > 5
    has_phantom = severities.get("phantom_liability", 0) > 5
    has_collision = severities.get("inventory_collision", 0) > 5

    if has_zombie and has_cash:
        bonus += 15
        cross_signal_reason = "Zombie SKU + Cash Cliff — 73% of brands with this combo face shutdown within 60 days"
    elif has_phantom and has_cash:
        bonus += 12
        cross_signal_reason = "Phantom Liability + Cash Cliff — true cash position critically misread"
    elif has_collision and has_cash:
        bonus += 10
        cross_signal_reason = "Inventory-Capital Collision + Cash Cliff — liquidity crisis imminent"
    else:
        cross_signal_reason = None

    final_score = min(100, round(base_score + bonus))

    return {
        "silent_killer_score": final_score,
        "base_score": round(base_score),
        "cross_signal_bonus": bonus,
        "cross_signal_reason": cross_signal_reason,
        "risk_level": (
            "CRITICAL" if final_score > 60
            else "WARNING" if final_score > 30
            else "HEALTHY"
        )
    }


alert_agent = Agent(
    model="gemini-2.5-flash",
    name="alert_agent",
    description="Calculates Silent Killer Score and generates alerts with Guardrail action buttons.",
    instruction="""You are the Alert Orchestrator for Nerve.

When called with signal results:
1. Call calculate_silent_killer_score with all signals
2. Call generate_alert_payload with signals + score
3. Return the complete alert package

Your output must always include:
- Silent Killer Score (0-100)
- Risk level (CRITICAL/WARNING/HEALTHY)
- Cross-signal reasoning if applicable
- Guardrail action buttons for the frontend
- Email digest content

Be dramatic but accurate — founders need to feel the urgency.""",
    tools=[calculate_silent_killer_score, generate_alert_payload],
)