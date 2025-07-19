"""
Enhanced Excel analyzer agent using LangGraph and Anthropic's Code Execution tool.
Returns structured JSON output optimized for Chart.js visualizations.
"""

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
    get_structured_output_prompt,
    get_system_prompt,
    get_user_prompt,
)
from src.modules.reporting_analyses.agent.schemas import ExcelAnalysisOutput

logger = get_logger(__name__)


class GraphState(TypedDict):
    """State for the graph."""

    anthropic_file_id: str
    analysis: str
    structured_output: dict[str, Any] | None
    success: bool
    error: str
    input_tokens: int
    output_tokens: int


def _extract_text_from_response(response: Any) -> str:
    """Extract text content from Claude's response, including code execution results."""
    if not hasattr(response, "content"):
        logger.warning("Response has no content attribute")
        return ""

    if isinstance(response.content, str):
        return response.content

    if isinstance(response.content, list):
        text_parts = []
        code_outputs = []  # Collect code execution outputs

        for i, block in enumerate(response.content):
            block_type = type(block).__name__

            # Log block info for debugging
            if i < 3 or i >= len(response.content) - 3:
                if isinstance(block, dict):
                    logger.info(
                        f"Block {i}/{len(response.content)}",
                        block_type=block_type,
                        is_dict=True,
                        dict_type=block.get("type", "no_type"),
                        dict_keys=list(block.keys()) if len(block) < 10 else f"{len(block)} keys",
                    )
                else:
                    logger.info(
                        f"Block {i}/{len(response.content)}",
                        block_type=block_type,
                        is_dict=False,
                        has_type_attr=hasattr(block, "type"),
                        type_attr=getattr(block, "type", None),
                    )

            # Handle different block types - blocks come as dicts from LangChain
            if isinstance(block, dict):
                block_type_str = block.get("type", "")

                # Text blocks
                if block_type_str == "text" and "text" in block:
                    text_parts.append(str(block["text"]))
                    logger.info(f"Found text block {i}", length=len(block["text"]))

                # Code execution result blocks
                elif block_type_str == "code_execution_tool_result":
                    # Log the full block structure for debugging
                    logger.info(
                        f"Code execution block {i} structure",
                        text_value=block.get("text", "NO_TEXT"),
                        text_empty=block.get("text") == "",
                        content_type=type(block.get("content")).__name__,
                        content_value=(
                            str(block.get("content"))[:200]
                            if block.get("content")
                            else "NO_CONTENT"
                        ),
                    )

                    # Extract text from code execution result
                    # The content is in block["content"]["stdout"]
                    if "content" in block and isinstance(block["content"], dict):
                        content_dict = block["content"]

                        # Extract stdout if present
                        if "stdout" in content_dict and content_dict["stdout"]:
                            code_outputs.append(str(content_dict["stdout"]))
                            logger.info(
                                f"Found stdout in block {i}", length=len(content_dict["stdout"])
                            )

                        # Log stderr for debugging (but don't include in outputs)
                        if "stderr" in content_dict and content_dict["stderr"]:
                            logger.warning(
                                f"Code execution error in block {i}",
                                stderr=content_dict["stderr"][:200],
                            )

                    # Fallback checks for other formats
                    elif "text" in block and block["text"]:
                        code_outputs.append(str(block["text"]))
                        logger.info(f"Found text in block {i}", length=len(block["text"]))
                    elif "stdout" in block and block["stdout"]:
                        code_outputs.append(str(block["stdout"]))
                        logger.info(
                            f"Found direct stdout in block {i}", length=len(block["stdout"])
                        )

                # Tool use blocks (skip these)
                elif block_type_str in ["tool_use", "server_tool_use"]:
                    logger.debug(f"Skipping tool use block {i}")
                    continue

                # Log unknown block types
                else:
                    logger.warning(
                        f"Unknown block type in {i}",
                        block_type=block_type_str,
                        keys=list(block.keys()),
                    )

            # Handle objects with attributes (in case response format varies)
            elif hasattr(block, "type"):
                block_type_attr = getattr(block, "type", "")

                # Text blocks
                if block_type_attr == "text" and hasattr(block, "text"):
                    text_parts.append(str(block.text))

                # Code execution result blocks
                elif block_type_attr == "code_execution_tool_result":
                    if hasattr(block, "stdout") and block.stdout:
                        code_outputs.append(str(block.stdout))
                        logger.info(f"Found code output in block {i}", length=len(block.stdout))

        # Combine text and code outputs
        # Look for JSON in code outputs first (preferred), then in text parts
        all_text = "".join(code_outputs) + "".join(text_parts)

        # If we still have no text, check if the last block might be the JSON
        if not all_text and response.content:
            logger.info("No text found, checking last block for JSON")
            last_block = response.content[-1]
            if isinstance(last_block, dict) and "text" in last_block:
                all_text = str(last_block["text"])

        # Debug: Log all text blocks to see if we're missing the JSON
        if response.content:
            for i, block in enumerate(response.content):
                if isinstance(block, dict) and block.get("type") == "text":
                    logger.info(
                        f"Text block {i} content",
                        text_preview=str(block.get("text", ""))[:200],
                        text_length=len(str(block.get("text", ""))),
                    )

        logger.info(
            "Text extraction summary",
            text_parts_count=len(text_parts),
            code_outputs_count=len(code_outputs),
            total_length=len(all_text),
        )

        return all_text

    # Log the actual content type for debugging
    logger.warning(
        "Response content is not string or list",
        content_type=type(response.content).__name__,
    )
    return ""


def create_excel_analyzer_agent() -> Any:
    """Create an enhanced LangGraph agent for Excel file analysis with structured output."""

    settings = get_settings()

    # Initialize Anthropic model with Code Execution tool AND structured output
    base_model = ChatAnthropic(
        model_name="claude-sonnet-4-20250514",
        api_key=SecretStr(settings.anthropic_api_key),
        temperature=0,
        max_tokens_to_sample=MAX_TOKENS,
        timeout=ANALYSIS_TIMEOUT,
        stop=None,
        default_headers={"anthropic-beta": "code-execution-2025-05-22,files-api-2025-04-14"},
    ).bind_tools([{"type": "code_execution_20250522", "name": "code_execution"}])

    # Create structured output model
    structured_model = base_model.with_structured_output(ExcelAnalysisOutput)  # type: ignore[attr-defined]

    # Create graph
    graph = StateGraph(GraphState)

    # Define the analysis function
    def analyze_excel(state: GraphState) -> dict[str, Any]:
        """Analyze Excel file using two-phase approach: analysis + structured output."""
        anthropic_file_id = state["anthropic_file_id"]
        input_tokens = 0
        output_tokens = 0

        try:
            # Phase 1: Analysis with code execution
            analysis_messages = [
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

            logger.info("Starting Phase 1: Excel analysis with code execution")
            analysis_response = base_model.invoke(analysis_messages)

            # Extract token usage
            if hasattr(analysis_response, "usage_metadata"):
                input_tokens += getattr(analysis_response.usage_metadata, "input_tokens", 0)
                output_tokens += getattr(analysis_response.usage_metadata, "output_tokens", 0)

            # Extract analysis text
            analysis_text = _extract_text_from_response(analysis_response)
            logger.info(
                "Phase 1 complete",
                analysis_length=len(analysis_text) if analysis_text else 0,
                phase1_input_tokens=input_tokens,
                phase1_output_tokens=output_tokens,
            )

            # Phase 2: Generate structured output
            structured_messages = [
                SystemMessage(content=get_structured_output_prompt()),
                HumanMessage(
                    content=(
                        f"Based on my analysis of the Excel file, "
                        f"here's what I found:\n\n{analysis_text}"
                    )
                ),
            ]

            logger.info("Starting Phase 2: Generating structured output")
            structured_response = structured_model.invoke(structured_messages)

            # Extract token usage from phase 2
            phase2_input = 0
            phase2_output = 0
            if hasattr(structured_response, "usage_metadata"):
                phase2_input = getattr(structured_response.usage_metadata, "input_tokens", 0)
                phase2_output = getattr(structured_response.usage_metadata, "output_tokens", 0)
                input_tokens += phase2_input
                output_tokens += phase2_output

            # Convert Pydantic model to dict
            structured_dict = (
                structured_response.model_dump()
                if hasattr(structured_response, "model_dump")
                else structured_response
            )

            logger.info(
                "Analysis completed with structured output",
                has_structured_output=bool(structured_dict),
                num_metrics=len(structured_dict.get("key_metrics", [])) if structured_dict else 0,
                num_visualizations=(
                    len(structured_dict.get("visualizations", [])) if structured_dict else 0
                ),
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
            )

            return {
                "analysis": analysis_text.strip() if analysis_text else "Analysis completed",
                "structured_output": structured_dict,
                "success": True,
                "error": "",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            logger.error("Analysis failed", error=str(e), anthropic_file_id=anthropic_file_id)
            return {
                "error": str(e),
                "success": False,
                "analysis": "",
                "structured_output": None,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
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
            "input_tokens": 0,
            "output_tokens": 0,
        }
    )

    return cast(dict[str, Any], result)
