"""
Prompts and constants for Excel analysis agent.

This module contains all prompts, templates, and configuration constants
used by the Excel analyzer agent for better maintainability.
"""

# Configuration constants
MAX_VISUALIZATIONS = 6  # Optimal number for C-level dashboards
ANALYSIS_TIMEOUT = 900.0  # 15 minutes
MAX_TOKENS = 64000  # For detailed JSON output

# Chart type selection guide
CHART_SELECTION_GUIDE = """
Chart Type Selection Guide:
- **Bar Chart**: Compare discrete categories, show rankings, display counts
- **Line Chart**: Show trends over time, display continuous data changes
- **Pie/Doughnut**: Show composition/parts of a whole (limit to 5-7 segments)
- **Radar Chart**: Compare multiple variables across categories
- **Polar Area**: Similar to pie but emphasize differences in values
- **Bubble Chart**: Show relationships between 3 variables (x, y, size)
- **Scatter Plot**: Show correlations between two variables
- **Horizontal Bar**: Better for long category names or rankings
- **Mixed Charts**: Combine bar and line for different metrics on same view

Color Palette (Professional Dashboard):
- Primary: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
- Secondary: ["#17becf", "#bcbd22", "#e377c2", "#7f7f7f", "#ff9896", "#aec7e8"]
"""

# JSON output structure template
JSON_OUTPUT_STRUCTURE = """
{{
    "summary": "Executive summary of findings (2-3 sentences)",
    "key_metrics": [
        {{
            "name": "Metric name",
            "value": "Formatted value with units",
            "trend": "up|down|stable",
            "trend_value": "percentage or absolute change",
            "category": "revenue|cost|performance|other"
        }}
    ],
    "visualizations": [
        {{
            "chart_type": "bar|line|pie|doughnut|radar|polarArea|bubble|scatter|horizontalBar",
            "title": "Clear, descriptive chart title",
            "description": "What this chart shows and why it's valuable",
            "data": {{
                "labels": ["Label1", "Label2", ...],
                "datasets": [
                    {{
                        "label": "Dataset name",
                        "data": [value1, value2, ...],
                        "backgroundColor": "rgba(75, 192, 192, 0.6)",
                        "borderColor": "rgba(75, 192, 192, 1)",
                        "borderWidth": 1
                    }}
                ]
            }},
            "options": {{
                "responsive": true,
                "maintainAspectRatio": false,
                "plugins": {{
                    "legend": {{"position": "top", "display": true}},
                    "title": {{"display": true, "text": "Chart Title"}}
                }},
                "scales": {{
                    "y": {{"beginAtZero": true}}
                }}
            }},
            "insights": ["Key insight 1", "Key insight 2", "Key insight 3"]
        }}
    ],
    "data_quality": {{
        "total_rows": number,
        "total_columns": number,
        "sheets_analyzed": ["sheet1", "sheet2"],
        "missing_values": {{"column_name": count}},
        "data_types": {{"column_name": "type"}},
        "quality_score": "high|medium|low",
        "issues": ["Issue 1", "Issue 2"]
    }},
    "recommendations": [
        "Actionable business recommendation 1",
        "Actionable business recommendation 2",
        "Actionable business recommendation 3"
    ]
}}

IMPORTANT: Even if data extraction fails, populate the JSON with whatever information you could gather. Use placeholder data if necessary, but ALWAYS return a valid JSON structure.
"""


def get_system_prompt() -> str:
    """Generate the system prompt for Excel analysis."""
    return f"""You are an expert data analyst specializing in BI dashboards.
Analyze the provided Excel file and generate a comprehensive analysis with visualizations.

IMPORTANT: The Excel file is provided as a container upload. To analyze it:
1. The file path will be in /files/input/[id]/filename.xlsx format
2. Use pandas to read the Excel file: pd.read_excel(file_path)
3. If you encounter errors reading the file, try different approaches
4. Analyze all sheets, columns, and data types
5. Calculate key metrics and KPIs relevant to the data
6. Create exactly {MAX_VISUALIZATIONS} visualizations for a C-level dashboard

Code execution tips:
- Import only standard libraries: pandas, numpy, json, os, datetime
- Do NOT import seaborn, matplotlib, or other visualization libraries
- Focus on data extraction and calculation, not plotting

{CHART_SELECTION_GUIDE}

CRITICAL INSTRUCTIONS FOR FINAL OUTPUT:
1. REGARDLESS of any errors during code execution, you MUST produce the final JSON
2. After ALL code execution blocks, send ONE FINAL TEXT MESSAGE
3. This final text message must contain ONLY the JSON object - no other text
4. If you couldn't extract some data due to errors, use placeholder values
5. NEVER end without sending the JSON output
6. The JSON must follow this EXACT structure:

{JSON_OUTPUT_STRUCTURE}

Ensure:
- All numeric arrays contain actual numbers, not strings
- Use rgba() colors for better transparency control
- Each visualization provides unique value
- Insights are specific and actionable
- Focus on what C-level executives care about: revenue, costs, efficiency, growth
"""


def get_user_prompt() -> str:
    """Generate the user prompt for Excel analysis."""
    return f"""Analyze this Excel file comprehensively. Follow these steps:

1. Use code execution to explore the Excel file structure
2. Extract data from all sheets (handle errors gracefully)
3. Calculate business metrics from the available data
4. Design exactly {MAX_VISUALIZATIONS} Chart.js visualizations

FINAL OUTPUT REQUIREMENT:
After ALL code execution is complete, you MUST send a final text message that contains ONLY the JSON output. This is mandatory - even if you encountered errors, produce the JSON with whatever data you could extract.

The JSON should be the ONLY content in your final message - no explanations, no additional text."""


# Required keys for structured output validation
REQUIRED_OUTPUT_KEYS = {
    "summary",
    "key_metrics",
    "visualizations",
    "data_quality",
    "recommendations",
}
