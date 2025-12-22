# Frontend API Changes - December 2025

## Latest Update: Unrealized Gain/Loss in Summary

The `/portfolio/aggregations/summary` endpoint now includes unrealized gain totals for the KPI cards.

### New Fields in PortfolioSummaryResponse

| Field | Type | Description |
|-------|------|-------------|
| `total_unrealized_gain_usd` | `number` | Sum of unrealized gains across all assets (USD) |
| `total_unrealized_gain_eur` | `number` | Sum of unrealized gains across all assets (EUR) |

### Updated TypeScript Interface

```typescript
interface PortfolioSummaryResponse {
  report_date: string | null
  total_assets: number
  total_estimated_value_usd: number      // NAV
  total_paid_in_capital_usd: number      // Cost Basis
  total_unfunded_commitment_usd: number
  total_unrealized_gain_usd: number      // NEW - for Unrealized Gain/Loss card
  total_estimated_value_eur: number
  total_paid_in_capital_eur: number
  total_unfunded_commitment_eur: number
  total_unrealized_gain_eur: number      // NEW - for Unrealized Gain/Loss card
  weighted_avg_return: number | null
}
```

### Example Response

```json
{
  "report_date": "2025-12-09",
  "total_assets": 110,
  "total_estimated_value_usd": 123456789.00,
  "total_paid_in_capital_usd": 100000000.00,
  "total_unfunded_commitment_usd": 5000000.00,
  "total_unrealized_gain_usd": 23456789.00,
  "total_estimated_value_eur": 113456789.00,
  "total_paid_in_capital_eur": 92000000.00,
  "total_unfunded_commitment_eur": 4600000.00,
  "total_unrealized_gain_eur": 21456789.00,
  "weighted_avg_return": 0.15
}
```

---

## Historical NAV Endpoint - Dynamic group_by

The `/portfolio/aggregations/historical` endpoint now supports dynamic grouping.

### Parameter Change

| Old Parameter | New Parameter | Description |
|---------------|---------------|-------------|
| `group_by_entity` (bool) | `group_by` (string) | Field to group series by |

### Valid `group_by` Values

- `holding_company` - Group by parent holding company
- `ownership_holding_entity` - Group by ownership entity
- *omit parameter* - Single "Total" series

### Example Requests

```bash
# Group by holding company
GET /portfolio/aggregations/historical?group_by=holding_company

# Group by ownership entity
GET /portfolio/aggregations/historical?group_by=ownership_holding_entity

# Single total series
GET /portfolio/aggregations/historical
```

---

## Query Parameter Renames (All Endpoints)

| Old Parameter | New Parameter | Description |
|---------------|---------------|-------------|
| `asset_group` | `managing_entity` | Filter by managing entity |
| `asset_group_strategy` | `asset_group` | Filter by asset group |
| *(new)* | `holding_company` | Filter by holding company |

### Affected Endpoints

- `GET /portfolio/assets`
- `GET /portfolio/aggregations/summary`
- `GET /portfolio/aggregations/by-entity`
- `GET /portfolio/aggregations/by-asset-type`
- `GET /portfolio/aggregations/historical`
- `GET /portfolio/aggregations/flexible`

---

## New Field in FilterOptionsResponse

```typescript
interface FilterOptionsResponse {
  entities: string[]
  holding_companies: string[]  // NEW - for sidebar navigation
  asset_types: string[]
  report_dates: string[]
}
```
