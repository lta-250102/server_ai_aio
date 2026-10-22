---
name: case-06-creative-spending
description: Creative spending nhiều nhất
---

# Case 6: Creative spending nhiều nhất (Top Creative by Spend)

## Trigger
- Khi user hỏi về creative performance, top creatives by spend, creative analysis.

## Mục tiêu
Xác định các creatives đang chi tiêu nhiều nhất và hiệu quả của chúng.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        creative_id,
        created_day,
        sum(cost) AS spend,
        sum(conversion) AS installs,
        sum(revenue) AS revenue
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND creative_id != ''
      AND creative_id != 'UNKNOWN'
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY creative_id, created_day
)
SELECT
    creative_id,
    created_day,
    round(spend, 2) AS spend,
    installs,
    round(revenue, 2) AS revenue,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY creative_id, created_day
LIMIT 20
```

**Output columns:** `creative_id`, `spend`, `installs`, `revenue`, `cpi`, `roas`

## Bước 2: Phân tích

- **Creative spend > 10% nhưng ROAS < 100%**: Creative này ngốn budget nhưng hiệu quả thấp → cân nhắc pause
- **Creative spend thấp nhưng ROAS cao**: Creative chất lượng → scale up
- **Top 5 creatives chiếm > 40% spend**: Phụ thuộc quá nhiều vào vài creatives → cần tạo mới

## Bước 3: Gợi ý

- Pause creatives có ROAS < 50% của trung bình
- Tăng budget cho creatives có ROAS > 200%
- Tạo thêm creatives mới để diversify và test

## Cảnh báo thresholds
- Single creative spend % > 20% → cảnh báo phụ thuộc
- Creative ROAS < 50% avg → cảnh báo kém hiệu quả
- Creative CPI > 3x avg → cảnh báo CPI quá cao
