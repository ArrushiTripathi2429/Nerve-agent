from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from routers.signals import get_all_signals
import traceback

router = APIRouter()

class WhatIfRequest(BaseModel):
    ad_spend_change: float = 0
    return_rate_change: float = 0
    pause_zombie_sku: bool = False
    delay_payment_days: int = 0

@router.post("/whatif")
def whatif_simulator(req: WhatIfRequest):
    try:
        data = get_all_signals()
        signals = data["signals"]

        cash = signals.get("cash_cliff", {})
        phantom = signals.get("phantom_liability", {})
        zombie = signals.get("zombie_sku", {})

        bank_balance = cash.get("bank_balance", 0)
        daily_burn = cash.get("daily_burn_rate", 8000)
        total_unbilled = phantom.get("total_unbilled", 0)
        locked_capital = zombie.get("total_locked_capital", 0)

        new_burn = daily_burn * (1 + req.ad_spend_change / 100)
        new_unbilled = total_unbilled * (1 + req.ad_spend_change / 100)

        freed_capital = locked_capital * 0.6 if req.pause_zombie_sku else 0
        new_balance = bank_balance + freed_capital
        new_true_cash = new_balance - new_unbilled
        new_runway = int(new_balance / new_burn) if new_burn > 0 else 999

        runway_severity = 10 if new_runway < 10 else 7 if new_runway < 20 else 2
        phantom_severity = 9 if new_unbilled > new_balance * 0.25 else 5 if new_unbilled > new_balance * 0.1 else 2
        zombie_severity = 1 if req.pause_zombie_sku else signals.get("zombie_sku", {}).get("severity", 5)

        new_score = min(100, round(
            zombie_severity * 0.20 * 10 +
            runway_severity * 0.30 * 10 +
            signals.get("margin_drift", {}).get("severity", 2) * 0.20 * 10 +
            signals.get("inventory_collision", {}).get("severity", 2) * 0.15 * 10 +
            phantom_severity * 0.15 * 10
        ))

        return {
            "baseline": {
                "runway_days": cash.get("runway_days", 0),
                "true_cash": phantom.get("true_cash", 0),
                "silent_killer_score": 67
            },
            "projected": {
                "runway_days": new_runway,
                "true_cash": round(new_true_cash, 2),
                "daily_burn": round(new_burn, 2),
                "silent_killer_score": new_score,
                "freed_capital": round(freed_capital, 2)
            },
            "improvement": {
                "runway_change": new_runway - cash.get("runway_days", 0),
                "score_change": new_score - 67,
                "cash_freed": round(freed_capital, 2)
            }
        }

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[whatif] ERROR: {e}\n{tb}")
        return JSONResponse(status_code=500, content={"detail": str(e), "traceback": tb})