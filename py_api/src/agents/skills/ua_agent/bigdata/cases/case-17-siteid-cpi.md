---
name: case-17-siteid-cpi
description: Site_id CPI bất thường
---

# Case 17: Site_id CPI bất thường (Site_id CPI)

## Trigger
- Khi user hỏi về CPI theo site_id, site nào có CPI bất thường.

## Mục tiêu
Xác định site_ids có CPI cao nhất/thấp nhất, tối ưu placement cost.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        site_id,
        created_day,
        sum(conversion) AS installs,
        sum(cost) AS spend,
        sum(revenue) AS revenue
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND site_id != ''
      AND site_id != 'UNKNOWN'
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY site_id, created_day
)
SELECT
    site_id,
    created_day,
    installs,
    spend,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    revenue,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY site_id, created_day
LIMIT 20
```

**Output columns:** `site_id`, `installs`, `spend`, `cpi`, `revenue`, `roas`

## Bước 2: Phân tích

- **Site_id CPI thấp nhưng ROAS thấp**: Site rẻ nhưng user chất lượng thấp → cân nhắc
- **Site_id CPI cao nhưng ROAS cao**: Site đắt nhưng user chất lượng cao → chấp nhận
- **Site_id CPI cao mà ROAS thấp**: Site vừa đắt vừa kém hiệu quả → block

## Bước 3: Gợi ý

- Tăng bid cho site_ids có CPI thấp và ROAS cao
- Giảm bid cho site_ids có CPI cao và ROAS thấp
- Review creative phù hợp với từng site_id

## Cảnh báo thresholds
- Site_id CPI > 2x avg → cảnh báo CPI cao
- Site_id CPI < 0.5x avg mà ROAS < 100% → cảnh báo user chất lượng thấp
