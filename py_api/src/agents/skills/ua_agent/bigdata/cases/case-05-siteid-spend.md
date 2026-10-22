---
name: case-05-siteid-spend
description: Phân tích spend theo site_id
---

# Case 5: Site_id đẩy spend (Site_id Spend Analysis)

## Trigger
- Khi user hỏi về site_id, placement, publisher impact đến spend và performance.

## Mục tiêu
Xác định các site_id nào đang đẩy spend nhiều nhất và hiệu quả của chúng.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        site_id,
        created_day,
        sum(cost) AS spend,
        sum(conversion) AS installs,
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
    round(spend, 2) AS spend,
    installs,
    round(revenue, 2) AS revenue,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY site_id, created_day
LIMIT 20
```

**Output columns:** `site_id`, `spend`, `installs`, `revenue`, `cpi`, `roas`

## Bước 2: Phân tích

- **Site_id spend > 20% nhưng ROAS < 100%**: Site này ngốn budget nhưng hiệu quả thấp → cân nhắc block
- **Site_id spend thấp nhưng ROAS cao**: Site chất lượng → cân nhắc tăng bid
- **Top 5 site_ids chiếm > 50% spend**: Phụ thuộc quá nhiều vào vài site → diversify

## Bước 3: Gợi ý

- Block site_ids có ROAS < 50% của trung bình
- Tăng bid cho site_ids có ROAS > 200%
- Review creative phù hợp với từng site_id

## Cảnh báo thresholds
- Single site_id spend % > 30% → cảnh báo phụ thuộc
- Site_id ROAS < 50% avg → cảnh báo kém hiệu quả
- Site_id CPI > 3x avg → cảnh báo CPI quá cao
