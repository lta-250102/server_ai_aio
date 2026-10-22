# Case 17: Site_id CPI thấp/cao bất thường

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định site_id nào đang cho CPI thấp/cao bất thường.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI theo site_id với DoD delta
WITH siteid_cpi AS (
    SELECT 
        publisher_id,
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY publisher_id, created_day
)
SELECT 
    publisher_id,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY publisher_id ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY publisher_id ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY publisher_id ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM siteid_cpi
WHERE installs > 0
ORDER BY publisher_id, created_day
```

**Output columns:** `publisher_id`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- Tương tự case 13 cho site_id
- Chỉ đánh giá site_id đã có > 20 installs hoặc đã có traffic > 5 ngày
- Site_id có CPI cao nhưng ROAS cũng cao → user chất lượng cao
- Site_id mới → CPI chưa ổn định

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA + kết hợp check ROAS và RR
- Nếu ROAS và RR giảm quá 20% → suggest UA block hoặc hạ bid
- Δ CPI DoD tăng đột ngột > 50% → cảnh báo và suggest block site_id
- Site_id CPI cao + ROAS thấp → xem xét block

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Δ CPI DoD > 50% → suggest block site_id
- Chỉ đánh giá khi site_id có > 20 installs hoặc traffic > 5 ngày
