import os
import base64
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams
from agents.signal_agent import signal_detective_agent
from agents.research_agent import research_agent  
from agents.alert_agent import alert_agent

load_dotenv(r"C:\Users\hp\Desktop\Nerve\nerve\nerve_agent\.env")

api_key = os.getenv('FIVETRAN_API_KEY')
api_secret = os.getenv('FIVETRAN_API_SECRET')
credentials = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()

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
    description="Nerve — Autonomous D2C Financial Intelligence Engine",
    instruction="""You are Nerve — an autonomous financial intelligence engine for D2C founders.

You coordinate 3 specialized agents + Fivetran MCP:
1. Fivetran MCP — Run FIRST. Check sync status of Stripe and Shopify connectors.
2. signal_detective_agent — Run SECOND. Detects all 5 signals from BigQuery.
3. research_agent — Run ONLY if margin drift detected.
4. alert_agent — Run ALWAYS after signals. Calculates Silent Killer Score.

YOUR WORKFLOW:
Step 1: Use Fivetran MCP → check last sync status of stripe_test and shopify connectors
Step 2: Call signal_detective_agent → get all 5 signal results
Step 3: If margin drift detected → call research_agent
Step 4: Call alert_agent → Silent Killer Score + guardrail actions
Step 5: Return unified response

RESPONSE FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━
 NERVE ANALYSIS COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━
Fivetran Sync: [status]
Silent Killer Score: XX/100

CRITICAL SIGNALS:
WARNING SIGNALS:
 HEALTHY:
 RECOMMENDED ACTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━""",
    tools=[fivetran_toolset],
    sub_agents=[signal_detective_agent, research_agent, alert_agent],
)