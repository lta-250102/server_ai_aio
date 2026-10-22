---
name: bigdata
description: DWH Bigdata — SQL analysis trên Falcon Data DWH (ClickHouse). Dùng cho UA attribution granular, creative-level metrics, spend/ROAS/CPI analysis. Schema lookup qua Falcon Data MCP.
version: 3.0
last_updated: 2026-10-05
---

# DWH Bigdata Skills

## Trigger
Khi user cần phân tích UA qua SQL trên ClickHouse DWH.

Mặc định check chỉ số các campaign thì luôn loại bỏ organic, luôn thêm điều kiện ```AND network_code NOT IN ('UNKNOWN', '', 'organic')``` vào khối where của query sql

## Khi nào dùng
- ✅ Attribution granular (creative, keyword, site_id, geo, network)
- ✅ Creative-level metrics (spend, installs, cost)
- ✅ Spend, ROAS, CPI analysis theo mọi dimension
- ✅ Cohort retention analysis (D1/D3/D7) theo mọi dimension
- ❌ Quick overview → dùng GrowX MCP nhanh hơn

## Schema Lookup — Dùng Falcon Data MCP

**⚠️ KHÔNG có local schema files.** Tất cả schema, business rules, pitfalls lookup qua Falcon Data MCP.

### Bước 1: Tìm table cần query

```
search_data_docs(query="ua attribution")
→ Trả về danh sách tables liên quan
```

### Bước 2: Đọc schema chi tiết

```
read_data_page(path="schemas/f_puller_ua_attribution")
→ Trả về: columns, types, query notes, pitfalls
```

### Bước 3: Đọc business rules

```
read_data_page(path="concepts/business-rules")
→ Trả về: quy tắc tính metric, sentinel values, timezone
```

### Bước 4: Tìm example SQL (nếu có)

```
read_data_page(path="examples/ua/campaign-roas")
→ Trả về: SQL mẫu + pitfalls cụ thể
```

## Tables UA chính (tham khảo)

| Table | Purpose | MCP Path |
|-------|---------|----------|
| `f_puller_ua_attribution` | UA attribution granular | `schemas/f_puller_ua_attribution` |
| `f_puller_ua_creative` | Creative-level UA metrics | `schemas/f_puller_ua_creative` |
| `f_summarised_user_daily_v2_utc` | Gold user-day (retention, sessions, revenue) | `schemas/f_summarised_user_daily_v2_utc` |

## Generic SQL Templates

### Template 1: Dimension ROAS/CPI (attribution table)

Dùng cho **tất cả cases** phân tích theo dimension (network, campaign, site, geo, creative).

**⚠️ CLICKHOUSE LIMITATION:** ClickHouse không hỗ trợ nhiều aggregate functions (`sum()`, `round()`) cùng level trong SELECT với GROUP BY. Lỗi: `Nested aggregate function sum(revenue) is not supported`.

**Solution:** Dùng **CTE pattern** (`WITH ... AS (...)`) — aggregate trong CTE, tính derived metrics (ROAS, CPI) ở outer query.

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        {{dimension_column}} AS dimension,
        created_day,
        sum(cost) AS cost,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 14 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY {{dimension_column}}, created_day
)
SELECT
    dimension,
    created_day,
    cost,
    revenue,
    installs,
    round(revenue / NULLIF(cost, 0) * 100, 2) AS roas,
    round(cost / NULLIF(installs, 0), 4) AS cpi
FROM base_agg
ORDER BY dimension, created_day
```

**Dimension → Column mapping:**

| Dimension | Column | Cases |
|-----------|--------|-------|
| Game (overall) | `'all'` | Case 1 (spend trend) |
| Network | `network_code` | Case 2, 8, 14 |
| Campaign | `campaign_id` | Case 3, 9, 15 |
| Geo | `country` | Case 4, 10, 16 |
| Site | `site_id` | Case 5, 11, 17 |
| Creative | `creative_id` | Case 6, 12, 18 |

**Rules:**
- Luôn có `WHERE package_name = '<package_name>'`
- Luôn thêm `AND network_code NOT IN ('UNKNOWN', '', 'organic')`
- **Tuyệt đối không JOIN 2 bảng**
- **Luôn dùng `BETWEEN today() - INTERVAL X DAY AND today() - 1`** — exclude today, không dùng `>=`
- **Aggregate trong CTE, tính derived metrics ở outer query**
- ORDER BY dimension, created_day

### Template 2: Daily Trend (attribution table)

Dùng cho cases phân tích **trend theo ngày** (spend trend, CPI trend).

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH daily_agg AS (
    SELECT
        created_day,
        sum(cost) AS cost,
        sum(conversion) AS installs,
        sum(revenue) AS revenue
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 14 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY created_day
)
SELECT
    created_day,
    round(cost, 2) AS cost,
    installs,
    round(revenue, 2) AS revenue,
    round(cost / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(cost, 0) * 100, 2) AS roas,
    round(
        (cost / NULLIF(installs, 0)) - LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day),
        4
    ) AS delta_cpi,
    round(
        ((cost / NULLIF(installs, 0)) - LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day))
        / NULLIF(LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day), 0) * 100,
        2
    ) AS delta_cpi_pct
FROM daily_agg
WHERE installs > 0
ORDER BY created_day
```

**Output columns:** `created_day`, `cost`, `installs`, `revenue`, `cpi`, `roas`, `delta_cpi`, `delta_cpi_pct`

### Template 3: Cohort Retention (user-day table)

Dùng cho **tất cả retention cases** — D1/D3/D7 retention theo mọi dimension (game, network, campaign, geo, site, creative).

**Table:** `f_summarised_user_daily_v2_utc` (gold user-day table)

**⚠️ RULES:**
- Luôn filter `package_name` + date range trên `install_day` và `created_day`
- Luôn loại bỏ `''` và `'UNKNOWN'` cho dimension column
- Dùng `uniqExact(account_id)` để count people, không dùng `count()`
- Retention = user quay lại (có `created_day` trong ngày đó), KHÔNG phải purchase

```sql
WITH base AS (
    SELECT 
        {{dimension_column}},
        install_day,
        uniqExact(account_id) AS total_installs,
        uniqExactIf(account_id, created_day = install_day + 1) AS d1_retained,
        uniqExactIf(account_id, created_day = install_day + 3) AS d3_retained,
        uniqExactIf(account_id, created_day = install_day + 7) AS d7_retained
    FROM dwh_system.f_summarised_user_daily_v2_utc
    WHERE package_name = '<package_name>'
      AND install_day BETWEEN today() - INTERVAL 14 DAY AND today() - INTERVAL 7 DAY
      AND created_day BETWEEN today() - INTERVAL 14 DAY AND today()
      AND install_day IS NOT NULL
      AND {{dimension_column}} != ''
      AND {{dimension_column}} != 'UNKNOWN'
    GROUP BY {{dimension_column}}, install_day
)
SELECT 
    {{dimension_column}} AS {{dimension_name}},
    install_day AS cohort_day,
    total_installs,
    d1_retained,
    round(d1_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d1_pct,
    d3_retained,
    round(d3_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d3_pct,
    d7_retained,
    round(d7_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d7_pct
FROM base
WHERE total_installs > 0
ORDER BY install_day
```

**Dimension → Column mapping:**

| Dimension | Column (`{{dimension_column}}`) | Name (`{{dimension_name}}`) | Cases |
|-----------|------|------|-------|
| Game (overall) | *none* | — | Case 19 |
| Network | `mmp_media_source` | `network` | Case 20 |
| Campaign | `mmp_campaign_id` | `campaign` | Case 21 |
| Geo | `country` | `geo` | Case 22 |
| Site | `mmp_adset_id` | `site_id` | Case 23 |
| Creative | `mmp_ad_id` | `creative` | Case 24 |

**⚠️ Case 19 (Game overall):** Không có dimension — query không GROUP BY dimension column, chỉ GROUP BY `install_day` để tính retention tổng thể của game.

**Output columns:** `cohort_day`, `total_installs`, `d1_retained`, `rr_d1_pct`, `d3_retained`, `rr_d3_pct`, `d7_retained`, `rr_d7_pct`

## Cases

### Spend & Budget (Cases 1-6)
| # | Case | File |
|---|------|------|
| 1 | Spend game tăng/giảm | [cases/case-01-spend-trend.md](cases/case-01-spend-trend.md) |
| 2 | Phân bổ budget media source | [cases/case-02-budget-allocation.md](cases/case-02-budget-allocation.md) |
| 3 | Campaign trong network biến động | [cases/case-03-campaign-analysis.md](cases/case-03-campaign-analysis.md) |
| 4 | Geo thay đổi traffic | [cases/case-04-geo-traffic.md](cases/case-04-geo-traffic.md) |
| 5 | Site_id đẩy spend | [cases/case-05-siteid-spend.md](cases/case-05-siteid-spend.md) |
| 6 | Creative spending nhiều nhất | [cases/case-06-creative-spending.md](cases/case-06-creative-spending.md) |

### ROAS/ROI (Cases 7-12)
| # | Case | File |
|---|------|------|
| 7 | ROAS/ROI game | [cases/case-07-roas-roi.md](cases/case-07-roas-roi.md) |
| 8 | Network ảnh hưởng dòng tiền (LTV/ROAS) | [cases/case-08-network-ltv.md](cases/case-08-network-ltv.md) |
| 9 | ROAS của campaign | [cases/case-09-campaign-roas.md](cases/case-09-campaign-roas.md) |
| 10 | Geo nào có ROAS lệch | [cases/case-10-geo-roas.md](cases/case-10-geo-roas.md) |
| 11 | Site_id ROAS thấp/cao | [cases/case-11-siteid-roas.md](cases/case-11-siteid-roas.md) |
| 12 | Creative ROAS tốt/xấu | [cases/case-12-creative-roas.md](cases/case-12-creative-roas.md) |

### CPI (Cases 13-18)
| # | Case | File |
|---|------|------|
| 13 | CPI game tăng/giảm | [cases/case-13-cpi-game.md](cases/case-13-cpi-game.md) |
| 14 | Network CPI cao/thấp | [cases/case-14-network-cpi.md](cases/case-14-network-cpi.md) |
| 15 | Campaign CPI lệch | [cases/case-15-campaign-cpi.md](cases/case-15-campaign-cpi.md) |
| 16 | Geo CPI lệch | [cases/case-16-geo-cpi.md](cases/case-16-geo-cpi.md) |
| 17 | Site_id CPI bất thường | [cases/case-17-siteid-cpi.md](cases/case-17-siteid-cpi.md) |
| 18 | Creative CPI thấp/cao | [cases/case-18-creative-cpi.md](cases/case-18-creative-cpi.md) |

### Retention (Cases 19-24)

Retention data query trên **gold user-day table** `f_summarised_user_daily_v2_utc` với cohort pattern — D1/D3/D7 retention theo dimension.

| # | Case | Dimension | File |
|---|------|-----------|------|
| 19 | Retention game D1/D3/D7 | Game | [cases/case-19-retention-game.md](cases/case-19-retention-game.md) |
| 20 | Network retention | Network | [cases/case-20-network-retention.md](cases/case-20-network-retention.md) |
| 21 | Campaign retention | Campaign | [cases/case-21-campaign-retention.md](cases/case-21-campaign-retention.md) |
| 22 | Geo retention | Geo | [cases/case-22-geo-retention.md](cases/case-22-geo-retention.md) |
| 23 | Site_id retention | Site | [cases/case-23-siteid-retention.md](cases/case-23-siteid-retention.md) |
| 24 | Creative retention | Creative | [cases/case-24-creative-retention.md](cases/case-24-creative-retention.md) |
