# Case 13: CPI game tăng/giảm

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định CPI trung bình của game có tăng/giảm và có hợp lý so với target không.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI daily với DoD delta
WITH daily_cpi AS (
    SELECT 
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY created_day
)
SELECT 
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (ORDER BY created_day)) / NULLIF(LAG(cpi) OVER (ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM daily_cpi
WHERE installs > 0
ORDER BY created_day
```

**Output columns:** `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

- `CPI` = Σ Cost / Σ Installs (theo ngày)
- `Δ CPI DoD` = (CPI Dx - CPI Dx-1) / CPI Dx-1
- `Δ CPI tuần` = (CPI tuần này - CPI tuần trước) / CPI tuần trước

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
