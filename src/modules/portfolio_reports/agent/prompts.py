"""
Prompts for portfolio report generation agent.

Contains:
- SYSTEM_PROMPT: Fixed general portfolio analysis framework
- get_analysis_prompt: Builds dynamic prompt with portfolio data
- get_markdown_generation_prompt: Instructions for markdown report generation
"""

import json
from typing import Any

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are an expert portfolio analyst and investment advisor
specializing in family office and institutional portfolio management.

Your expertise includes:
- Asset allocation and diversification analysis
- Private equity and venture capital investments
- Real estate investment analysis
- Structured products and fixed income
- Multi-currency portfolio management
- Risk assessment and concentration analysis
- Performance attribution and benchmarking

Your task is to analyze portfolio data and generate professional, insightful
reports for C-level executives and investment committees.

Key principles:
1. Be precise with numbers - use appropriate formatting ($1.2M, 12.34%)
2. Identify both strengths and areas of concern
3. Provide actionable insights, not just observations
4. Consider tax efficiency and liquidity implications
5. Use professional financial terminology appropriately
6. Structure analysis logically with clear sections

When research data is provided, integrate market context into your analysis."""


# ============================================================
# REPORT SECTIONS
# ============================================================

REPORT_SECTIONS = [
    {
        "id": "executive_summary",
        "title": "Executive Summary",
        "description": "High-level overview of portfolio performance and key findings (2-3 paragraphs)",
    },
    {
        "id": "portfolio_overview",
        "title": "Portfolio Overview",
        "description": "Total AUM, asset count, and high-level composition",
    },
    {
        "id": "asset_class_analysis",
        "title": "Asset Class Analysis",
        "description": "Breakdown by asset_type and asset_subtype with performance metrics",
    },
    {
        "id": "geographic_distribution",
        "title": "Geographic Distribution",
        "description": "Analysis by geographic_focus",
    },
    {
        "id": "currency_exposure",
        "title": "Currency Exposure Analysis",
        "description": "Analysis of denomination currencies and FX impacts",
    },
    {
        "id": "performance_analysis",
        "title": "Performance Analysis",
        "description": "Returns, gains, and performance attribution",
    },
    {
        "id": "risk_assessment",
        "title": "Risk Assessment",
        "description": "Concentration risks, liquidity analysis, unfunded commitments",
    },
    {
        "id": "market_research",
        "title": "Market Research & Outlook",
        "description": "Current market conditions and outlook for assets (if research enabled)",
    },
    {
        "id": "historical_trends",
        "title": "Historical Trends",
        "description": "NAV evolution and allocation changes over time (if ALL_DATES scope)",
    },
    {
        "id": "recommendations",
        "title": "Recommendations",
        "description": "Actionable recommendations based on analysis",
    },
    {
        "id": "appendix",
        "title": "Appendix: Top Holdings",
        "description": "Summary table of largest holdings with key metrics",
    },
]


# ============================================================
# PROMPT BUILDERS
# ============================================================


def get_analysis_prompt(
    portfolio_data: dict[str, Any],
    user_prompt: str | None = None,
    research_data: dict[str, Any] | None = None,
) -> str:
    """
    Build the analysis prompt with portfolio data.

    Args:
        portfolio_data: Portfolio data from database
        user_prompt: Optional user instructions for focus
        research_data: Optional market research data

    Returns:
        Complete prompt string for analysis
    """
    prompt = f"""Analyze the following portfolio data comprehensively.

## PORTFOLIO DATA
```json
{json.dumps(portfolio_data, indent=2, default=str)}
```

"""

    if user_prompt:
        prompt += f"""
## USER REQUIREMENTS
{user_prompt}

Please ensure your analysis addresses these specific requirements.

"""

    if research_data:
        prompt += f"""
## MARKET RESEARCH DATA
```json
{json.dumps(research_data, indent=2, default=str)}
```

"""

    prompt += """
## ANALYSIS REQUIREMENTS

Please provide a thorough analysis covering:

1. **Portfolio Composition**
   - Total AUM in USD and EUR
   - Asset count by type and subtype
   - Entity and holding company breakdown

2. **Performance Metrics**
   - Total returns (realized and unrealized)
   - Performance by asset class
   - Top and bottom performers

3. **Risk Indicators**
   - Concentration analysis (single asset, entity, sector)
   - Liquidity assessment
   - Unfunded commitment exposure
   - Currency exposure

4. **Key Insights**
   - Notable trends or patterns
   - Areas of concern
   - Opportunities identified

5. **Recommendations**
   - Specific, actionable suggestions
   - Priority ranking

Provide detailed numerical analysis with supporting data."""

    return prompt


def get_markdown_generation_prompt() -> str:
    """
    Get the prompt for generating the final markdown report.

    Returns:
        Prompt string for markdown generation
    """
    sections_desc = "\n".join([f"- **{s['title']}**: {s['description']}" for s in REPORT_SECTIONS])

    return f"""You are a professional report writer specializing in investment reports.
Generate a comprehensive, well-structured markdown report based on the analysis provided.

## REPORT STRUCTURE

The report must include the following sections:
{sections_desc}

## FORMATTING REQUIREMENTS

1. Use proper markdown formatting:
   - H1 (#) for report title only
   - H2 (##) for main sections
   - H3 (###) for subsections
   - Tables for numerical data
   - Bold for key figures and emphasis
   - Bullet points for lists

2. Numerical formatting:
   - Currency: $1,234,567.89 or EUR 1,234,567.89
   - Percentages: 12.34%
   - Large numbers: Use M for millions, B for billions (e.g., $10.5M)

3. Tables format:
```markdown
| Asset Type | Value (USD) | % of Portfolio | Return |
|------------|-------------|----------------|--------|
| Equities   | $10.5M      | 35.2%          | 12.3%  |
```

4. Style guidelines:
   - Professional but accessible tone
   - Clear section transitions
   - Key findings highlighted
   - Actionable language for recommendations

## SPECIAL INSTRUCTIONS

- If market research data is available, integrate it into relevant sections
- If historical data is available (ALL_DATES scope), include the Historical Trends section
- Include the Appendix section with a summary table of top holdings
- Add horizontal rules (---) between major sections for visual separation
- Keep the Executive Summary concise (max 3 paragraphs)
- Omit sections that don't have relevant data (e.g., skip Market Research if no research was done)
"""
