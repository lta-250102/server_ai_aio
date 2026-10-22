---
name: case-10-geo-roas
description: Geo nào có ROAS lệch
---

# Case 10: Geo nào có ROAS lệch (Geo ROAS Analysis)

## Trigger
- Khi user hỏi về ROAS theo quốc gia, geo nào có ROAS cao/thấp bất thường.

## Mục tiêu
Xác định các geo có ROAS cao nhất/thấp nhất, so sánh hiệu quả giữa các quốc gia.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        country,
        created_day,
        sum(cost) AS spend,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND country != ''
      AND country != 'UNKNOWN'
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY country, created_day
)
SELECT
    country AS geo,
    created_day,
    round(spend, 2) AS spend,
    round(revenue, 2) AS revenue,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY geo, created_day
```

**Output columns:** `geo`, `spend`, `revenue`, `installs`, `cpi`, `roas`

## Bước 2: Phân tích

- **Geo ROAS > 200%**: Geo rất hiệu quả → tăng budget
- **Geo ROAS 100-200%**: Geo hiệu quả → giữ nguyên
- **Geo ROAS 50-100%**: Geo hòa vốn/lỗ nhẹ → theo dõi
- **Geo ROAS < 50%**: Geo kém hiệu quả → cân nhắc giảm budget

## Bước 3: Gợi ý

- Tăng budget cho top 5 geos có ROAS cao nhất
- Giảm budget cho geos có ROAS < 50% của trung bình
- Test thêm geo mới để diversify

## Cảnh báo thresholds
- Geo ROAS > 200% → gợi ý scale up
- Geo ROAS 100-200% → giữ nguyên
- Geo ROAS < 50% avg → cảnh báo kém hiệu quả
