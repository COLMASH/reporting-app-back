"""
Enhanced Excel analyzer agent using LangGraph and Anthropic's Code Execution tool.
Returns structured JSON output optimized for Chart.js visualizations.
"""

import json
from typing import Any, TypedDict, cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.logging import get_logger
from src.modules.reporting_analyses.agent.prompts import (
    ANALYSIS_TIMEOUT,
    MAX_TOKENS,
    REQUIRED_OUTPUT_KEYS,
    get_system_prompt,
    get_user_prompt,
)

logger = get_logger(__name__)


class GraphState(TypedDict):
    """State for the graph."""

    anthropic_file_id: str
    analysis: str
    structured_output: dict[str, Any] | None
    success: bool
    error: str


def _extract_text_from_response(response: Any) -> str:
    """Extract text content from Claude's response."""
    if not hasattr(response, "content"):
        return ""

    if isinstance(response.content, str):
        return response.content

    if isinstance(response.content, list):
        text_parts = []
        for block in response.content:
            if hasattr(block, "text") and block.text is not None:
                text_parts.append(str(block.text))
            elif isinstance(block, dict) and "text" in block and block["text"] is not None:
                text_parts.append(str(block["text"]))
        return "".join(text_parts)

    return ""


def _parse_structured_output(analysis_text: str) -> dict[str, Any] | None:
    """Parse and validate structured JSON output from analysis."""
    if not analysis_text:
        return None

    try:
        # Find JSON content (in case there's extra text)
        json_start = analysis_text.find("{")
        json_end = analysis_text.rfind("}") + 1

        if json_start < 0 or json_end <= json_start:
            return None

        json_str = analysis_text[json_start:json_end]
        structured_output = json.loads(json_str)

        # Validate required keys
        if all(key in structured_output for key in REQUIRED_OUTPUT_KEYS):
            logger.info(
                "Successfully parsed structured output",
                metrics_count=len(structured_output.get("key_metrics", [])),
                visualizations_count=len(structured_output.get("visualizations", [])),
            )
            return cast(dict[str, Any], structured_output)
        else:
            missing = REQUIRED_OUTPUT_KEYS - set(structured_output.keys())
            logger.warning("Structured output missing required keys", missing_keys=missing)
            return None

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON",
            error=str(e),
            preview=analysis_text[:200] if analysis_text else "empty",
        )
        return None


def create_excel_analyzer_agent() -> Any:
    """Create an enhanced LangGraph agent for Excel file analysis with structured output."""

    settings = get_settings()

    # Initialize Anthropic model with Code Execution tool
    model = ChatAnthropic(
        model_name="claude-sonnet-4-20250514",
        api_key=SecretStr(settings.anthropic_api_key),
        temperature=0.3,
        max_tokens_to_sample=MAX_TOKENS,
        timeout=ANALYSIS_TIMEOUT,
        stop=None,
        default_headers={"anthropic-beta": "code-execution-2025-05-22,files-api-2025-04-14"},
    ).bind_tools([{"type": "code_execution_20250522", "name": "code_execution"}])

    # Create graph
    graph = StateGraph(GraphState)

    # Define the analysis function
    def analyze_excel(state: GraphState) -> dict[str, Any]:
        """Analyze Excel file using Anthropic's Code Execution tool."""
        anthropic_file_id = state["anthropic_file_id"]

        try:
            # Create message with file reference
            messages = [
                SystemMessage(content=get_system_prompt()),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": get_user_prompt(),
                        },
                        {"type": "container_upload", "file_id": anthropic_file_id},
                    ]
                ),
            ]

            # Get analysis from model with code execution
            response = model.invoke(messages)

            # Log response for debugging
            logger.info(
                "Claude response received",
                response_type=type(response).__name__,
                content_length=len(str(response.content)) if hasattr(response, "content") else 0,
            )

            # Extract text content from response
            analysis_text = _extract_text_from_response(response)

            # Try to parse structured JSON output
            structured_output = _parse_structured_output(analysis_text)

            return {
                "analysis": analysis_text.strip(),
                "structured_output": structured_output,
                "success": True,
                "error": "",
            }

        except Exception as e:
            logger.error("Analysis failed", error=str(e), anthropic_file_id=anthropic_file_id)
            return {
                "error": str(e),
                "success": False,
                "analysis": "",
                "structured_output": None,
            }

    # Add node to graph
    graph.add_node("analyze", analyze_excel)

    # Add edges
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", END)

    return graph.compile()


async def analyze_excel_file(anthropic_file_id: str) -> dict[str, Any]:
    """
    Analyze an Excel file using Claude's Code Execution tool.

    Args:
        anthropic_file_id: Anthropic file ID from the File record in database

    Returns:
        Dictionary with analysis results including structured output for Chart.js
    """
    agent = create_excel_analyzer_agent()

    # Run the agent
    result = await agent.ainvoke(
        {
            "anthropic_file_id": anthropic_file_id,
            "analysis": "",
            "structured_output": None,
            "success": False,
            "error": "",
        }
    )

    return cast(dict[str, Any], result)
