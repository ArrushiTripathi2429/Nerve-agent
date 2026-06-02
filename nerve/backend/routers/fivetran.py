from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/fivetran/sync")
def get_fivetran_sync_status():
    return {
        "connector": "shopify",
        "status": "Active",
        "last_synced": "3 hours ago",
        "next_sync": "in 31 minutes",
        "sync_frequency": "6 hours",
        "tables_synced": 43,
        "destination": "BigQuery — nerve-agent-496707",
        "dataset": "nerve_data",
        "health": " Connected"
    }