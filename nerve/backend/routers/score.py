from fastapi import APIRouter
from fastapi.responses import JSONResponse
from routers.signals import get_all_signals
import traceback

router = APIRouter()

@router.get("/score")
def get_silent_killer_score():
    try:
        data = get_all_signals()
        signals = data["signals"]

        weights = {
            "zombie_sku": 0.20,
            "cash_cliff": 0.30,
            "margin_drift": 0.20,
            "inventory_collision": 0.15,
            "phantom_liability": 0.15,
        }

        base_score = sum(
            signals.get(k, {}).get("severity", 1) * w * 10
            for k, w in weights.items()
        )

        bonus = 0
        cross_reason = None

        has_zombie = signals.get("zombie_sku", {}).get("severity", 0) > 5
        has_phantom = signals.get("phantom_liability", {}).get("severity", 0) > 5
        has_collision = signals.get("inventory_collision", {}).get("severity", 0) > 5

        if has_zombie and has_collision:
            bonus = 15
            zombie_capital = signals.get("zombie_sku", {}).get("total_locked_capital", 0)
            due_days = signals.get("inventory_collision", {}).get("nearest_due_days", 0)
            nearest_vendor = signals.get("inventory_collision", {}).get("nearest_vendor", "vendor")
            upcoming_bills = signals.get("inventory_collision", {}).get("upcoming_bills", 0)
            cross_reason = (
                f" Zombie SKU + Inventory Collision — "
                f"₹{zombie_capital:,.0f} locked in dead stock while "
                f"₹{upcoming_bills:,.0f} due to {nearest_vendor} "
                f"in {due_days} days. Cash crisis imminent!"
            )
        elif has_phantom and has_collision:
            bonus = 12
            true_cash = signals.get("phantom_liability", {}).get("true_cash", 0)
            upcoming_bills = signals.get("inventory_collision", {}).get("upcoming_bills", 0)
            due_days = signals.get("inventory_collision", {}).get("nearest_due_days", 0)
            cross_reason = (
                f"Phantom Liability + Inventory Collision — "
                f"True cash ₹{true_cash:,.0f} vs "
                f"₹{upcoming_bills:,.0f} upcoming bills due in {due_days} days!"
            )
        elif has_zombie and has_phantom:
            bonus = 10
            zombie_capital = signals.get("zombie_sku", {}).get("total_locked_capital", 0)
            unbilled = signals.get("phantom_liability", {}).get("total_unbilled", 0)
            cross_reason = (
                f" Zombie SKU + Phantom Debt — "
                f"₹{zombie_capital:,.0f} locked in dead stock while "
                f"₹{unbilled:,.0f} hidden ad debt accumulates"
            )

        final_score = min(100, round(base_score + bonus))

        return {
            "silent_killer_score": final_score,
            "risk_level": "CRITICAL" if final_score > 60 else "WARNING" if final_score > 30 else "HEALTHY",
            "cross_signal_bonus": bonus,
            "cross_signal_reason": cross_reason,
            "signals": signals
        }

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[score] ERROR: {e}\n{tb}")
        return JSONResponse(status_code=500, content={"detail": str(e), "traceback": tb})
