---
name: case-22-geo-retention
description: Geo Retention
---

# Case 22: Geo Retention (Geo-level Retention)

## Trigger
- Khi user hỏi về retention theo quốc gia, geo nào có user retention tốt nhất.

## Mục tiêu
So sánh retention giữa các geo, xác định geo nào có user quality cao nhất.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
WITH base AS (
    SELECT 
        country,
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
      AND country != ''
      AND country != 'UNKNOWN'
    GROUP BY country, install_day
)
SELECT 
    country AS geo,
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

**Output columns:** `cohort_day`, `total_installs`, `d1_retained`, `rr_d1_pct`, `d3_retained`, `rr_d3_pct`, `d7_retained`, `rr_d7_pct`

## Bước 2: Phân tích

- **Geo retention D7/D1 > 40%**: Geo có user long-term engagement tốt → tăng budget
- **Geo retention D7/D1 20-40%**: Retention trung bình → giữ nguyên
- **Geo retention D7/D1 < 20%**: Geo có user churn cao → giảm budget

## Bước 3: Gợi ý

- Tăng budget cho geos có retention D7/D1 cao nhất
- Giảm budget cho geos có retention D7/D1 thấp nhất
- Test thêm geo mới để diversify

## Cảnh báo thresholds
- Geo retention D7/D1 < 20% → cảnh báo churn cao
- Geo retention D7/D1 > 40% → gợi ý scale up
