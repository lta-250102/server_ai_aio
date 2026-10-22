---
name: case-18-creative-cpi
description: Creative CPI thấp/cao
---

# Case 18: Creative CPI thấp/cao (Creative CPI)

## Trigger
- Khi user hỏi về CPI theo creative, creative nào có CPI thấp/cao.

## Mục tiêu
Xác định creatives có CPI cao nhất/thấp nhất, tối ưu creative cost.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        creative_id,
        created_day,
        sum(conversion) AS installs,
        sum(cost) AS spend,
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
    installs,
    spend,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    revenue,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY creative_id, created_day
LIMIT 20
```

**Output columns:** `creative_id`, `installs`, `spend`, `cpi`, `revenue`, `roas`

## Bước 2: Phân tích

- **Creative CPI thấp nhưng ROAS thấp**: Creative rẻ nhưng user chất lượng thấp → cân nhắc
- **Creative CPI cao nhưng ROAS cao**: Creative đắt nhưng user chất lượng cao → chấp nhận
- **Creative CPI cao mà ROAS thấp**: Creative vừa đắt vừa kém hiệu quả → pause

## Bước 3: Gợi ý

- Tăng budget cho creatives có CPI thấp và ROAS cao
- Giảm budget cho creatives có CPI cao và ROAS thấp
- Tạo thêm creatives mới dựa trên top performers

## Cảnh báo thresholds
- Creative CPI > 2x avg → cảnh báo CPI cao
- Creative CPI < 0.5x avg mà ROAS < 100% → cảnh báo user chất lượng thấp
