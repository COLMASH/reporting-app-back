# Portfolio API Documentation

> **Version**: 1.0
> **Base URL**: `/api/v1/portfolio`
> **Authentication**: Required (JWT Bearer Token)

## Overview

The Portfolio API provides endpoints for displaying portfolio data in a dashboard frontend. It supports:

- **Filtering**: By entity, asset type, report date
- **Pagination**: Configurable page size (max 100)
- **Sorting**: Multiple sortable columns
- **Aggregations**: Pre-calculated summaries for charts
- **Multi-currency**: Values in USD and EUR

---

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portfolio/filters` | GET | Dropdown options for filters |
| `/portfolio/assets` | GET | Paginated asset list |
| `/portfolio/assets/{id}` | GET | Single asset detail |
| `/portfolio/aggregations/summary` | GET | Portfolio KPIs |
| `/portfolio/aggregations/by-entity` | GET | Distribution by owner |
| `/portfolio/aggregations/by-asset-type` | GET | Distribution by type |
| `/portfolio/aggregations/flexible` | GET | Dynamic grouping |
| `/portfolio/aggregations/historical` | GET | NAV time series |

---

## Authentication

All endpoints require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

---

## Endpoints

### 1. Get Filter Options

Returns distinct values for populating filter dropdowns.

```http
GET /api/v1/portfolio/filters
```

#### Response

```json
{
  "entities": ["ILV", "Isis Invest", "Pivert"],
  "asset_types": ["Bonds", "Equities", "Real Estate", "Structured Notes"],
  "report_dates": ["2024-03-31", "2024-02-29", "2024-01-31"]
}
```

#### Frontend Usage

- **Sidebar**: Use `entities` for owner filter
- **Navbar tabs**: Use `asset_types` for category tabs
- **Date picker**: Use `report_dates` for available dates

---

### 2. List Assets

Returns paginated list of assets with all columns.

```http
GET /api/v1/portfolio/assets
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity` | string | null | Filter by owner (e.g., "ILV") |
| `asset_type` | string | null | Filter by type (e.g., "Equities") |
| `report_date` | date | latest | Filter by date (YYYY-MM-DD) |
| `search` | string | null | Search in asset_name (case-insensitive) |
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Results per page (max: 100) |
| `sort_by` | string | "asset_name" | Column to sort by |
| `sort_order` | string | "asc" | Sort direction: "asc" or "desc" |
| `include_extension` | bool | false | Include structured_note/real_estate data |

#### Allowed Sort Columns

```
asset_name, ownership_holding_entity, asset_type, asset_group,
denomination_currency, report_date, initial_investment_date,
estimated_asset_value_usd, estimated_asset_value_eur,
paid_in_capital_usd, unfunded_commitment_usd, total_asset_return_usd,
created_at, display_id
```

#### Response

```json
{
  "assets": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "display_id": 1,
      "ownership_holding_entity": "ILV",
      "asset_group": "Various",
      "asset_group_strategy": "Growth",
      "asset_type": "Equities",
      "asset_subtype": "Public Equity",
      "asset_subtype_2": null,
      "asset_name": "Apple Inc.",
      "asset_identifier": "AAPL",
      "asset_status": "Active in portfolio",
      "geographic_focus": "USA",
      "broker_asset_manager": "Goldman Sachs",
      "denomination_currency": "USD",
      "report_date": "2024-03-31",
      "initial_investment_date": "2020-01-15",
      "number_of_shares": 1000.0,
      "avg_purchase_price_base_currency": 150.00,
      "current_share_price": 175.50,
      "usd_eur_inception": 0.89,
      "usd_eur_current": 0.92,
      "usd_cad_current": 1.36,
      "usd_chf_current": 0.88,
      "usd_hkd_current": 7.82,
      "total_investment_commitment_base_currency": 150000.00,
      "paid_in_capital_base_currency": 150000.00,
      "asset_level_financing_base_currency": 0.00,
      "unfunded_commitment_base_currency": 0.00,
      "estimated_asset_value_base_currency": 175500.00,
      "total_asset_return_base_currency": 0.17,
      "total_investment_commitment_usd": 150000.00,
      "paid_in_capital_usd": 150000.00,
      "unfunded_commitment_usd": 0.00,
      "estimated_asset_value_usd": 175500.00,
      "total_asset_return_usd": 0.17,
      "total_investment_commitment_eur": 138000.00,
      "paid_in_capital_eur": 138000.00,
      "unfunded_commitment_eur": 0.00,
      "estimated_asset_value_eur": 161460.00,
      "total_asset_return_eur": 0.17,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-03-31T12:00:00",
      "structured_note": null,
      "real_estate": null
    }
  ],
  "total": 118,
  "page": 1,
  "page_size": 20,
  "total_pages": 6
}
```

#### Example Requests

```javascript
// Basic list
GET /api/v1/portfolio/assets

// Filtered by entity and type
GET /api/v1/portfolio/assets?entity=ILV&asset_type=Equities

// Search with pagination
GET /api/v1/portfolio/assets?search=apple&page=1&page_size=10

// Sorted by value descending
GET /api/v1/portfolio/assets?sort_by=estimated_asset_value_usd&sort_order=desc

// With extension data (for structured notes/real estate)
GET /api/v1/portfolio/assets?asset_type=Structured%20Notes&include_extension=true
```

---

### 3. Get Asset Detail

Returns a single asset with all data including extensions.

```http
GET /api/v1/portfolio/assets/{asset_id}
```

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `asset_id` | UUID | Asset unique identifier |

#### Response

Same structure as a single asset in list response, always includes extension data.

#### Extension Data Examples

**Structured Note** (when `asset_type = "Structured Notes"`):

```json
{
  "structured_note": {
    "annual_coupon": 5.5,
    "coupon_payment_frequency": "Quarterly",
    "next_coupon_review_date": "2024-06-30",
    "next_principal_review_date": "2025-01-15",
    "final_due_date": "2027-01-15",
    "redemption_type": "AUTOCALL",
    "underlying_index_name": "S&P 500",
    "underlying_index_code": "SPX",
    "strike_level": 4500.00,
    "underlying_index_level": 5200.00,
    "performance_vs_strike": 0.1556,
    "effective_strike_percentage": 100.0,
    "note_leverage": "1x",
    "capital_protection": 90.0,
    "capital_protection_barrier": 4050.00,
    "coupon_protection_barrier_pct": 70.0,
    "coupon_protection_barrier_value": 3150.00
  }
}
```

**Real Estate** (when `asset_type = "Real Estate"`):

```json
{
  "real_estate": {
    "cost_original_asset": 5000000.00,
    "estimated_capex_budget": 1500000.00,
    "pivert_development_fees": 300000.00,
    "estimated_total_cost": 6800000.00,
    "capex_invested": 800000.00,
    "total_investment_to_date": 6100000.00,
    "equity_investment_to_date": 4000000.00,
    "pending_equity_investment": 700000.00,
    "estimated_capital_gain": 1200000.00
  }
}
```

---

### 4. Get Portfolio Summary

Returns aggregated KPIs for the portfolio.

```http
GET /api/v1/portfolio/aggregations/summary
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity` | string | null | Filter by owner (null = consolidated) |
| `asset_type` | string | null | Filter by asset type |
| `report_date` | date | latest | Report date |

#### Response

```json
{
  "report_date": "2024-03-31",
  "total_assets": 118,
  "total_estimated_value_usd": 52450000.00,
  "total_paid_in_capital_usd": 45000000.00,
  "total_unfunded_commitment_usd": 8500000.00,
  "total_estimated_value_eur": 48254000.00,
  "total_paid_in_capital_eur": 41400000.00,
  "total_unfunded_commitment_eur": 7820000.00,
  "weighted_avg_return": 0.165
}
```

#### Frontend Usage

Display as KPI cards at the top of the dashboard:
- Total Assets: `total_assets`
- Portfolio Value: `total_estimated_value_usd` or `total_estimated_value_eur`
- Paid In Capital: `total_paid_in_capital_usd` or `total_paid_in_capital_eur`
- Unfunded: `total_unfunded_commitment_usd` or `total_unfunded_commitment_eur`
- Avg Return: `weighted_avg_return` (format as percentage)

Use currency toggle to switch between USD and EUR values.

---

### 5. Get Aggregation by Entity

Returns distribution grouped by ownership entity.

```http
GET /api/v1/portfolio/aggregations/by-entity
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `asset_type` | string | null | Pre-filter by asset type |
| `report_date` | date | latest | Report date |

#### Response

```json
{
  "report_date": "2024-03-31",
  "total_value_usd": 52450000.00,
  "total_value_eur": 48254000.00,
  "groups": [
    {
      "name": "ILV",
      "value_usd": 25000000.00,
      "value_eur": 23000000.00,
      "percentage": 47.66,
      "count": 45
    },
    {
      "name": "Isis Invest",
      "value_usd": 18000000.00,
      "value_eur": 16560000.00,
      "percentage": 34.32,
      "count": 42
    },
    {
      "name": "Pivert",
      "value_usd": 9450000.00,
      "value_eur": 8694000.00,
      "percentage": 18.02,
      "count": 31
    }
  ]
}
```

#### Frontend Usage

- **Donut/Pie Chart**: `name` as label, `percentage` or `value_usd`/`value_eur` as value
- **Legend**: Show all groups with their percentages
- **Currency Toggle**: Use `value_usd` or `value_eur` based on user preference

---

### 6. Get Aggregation by Asset Type

Returns distribution grouped by asset type with additional financial metrics.

```http
GET /api/v1/portfolio/aggregations/by-asset-type
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity` | string | null | Pre-filter by owner |
| `report_date` | date | latest | Report date |

#### Response

```json
{
  "report_date": "2024-03-31",
  "total_value_usd": 52450000.00,
  "total_value_eur": 48254000.00,
  "groups": [
    {
      "asset_type": "Equities",
      "value_usd": 22000000.00,
      "value_eur": 20240000.00,
      "percentage": 41.95,
      "count": 35,
      "paid_in_capital_usd": 18000000.00,
      "paid_in_capital_eur": 16560000.00,
      "unfunded_commitment_usd": 2000000.00,
      "unfunded_commitment_eur": 1840000.00
    },
    {
      "asset_type": "Bonds",
      "value_usd": 15000000.00,
      "value_eur": 13800000.00,
      "percentage": 28.60,
      "count": 28,
      "paid_in_capital_usd": 14500000.00,
      "paid_in_capital_eur": 13340000.00,
      "unfunded_commitment_usd": 500000.00,
      "unfunded_commitment_eur": 460000.00
    },
    {
      "asset_type": "Real Estate",
      "value_usd": 10000000.00,
      "value_eur": 9200000.00,
      "percentage": 19.07,
      "count": 15,
      "paid_in_capital_usd": 8000000.00,
      "paid_in_capital_eur": 7360000.00,
      "unfunded_commitment_usd": 4000000.00,
      "unfunded_commitment_eur": 3680000.00
    },
    {
      "asset_type": "Structured Notes",
      "value_usd": 5450000.00,
      "value_eur": 5014000.00,
      "percentage": 10.39,
      "count": 40,
      "paid_in_capital_usd": 4500000.00,
      "paid_in_capital_eur": 4140000.00,
      "unfunded_commitment_usd": 2000000.00,
      "unfunded_commitment_eur": 1840000.00
    }
  ]
}
```

#### Frontend Usage

- **Donut/Pie Chart**: `asset_type` as label, `percentage` as value
- **Summary Table**: Show all columns for detailed breakdown
- **Currency Toggle**: Use `_usd` or `_eur` suffixed fields based on user preference

---

### 7. Get Flexible Aggregation

Dynamic aggregation by any dimension - supports all chart types.

```http
GET /api/v1/portfolio/aggregations/flexible
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `group_by` | enum | **Yes** | Field to group by (see below) |
| `entity` | string | No | Pre-filter by owner |
| `asset_type` | string | No | Pre-filter by type |
| `report_date` | date | No | Report date (default: latest) |

#### Valid `group_by` Values

| Value | Description | Example Labels |
|-------|-------------|----------------|
| `ownership_holding_entity` | By owner | ILV, Isis Invest, Pivert |
| `asset_type` | By type | Equities, Bonds, Real Estate |
| `asset_group` | By group | Various, StructuredNotes |
| `asset_group_strategy` | By strategy | Growth, Income, Value |
| `geographic_focus` | By geography | USA, Europe, Asia |
| `denomination_currency` | By currency | USD, EUR, CHF, CAD |
| `asset_status` | By status | Active in portfolio, Sold |
| `broker_asset_manager` | By manager | Goldman Sachs, UBS, JP Morgan |

#### Response

```json
{
  "report_date": "2024-03-31",
  "group_by": "geographic_focus",
  "total_value_usd": 52450000.00,
  "total_value_eur": 48254000.00,
  "total_count": 118,
  "groups": [
    {
      "label": "USA",
      "value_usd": 28000000.00,
      "value_eur": 25760000.00,
      "percentage": 53.38,
      "count": 55,
      "paid_in_capital_usd": 24000000.00,
      "unfunded_commitment_usd": 3000000.00,
      "avg_return": 0.18
    },
    {
      "label": "Europe",
      "value_usd": 18000000.00,
      "value_eur": 16560000.00,
      "percentage": 34.32,
      "count": 42,
      "paid_in_capital_usd": 15000000.00,
      "unfunded_commitment_usd": 4000000.00,
      "avg_return": 0.12
    },
    {
      "label": "Asia",
      "value_usd": 6450000.00,
      "value_eur": 5934000.00,
      "percentage": 12.30,
      "count": 21,
      "paid_in_capital_usd": 6000000.00,
      "unfunded_commitment_usd": 1500000.00,
      "avg_return": 0.22
    }
  ]
}
```

#### Chart Type Mapping

| Chart Type | Use Fields |
|------------|------------|
| **Donut/Pie** | `label` + `percentage` |
| **Bar Chart** | `label` + `value_usd` |
| **Treemap** | `label` + `value_usd` |
| **Radar/Spider** | `label` + `percentage` |
| **Bubble Chart** | `label` (name) + `value_usd` (x-axis) + `count` (bubble size) |

#### Example Requests

```javascript
// By geography
GET /api/v1/portfolio/aggregations/flexible?group_by=geographic_focus

// By currency for specific entity
GET /api/v1/portfolio/aggregations/flexible?group_by=denomination_currency&entity=ILV

// By manager for equities only
GET /api/v1/portfolio/aggregations/flexible?group_by=broker_asset_manager&asset_type=Equities
```

---

### 8. Get Historical NAV

Returns time series data for historical charts.

```http
GET /api/v1/portfolio/aggregations/historical
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity` | string | null | Filter by owner (ignored if group_by_entity=true) |
| `asset_type` | string | null | Filter by asset type |
| `start_date` | date | null | Start of date range |
| `end_date` | date | null | End of date range |
| `group_by_entity` | bool | true | Separate series per entity |

#### Response (group_by_entity=true)

```json
{
  "series": [
    {
      "name": "ILV",
      "data": [
        { "date": "2024-01-31", "value_usd": 23000000.00, "value_eur": 21160000.00 },
        { "date": "2024-02-29", "value_usd": 24200000.00, "value_eur": 22264000.00 },
        { "date": "2024-03-31", "value_usd": 25000000.00, "value_eur": 23000000.00 }
      ]
    },
    {
      "name": "Isis Invest",
      "data": [
        { "date": "2024-01-31", "value_usd": 16500000.00, "value_eur": 15180000.00 },
        { "date": "2024-02-29", "value_usd": 17200000.00, "value_eur": 15824000.00 },
        { "date": "2024-03-31", "value_usd": 18000000.00, "value_eur": 16560000.00 }
      ]
    },
    {
      "name": "Pivert",
      "data": [
        { "date": "2024-01-31", "value_usd": 8800000.00, "value_eur": 8096000.00 },
        { "date": "2024-02-29", "value_usd": 9100000.00, "value_eur": 8372000.00 },
        { "date": "2024-03-31", "value_usd": 9450000.00, "value_eur": 8694000.00 }
      ]
    }
  ]
}
```

#### Response (group_by_entity=false)

```json
{
  "series": [
    {
      "name": "Total",
      "data": [
        { "date": "2024-01-31", "value_usd": 48300000.00, "value_eur": 44436000.00 },
        { "date": "2024-02-29", "value_usd": 50500000.00, "value_eur": 46460000.00 },
        { "date": "2024-03-31", "value_usd": 52450000.00, "value_eur": 48254000.00 }
      ]
    }
  ]
}
```

#### Frontend Usage

- **Stacked Bar Chart**: Use with `group_by_entity=true` for entity breakdown over time
- **Line Chart**: Use with `group_by_entity=false` for total portfolio evolution
- **Area Chart**: Use series data directly with your charting library
- **Currency Toggle**: Use `value_usd` or `value_eur` based on user preference

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found

```json
{
  "detail": "Asset {asset_id} not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["query", "group_by"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

---

## Frontend Integration Examples

### React Query Example

```typescript
import { useQuery } from '@tanstack/react-query';

// Fetch filters for dropdowns
const { data: filters } = useQuery({
  queryKey: ['portfolio', 'filters'],
  queryFn: () => fetch('/api/v1/portfolio/filters', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.json())
});

// Fetch assets with filters
const { data: assets } = useQuery({
  queryKey: ['portfolio', 'assets', { entity, assetType, page }],
  queryFn: () => fetch(
    `/api/v1/portfolio/assets?entity=${entity}&asset_type=${assetType}&page=${page}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  ).then(r => r.json())
});

// Fetch aggregation for chart
const { data: chartData } = useQuery({
  queryKey: ['portfolio', 'aggregation', 'by-entity'],
  queryFn: () => fetch('/api/v1/portfolio/aggregations/by-entity', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.json())
});
```

### Recharts Donut Example

```tsx
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

function EntityDonut({ data }) {
  return (
    <PieChart width={400} height={400}>
      <Pie
        data={data.groups}
        dataKey="value_usd"
        nameKey="name"
        cx="50%"
        cy="50%"
        innerRadius={60}
        outerRadius={120}
        label={({ percentage }) => `${percentage}%`}
      >
        {data.groups.map((entry, index) => (
          <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
      <Legend />
    </PieChart>
  );
}
```

---

## TypeScript Types

```typescript
// Filter Options
interface FilterOptions {
  entities: string[];
  asset_types: string[];
  report_dates: string[];
}

// Asset Response
interface Asset {
  id: string;
  display_id: number | null;
  ownership_holding_entity: string;
  asset_group: string;
  asset_type: string;
  asset_name: string;
  denomination_currency: string;
  report_date: string | null;
  estimated_asset_value_usd: number | null;
  estimated_asset_value_eur: number | null;
  // ... (42+ fields total)
  structured_note: StructuredNote | null;
  real_estate: RealEstate | null;
}

// Paginated Response
interface AssetListResponse {
  assets: Asset[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Portfolio Summary
interface PortfolioSummary {
  report_date: string | null;
  total_assets: number;
  total_estimated_value_usd: number;
  total_paid_in_capital_usd: number;
  total_unfunded_commitment_usd: number;
  total_estimated_value_eur: number;
  total_paid_in_capital_eur: number;
  total_unfunded_commitment_eur: number;
  weighted_avg_return: number | null;
}

// Entity Aggregation Group
interface AggregationGroup {
  name: string;
  value_usd: number;
  value_eur: number;
  percentage: number;
  count: number;
}

// Entity Aggregation Response
interface EntityAggregationResponse {
  report_date: string | null;
  total_value_usd: number;
  total_value_eur: number;
  groups: AggregationGroup[];
}

// Asset Type Aggregation Group
interface AssetTypeGroup {
  asset_type: string;
  value_usd: number;
  value_eur: number;
  percentage: number;
  count: number;
  paid_in_capital_usd: number;
  paid_in_capital_eur: number;
  unfunded_commitment_usd: number;
  unfunded_commitment_eur: number;
}

// Asset Type Aggregation Response
interface AssetTypeAggregationResponse {
  report_date: string | null;
  total_value_usd: number;
  total_value_eur: number;
  groups: AssetTypeGroup[];
}

// Flexible Aggregation Group
interface FlexibleAggregationGroup {
  label: string;
  value_usd: number;
  value_eur: number;
  percentage: number;
  count: number;
  paid_in_capital_usd: number;
  unfunded_commitment_usd: number;
  avg_return: number | null;
}

// Historical NAV
interface NavDataPoint {
  date: string;
  value_usd: number;
  value_eur: number;
}

interface NavSeries {
  name: string;
  data: NavDataPoint[];
}
```

---

## Notes

1. **Default Report Date**: If `report_date` is not specified, endpoints return data for the most recent date available.

2. **Currency**: All monetary values are available in both USD and EUR. The primary currency is USD.

3. **Pagination**: Maximum page size is 100 items. Use `total_pages` to implement pagination controls.

4. **Null Handling**: Some fields may be `null`. Always handle null values in your frontend code.

5. **Rate Limiting**: API is rate limited to 100 requests per minute per user.
