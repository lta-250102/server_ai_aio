---
name: case-04-geo-traffic
description: Phân tích traffic theo geo
---

# Case 4: Geo thay đổi traffic (Geo Traffic Analysis)

## Trigger
- Khi user hỏi về traffic theo quốc gia, phân bổ geo, CPI/ROAS theo country.

## Mục tiêu
Phân tích phân bổ traffic theo quốc gia, so sánh CPI và ROAS giữa các geo.

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
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY country, created_day
)
SELECT
    geo,
    created_day,
    installs,
    spend,
    revenue,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY geo, created_day
```

**Output columns:** `geo`, `installs`, `spend`, `revenue`, `cpi`, `roas`

## Bước 2: Phân tích

- **Geo có installs > 30% nhưng ROAS < 100%**: Geo này ngốn traffic nhưng hiệu quả thấp → cân nhắc giảm
- **Geo có installs < 5% nhưng ROAS > 200%**: Geo nhỏ nhưng hiệu quả cao → cân nhắc scale
- **Top 5 geos chiếm > 70% installs**: Phụ thuộc quá nhiều vào vài quốc gia → diversify

## Bước 3: Gợi ý

- Tăng budget cho geo có ROAS cao nhất
- Giảm budget cho geo có CPI cao nhất
- Test thêm geo mới để diversify traffic

## Cảnh báo thresholds
- Single geo install % > 40% → cảnh báo phụ thuộc
- Geo ROAS < 100% → cảnh báo lỗ
- Geo CPI > 2x avg → cảnh báo CPI cao
