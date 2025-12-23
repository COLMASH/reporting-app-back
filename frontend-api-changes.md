# Frontend API Changes - December 2025

## Latest Update: Asset Subtype Support

Enables "Asset Subtype Summary" table when viewing specific asset types.

### 1. New `group_by` Value for Flexible Aggregation

| Value | Description |
|-------|-------------|
| `asset_subtype` | Group by asset subtype |

**Usage:**
```bash
# Get subtypes for Private Equity
GET /portfolio/aggregations/flexible?asset_type=Private%20Equity&group_by=asset_subtype
```

### 2. New `asset_subtype` Filter Parameter

All portfolio endpoints now support filtering by `asset_subtype`:

- `GET /portfolio/assets`
- `GET /portfolio/aggregations/summary`
- `GET /portfolio/aggregations/by-asset-type`
- `GET /portfolio/aggregations/historical`
- `GET /portfolio/aggregations/flexible`

**Usage (click-to-filter from subtype table row):**
```bash
GET /portfolio/assets?asset_type=Private%20Equity&asset_subtype=Venture%20Capital
GET /portfolio/aggregations/summary?asset_type=Private%20Equity&asset_subtype=Buyout
```

---

## Geographic Focus Filter Parameter

All portfolio endpoints now support filtering by `geographic_focus`. This enables click-to-filter on the "Distribution by Geographic Focus" chart.

### New Query Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `geographic_focus` | `string` | Filter by geographic focus (e.g., "France", "USA", "Europe") |

### Affected Endpoints

- `GET /portfolio/assets`
- `GET /portfolio/aggregations/summary`
- `GET /portfolio/aggregations/by-asset-type`
- `GET /portfolio/aggregations/historical`
- `GET /portfolio/aggregations/flexible`

### Usage Example

```bash
# Filter all endpoints by geographic focus
GET /portfolio/aggregations/summary?geographic_focus=France
GET /portfolio/assets?geographic_focus=USA
GET /portfolio/aggregations/by-asset-type?geographic_focus=Europe
```

---

## Unrealized Gain/Loss in Asset Type Aggregation

The `/portfolio/aggregations/by-asset-type` endpoint now includes unrealized gain fields for the Asset Type Summary table.

### New Fields in AssetTypeGroup

| Field | Type | Description |
|-------|------|-------------|
| `unrealized_gain_usd` | `number` | Sum of unrealized gains for this asset type (USD) |
| `unrealized_gain_eur` | `number` | Sum of unrealized gains for this asset type (EUR) |

### Updated TypeScript Interface

```typescript
interface AssetTypeGroup {
  asset_type: string
  value_usd: number           // NAV
  value_eur: number
  percentage: number          // Allocation %
  count: number               // # Positions
  paid_in_capital_usd: number // Cost Basis
  paid_in_capital_eur: number
  unrealized_gain_usd: number // NEW - for Unrealized Gain/Loss column
  unrealized_gain_eur: number // NEW - for Unrealized Gain/Loss column
  unfunded_commitment_usd: number
  unfunded_commitment_eur: number
}
```

---

## Unrealized Gain/Loss in Portfolio Summary

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
  total_estimated_value_usd: number
  total_paid_in_capital_usd: number
  total_unfunded_commitment_usd: number
  total_unrealized_gain_usd: number      // NEW
  total_estimated_value_eur: number
  total_paid_in_capital_eur: number
  total_unfunded_commitment_eur: number
  total_unrealized_gain_eur: number      // NEW
  weighted_avg_return: number | null
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

---

## Query Parameter Renames (All Endpoints)

| Old Parameter | New Parameter | Description |
|---------------|---------------|-------------|
| `asset_group` | `managing_entity` | Filter by managing entity |
| `asset_group_strategy` | `asset_group` | Filter by asset group |
| *(new)* | `holding_company` | Filter by holding company |

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
