"""Financial Optimization Orchestrator Agent.

This agent demonstrates the orchestrator-workers pattern using Claude Agent SDK.
It fetches financial data from MCP servers and coordinates specialized sub-agents
to provide comprehensive financial optimization recommendations.
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)

logger = logging.getLogger(__name__)


DATA_DIR: Path = Path(__file__).parent.parent / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw_data"
AGENT_OUTPUTS_DIR: Path = DATA_DIR / "agent_outputs"


def _ensure_directories():
    """Ensure all required directories exist."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_json(data: dict, filename: str):
    """Save data to JSON file."""
    filepath = RAW_DATA_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved data to {filepath}")


def _load_prompt(filename: str) -> str:
    """Load prompt from prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    return prompt_path.read_text()


async def _auto_approve_all(tool_name: str, input_data: dict, context):
    """Auto-approve all tools without prompting."""
    logger.debug(f"Auto-approving tool: {tool_name}")
    from claude_agent_sdk import PermissionResultAllow

    return PermissionResultAllow()


def _detect_subscriptions(
    bank_transactions: list[dict], credit_card_transactions: list[dict]
) -> list[dict]:
    """Detect subscription services from recurring transactions.

    TODO: Implement logic to:
    1. Filter transactions marked as recurring
    2. Identify subscription patterns (monthly charges)
    3. Categorize by service type
    4. Calculate total monthly subscription cost

    Args:
        bank_transactions: List of bank transaction dicts
        credit_card_transactions: List of credit card transaction dicts

    Returns:
        List of subscription dictionaries with service name, amount, frequency
    """
    subscriptions = []

    # TODO: Implement subscription detection logic
    # Hint: Look for transactions with recurring=True
    # Hint: Subscriptions are typically negative amounts (outflows)
    all_transactions = bank_transactions + credit_card_transactions
    for txn in all_transactions:
        if txn.get("recurring", False):
            amount = abs(txn.get("amount", 0))
            subscription = {
                "service": txn.get("description", txn.get("merchant", "Unknown")),
                "amount": amount,
                "frequency": "monthly",
            }
            subscriptions.append(subscription)
    return subscriptions


async def _fetch_financial_data(
    username: str, start_date: str, end_date: str
) -> tuple[dict, dict]:
    """Fetch data from Bank and Credit Card MCP servers.

    TODO: Implement MCP server connections using Claude Agent SDK
    1. Configure MCP server connections (ports 5001, 5002)
    2. Call get_bank_transactions tool
    3. Call get_credit_card_transactions tool
    4. Save raw data to files

    Args:
        username: Username for the account
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Tuple of (bank_data, credit_card_data) dictionaries
    """
    logger.info(
        f"Fetching financial data for {username} from {start_date} to {end_date}"
    )

    # TODO: Configure and connect to MCP servers
    # Example MCP configuration (keys must match FastMCP server names exactly):
    mcp_servers = {
        "Bank Account Server": {  # MUST match FastMCP server name exactly
            "type": "http",
            "url": "http://127.0.0.1:5001/mcp",
        },
        "Credit Card Server": {"type": "http", "url": "http://127.0.0.1:5002/mcp"},
    }

    working_dir = Path(__file__).parent.parent
    options = ClaudeAgentOptions(
        model="haiku",
        system_prompt="You are a data fetching assistant. Call the requested MCP tools and return the raw JSON results. Do not analyze or summarize the data.",
        mcp_servers=mcp_servers,
        can_use_tool=_auto_approve_all,
        cwd=str(working_dir),
    )

    # TODO: Call MCP tools to fetch data
    bank_data = {}  # Placeholder
    credit_card_data = {}  # Placeholder

    try:
        async with ClaudeSDKClient(options=options) as client:
            prompt = f"""Please fetch financial data using these two tools:

1. Call get_bank_transactions with:
   - username: "{username}"
   - start_date: "{start_date}"
   - end_date: "{end_date}"

2. Call get_credit_card_transactions with:
   - username: "{username}"
   - start_date: "{start_date}"
   - end_date: "{end_date}"

Return the raw JSON results from both tools."""

            await client.query(prompt)

            full_text = ""
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_text += block.text
                elif isinstance(message, ResultMessage):
                    logger.info(f"Data fetch completed in {message.duration_ms}ms")
                    break

    except Exception as e:
        logger.error(f"Error fetching financial data: {e}", exc_info=True)

    # Save raw data
    _save_json(bank_data, "bank_transactions.json")
    _save_json(credit_card_data, "credit_card_transactions.json")

    return bank_data, credit_card_data


async def _run_orchestrator(
    username: str, start_date: str, end_date: str, user_query: str
):
    """Main orchestrator agent logic.

    TODO: Implement the orchestrator pattern:
    1. Fetch data from MCP servers (use tools)
    2. Perform initial analysis (detect subscriptions, anomalies)
    3. Decide which sub-agents to invoke based on query
    4. Define sub-agents using AgentDefinition
    5. Invoke sub-agents (can be parallel)
    6. Read and synthesize sub-agent results
    7. Generate final report

    Args:
        username: Username for the account
        start_date: Start date for analysis
        end_date: End date for analysis
        user_query: User's financial question/request
    """
    logger.info(f"Starting financial optimization orchestrator")
    logger.info(f"User query: {user_query}")

    _ensure_directories()

    # Step 1: Fetch financial data from MCP servers
    bank_data, credit_card_data = await _fetch_financial_data(
        username, start_date, end_date
    )

    # Step 2: Initial analysis
    logger.info("Performing initial analysis...")

    bank_transactions = bank_data.get("transactions", [])
    credit_card_transactions = credit_card_data.get("transactions", [])

    subscriptions = _detect_subscriptions(bank_transactions, credit_card_transactions)

    logger.info(f"Detected {len(subscriptions)} subscriptions")

    # Step 3: Define sub-agents
    # TODO: Define sub-agents using AgentDefinition
    research_agent = AgentDefinition(
        description="Research cheaper alternatives for subscriptions and services",
        prompt=_load_prompt("research_agent_prompt.txt"),
        tools=["write"],
        model="haiku",
    )

    negotiation_agent = AgentDefinition(
        description="Create negotiation strategies and scripts for bills and services",
        prompt=_load_prompt("negotiation_agent_prompt.txt"),
        tools=["write"],
        model="haiku",
    )

    tax_agent = AgentDefinition(
        description="Identify tax-deductible expenses and optimization opportunities",
        prompt=_load_prompt("tax_agent_prompt.txt"),
        tools=["write"],
        model="haiku",
    )

    agents = {
        "research_agent": research_agent,
        "negotiation_agent": negotiation_agent,
        "tax_agent": tax_agent,
    }

    # Step 4: Configure orchestrator agent with sub-agents
    # TODO: Create ClaudeAgentOptions with agents and MCP servers
    working_dir = Path(__file__).parent.parent
    mcp_servers = {
        "Bank Account Server": {"type": "http", "url": "http://127.0.0.1:5001/mcp"},
        "Credit Card Server": {"type": "http", "url": "http://127.0.0.1:5002/mcp"},
    }
    options = ClaudeAgentOptions(
        model="sonnet",  # Main orchestrator uses Sonnet
        system_prompt=_load_prompt(
            "orchestrator_system_prompt.txt"
        ),  # Instructions from file
        mcp_servers=mcp_servers,  # External data sources
        agents=agents,  # Sub-agents available as "tools"
        can_use_tool=_auto_approve_all,  # Permission callback
        cwd=str(working_dir),  # Base directory for file ops
    )

    # Step 5: Run orchestrator with Claude Agent SDK
    # TODO: Use ClaudeSDKClient to run the orchestration
    user_prompt_template = _load_prompt("orchestrator_user_prompt.txt")
    prompt = user_prompt_template.format(
        user_query=user_query,
        username=username,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send initial query
            await client.query(prompt)

            # Receive streaming responses
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    # Handle text output
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end='', flush=True)
                elif isinstance(message, ResultMessage):
                    # Conversation complete
                    logger.info(f"Duration: {message.duration_ms}ms")
                    logger.info(f"Cost: ${message.total_cost_usd:.4f}")
                    logger.info(f"Stop reason: {message.stop_reason}")
                    break
    except Exception as e:
        logger.error(f"Error during orchestration: {e}", exc_info=True)
        logger.error("\nTroubleshooting:")
        logger.error("1. Make sure MCP servers are running")
        logger.error("2. Test servers: ...")
        logger.error("   curl http://127.0.0.1:5001/health")
        logger.error("   curl http://127.0.0.1:5002/health")
        logger.error("3. Check that ANTHROPIC_API_KEY is set")
        raise

    # Step 6: Generate final report
    logger.info("Orchestration complete. Check data/final_report.txt for results.")


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Financial Optimization Orchestrator Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    # Basic analysis
    uv run python financial_orchestrator.py \\
        --username john_doe \\
        --start-date 2026-01-01 \\
        --end-date 2026-01-31 \\
        --query "How can I save $500 per month?"

    # Subscription analysis
    uv run python financial_orchestrator.py \\
        --username jane_smith \\
        --start-date 2026-01-01 \\
        --end-date 2026-01-31 \\
        --query "Analyze my subscriptions and find better deals"
""",
    )

    parser.add_argument(
        "--username",
        type=str,
        required=True,
        help="Username for account (john_doe or jane_smith)",
    )

    parser.add_argument(
        "--start-date", type=str, required=True, help="Start date in YYYY-MM-DD format"
    )

    parser.add_argument(
        "--end-date", type=str, required=True, help="End date in YYYY-MM-DD format"
    )

    parser.add_argument(
        "--query", type=str, required=True, help="User's financial question or request"
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = _parse_args()

    await _run_orchestrator(
        username=args.username,
        start_date=args.start_date,
        end_date=args.end_date,
        user_query=args.query,
    )


if __name__ == "__main__":
    asyncio.run(main())
