---
name: case-14-network-cpi
description: Network CPI cao/thấp
---

# Case 14: Network CPI cao/thấp (Network CPI)

## Trigger
- Khi user hỏi về CPI theo network, network nào có CPI cao/thấp bất thường.

## Mục tiêu
So sánh CPI giữa các network, xác định network nào đắt nhất/rẻ nhất.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        network_code,
        created_day,
        sum(cost) AS spend,
        sum(conversion) AS installs,
        sum(revenue) AS revenue
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY network_code, created_day
)
SELECT
    network_code,
    created_day,
    spend,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    revenue,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY network_code, created_day
```

**Output columns:** `network_code`, `spend`, `installs`, `cpi`, `revenue`, `roas`

## Bước 2: Phân tích

- **Network CPI thấp nhưng ROAS thấp**: Network rẻ nhưng user chất lượng thấp → cân nhắc
- **Network CPI cao nhưng ROAS cao**: Network đắt nhưng user chất lượng cao → chấp nhận
- **Network CPI cao mà ROAS thấp**: Network vừa đắt vừa kém hiệu quả → giảm budget

## Bước 3: Gợi ý

- Tăng budget cho network có CPI thấp và ROAS cao
- Giảm budget cho network có CPI cao và ROAS thấp
- Theo dõi CPI theo thời gian để phát hiện trend

## Cảnh báo thresholds
- Network CPI > 2x avg → cảnh báo CPI cao
- Network CPI < 0.5x avg mà ROAS < 100% → cảnh báo user chất lượng thấp
