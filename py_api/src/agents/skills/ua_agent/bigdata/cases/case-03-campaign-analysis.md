---
name: case-03-campaign-analysis
description: Phân tích campaign trong network
---

# Case 3: Campaign trong network biến động (Campaign Analysis)

## Trigger
- Khi user hỏi về campaign performance, biến động campaign, so sánh campaigns trong cùng network.

## Mục tiêu
Phân tích hiệu quả của các campaign trong một network cụ thể, xác định top/bottom performers.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        campaign_id,
        created_day,
        sum(cost) AS spend,
        sum(conversion) AS installs,
        sum(revenue) AS revenue
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
    installs,
    round(revenue, 2) AS revenue,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY campaign_id, created_day
```

**Output columns:** `campaign_id`, `spend`, `installs`, `revenue`, `cpi`, `roas`

## Bước 2: Phân tích

- **Campaign spend > 50% trong network**: Tập trung quá nhiều vào 1 campaign → risk cao
- **Campaign CPI > 2x trung bình network**: CPI quá cao → xem lại targeting/creative
- **Campaign ROAS < 50% của trung bình network**: Hiệu quả thấp → cân nhắc pause

## Bước 3: Gợi ý

- Tăng budget cho campaign có ROAS cao nhất
- Pause hoặc giảm budget cho campaign có ROAS thấp nhất
- A/B test creative mới cho các campaign dưới trung bình

## Cảnh báo thresholds
- Campaign spend % > 50% → cảnh báo tập trung
- Campaign CPI > 2x avg → cảnh báo CPI cao
- Campaign ROAS < 50% avg → gợi ý pause
