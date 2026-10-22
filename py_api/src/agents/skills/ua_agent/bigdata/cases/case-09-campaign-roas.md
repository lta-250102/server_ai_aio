---
name: case-09-campaign-roas
description: ROAS của campaign
---

# Case 9: ROAS của campaign (Campaign ROAS)

## Trigger
- Khi user hỏi về ROAS của từng campaign, so sánh ROAS giữa campaigns.

## Mục tiêu
Xác định ROAS của từng campaign, so sánh hiệu quả giữa các campaigns.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        campaign_id,
        created_day,
        sum(cost) AS spend,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY campaign_id, created_day
)
SELECT
    campaign_id,
    created_day,
    round(spend, 2) AS spend,
    round(revenue, 2) AS revenue,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY campaign_id, created_day
```

**Output columns:** `campaign_id`, `spend`, `revenue`, `installs`, `cpi`, `roas`

## Bước 2: Phân tích

- **Campaign ROAS > 200%**: Campaign rất hiệu quả → tăng budget
- **Campaign ROAS 100-200%**: Campaign hiệu quả → giữ nguyên hoặc tăng nhẹ
- **Campaign ROAS 50-100%**: Campaign hòa vốn/lỗ nhẹ → theo dõi sát
- **Campaign ROAS < 50%**: Campaign kém hiệu quả → cân nhắc pause

## Bước 3: Gợi ý

- Tăng budget cho top 3 campaigns có ROAS cao nhất
- Pause campaigns có ROAS < 50% của trung bình
- A/B test creative mới cho campaigns dưới trung bình

## Cảnh báo thresholds
- Campaign ROAS > 200% → gợi ý scale up
- Campaign ROAS 100-200% → giữ nguyên
- Campaign ROAS < 50% avg → cảnh báo kém hiệu quả
