# Portfolio Reports API Documentation

> API reference for AI-powered portfolio analysis reports

---

## Overview

Generates professional markdown financial reports from portfolio data using Claude Opus 4.5. Reports are created asynchronously - the API returns immediately and the frontend must poll for completion.

**Base URL**: `/api/v1/portfolio_reports`

**Authentication**: Bearer token in `Authorization` header

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Create report (async) |
| `GET` | `/{report_id}` | Get report by ID |
| `GET` | `/` | List user's reports |
| `DELETE` | `/{report_id}` | Delete report |

---

## POST / — Create Report

Creates a new report. Returns immediately with `status: "pending"`. Poll `GET /{id}` for completion.

### Request

```json
{
  "title": "Q4 2024 Portfolio Analysis",
  "scope": "single_date",
  "report_date": "2024-12-31",
  "entity_filter": null,
  "asset_type_filter": null,
  "holding_company_filter": null,
  "user_prompt": "Focus on private equity performance and concentration risks.",
  "research_enabled": false
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | `string` | No | `"Portfolio Analysis Report"` | Report title (max 255 chars) |
| `scope` | `string` | No | `"single_date"` | `"single_date"` or `"all_dates"` |
| `report_date` | `string\|null` | No | Latest available | ISO date `YYYY-MM-DD`. Only for `single_date` scope |
| `entity_filter` | `string\|null` | No | `null` | Filter by ownership_holding_entity |
| `asset_type_filter` | `string\|null` | No | `null` | Filter by asset_type |
| `holding_company_filter` | `string\|null` | No | `null` | Filter by holding_company |
| `user_prompt` | `string\|null` | No | `null` | Custom instructions for the AI |
| `research_enabled` | `boolean` | No | `false` | Enable internet research (slower) |

### Scope Values

| Value | Description |
|-------|-------------|
| `single_date` | Point-in-time analysis at specific date |
| `all_dates` | Trend analysis across all available dates |

### Response `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Q4 2024 Portfolio Analysis",
  "scope": "single_date",
  "report_date": "2024-12-31",
  "entity_filter": null,
  "asset_type_filter": null,
  "holding_company_filter": null,
  "user_prompt": "Focus on private equity performance and concentration risks.",
  "research_enabled": false,
  "status": "pending",
  "agent_version": "1.0.0",
  "error_message": null,
  "markdown_content": null,
  "tokens_used": null,
  "input_tokens": null,
  "output_tokens": null,
  "processing_time_seconds": null,
  "created_at": "2024-12-31T10:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

---

## GET /{report_id} — Get Report

Retrieves report by ID. Use for polling during generation.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | `UUID` | Report identifier |

### Response `200 OK` (Completed)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Q4 2024 Portfolio Analysis",
  "scope": "single_date",
  "report_date": "2024-12-31",
  "entity_filter": null,
  "asset_type_filter": null,
  "holding_company_filter": null,
  "user_prompt": "Focus on private equity performance.",
  "research_enabled": false,
  "status": "completed",
  "agent_version": "1.0.0",
  "error_message": null,
  "markdown_content": "# Portfolio Analysis Report\n\n## Executive Summary\n\n...",
  "tokens_used": 15000,
  "input_tokens": 8000,
  "output_tokens": 7000,
  "processing_time_seconds": 45.5,
  "created_at": "2024-12-31T10:00:00Z",
  "started_at": "2024-12-31T10:00:01Z",
  "completed_at": "2024-12-31T10:00:46Z"
}
```

### Response `200 OK` (Failed)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_message": "AI service timeout after 600 seconds",
  "markdown_content": null,
  "...": "..."
}
```

---

## GET / — List Reports

Lists all reports for the authenticated user, newest first.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `integer` | `20` | Max reports to return (1-100) |
| `offset` | `integer` | `0` | Pagination offset |

### Response `200 OK`

```json
{
  "reports": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Q4 2024 Portfolio Analysis",
      "scope": "single_date",
      "status": "completed",
      "...": "..."
    }
  ],
  "total": 25
}
```

---

## DELETE /{report_id} — Delete Report

Permanently deletes a report.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | `UUID` | Report identifier |

### Response

- `204 No Content` — Deleted successfully
- `404 Not Found` — Report not found or not owned by user

---

## TypeScript Types

```typescript
enum ReportStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
}

enum ReportScope {
  SINGLE_DATE = "single_date",
  ALL_DATES = "all_dates",
}

interface CreateReportRequest {
  title?: string;
  scope?: ReportScope;
  report_date?: string | null;
  entity_filter?: string | null;
  asset_type_filter?: string | null;
  holding_company_filter?: string | null;
  user_prompt?: string | null;
  research_enabled?: boolean;
}

interface ReportResponse {
  id: string;
  user_id: string;
  title: string;
  scope: ReportScope;
  report_date: string | null;
  entity_filter: string | null;
  asset_type_filter: string | null;
  holding_company_filter: string | null;
  user_prompt: string | null;
  research_enabled: boolean;
  status: ReportStatus;
  agent_version: string;
  error_message: string | null;
  markdown_content: string | null;
  tokens_used: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  processing_time_seconds: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}
```

---

## Status Flow

```
PENDING → IN_PROGRESS → COMPLETED
                     ↘ FAILED
```

| Status | Description |
|--------|-------------|
| `pending` | Queued, waiting to start |
| `in_progress` | AI is generating the report |
| `completed` | Report ready in `markdown_content` |
| `failed` | Error occurred, see `error_message` |

---

## Polling Strategy

| Time Elapsed | Poll Interval |
|--------------|---------------|
| 0-10 seconds | Every 2 seconds |
| 10-60 seconds | Every 5 seconds |
| 60+ seconds | Every 10 seconds |

**Maximum wait**: 10 minutes (600 seconds)

**Expected generation time**:
- Without research: 30-90 seconds
- With research: 60-180 seconds

---

## Filter Options

To populate filter dropdowns, use the existing portfolio filters endpoint:

**`GET /api/v1/portfolio/filters`**

```json
{
  "entities": ["Family Trust", "Holding LLC"],
  "holding_companies": ["Main Holdings", "Secondary Holdings"],
  "asset_types": ["Private Equity", "Real Estate", "Fixed Income"],
  "report_dates": ["2024-12-31", "2024-09-30", "2024-06-30"]
}
```

---

## Markdown Output

The `markdown_content` field contains **GitHub Flavored Markdown (GFM)**.

### Markdown Features Used

| Feature | Syntax | Usage |
|---------|--------|-------|
| Headers | `#`, `##`, `###` | Section titles |
| Tables | GFM pipe tables | Financial data, metrics |
| Horizontal rules | `---` | Section separators |
| Bold | `**text**` | Key figures, emphasis |
| Lists | `- item` or `1. item` | Recommendations, findings |
| Line breaks | Double newline | Paragraph separation |

### Rendering Requirements

- **Parser**: Must support GitHub Flavored Markdown (GFM)
- **Tables**: GFM table syntax with alignment
- **Recommended libraries**:
  - React: `react-markdown` + `remark-gfm`
  - Vue: `markdown-it` + `markdown-it-gfm`
  - Vanilla: `marked` with GFM enabled

### Example Markdown Structure

```markdown
# Portfolio Analysis Report

## Executive Summary

The portfolio demonstrates strong performance with a total AUM of **$125.5M**...

---

## Portfolio Overview

| Metric | Value |
|--------|-------|
| Total AUM (USD) | $125.5M |
| Total AUM (EUR) | €115.2M |
| Total Assets | 47 |

---

## Asset Class Analysis

### By Asset Type

| Asset Type | Value (USD) | % of Portfolio | Return |
|------------|-------------|----------------|--------|
| Private Equity | $45.2M | 36.0% | 18.5% |
| Real Estate | $32.1M | 25.6% | 12.3% |

---

## Recommendations

1. **Reduce concentration** in Private Equity sector
2. **Increase allocation** to Fixed Income for stability
3. **Monitor** unfunded commitments totaling $8.2M
```

### Report Sections

1. Executive Summary
2. Portfolio Overview
3. Asset Class Analysis
4. Geographic Distribution
5. Currency Exposure Analysis
6. Performance Analysis
7. Risk Assessment
8. Historical Trends *(only with `all_dates` scope)*
9. Recommendations
10. Appendix: Top Holdings

---

## Error Responses

| Status | Description |
|--------|-------------|
| `400` | Invalid request body |
| `401` | Missing or invalid token |
| `404` | Report not found |
| `500` | Server error |

```json
{
  "detail": "Report 550e8400-... not found"
}
```

---

## User Prompt Examples

```text
"Focus on private equity performance and real estate exposure. Highlight concentration risks."

"Analyze currency exposure and FX hedging recommendations. Compare EUR vs USD."

"Identify liquidity risks and unfunded commitments. Recommend rebalancing."

"Compare current allocation vs Q3 2024. Highlight significant changes."
```
