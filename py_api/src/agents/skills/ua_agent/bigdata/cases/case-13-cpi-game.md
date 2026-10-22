---
name: case-13-cpi-game
description: CPI game tăng/giảm
---

# Case 13: CPI game tăng/giảm (CPI Trend)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.

## Mục tiêu
Xác định CPI trung bình của game có tăng/giảm và có hợp lý so với target không.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH daily_agg AS (
    SELECT
        created_day,
        sum(cost) AS cost,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 13 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY created_day
)
SELECT
    created_day,
    round(cost, 2) AS cost,
    installs,
    round(cost / NULLIF(installs, 0), 4) AS cpi,
    round(
        (cost / NULLIF(installs, 0)) - LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day),
        4
    ) AS delta_cpi,
    round(
        ((cost / NULLIF(installs, 0)) - LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day))
        / NULLIF(LAG(cost / NULLIF(installs, 0), 1) OVER (ORDER BY created_day), 0) * 100,
        2
    ) AS delta_cpi_pct
FROM daily_agg
WHERE installs > 0
ORDER BY created_day
```

**Output columns:** `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- Xem 7 ngày gần nhất trend của CPI là gì
- Trend tương tự case 1 (spend trend)
- CPI tăng → network đang đắt hơn, có thể do competition tăng hoặc quality user giảm
- CPI giảm → network đang rẻ hơn, có thể do scale tốt hoặc quality user giảm

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA → check tiếp network (#14)
- CPI tăng nhưng ROAS cũng tăng → có thể chấp nhận (user chất lượng cao hơn)
- CPI tăng mà ROAS giảm → cảnh báo nghiêm trọng

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA → check tiếp network (#14)
- CPI tăng nhưng ROAS cũng tăng → có thể chấp nhận (user chất lượng cao hơn)
- CPI tăng mà ROAS giảm → cảnh báo nghiêm trọng

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
