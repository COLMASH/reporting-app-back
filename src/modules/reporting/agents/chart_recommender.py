"""
Chart recommendation agent for suggesting appropriate visualizations.
"""

from typing import Any

from langgraph.graph import END, StateGraph

from src.modules.reporting.agents.base import AgentState, BaseAgent


class ChartRecommenderAgent(BaseAgent):
    """Agent for recommending appropriate chart types based on data characteristics."""

    def __init__(self) -> None:
        super().__init__("chart_recommender")

    def _build_graph(self) -> StateGraph:
        """Build the chart recommendation state graph."""
        workflow = StateGraph(AgentState)

        # Define nodes
        workflow.add_node("analyze_data_types", self._analyze_data_types)
        workflow.add_node("recommend_visualizations", self._recommend_visualizations)

        # Define edges
        workflow.set_entry_point("analyze_data_types")
        workflow.add_edge("analyze_data_types", "recommend_visualizations")
        workflow.add_edge("recommend_visualizations", END)

        return workflow

    async def _analyze_data_types(self, state: AgentState) -> AgentState:
        """Analyze data types to determine suitable visualizations."""
        try:
            # This would analyze the data structure passed in metadata
            data_info = state["metadata"].get("data_info", {})

            analysis = {
                "has_time_series": data_info.get("has_dates", False),
                "has_categories": len(data_info.get("categorical_columns", [])) > 0,
                "has_numeric": len(data_info.get("numeric_columns", [])) > 0,
                "row_count": data_info.get("row_count", 0),
                "is_comparison": data_info.get("is_comparison", False),
                "is_distribution": data_info.get("is_distribution", False),
                "is_relationship": data_info.get("is_relationship", False),
            }

            state["metadata"]["analysis"] = analysis
            return state

        except Exception as e:
            self.logger.error("Failed to analyze data types", error=str(e))
            state["error"] = f"Failed to analyze data types: {str(e)}"
            return state

    async def _recommend_visualizations(self, state: AgentState) -> AgentState:
        """Recommend appropriate visualizations based on analysis."""
        if state.get("error"):
            return state

        try:
            analysis = state["metadata"].get("analysis", {})
            recommendations = []

            # Time series data -> Line chart
            if analysis.get("has_time_series") and analysis.get("has_numeric"):
                recommendations.append(
                    {
                        "chart_type": "line",
                        "reason": "Time series data is best visualized with line charts",
                        "priority": 1,
                    }
                )

            # Categorical comparison -> Bar chart
            if analysis.get("has_categories") and analysis.get("has_numeric"):
                recommendations.append(
                    {
                        "chart_type": "bar",
                        "reason": "Categorical comparisons are effective with bar charts",
                        "priority": 2,
                    }
                )

            # Distribution -> Pie chart (for small categories)
            if analysis.get("is_distribution") and analysis.get("has_categories"):
                recommendations.append(
                    {
                        "chart_type": "pie",
                        "reason": "Distribution of categories can be shown with pie charts",
                        "priority": 3,
                    }
                )

            # Relationship between variables -> Scatter plot
            if analysis.get("is_relationship") and analysis.get("has_numeric"):
                recommendations.append(
                    {
                        "chart_type": "scatter",
                        "reason": "Relationships between variables are shown with scatter plots",
                        "priority": 4,
                    }
                )

            # Summary metrics -> KPI cards
            if analysis.get("has_numeric"):
                recommendations.append(
                    {
                        "chart_type": "kpi",
                        "reason": "Key metrics can be displayed as KPI cards",
                        "priority": 5,
                    }
                )

            state["results"] = recommendations
            return state

        except Exception as e:
            self.logger.error("Failed to recommend visualizations", error=str(e))
            state["error"] = f"Failed to recommend visualizations: {str(e)}"
            return state

    async def analyze(
        self, file_path: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Analyze data and recommend appropriate charts."""
        initial_state = self._create_initial_state(file_path, parameters)
        final_state = await self.run(initial_state)

        if final_state.get("error"):
            raise Exception(final_state["error"])

        return final_state["results"]
