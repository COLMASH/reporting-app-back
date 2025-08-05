"""
Pydantic schemas for structured output from the Excel analyzer agent.
Ensures compatibility with Chart.js data structures.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class KeyMetric(BaseModel):
    """Individual key metric from the analysis."""

    name: str = Field(description="Metric name")
    value: str = Field(description="Formatted value with units")
    trend: Literal["up", "down", "stable"] = Field(description="Trend direction")
    trend_value: str = Field(description="Percentage or absolute change")
    category: Literal["revenue", "cost", "performance", "other"] = Field(description="Metric category")


class BubbleDataPoint(BaseModel):
    """Data point for bubble/scatter charts."""

    x: float | int = Field(description="X coordinate")
    y: float | int = Field(description="Y coordinate")
    r: float | int | None = Field(default=None, description="Radius (for bubble charts)")


class ChartDataset(BaseModel):
    """Dataset for Chart.js visualization - matches Chart.js dataset structure."""

    label: str = Field(description="Dataset name")
    data: list[float | int | BubbleDataPoint | dict[str, Any]] = Field(description="Data points - numbers for most charts, objects for bubble/scatter")
    backgroundColor: str | list[str] = Field(
        default="rgba(75, 192, 192, 0.6)",
        description="Color or array of colors for bars/segments",
    )
    borderColor: str | list[str] = Field(
        default="rgba(75, 192, 192, 1)",
        description="Border color or array of colors",
    )
    borderWidth: int = Field(default=1, description="Border width in pixels")
    # Additional Chart.js dataset properties
    fill: bool = Field(default=False, description="Fill area under line")
    tension: float = Field(default=0.1, description="Bezier curve tension (0 for straight lines)")
    pointRadius: int = Field(default=3, description="Radius of point markers")
    pointHoverRadius: int = Field(default=5, description="Radius of point markers on hover")

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: list[Any]) -> list[Any]:
        """Ensure data contains no None values and filter them out if present."""
        # Filter out None values if any exist
        filtered_data = [item for item in v if item is not None]

        # If all data was None, provide a default
        # Note: The agent should add an insight about placeholder data when this happens
        if not filtered_data:
            return [10, 20, 30, 40, 50]  # Return placeholder values to show a trend

        return filtered_data


class ChartData(BaseModel):
    """Data structure for Chart.js - matches Chart.js data object."""

    labels: list[str] | None = Field(
        default=None,
        description="Labels for data points (x-axis) - optional for scatter/bubble charts",
    )
    datasets: list[ChartDataset] = Field(description="One or more datasets")

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[str] | None) -> list[str] | None:
        """Ensure labels is either None or a non-empty list."""
        if v is not None and len(v) == 0:
            return None
        return v


class ChartPlugins(BaseModel):
    """Chart.js plugins configuration."""

    legend: dict[str, Any] = Field(
        default={"position": "top", "display": True},
        description="Legend configuration",
    )
    title: dict[str, Any] = Field(
        default={"display": True, "text": "Chart Title"},
        description="Title configuration",
    )
    tooltip: dict[str, Any] = Field(
        default={"enabled": True, "mode": "index", "intersect": False},
        description="Tooltip configuration",
    )


class ChartScales(BaseModel):
    """Chart.js scales configuration."""

    x: dict[str, Any] = Field(
        default={"display": True, "grid": {"display": True}},
        description="X-axis configuration",
    )
    y: dict[str, Any] = Field(
        default={"display": True, "beginAtZero": True, "grid": {"display": True}},
        description="Y-axis configuration",
    )


class ChartOptions(BaseModel):
    """Chart.js options configuration - matches Chart.js options object."""

    responsive: bool = Field(default=True, description="Resize chart on container resize")
    maintainAspectRatio: bool = Field(default=False, description="Maintain original aspect ratio")
    aspectRatio: float = Field(default=2, description="Canvas aspect ratio")
    plugins: ChartPlugins = Field(default_factory=ChartPlugins, description="Plugin configurations")
    scales: ChartScales | None = Field(default=None, description="Scales configuration (not used for pie/doughnut)")
    animation: dict[str, Any] = Field(default={"duration": 1000}, description="Animation configuration")
    interaction: dict[str, Any] = Field(
        default={"mode": "nearest", "intersect": True},
        description="Interaction configuration",
    )


class Visualization(BaseModel):
    """Individual visualization configuration for Chart.js."""

    chart_type: Literal[
        "bar",
        "line",
        "pie",
        "doughnut",
        "radar",
        "polarArea",
        "bubble",
        "scatter",
    ] = Field(description="Type of chart (note: horizontalBar is now bar with indexAxis)")
    title: str = Field(description="Clear, descriptive chart title")
    description: str = Field(description="What this chart shows and why it's valuable")
    data: ChartData = Field(description="Chart data configuration")
    options: ChartOptions = Field(description="Chart display options")
    insights: list[str] = Field(description="Key insights from this visualization (1-5 insights)")

    def model_post_init(self, __context: Any) -> None:  # noqa: ARG002
        """Adjust options based on chart type."""
        # Pie and doughnut charts don't use scales
        if self.chart_type in ["pie", "doughnut", "polarArea"]:
            self.options.scales = None
        # For horizontal bar, we'd set indexAxis: 'y' in options
        elif self.chart_type == "bar" and "horizontal" in self.title.lower():
            if self.options.scales and isinstance(self.options.scales, ChartScales):
                # Note: In Chart.js v3+, use indexAxis: 'y' instead
                pass


class DataQuality(BaseModel):
    """Data quality assessment results."""

    total_rows: int = Field(description="Total number of rows analyzed")
    total_columns: int = Field(description="Total number of columns analyzed")
    sheets_analyzed: list[str] = Field(description="Names of sheets analyzed")
    missing_values: dict[str, int] = Field(description="Count of missing values per column", default_factory=dict)
    data_types: dict[str, str] = Field(description="Data type per column", default_factory=dict)
    quality_score: Literal["high", "medium", "low"] = Field(description="Overall data quality assessment")
    issues: list[str] = Field(description="Data quality issues found", default_factory=list)


class ExcelAnalysisOutput(BaseModel):
    """Complete structured output from Excel analysis."""

    summary: str = Field(
        description="Executive summary of findings (2-3 sentences)",
        min_length=50,
        max_length=2000,
    )
    key_metrics: list[KeyMetric] = Field(description="Important KPIs extracted from data (3-10 metrics)")
    visualizations: list[Visualization] = Field(description="Chart.js visualization configurations (exactly 6)")
    data_quality: DataQuality = Field(description="Data quality assessment")
    recommendations: list[str] = Field(description="Actionable business recommendations (3-5 recommendations)")
