"""
LangGraph agent for portfolio report generation.

Two-phase approach:
1. Optional research using Brave Search
2. Analyze portfolio data and generate insights
3. Generate professional markdown report
"""

from typing import Any, TypedDict, cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.logging import get_logger
from src.modules.portfolio_reports.agent.prompts import (
    SYSTEM_PROMPT,
    get_analysis_prompt,
    get_markdown_generation_prompt,
)
from src.modules.portfolio_reports.agent.research import perform_asset_research

logger = get_logger(__name__)

# Constants
MAX_TOKENS = 64000
ANALYSIS_TIMEOUT = 600.0  # 10 minutes


class GraphState(TypedDict):
    """State for the report generation graph."""

    portfolio_data: dict[str, Any]
    user_prompt: str | None
    research_enabled: bool
    research_data: dict[str, Any] | None
    analysis: str
    markdown_report: str
    success: bool
    error: str
    input_tokens: int
    output_tokens: int


def create_portfolio_report_agent() -> Any:
    """Create LangGraph agent for portfolio report generation."""

    settings = get_settings()

    # Initialize Claude Opus 4.5
    model = ChatAnthropic(
        model_name="claude-opus-4-5-20251101",
        api_key=SecretStr(settings.anthropic_api_key),
        temperature=0.3,  # Slightly creative for report writing
        max_tokens_to_sample=MAX_TOKENS,
        timeout=ANALYSIS_TIMEOUT,
        stop=None,
    )

    graph = StateGraph(GraphState)

    # Node 1: Research (conditional)
    async def research_assets(state: GraphState) -> dict[str, Any]:
        """Perform internet research on portfolio assets if enabled."""
        if not state["research_enabled"]:
            logger.info("Research mode disabled, skipping")
            return {"research_data": None}

        try:
            portfolio_data = state["portfolio_data"]
            research_results = await perform_asset_research(portfolio_data)

            logger.info(
                "Asset research completed",
                assets_researched=len(research_results),
            )

            return {"research_data": research_results}
        except Exception as e:
            logger.error("Research failed", error=str(e))
            return {"research_data": None}

    # Node 2: Analysis
    def analyze_portfolio(state: GraphState) -> dict[str, Any]:
        """Analyze portfolio data and generate insights."""
        try:
            portfolio_data = state["portfolio_data"]
            user_prompt = state.get("user_prompt")
            research_data = state.get("research_data")

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=get_analysis_prompt(
                        portfolio_data=portfolio_data,
                        user_prompt=user_prompt,
                        research_data=research_data,
                    )
                ),
            ]

            logger.info("Starting portfolio analysis")
            response = model.invoke(messages)

            analysis_text = response.content if isinstance(response.content, str) else str(response.content)

            logger.info("Portfolio analysis completed", analysis_length=len(analysis_text))

            return {"analysis": analysis_text}
        except Exception as e:
            logger.error("Analysis failed", error=str(e))
            return {"error": str(e), "success": False}

    # Node 3: Generate Markdown Report
    def generate_markdown(state: GraphState) -> dict[str, Any]:
        """Generate structured markdown report from analysis."""
        try:
            analysis = state["analysis"]
            portfolio_data = state["portfolio_data"]
            user_prompt = state.get("user_prompt")
            research_data = state.get("research_data")

            # Build context for markdown generation
            context = f"""
Based on the following analysis, generate a complete professional markdown report.

## Portfolio Data Summary
- Report Scope: {portfolio_data.get('scope', 'unknown')}
- Report Date: {portfolio_data.get('report_date', 'all dates')}
- Total Assets: {portfolio_data.get('total_assets_count', 0)}
- Total Value (USD): ${portfolio_data.get('summary', {}).get('total_estimated_value_usd', 0):,.2f}
- Total Value (EUR): EUR {portfolio_data.get('summary', {}).get('total_estimated_value_eur', 0):,.2f}

## Applied Filters
{_format_filters(portfolio_data.get('filters_applied', {}))}

## Analysis Results
{analysis}
"""

            if user_prompt:
                context += f"""
## User Requirements
{user_prompt}
"""

            if research_data:
                context += f"""
## Market Research Data
Research was conducted on {len(research_data)} assets. Key findings:
{_summarize_research(research_data)}
"""

            context += """

Generate the complete markdown report with all relevant sections.
Ensure proper formatting with tables for numerical data.
"""

            messages = [
                SystemMessage(content=get_markdown_generation_prompt()),
                HumanMessage(content=context),
            ]

            logger.info("Generating markdown report")
            response = model.invoke(messages)

            markdown_content = response.content if isinstance(response.content, str) else str(response.content)

            logger.info(
                "Markdown report generated",
                content_length=len(markdown_content),
            )

            # Calculate token usage if available
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0

            return {
                "markdown_report": markdown_content,
                "success": True,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        except Exception as e:
            logger.error("Markdown generation failed", error=str(e))
            return {"error": str(e), "success": False}

    # Add nodes
    graph.add_node("research", research_assets)
    graph.add_node("analyze", analyze_portfolio)
    graph.add_node("generate", generate_markdown)

    # Add edges
    graph.add_edge(START, "research")
    graph.add_edge("research", "analyze")
    graph.add_edge("analyze", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


def _format_filters(filters: dict[str, Any]) -> str:
    """Format applied filters for display."""
    parts = []
    if filters.get("entity"):
        parts.append(f"- Entity: {filters['entity']}")
    if filters.get("asset_type"):
        parts.append(f"- Asset Type: {filters['asset_type']}")
    if filters.get("holding_company"):
        parts.append(f"- Holding Company: {filters['holding_company']}")

    if not parts:
        return "- No filters applied"
    return "\n".join(parts)


def _summarize_research(research_data: dict[str, Any]) -> str:
    """Summarize research data for context."""
    summaries = []
    for asset_name, data in list(research_data.items())[:5]:  # Top 5
        results = data.get("results", [])
        if results:
            summaries.append(f"- **{asset_name}**: {results[0].get('title', 'No title')}")

    if not summaries:
        return "No research results available."
    return "\n".join(summaries)


async def generate_portfolio_report(
    portfolio_data: dict[str, Any],
    user_prompt: str | None = None,
    research_enabled: bool = False,
) -> dict[str, Any]:
    """
    Generate a portfolio analysis report.

    Args:
        portfolio_data: Portfolio data from database
        user_prompt: Optional user instructions
        research_enabled: Whether to fetch internet data

    Returns:
        Dict with markdown_report, success, and error
    """
    agent = create_portfolio_report_agent()

    result = await agent.ainvoke(
        {
            "portfolio_data": portfolio_data,
            "user_prompt": user_prompt,
            "research_enabled": research_enabled,
            "research_data": None,
            "analysis": "",
            "markdown_report": "",
            "success": False,
            "error": "",
            "input_tokens": 0,
            "output_tokens": 0,
        }
    )

    return cast(dict[str, Any], result)
