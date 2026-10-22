# Case 16: Geo CPI lệch

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định geo nào trong campaign khiến CPI lệch.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI theo geo với DoD delta
WITH geo_cpi AS (
    SELECT 
        country,
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY country, created_day
)
SELECT 
    country,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY country ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY country ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY country ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM geo_cpi
WHERE installs > 0
ORDER BY country, created_day
```

**Output columns:** `country`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- Tương tự case 13 cho geo
- Chỉ đánh giá geo đã có > 50 installs
- Geo có CPI cao nhưng ROAS cũng cao → user chất lượng cao
- Geo mới → CPI chưa ổn định

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA + kết hợp check ROAS và RR
- Nếu ROAS và RR giảm quá 20% → check tiếp xuống site_id (#17)
- Geo CPI cao + ROAS thấp → xem xét giảm budget tại geo

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi geo có > 50 installs
