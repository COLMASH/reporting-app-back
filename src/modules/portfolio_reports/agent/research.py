"""
Internet research functions for portfolio assets.

Uses Brave Search API to gather market data and news about portfolio assets.
"""

from typing import Any

import httpx

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Asset types that benefit from internet research
RESEARCHABLE_ASSET_TYPES = {
    "Equities",
    "Public Equities",
    "Fixed Income",
    "Bonds",
    "Cryptocurrency",
    "Crypto",
    "Commodities",
    "ETFs",
    "ETF",
    "Mutual Funds",
    "REITs",
}

# Maximum number of assets to research (to avoid excessive API calls)
MAX_ASSETS_TO_RESEARCH = 15

# Brave Search API endpoint
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


async def perform_asset_research(portfolio_data: dict[str, Any]) -> dict[str, Any]:
    """
    Perform internet research on portfolio assets using Brave Search.

    Args:
        portfolio_data: Portfolio data containing assets

    Returns:
        Dict mapping asset names to research results
    """
    settings = get_settings()
    api_key = settings.brave_api_key

    if not api_key:
        logger.warning("Brave API key not configured, skipping research")
        return {}

    # Get unique researchable assets
    assets_to_research = _get_researchable_assets(portfolio_data)

    if not assets_to_research:
        logger.info("No researchable assets found in portfolio")
        return {}

    logger.info(f"Researching {len(assets_to_research)} assets with Brave Search")

    results: dict[str, Any] = {}

    for asset in assets_to_research[:MAX_ASSETS_TO_RESEARCH]:
        try:
            asset_name = asset.get("asset_name", "Unknown")
            research = await _research_single_asset(asset, api_key)
            if research:
                results[asset_name] = research
        except Exception as e:
            logger.warning(
                "Research failed for asset",
                asset_name=asset.get("asset_name"),
                error=str(e),
            )

    logger.info(f"Completed research for {len(results)} assets")
    return results


def _get_researchable_assets(portfolio_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract assets that can be researched (public securities, crypto, etc.).

    Args:
        portfolio_data: Portfolio data containing assets

    Returns:
        List of unique researchable assets
    """
    assets: list[dict[str, Any]] = []

    # Get assets from top_assets
    top_assets = portfolio_data.get("top_assets", [])
    for asset in top_assets:
        asset_type = asset.get("asset_type", "")
        if asset_type in RESEARCHABLE_ASSET_TYPES:
            assets.append(asset)

    # Deduplicate by asset_identifier or asset_name
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for asset in assets:
        key = asset.get("asset_identifier") or asset.get("asset_name")
        if key and key not in seen:
            seen.add(key)
            unique.append(asset)

    # Sort by value to prioritize largest holdings
    unique.sort(key=lambda x: x.get("estimated_value_usd", 0), reverse=True)

    return unique


async def _research_single_asset(
    asset: dict[str, Any],
    api_key: str,
) -> dict[str, Any] | None:
    """
    Research a single asset using Brave Search.

    Args:
        asset: Asset data dict
        api_key: Brave Search API key

    Returns:
        Research results or None if failed
    """
    asset_name = asset.get("asset_name", "")
    asset_identifier = asset.get("asset_identifier", "")
    asset_type = asset.get("asset_type", "")

    # Build search query
    query = _build_search_query(asset_name, asset_identifier, asset_type)

    # Perform search
    search_results = await _search_brave(query, api_key)

    if not search_results:
        return None

    # Parse and structure results
    return {
        "asset_name": asset_name,
        "asset_type": asset_type,
        "query": query,
        "results": [
            {
                "title": r.get("title", ""),
                "description": r.get("description", ""),
                "url": r.get("url", ""),
            }
            for r in search_results[:5]  # Top 5 results
        ],
    }


def _build_search_query(
    asset_name: str,
    asset_identifier: str | None,
    asset_type: str,
) -> str:
    """
    Build a search query for an asset.

    Args:
        asset_name: Name of the asset
        asset_identifier: Optional identifier (ISIN, ticker, etc.)
        asset_type: Type of asset

    Returns:
        Search query string
    """
    # If we have an identifier (ISIN, ticker), use it for more precise results
    if asset_identifier:
        if asset_type in {"Cryptocurrency", "Crypto"}:
            return f"{asset_identifier} crypto price analysis market outlook"
        else:
            return f"{asset_identifier} stock analysis market outlook 2024"

    # Otherwise use asset name
    if asset_type in {"Cryptocurrency", "Crypto"}:
        return f"{asset_name} cryptocurrency price prediction market analysis"
    elif asset_type in {"ETFs", "ETF", "Mutual Funds"}:
        return f"{asset_name} ETF fund analysis performance outlook"
    elif asset_type in {"Commodities"}:
        return f"{asset_name} commodity price forecast market trends"
    elif asset_type in {"REITs"}:
        return f"{asset_name} REIT real estate investment analysis"
    else:
        return f"{asset_name} investment analysis market outlook 2024"


async def _search_brave(query: str, api_key: str, count: int = 5) -> list[dict[str, Any]]:
    """
    Search using Brave Search API.

    Args:
        query: Search query
        api_key: Brave API key
        count: Number of results to return

    Returns:
        List of search results
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                BRAVE_SEARCH_URL,
                params={
                    "q": query,
                    "count": count,
                    "safesearch": "moderate",
                },
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
            )

            if response.status_code == 200:
                data = response.json()
                results: list[dict[str, Any]] = data.get("web", {}).get("results", [])
                return results
            else:
                logger.error(
                    "Brave search failed",
                    status_code=response.status_code,
                    query=query,
                )
                return []

    except httpx.TimeoutException:
        logger.warning("Brave search timeout", query=query)
        return []
    except Exception as e:
        logger.error("Brave search error", error=str(e), query=query)
        return []
