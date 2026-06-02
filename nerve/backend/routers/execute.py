from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ExecuteRequest(BaseModel):
    action_id: str
    confirmed: bool = False

@router.post("/execute")
def execute_guardrail_action(req: ExecuteRequest):
    actions = {
        "pause_zombie_ads": {
            "message": "Zombie SKU ads paused successfully",
            "detail": "Ad spend for Classic Tan Wallet and Tan Wallet Pro has been paused across Meta and Google.",
            "impact": "Estimated daily savings: ₹8,400"
        },
        "flash_discount": {
            "message": " Flash 40% discount applied",
            "detail": "Discount applied to Classic Tan Wallet and Tan Wallet Pro. Expected liquidation: 14 days.",
            "impact": "Estimated capital freed: ₹78,960"
        },
        "send_receivable_reminder": {
            "message": " Payment reminder sent",
            "detail": "Automated reminder sent to all pending receivable clients.",
            "impact": "Expected recovery: ₹35,000-60,000 in 7 days"
        },
        "reduce_ad_budget": {
            "message": " Ad budget reduced by 30%",
            "detail": "Meta and Google ad budgets reduced. Phantom liability exposure minimized.",
            "impact": "Reduced unbilled exposure by ₹36,680"
        }
    }

    action = actions.get(req.action_id)
    if not action:
        return {"status": "error", "message": "Unknown action"}

    return {
        "status": "success",
        "action_id": req.action_id,
        "confirmed": req.confirmed,
        **action
    }