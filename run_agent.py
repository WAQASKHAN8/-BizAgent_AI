import sys
import os
import json
from agents.coordinator import CoordinatorAgent
from database.db import init_db

# Ensure database is initialized
init_db()

def run_agent_workflow(user_query: str):
    print("=" * 70)
    print("🤖 BIZAGENT AI — MULTI-AGENT EXECUTION RUNNER")
    print("=" * 70)
    print(f"\n📥 User Input Query:\n   \"{user_query}\"\n")
    print("-" * 70)
    print("🧠 Master Coordinator analyzing query with Gemini AI...")
    
    result = CoordinatorAgent.route_request(
        user_message=user_query,
        customer_info={"name": "Executive Tester", "email": "tester@enterprise.com"}
    )
    
    print(f"\n⚡ Active Agent Swarm: {result['agent']}")
    print(f"🎯 Classified Workflow Intent: {result['intent']}\n")
    
    print("📋 Autonomous Actions Executed by Agents:")
    for act in result.get("actions", []):
        print(f"   ✓ {act}")
        
    if result.get("approval_required"):
        print("\n⚠️ HUMAN-IN-THE-LOOP (HITL) GOVERNANCE TRIGGERED:")
        for flag in result.get("approval_flags", []):
            print(f"   [PENDING MANAGER REVIEW] {flag}")
            
    print("\n" + "=" * 70)
    print("💬 FINAL SYNTHESIZED AI RESPONSE:")
    print("=" * 70)
    print(result["response"])
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default test scenario requiring multi-agent collaboration:
        query = (
            "We want to buy BizAgent AI for Acme Corp (50 employees, budget $12,000). "
            "Can we get a 25% discount and book an enterprise demo meeting for tomorrow?"
        )
    run_agent_workflow(query)
