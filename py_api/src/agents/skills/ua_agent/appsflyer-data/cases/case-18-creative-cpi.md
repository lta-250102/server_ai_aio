# Case 18: Creative CPI thấp/cao

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định creative (af_ad) nào đang cho CPI thấp/cao.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI theo creative với DoD delta
WITH creative_cpi AS (
    SELECT 
        ad,
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY ad, created_day
)
SELECT 
    ad,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY ad ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY ad ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY ad ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM creative_cpi
WHERE installs > 0
ORDER BY ad, created_day
```

**Output columns:** `ad`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

**Lưu ý:** Với `googleadwords_int`: thay `ad` bằng `ad_set`

## Bước 2: Phân tích

- Tương tự case 17 nhưng áp dụng cho creative (af_ad/af_adset)
- Chỉ đánh giá creative đã có > 20 installs hoặc đã chạy > 7 ngày
- Creative có CPI cao nhưng ROAS cũng cao → user chất lượng cao
- Creative mới → CPI chưa ổn định

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA + kết hợp check ROAS và RR
- Creative CPI cao + ROAS thấp → xem xét remove creative
- Creative CPI thấp + ROAS cao → xem xét scale creative

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi creative có > 20 installs hoặc chạy > 7 ngày
