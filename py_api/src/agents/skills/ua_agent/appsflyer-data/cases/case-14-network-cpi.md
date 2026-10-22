# Case 14: Network CPI cao/thấp bất thường

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định network nào đang có CPI cao/thấp bất thường.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI theo network với DoD delta
WITH network_cpi AS (
    SELECT 
        media_source,
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY media_source, created_day
)
SELECT 
    media_source,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY media_source ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY media_source ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY media_source ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM network_cpi
WHERE installs > 0
ORDER BY media_source, created_day
```

**Output columns:** `media_source`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- Tương tự case 13 nhưng áp dụng cho từng media_source
- Chỉ đánh giá network đã có > 200 installs hoặc đã start > 7 ngày
- Network mới test (< 200 installs) → CPI chưa ổn định, cần theo dõi thêm
- Network có CPI cao nhưng ROAS cũng cao → user chất lượng cao

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA → check tiếp campaign (#15)
- Network CPI cao + ROAS thấp → xem xét giảm budget
- Network CPI thấp + ROAS cao → xem xét tăng budget

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi network có > 200 installs hoặc start > 7 ngày
