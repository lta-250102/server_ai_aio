---
name: case-15-campaign-cpi
description: Campaign CPI lệch
---

# Case 15: Campaign CPI lệch (Campaign CPI)

## Trigger
- Khi user hỏi về CPI theo campaign, campaign nào có CPI bất thường.

## Mục tiêu
Xác định campaigns có CPI cao nhất/thấp nhất, so sánh hiệu quả chi phí.

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
    spend,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    revenue,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY campaign_id, created_day
```

**Output columns:** `campaign_id`, `spend`, `installs`, `cpi`, `revenue`, `roas`

## Bước 2: Phân tích

- **Campaign CPI thấp nhưng ROAS thấp**: Campaign rẻ nhưng user chất lượng thấp → cân nhắc
- **Campaign CPI cao nhưng ROAS cao**: Campaign đắt nhưng user chất lượng cao → chấp nhận
- **Campaign CPI cao mà ROAS thấp**: Campaign vừa đắt vừa kém hiệu quả → pause

## Bước 3: Gợi ý

- Tăng budget cho campaigns có CPI thấp và ROAS cao
- Giảm budget cho campaigns có CPI cao và ROAS thấp
- A/B test creative mới cho campaigns có CPI cao

## Cảnh báo thresholds
- Campaign CPI > 2x avg → cảnh báo CPI cao
- Campaign CPI < 0.5x avg mà ROAS < 100% → cảnh báo user chất lượng thấp
