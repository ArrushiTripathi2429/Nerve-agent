from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams
from agents.signal_agent import signal_detective_agent
from agents.alert_agent import alert_agent
from agents.research_agent import research_agent
from dotenv import load_dotenv
import os

load_dotenv(r"C:\Users\hp\Desktop\Nerve\nerve\nerve_agent\.env")

api_key = os.getenv('FIVETRAN_API_KEY')
api_secret = os.getenv('FIVETRAN_API_SECRET')
credentials = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
# Fivetran MCP Toolset
fivetran_toolset = MCPToolset(
    connection_params=SseServerParams(
        url="https://mcp.fivetran.com/sse",
        headers={
           "Authorization": f"Basic {credentials}"
        }
    )
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="nerve_orchestrator",
    description="""Nerve is a multi-agent D2C financial intelligence engine.
    It detects silent killers in your business before they kill you.""",
    instruction="""You are Nerve — the AI CFO for D2C brands.

Your job is to orchestrate a full financial health scan every time you are called.

STEP 1 — FIVETRAN SYNC CHECK:
- Use Fivetran MCP tools to check last sync status
- Verify that Stripe and Shopify data is fresh (synced within last 24 hours)
- If sync is stale, trigger a new sync via Fivetran MCP

STEP 2 — SIGNAL DETECTION:
- Call signal_detective_agent to run all 5 signal checks:
  1. Zombie SKU detection
  2. Cash Cliff detection
  3. Margin Drift detection
  4. Inventory-Capital Collision detection
  5. Phantom Liability detection

STEP 3 — RESEARCH (if needed):
- If Margin Drift is CRITICAL or WARNING, call research_agent
- Get competitor benchmarks and ROAS recovery strategies

STEP 4 — ALERT GENERATION:
- Call alert_agent with all signal results
- Generate Silent Killer Score (0-100)
- Generate Guardrail action buttons for frontend
- Generate founder email digest

STEP 5 — FINAL RESPONSE:
Return a complete JSON with:
{
  "fivetran_sync_status": "...",
  "silent_killer_score": 0-100,
  "risk_level": "CRITICAL/WARNING/HEALTHY",
  "signals": [...],
  "guardrail_actions": [...],
  "research_insights": "..." (if applicable),
  "email_digest": "...",
  "cross_signal_reason": "..."
}

Be urgent, specific, and actionable. Think like a CFO who has seen D2C brands die from these exact patterns.""",
    tools=[fivetran_toolset],
    sub_agents=[signal_detective_agent, alert_agent, research_agent],
)
