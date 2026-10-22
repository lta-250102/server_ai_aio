# Case 15: Campaign CPI lệch nhiều nhất

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định campaign nào trong network có CPI lệch nhiều nhất.

## Bước 1: Lấy data + Tính toán

```sql
-- CPI theo campaign với DoD delta
WITH campaign_cpi AS (
    SELECT 
        campaign,
        created_day,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(SUM(cost) / NULLIF(SUM(installs), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND media_source = '<media_source>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY campaign, created_day
)
SELECT 
    campaign,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY campaign ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY campaign ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY campaign ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM campaign_cpi
WHERE installs > 0
ORDER BY campaign, created_day
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- Tương tự case 13 cho campaign
- Chỉ đánh giá campaign đã có > 200 installs hoặc đã start > 7 ngày
- Campaign có CPI cao nhưng ROAS cũng cao → user chất lượng cao
- Campaign mới test → CPI chưa ổn định

## Bước 3: Gợi ý

- Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20% → báo UA → check tiếp geo (#16) và site_id
- Campaign CPI cao + ROAS thấp → xem xét giảm budget
- Campaign CPI thấp + ROAS cao → xem xét tăng budget

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi campaign có > 200 installs hoặc start > 7 ngày
