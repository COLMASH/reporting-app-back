# Backend Changes Required - December 19, 2025

This document outlines the backend changes needed **BEFORE** frontend migration can begin.

---

## 1. Update `/filters` Endpoint

**File:** `app/portfolio/service.py` (around line 65)

```python
# Current:
entities = db.query(distinct(Asset.ownership_holding_entity)).all()

# Add holding_companies query:
holding_companies = db.query(distinct(Asset.holding_company)).filter(
    Asset.holding_company.isnot(None)
).all()
```

**Schema change (schemas.py):**
```python
class FilterOptionsResponse(BaseModel):
    holding_companies: list[str]  # NEW - for sidebar navigation
    entities: list[str]           # Keep for backwards compat
    asset_types: list[str]
    report_dates: list[str]
```

**Expected response:**
```json
{
    "holding_companies": ["Company A", "Company B", ...],
    "entities": ["Carlos Perso", "Dovela", ...],
    "asset_types": [...],
    "report_dates": [...]
}
```

---

## 2. Rename Query Parameters

Update all portfolio endpoints to use new parameter names:

| Endpoint | Old Param | New Param |
|----------|-----------|-----------|
| `/portfolio/assets` | `asset_group` | `managing_entity` |
| `/portfolio/assets` | `asset_group_strategy` | `asset_group` |
| `/portfolio/summary` | `asset_group` | `managing_entity` |
| `/portfolio/summary` | `asset_group_strategy` | `asset_group` |
| `/portfolio/aggregations/*` | `asset_group` | `managing_entity` |
| `/portfolio/aggregations/*` | `asset_group_strategy` | `asset_group` |
| `/portfolio/historical-nav` | `asset_group` | `managing_entity` |
| `/portfolio/historical-nav` | `asset_group_strategy` | `asset_group` |

**Also add new filter parameter to all endpoints:**
- `holding_company` - Filter by holding company (for sidebar filtering)

---

## 3. Update GroupByField Enum

**File:** `app/portfolio/schemas.py`

```python
# New enum (replaces current):
class GroupByField(str, Enum):
    ownership_holding_entity = "ownership_holding_entity"
    holding_company = "holding_company"        # NEW
    managing_entity = "managing_entity"        # NEW (replaces asset_group meaning)
    asset_type = "asset_type"
    asset_group = "asset_group"                # NOW means former asset_group_strategy
    geographic_focus = "geographic_focus"
    denomination_currency = "denomination_currency"
    asset_status = "asset_status"
    broker_asset_manager = "broker_asset_manager"
    # REMOVED: asset_group_strategy (replaced by asset_group with new meaning)
```

---

## 4. Verify Response Field Names

Ensure serialization uses correct field names:

**AssetResponse fields:**
```json
{
    "holding_company": "Company A",           // NEW field
    "ownership_holding_entity": "Entity A",   // KEEP as-is
    "managing_entity": "Manager A",           // RENAMED from asset_group
    "asset_group": "Strategy A",              // RENAMED from asset_group_strategy
    "unrealized_gain_usd": 10000,             // NEW field
    "unrealized_gain_eur": 9200               // NEW field
}
```

**RealEstateResponse fields (all with `_eur` suffix + new USD variants):**
```json
{
    "real_estate_status": "Under development",
    "cost_original_asset_eur": 1000000,
    "estimated_capex_budget_eur": 200000,
    "pivert_development_fees_eur": 50000,
    "estimated_total_cost_eur": 1500000,
    "capex_invested_eur": 100000,
    "total_investment_to_date_eur": 800000,
    "equity_investment_to_date_eur": 600000,
    "pending_equity_investment_eur": 200000,
    "estimated_capital_gain_eur": 400000,
    "estimated_total_cost_usd": 1620000,
    "total_investment_to_date_usd": 864000,
    "equity_investment_to_date_usd": 648000,
    "pending_equity_investment_usd": 216000,
    "estimated_capital_gain_usd": 432000
}
```

---

## 5. Testing Checklist

After making changes, verify these API calls work:

### Filters Endpoint
- [ ] `GET /api/v1/portfolio/filters` returns `holding_companies` array

### Asset Filtering
- [ ] `GET /api/v1/portfolio/assets?managing_entity=X` filters by managing entity
- [ ] `GET /api/v1/portfolio/assets?asset_group=Y` filters by asset group (former strategy)
- [ ] `GET /api/v1/portfolio/assets?holding_company=Z` filters by holding company

### Aggregations
- [ ] `GET /api/v1/portfolio/aggregations/flexible?group_by=managing_entity` works
- [ ] `GET /api/v1/portfolio/aggregations/flexible?group_by=holding_company` works
- [ ] `GET /api/v1/portfolio/aggregations/flexible?group_by=asset_group` works (with new meaning)

### Response Fields
- [ ] Asset responses include `holding_company` field
- [ ] Asset responses include `managing_entity` field (renamed from `asset_group`)
- [ ] Asset responses include `asset_group` field (renamed from `asset_group_strategy`)
- [ ] Asset responses include `unrealized_gain_usd` and `unrealized_gain_eur`
- [ ] Real estate extension includes `real_estate_status`
- [ ] Real estate extension includes all `_eur` suffix fields
- [ ] Real estate extension includes all USD variant fields

---

## Quick Reference: Field Mapping

| Concept | Old DB Column | Old API Field | New API Field |
|---------|---------------|---------------|---------------|
| Managing Entity | `asset_group` | `asset_group` | `managing_entity` |
| Asset Group | `asset_group_strategy` | `asset_group_strategy` | `asset_group` |
| Holding Company | `holding_company` | (new) | `holding_company` |

---

## After Backend Is Ready

Once all backend changes are complete and tested, notify the frontend team to proceed with:
1. Type definitions update
2. Filter hooks update
3. UI component updates
4. Sidebar switch to holding_company

Frontend implementation plan: `~/.claude/plans/zany-mixing-shore.md`
