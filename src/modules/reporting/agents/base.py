"""
Base agent class for analysis agents.
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, cast

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph

from src.core.logging import get_logger


class AgentState(TypedDict):
    """Base state for all agents."""

    messages: list[BaseMessage]
    file_path: str
    file_data: Any
    results: list[dict[str, Any]]
    error: str | None
    metadata: dict[str, Any]


class BaseAgent(ABC):
    """Abstract base class for analysis agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agents.{name}")
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the agent's state graph."""
        pass

    @abstractmethod
    async def analyze(
        self, file_path: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Analyze a file and return results.

        Args:
            file_path: Path to the file in storage
            parameters: Optional parameters for analysis

        Returns:
            List of result dictionaries
        """
        pass

    async def run(self, initial_state: AgentState) -> AgentState:
        """Run the agent with the given initial state."""
        try:
            self.logger.info(f"Starting {self.name} agent", file_path=initial_state["file_path"])

            # Compile and run the graph
            app = self.graph.compile()
            final_state = await app.ainvoke(initial_state)

            self.logger.info(
                f"{self.name} agent completed",
                results_count=len(final_state.get("results", [])),
            )

            return cast(AgentState, final_state)

        except Exception as e:
            self.logger.error(f"{self.name} agent failed", error=str(e))
            # Create error state manually to avoid TypedDict issues
            error_state = initial_state.copy()
            error_state["error"] = str(e)
            error_state["results"] = []
            return cast(AgentState, error_state)

    def _create_initial_state(
        self, file_path: str, parameters: dict[str, Any] | None = None
    ) -> AgentState:
        """Create initial state for the agent."""
        return {
            "messages": [],
            "file_path": file_path,
            "file_data": None,
            "results": [],
            "error": None,
            "metadata": parameters or {},
        }
