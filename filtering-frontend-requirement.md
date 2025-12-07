# Backend Request: Add `asset_group` and `asset_group_strategy` Filter Support

## Summary

The frontend portfolio dashboard now supports filtering by `asset_group` and `asset_group_strategy` via URL parameters. However, the backend endpoints currently ignore these parameters. We need backend support to filter data by these fields.

---

## Frontend Behavior (Already Implemented)

When a user clicks on a pie chart segment:

1. **URL is updated** with the filter parameter:
   ```
   /dashboards?asset_group=Liquid%20Assets
   /dashboards?asset_group_strategy=Direct%20investment
   ```

2. **API calls include these parameters**:
   ```
   GET /api/v1/portfolio/assets?asset_group=Liquid%20Assets
   GET /api/v1/portfolio/aggregations/summary?asset_group=Liquid%20Assets
   GET /api/v1/portfolio/aggregations/by-entity?asset_group=Liquid%20Assets
   GET /api/v1/portfolio/aggregations/by-asset-type?asset_group=Liquid%20Assets
   GET /api/v1/portfolio/aggregations/flexible?group_by=asset_group&asset_group=Liquid%20Assets
   GET /api/v1/portfolio/historical-nav?asset_group=Liquid%20Assets
   ```

3. **Backend currently ignores** these parameters - no filtering occurs.

---

## Required Backend Changes

### New Query Parameters to Add

| Parameter | Type | Description |
|-----------|------|-------------|
| `asset_group` | `string \| null` | Filter by asset group (e.g., "Liquid Assets", "Illiquid Assets") |
| `asset_group_strategy` | `string \| null` | Filter by asset group strategy (e.g., "Direct investment", "Fund investment") |

### Endpoints to Update

All portfolio endpoints that currently support `entity` and `asset_type` filters should also support these new filters:

| Endpoint | Current Filters | Add These |
|----------|-----------------|-----------|
| `GET /portfolio/assets` | entity, asset_type | asset_group, asset_group_strategy |
| `GET /portfolio/aggregations/summary` | entity, asset_type | asset_group, asset_group_strategy |
| `GET /portfolio/aggregations/by-entity` | asset_type | asset_group, asset_group_strategy |
| `GET /portfolio/aggregations/by-asset-type` | entity | asset_group, asset_group_strategy |
| `GET /portfolio/aggregations/flexible` | entity, asset_type | asset_group, asset_group_strategy |
| `GET /portfolio/historical-nav` | entity, asset_type | asset_group, asset_group_strategy |

---

## Implementation Example

The filter logic should follow the same pattern as existing `entity` and `asset_type` filters:

```python
# In service.py - add to existing query builders

def get_assets(
    db: Session,
    entity: str | None = None,
    asset_type: str | None = None,
    asset_group: str | None = None,           # ADD THIS
    asset_group_strategy: str | None = None,  # ADD THIS
    report_date: date | None = None,
    ...
) -> tuple[list[Asset], int]:
    query = db.query(Asset)

    # Existing filters
    if entity:
        query = query.filter(Asset.ownership_holding_entity == entity)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    # NEW filters - same pattern
    if asset_group:
        query = query.filter(Asset.asset_group == asset_group)
    if asset_group_strategy:
        query = query.filter(Asset.asset_group_strategy == asset_group_strategy)

    # ... rest of function
```

```python
# In controller.py - add query parameters

@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    entity: str | None = Query(None, description="Filter by entity"),
    asset_type: str | None = Query(None, description="Filter by asset type"),
    asset_group: str | None = Query(None, description="Filter by asset group"),  # ADD
    asset_group_strategy: str | None = Query(None, description="Filter by strategy"),  # ADD
    report_date: date | None = Query(None),
    ...
):
    return service.get_assets(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,                # ADD
        asset_group_strategy=asset_group_strategy,  # ADD
        report_date=report_date,
        ...
    )
```

---

## Database Schema Reference

The fields already exist in the `assets` table:

```python
# From models.py
class Asset(Base):
    __tablename__ = "assets"

    asset_group = Column(String(100), nullable=False)
    asset_group_strategy = Column(String(100))  # nullable
```

**Example values in database:**
- `asset_group`: "Liquid Assets", "Illiquid Assets", "Cash and Money Markets"
- `asset_group_strategy`: "Direct investment", "Fund investment", "Co-investment", etc.

---

## Expected Behavior After Implementation

1. User clicks "Liquid Assets" segment in pie chart
2. URL: `/dashboards?asset_group=Liquid%20Assets`
3. All API calls include `?asset_group=Liquid%20Assets`
4. **Backend filters all responses** to only include assets where `asset_group = 'Liquid Assets'`
5. Dashboard updates to show only Liquid Assets data across all charts and tables

---

## Files to Modify

```
src/modules/portfolio/
├── controller.py  # Add query parameters to endpoint definitions
├── service.py     # Add filter logic to query functions
└── schemas.py     # Update schemas if needed (optional)
```

---

## Testing

After implementation, these URLs should return filtered data:

```bash
# Filter by asset_group
curl "http://localhost:8000/api/v1/portfolio/assets?asset_group=Liquid%20Assets"

# Filter by asset_group_strategy
curl "http://localhost:8000/api/v1/portfolio/assets?asset_group_strategy=Direct%20investment"

# Combined filters
curl "http://localhost:8000/api/v1/portfolio/assets?entity=Isis%20Invest&asset_group=Liquid%20Assets"
```
