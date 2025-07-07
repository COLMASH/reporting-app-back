"""
Excel file analyzer agent using LangGraph.
"""

import io
from typing import Any

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.storage import get_storage_client
from src.modules.reporting.agents.base import AgentState, BaseAgent

settings = get_settings()


class ExcelAnalyzerAgent(BaseAgent):
    """Agent for analyzing Excel files and generating insights."""

    def __init__(self) -> None:
        super().__init__("excel_analyzer")
        self.storage = get_storage_client()
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4-turbo-preview",
            api_key=SecretStr(settings.openai_api_key) if settings.openai_api_key else None,
        )

    def _build_graph(self) -> StateGraph:
        """Build the Excel analysis state graph."""
        workflow = StateGraph(AgentState)

        # Define nodes
        workflow.add_node("load_excel", self._load_excel)
        workflow.add_node("analyze_structure", self._analyze_structure)
        workflow.add_node("detect_patterns", self._detect_patterns)
        workflow.add_node("generate_insights", self._generate_insights)
        workflow.add_node("recommend_charts", self._recommend_charts)

        # Define edges
        workflow.set_entry_point("load_excel")
        workflow.add_edge("load_excel", "analyze_structure")
        workflow.add_edge("analyze_structure", "detect_patterns")
        workflow.add_edge("detect_patterns", "generate_insights")
        workflow.add_edge("generate_insights", "recommend_charts")
        workflow.add_edge("recommend_charts", END)

        return workflow

    async def _load_excel(self, state: AgentState) -> AgentState:
        """Load Excel file from storage."""
        try:
            self.logger.info("Loading Excel file", file_path=state["file_path"])

            # Download file from storage
            file_content = await self.storage.download_file(state["file_path"])

            # Load into pandas
            excel_file = pd.ExcelFile(io.BytesIO(file_content))

            # Get all sheets
            sheets_data = {}
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheets_data[sheet_name] = df

            state["file_data"] = sheets_data
            state["metadata"]["sheet_names"] = excel_file.sheet_names

            self.logger.info(
                "Excel file loaded",
                sheets_count=len(excel_file.sheet_names),
                first_sheet_rows=len(sheets_data[excel_file.sheet_names[0]]),
            )

            return state

        except Exception as e:
            self.logger.error("Failed to load Excel file", error=str(e))
            state["error"] = f"Failed to load Excel file: {str(e)}"
            return state

    async def _analyze_structure(self, state: AgentState) -> AgentState:
        """Analyze the structure of the Excel data."""
        if state.get("error"):
            return state

        try:
            sheets_data = state["file_data"]
            structure_info = {}

            for sheet_name, df in sheets_data.items():
                structure_info[sheet_name] = {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "null_counts": df.isnull().sum().to_dict(),
                    "numeric_columns": df.select_dtypes(include=["number"]).columns.tolist(),
                    "date_columns": df.select_dtypes(include=["datetime"]).columns.tolist(),
                    "text_columns": df.select_dtypes(include=["object"]).columns.tolist(),
                }

            state["metadata"]["structure"] = structure_info

            # Add structure analysis as a message
            structure_msg = HumanMessage(content=f"Excel structure analysis:\n{structure_info}")
            state["messages"].append(structure_msg)

            return state

        except Exception as e:
            self.logger.error("Failed to analyze structure", error=str(e))
            state["error"] = f"Failed to analyze structure: {str(e)}"
            return state

    async def _detect_patterns(self, state: AgentState) -> AgentState:
        """Detect patterns in the data."""
        if state.get("error"):
            return state

        try:
            sheets_data = state["file_data"]
            patterns = {}

            for sheet_name, df in sheets_data.items():
                sheet_patterns = {
                    "time_series": self._detect_time_series(df),
                    "categorical_distribution": self._analyze_categorical(df),
                    "numeric_summary": self._summarize_numeric(df),
                    "correlations": self._find_correlations(df),
                }
                patterns[sheet_name] = sheet_patterns

            state["metadata"]["patterns"] = patterns

            # Add pattern analysis as a message
            pattern_msg = HumanMessage(content=f"Data patterns detected:\n{patterns}")
            state["messages"].append(pattern_msg)

            return state

        except Exception as e:
            self.logger.error("Failed to detect patterns", error=str(e))
            state["error"] = f"Failed to detect patterns: {str(e)}"
            return state

    async def _generate_insights(self, state: AgentState) -> AgentState:
        """Generate insights using LLM."""
        if state.get("error"):
            return state

        try:
            # Prepare context for LLM
            structure = state["metadata"].get("structure", {})
            patterns = state["metadata"].get("patterns", {})

            system_prompt = SystemMessage(
                content="""You are a financial data analyst expert. Analyze the provided Excel data
                structure and patterns to generate actionable insights. Focus on:
                1. Key trends and patterns
                2. Anomalies or outliers
                3. Relationships between variables
                4. Business implications
                5. Recommendations for further analysis

                Provide clear, concise insights that would be valuable for business decisions."""
            )

            analysis_prompt = HumanMessage(
                content=f"""Analyze this financial data:

                Structure: {structure}

                Patterns: {patterns}

                Generate 3-5 key insights from this data."""
            )

            # Get insights from LLM
            response = await self.llm.ainvoke([system_prompt, analysis_prompt])

            # Parse insights
            response_content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            insights = response_content.split("\n")

            # Add insights to results
            for i, insight in enumerate(insights):
                if insight.strip():
                    state["results"].append(
                        {
                            "type": "insight",
                            "title": f"Key Insight {i + 1}",
                            "content": insight.strip(),
                            "confidence": 0.85,  # Could be calculated based on data quality
                        }
                    )

            return state

        except Exception as e:
            self.logger.error("Failed to generate insights", error=str(e))
            state["error"] = f"Failed to generate insights: {str(e)}"
            return state

    async def _recommend_charts(self, state: AgentState) -> AgentState:
        """Recommend appropriate charts based on data analysis."""
        if state.get("error"):
            return state

        try:
            structure = state["metadata"].get("structure", {})
            patterns = state["metadata"].get("patterns", {})

            # Chart recommendation logic based on data types and patterns
            for sheet_name, sheet_info in structure.items():
                sheet_patterns = patterns.get(sheet_name, {})

                # Time series chart
                if sheet_patterns.get("time_series"):
                    state["results"].append(
                        self._create_time_series_chart(
                            sheet_name,
                            state["file_data"][sheet_name],
                            sheet_patterns["time_series"],
                        )
                    )

                # Bar chart for categorical data
                if sheet_info["text_columns"] and sheet_info["numeric_columns"]:
                    state["results"].append(
                        self._create_bar_chart(
                            sheet_name, state["file_data"][sheet_name], sheet_info
                        )
                    )

                # Pie chart for distribution
                if sheet_patterns.get("categorical_distribution"):
                    state["results"].append(
                        self._create_pie_chart(
                            sheet_name,
                            state["file_data"][sheet_name],
                            sheet_patterns["categorical_distribution"],
                        )
                    )

                # KPI metrics
                if sheet_info["numeric_columns"]:
                    state["results"].append(
                        self._create_kpi_metrics(
                            sheet_name,
                            state["file_data"][sheet_name],
                            sheet_patterns.get("numeric_summary", {}),
                        )
                    )

            return state

        except Exception as e:
            self.logger.error("Failed to recommend charts", error=str(e))
            state["error"] = f"Failed to recommend charts: {str(e)}"
            return state

    async def analyze(
        self, file_path: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Analyze an Excel file and return results."""
        initial_state = self._create_initial_state(file_path, parameters)
        final_state = await self.run(initial_state)

        if final_state.get("error"):
            raise Exception(final_state["error"])

        return final_state["results"]

    # Helper methods for pattern detection
    def _detect_time_series(self, df: pd.DataFrame) -> dict[str, Any] | None:
        """Detect if data contains time series."""
        date_columns = df.select_dtypes(include=["datetime"]).columns.tolist()
        if not date_columns:
            # Try to parse potential date columns
            for col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    date_columns.append(col)
                except Exception:
                    continue

        if date_columns:
            return {
                "date_column": date_columns[0],
                "frequency": "daily",  # Could be detected more intelligently
                "has_gaps": df[date_columns[0]].diff().nunique() > 1,
            }
        return None

    def _analyze_categorical(self, df: pd.DataFrame) -> dict[str, Any]:
        """Analyze categorical columns."""
        categorical_info = {}
        for col in df.select_dtypes(include=["object"]).columns:
            value_counts = df[col].value_counts()
            if len(value_counts) < 20:  # Only for reasonable number of categories
                categorical_info[col] = {
                    "unique_values": len(value_counts),
                    "top_values": value_counts.head(5).to_dict(),
                }
        return categorical_info

    def _summarize_numeric(self, df: pd.DataFrame) -> dict[str, Any]:
        """Summarize numeric columns."""
        numeric_summary = {}
        for col in df.select_dtypes(include=["number"]).columns:
            numeric_summary[col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
            }
        return numeric_summary

    def _find_correlations(self, df: pd.DataFrame) -> dict[str, Any]:
        """Find correlations between numeric columns."""
        numeric_df = df.select_dtypes(include=["number"])
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            high_corr = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    # Check for high correlation
                    if isinstance(corr_value, int | float) and abs(corr_value) > 0.7:
                        high_corr.append(
                            {
                                "col1": corr_matrix.columns[i],
                                "col2": corr_matrix.columns[j],
                                "correlation": float(corr_value),
                            }
                        )
            return {"high_correlations": high_corr}
        return {}

    # Chart creation methods
    def _create_time_series_chart(
        self, sheet_name: str, df: pd.DataFrame, time_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Create time series chart configuration."""
        date_col = time_info["date_column"]
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        if not numeric_cols:
            return {}

        # Use first numeric column for now
        value_col = numeric_cols[0]

        # Prepare data
        chart_df = df[[date_col, value_col]].copy()
        chart_df[date_col] = pd.to_datetime(chart_df[date_col])
        chart_df = chart_df.sort_values(date_col)

        return {
            "type": "chart",
            "chart_type": "line",
            "title": f"{value_col} Over Time",
            "description": f"Time series analysis of {value_col} from {sheet_name}",
            "data": {
                "labels": chart_df[date_col].dt.strftime("%Y-%m-%d").tolist(),
                "datasets": [
                    {
                        "label": value_col,
                        "data": chart_df[value_col].fillna(0).tolist(),
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                        "tension": 0.1,
                    }
                ],
            },
            "config": {
                "options": {
                    "responsive": True,
                    "plugins": {"title": {"display": True, "text": f"{value_col} Over Time"}},
                }
            },
        }

    def _create_bar_chart(
        self, sheet_name: str, df: pd.DataFrame, structure: dict[str, Any]
    ) -> dict[str, Any]:
        """Create bar chart configuration."""
        # Find suitable categorical and numeric columns
        text_cols = structure["text_columns"]
        numeric_cols = structure["numeric_columns"]

        if not text_cols or not numeric_cols:
            return {}

        cat_col = text_cols[0]
        num_col = numeric_cols[0]

        # Aggregate data
        chart_data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(10)

        return {
            "type": "chart",
            "chart_type": "bar",
            "title": f"{num_col} by {cat_col}",
            "description": f"Distribution of {num_col} across different {cat_col} categories",
            "data": {
                "labels": chart_data.index.tolist(),
                "datasets": [
                    {
                        "label": num_col,
                        "data": chart_data.values.tolist(),
                        "backgroundColor": "rgba(54, 162, 235, 0.8)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 1,
                    }
                ],
            },
            "config": {
                "options": {
                    "responsive": True,
                    "plugins": {"title": {"display": True, "text": f"{num_col} by {cat_col}"}},
                }
            },
        }

    def _create_pie_chart(
        self, sheet_name: str, df: pd.DataFrame, categorical_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Create pie chart configuration."""
        if not categorical_info:
            return {}

        # Use first categorical column with reasonable number of categories
        for col, info in categorical_info.items():
            if info["unique_values"] <= 10:
                top_values = info["top_values"]

                return {
                    "type": "chart",
                    "chart_type": "pie",
                    "title": f"Distribution of {col}",
                    "description": f"Breakdown of categories in {col}",
                    "data": {
                        "labels": list(top_values.keys()),
                        "datasets": [
                            {
                                "data": list(top_values.values()),
                                "backgroundColor": [
                                    "rgba(255, 99, 132, 0.8)",
                                    "rgba(54, 162, 235, 0.8)",
                                    "rgba(255, 205, 86, 0.8)",
                                    "rgba(75, 192, 192, 0.8)",
                                    "rgba(153, 102, 255, 0.8)",
                                ][: len(top_values)],
                            }
                        ],
                    },
                    "config": {
                        "options": {
                            "responsive": True,
                            "plugins": {
                                "title": {"display": True, "text": f"Distribution of {col}"}
                            },
                        }
                    },
                }

        return {}

    def _create_kpi_metrics(
        self, sheet_name: str, df: pd.DataFrame, numeric_summary: dict[str, Any]
    ) -> dict[str, Any]:
        """Create KPI metrics."""
        if not numeric_summary:
            return {}

        metrics = []
        for col, summary in list(numeric_summary.items())[:4]:  # Limit to 4 KPIs
            metrics.append(
                {
                    "label": col,
                    "value": summary["mean"],
                    "format": "number",
                    "change": None,  # Could calculate period-over-period change
                    "changeType": None,
                }
            )

        return {
            "type": "chart",
            "chart_type": "kpi",
            "title": "Key Metrics",
            "description": f"Summary metrics from {sheet_name}",
            "data": {"metrics": metrics},
        }
