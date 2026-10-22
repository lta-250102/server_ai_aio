---
name: case-16-geo-cpi
description: Geo CPI lệch
---

# Case 16: Geo CPI lệch (Geo CPI)

## Trigger
- Khi user hỏi về CPI theo quốc gia, geo nào có CPI cao/thấp bất thường.

## Mục tiêu
So sánh CPI giữa các geo, xác định geo nào đắt nhất/rẻ nhất.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        country AS geo,
        created_day,
        sum(conversion) AS installs,
        sum(cost) AS spend,
        sum(revenue) AS revenue
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
    geo,
    created_day,
    installs,
    spend,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    revenue,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY geo, created_day
```

**Output columns:** `geo`, `installs`, `spend`, `cpi`, `revenue`, `roas`

## Bước 2: Phân tích

- **Geo CPI thấp nhưng ROAS thấp**: Geo rẻ nhưng user chất lượng thấp → cân nhắc
- **Geo CPI cao nhưng ROAS cao**: Geo đắt nhưng user chất lượng cao → chấp nhận
- **Geo CPI cao mà ROAS thấp**: Geo vừa đắt vừa kém hiệu quả → giảm budget

## Bước 3: Gợi ý

- Tăng budget cho geos có CPI thấp và ROAS cao
- Giảm budget cho geos có CPI cao và ROAS thấp
- Test thêm geo mới để diversify

## Cảnh báo thresholds
- Geo CPI > 2x avg → cảnh báo CPI cao
- Geo CPI < 0.5x avg mà ROAS < 100% → cảnh báo user chất lượng thấp
