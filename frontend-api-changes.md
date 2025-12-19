# Frontend API Changes - December 19, 2025

## Summary

The portfolio API has been updated with schema changes, renamed fields, new columns, and **renamed query parameters**. This document outlines all breaking changes and additions that require frontend updates.

---

## Breaking Changes - Query Parameters

**All portfolio endpoints** now use new query parameter names:

| Old Parameter | New Parameter | Description |
|---------------|---------------|-------------|
| `asset_group` | `managing_entity` | Filter by managing entity |
| `asset_group_strategy` | `asset_group` | Filter by asset group |
| *(new)* | `holding_company` | Filter by holding company |

**Affected endpoints:**
- `GET /portfolio/assets`
- `GET /portfolio/aggregations/summary`
- `GET /portfolio/aggregations/by-entity`
- `GET /portfolio/aggregations/by-asset-type`
- `GET /portfolio/aggregations/historical`
- `GET /portfolio/aggregations/flexible`

---

## Breaking Changes - Response Field Renames

### AssetResponse

| Old Field Name | New Field Name | Notes |
|----------------|----------------|-------|
| `asset_group` | `managing_entity` | Now represents the managing entity |
| `asset_group_strategy` | `asset_group` | Renamed for clarity |

### RealEstateResponse

All EUR-denominated fields have been renamed with `_eur` suffix for multi-currency clarity:

| Old Field Name | New Field Name |
|----------------|----------------|
| `cost_original_asset` | `cost_original_asset_eur` |
| `estimated_capex_budget` | `estimated_capex_budget_eur` |
| `pivert_development_fees` | `pivert_development_fees_eur` |
| `estimated_total_cost` | `estimated_total_cost_eur` |
| `capex_invested` | `capex_invested_eur` |
| `total_investment_to_date` | `total_investment_to_date_eur` |
| `equity_investment_to_date` | `equity_investment_to_date_eur` |
| `pending_equity_investment` | `pending_equity_investment_eur` |
| `estimated_capital_gain` | `estimated_capital_gain_eur` |

---

## New Fields

### FilterOptionsResponse (`/portfolio/filters`)

| Field Name | Type | Description |
|------------|------|-------------|
| `holding_companies` | `string[]` | List of distinct holding companies for sidebar |

**Updated response:**
```json
{
    "entities": ["Carlos Perso", "Dovela", ...],
    "holding_companies": ["Company A", "Company B", ...],
    "asset_types": ["Equities", "Real Estate", ...],
    "report_dates": ["2025-12-09", ...]
}
```

### AssetResponse

| Field Name | Type | Description |
|------------|------|-------------|
| `holding_company` | `string \| null` | Parent holding company |
| `unrealized_gain_usd` | `number \| null` | Unrealized gain in USD |
| `unrealized_gain_eur` | `number \| null` | Unrealized gain in EUR |

### RealEstateResponse

| Field Name | Type | Description |
|------------|------|-------------|
| `real_estate_status` | `string \| null` | Status (e.g., "Under development", "Completed") |
| `estimated_total_cost_usd` | `number \| null` | Total cost in USD |
| `total_investment_to_date_usd` | `number \| null` | Investment to date in USD |
| `equity_investment_to_date_usd` | `number \| null` | Equity investment in USD |
| `pending_equity_investment_usd` | `number \| null` | Pending equity investment in USD |
| `estimated_capital_gain_usd` | `number \| null` | Capital gain in USD |

### GroupByField Enum (for aggregation endpoints)

New values added:

| Value | Description |
|-------|-------------|
| `holding_company` | Group by parent holding company |
| `managing_entity` | Group by managing entity (previously `asset_group`) |

---

## TypeScript Type Definitions

```typescript
// Updated FilterOptionsResponse
interface FilterOptionsResponse {
    entities: string[]
    holding_companies: string[]  // NEW
    asset_types: string[]
    report_dates: string[]
}

// Updated AssetResponse type
interface AssetResponse {
    // Identifiers
    id: string
    display_id: number | null

    // Classification
    holding_company: string | null         // NEW
    ownership_holding_entity: string
    managing_entity: string                // RENAMED from asset_group
    asset_group: string | null             // RENAMED from asset_group_strategy
    asset_type: string
    asset_subtype: string | null
    asset_subtype_2: string | null
    asset_name: string
    asset_identifier: string | null
    asset_status: string | null

    // Location & Manager
    geographic_focus: string | null
    broker_asset_manager: string | null
    denomination_currency: string

    // Dates
    report_date: string | null             // ISO date string
    initial_investment_date: string | null // ISO date string

    // Share data
    number_of_shares: number | null
    avg_purchase_price_base_currency: number | null
    current_share_price: number | null

    // FX Rates
    usd_eur_inception: number | null
    usd_eur_current: number | null
    usd_cad_current: number | null
    usd_chf_current: number | null
    usd_hkd_current: number | null

    // Financial - Base Currency
    total_investment_commitment_base_currency: number | null
    paid_in_capital_base_currency: number | null
    asset_level_financing_base_currency: number | null
    unfunded_commitment_base_currency: number | null
    estimated_asset_value_base_currency: number | null
    total_asset_return_base_currency: number | null

    // Financial - USD
    total_investment_commitment_usd: number | null
    paid_in_capital_usd: number | null
    unfunded_commitment_usd: number | null
    estimated_asset_value_usd: number | null
    total_asset_return_usd: number | null
    unrealized_gain_usd: number | null     // NEW

    // Financial - EUR
    total_investment_commitment_eur: number | null
    paid_in_capital_eur: number | null
    unfunded_commitment_eur: number | null
    estimated_asset_value_eur: number | null
    total_asset_return_eur: number | null
    unrealized_gain_eur: number | null     // NEW

    // Timestamps
    created_at: string                     // ISO datetime string
    updated_at: string | null              // ISO datetime string

    // Extension data (only populated when include_extension=true)
    structured_note: StructuredNoteResponse | null
    real_estate: RealEstateResponse | null
}

// Updated RealEstateResponse type
interface RealEstateResponse {
    // Status
    real_estate_status: string | null      // NEW

    // EUR columns (all RENAMED with _eur suffix)
    cost_original_asset_eur: number | null
    estimated_capex_budget_eur: number | null
    pivert_development_fees_eur: number | null
    estimated_total_cost_eur: number | null
    capex_invested_eur: number | null
    total_investment_to_date_eur: number | null
    equity_investment_to_date_eur: number | null
    pending_equity_investment_eur: number | null
    estimated_capital_gain_eur: number | null

    // USD columns (all NEW)
    estimated_total_cost_usd: number | null
    total_investment_to_date_usd: number | null
    equity_investment_to_date_usd: number | null
    pending_equity_investment_usd: number | null
    estimated_capital_gain_usd: number | null
}

// StructuredNoteResponse - NO CHANGES
interface StructuredNoteResponse {
    annual_coupon: number | null
    coupon_payment_frequency: string | null
    next_coupon_review_date: string | null
    next_principal_review_date: string | null
    final_due_date: string | null
    redemption_type: string | null
    underlying_index_name: string | null
    underlying_index_code: string | null
    strike_level: number | null
    underlying_index_level: number | null
    performance_vs_strike: number | null
    effective_strike_percentage: number | null
    note_leverage: string | null
    capital_protection: number | null
    capital_protection_barrier: number | null
    coupon_protection_barrier_pct: number | null
    coupon_protection_barrier_value: number | null
}

// Updated GroupByField enum
type GroupByField =
    | 'ownership_holding_entity'
    | 'holding_company'      // NEW
    | 'managing_entity'      // NEW (replaces old asset_group meaning)
    | 'asset_type'
    | 'asset_group'          // Now means what was asset_group_strategy
    | 'geographic_focus'
    | 'denomination_currency'
    | 'asset_status'
    | 'broker_asset_manager'
```

---

## Migration Checklist

### 1. Update API Calls - Query Parameters (BREAKING)

- [ ] Replace `?asset_group=X` with `?managing_entity=X`
- [ ] Replace `?asset_group_strategy=Y` with `?asset_group=Y`
- [ ] Add `?holding_company=Z` where needed for sidebar filtering

### 2. Update Type Definitions

- [ ] Add `holding_companies` to `FilterOptionsResponse`
- [ ] Update `AssetResponse` interface with renamed and new fields
- [ ] Update `RealEstateResponse` interface with `_eur` suffix renames and new USD fields
- [ ] Update `GroupByField` type with new enum values

### 3. Update Field References in Components

- [ ] Search and replace `asset_group` → `managing_entity` (where it refers to the managing entity)
- [ ] Search and replace `asset_group_strategy` → `asset_group`
- [ ] Update all real estate field references to use `_eur` suffix

### 4. Update Filter Hooks

- [ ] Update `/filters` response handling to include `holding_companies`
- [ ] Add sidebar support for filtering by `holding_company`

### 5. Update Tables/Data Grids

- [ ] Update column definitions for asset tables
- [ ] Add new columns: `holding_company`, `unrealized_gain_usd`, `unrealized_gain_eur`
- [ ] Update real estate columns with new naming

### 6. Update Aggregation/Chart Components

- [ ] Update any components using `GroupByField` for grouping
- [ ] Add support for new grouping options: `holding_company`, `managing_entity`

### 7. Testing

- [ ] Verify `/filters` returns `holding_companies` array
- [ ] Verify filtering with new query params works
- [ ] Verify asset list displays correctly
- [ ] Verify real estate extension data displays correctly
- [ ] Verify aggregation endpoints work with new group_by options
- [ ] Check all charts/visualizations render properly

---

## API Endpoints Affected

All portfolio endpoints returning asset data are affected:

- `GET /portfolio/filters` - Now returns `holding_companies`
- `GET /portfolio/assets` - Query params renamed + new fields
- `GET /portfolio/assets/{id}` - New response fields
- `GET /portfolio/aggregations/summary` - Query params renamed
- `GET /portfolio/aggregations/by-entity` - Query params renamed
- `GET /portfolio/aggregations/by-asset-type` - Query params renamed
- `GET /portfolio/aggregations/historical` - Query params renamed
- `GET /portfolio/aggregations/flexible` - Query params renamed + new group_by values

---

## Quick Reference: Field Mapping

| Concept | Old Query Param | New Query Param | Response Field |
|---------|-----------------|-----------------|----------------|
| Managing Entity | `asset_group` | `managing_entity` | `managing_entity` |
| Asset Group | `asset_group_strategy` | `asset_group` | `asset_group` |
| Holding Company | *(new)* | `holding_company` | `holding_company` |

---

## Questions?

Contact the backend team if you have questions about these changes.
