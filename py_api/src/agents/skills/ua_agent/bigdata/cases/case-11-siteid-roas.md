---
name: case-11-siteid-roas
description: Site_id ROAS thấp/cao
---

# Case 11: Site_id ROAS thấp/cao (Site_id ROAS)

## Trigger
- Khi user hỏi về ROAS theo site_id, placement nào có ROAS cao/thấp.

## Mục tiêu
Xác định site_ids có ROAS cao nhất/thấp nhất, tối ưu placement.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        site_id,
        created_day,
        sum(cost) AS spend,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
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
    round(revenue, 2) AS revenue,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY site_id, created_day
LIMIT 20
```

**Output columns:** `site_id`, `spend`, `revenue`, `installs`, `cpi`, `roas`

## Bước 2: Phân tích

- **Site_id ROAS > 200%**: Site rất hiệu quả → tăng bid
- **Site_id ROAS 100-200%**: Site hiệu quả → giữ nguyên
- **Site_id ROAS 50-100%**: Site hòa vốn/lỗ nhẹ → theo dõi
- **Site_id ROAS < 50%**: Site kém hiệu quả → cân nhắc block

## Bước 3: Gợi ý

- Tăng bid cho top 10 site_ids có ROAS cao nhất
- Block site_ids có ROAS < 50% của trung bình
- Review creative phù hợp với từng site_id

## Cảnh báo thresholds
- Site_id ROAS > 200% → gợi ý tăng bid
- Site_id ROAS 100-200% → giữ nguyên
- Site_id ROAS < 50% avg → cảnh báo block
