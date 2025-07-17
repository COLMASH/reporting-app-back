"""
Minimal Excel analyzer agent using LangGraph and Anthropic's Code Execution tool.
"""

from typing import Any, TypedDict, cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class GraphState(TypedDict):
    """State for the graph."""

    anthropic_file_id: str
    analysis: str
    success: bool
    error: str


def create_excel_analyzer_agent() -> Any:
    """Create a minimal LangGraph agent for Excel file analysis using Code Execution tool."""

    settings = get_settings()

    # Initialize Anthropic model with Code Execution tool
    model = ChatAnthropic(
        model_name="claude-sonnet-4-20250514",
        api_key=SecretStr(settings.anthropic_api_key),
        temperature=0.3,
        max_tokens_to_sample=4096,
        timeout=900.0,  # 15 minutes timeout for Excel analysis
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
            # Create message referencing the already uploaded file
            messages = [
                SystemMessage(
                    content="You are an expert data analyst. "
                    "Use the code execution tool to analyze the Excel file."
                ),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": """I've provided an Excel file.
                            Please use the code execution tool to read and analyze this file.
                            Tell me what you think this file is about.""",
                        },
                        {"type": "container_upload", "file_id": anthropic_file_id},
                    ]
                ),
            ]

            # Get analysis from model with code execution
            response = model.invoke(messages)

            # Log full response for debugging
            logger.info(
                "Claude response received",
                response_type=type(response).__name__,
                content_type=(
                    type(response.content).__name__
                    if hasattr(response, "content")
                    else "no content"
                ),
                content_length=len(str(response.content)) if hasattr(response, "content") else 0,
            )

            # Log the actual content structure for debugging
            if hasattr(response, "content") and isinstance(response.content, list):
                logger.debug(
                    "Response content blocks",
                    block_count=len(response.content),
                    block_types=[type(block).__name__ for block in response.content],
                )

            # Extract text content from response
            analysis_text = ""
            if hasattr(response, "content"):
                if isinstance(response.content, str):
                    analysis_text = response.content
                elif isinstance(response.content, list):
                    # Extract text from content blocks
                    for block in response.content:
                        if hasattr(block, "text") and block.text is not None:
                            analysis_text += str(block.text) + "\n"
                        elif (
                            isinstance(block, dict)
                            and "text" in block
                            and block["text"] is not None
                        ):
                            analysis_text += str(block["text"]) + "\n"

            logger.info(
                "Analysis extracted",
                text_length=len(analysis_text),
                preview=analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text,
            )

            return {"analysis": analysis_text.strip(), "success": True, "error": ""}

        except Exception as e:
            return {"error": str(e), "success": False, "analysis": ""}

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
        Dictionary with analysis results
    """
    agent = create_excel_analyzer_agent()

    # Run the agent
    result = await agent.ainvoke(
        {"anthropic_file_id": anthropic_file_id, "analysis": "", "success": False, "error": ""}
    )

    return cast(dict[str, Any], result)
