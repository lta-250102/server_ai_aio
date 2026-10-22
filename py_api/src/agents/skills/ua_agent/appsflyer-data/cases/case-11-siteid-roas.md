# Case 11: Site_id ROAS thấp/cao

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định site_id nào trong geo đang cho traffic có ROAS thấp/cao.

## Bước 1: Lấy data + Tính toán

```sql
-- ROAS theo site_id
WITH siteid_roas AS (
    SELECT 
        publisher_id,
        created_day,
        round(SUM(revenue), 2) as revenue,
        round(SUM(cost), 2) as cost,
        SUM(installs) as installs,
        round(
            (SUM(revenue) - SUM(cost)) / NULLIF(SUM(cost), 0) * 100,
            2
        ) as roi_pct
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND country = '<country_code>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY publisher_id, created_day
),
avg_roi AS (
    SELECT AVG(roi_pct) as avg_roi
    FROM siteid_roas
    WHERE installs >= 20
)
SELECT 
    sr.publisher_id,
    sr.created_day,
    sr.revenue,
    sr.cost,
    sr.installs,
    sr.roi_pct,
    round(ar.avg_roi, 2) as avg_roi,
    round(
        (sr.roi_pct - ar.avg_roi) / NULLIF(ar.avg_roi, 0) * 100,
        2
    ) as deviation_pct
FROM siteid_roas sr
CROSS JOIN avg_roi ar
WHERE sr.installs >= 20
ORDER BY sr.created_day, deviation_pct
```

**Output columns:** `publisher_id`, `created_day`, `revenue`, `cost`, `installs`, `roi_pct`, `avg_roi`, `deviation_pct`

## Bước 2: Phân tích

- Lọc site_id có > 20 installs và > $20 trong cohort days
- ROAS D0, D7 cao hơn trung bình 20% → site_id tốt
- ROAS D0, D7 thấp hơn trung bình 20% → site_id kém
- ROAS chênh lệch đột ngột > 30% → kiểm tra bất thường, check RR

## Bước 3: Gợi ý

- ROAS tăng + RR ổn định 3 ngày → theo dõi thêm, nếu RR giảm đột ngột → nghi ngờ fraud, cảnh báo UA block site_id
- ROAS giảm đột ngột > 50% → suggest block site_id
- ROAS < Avg game 30% trong 3 ngày liên tiếp → check spending (#5), nếu trong top 25 → suggest block
- ROAS tăng + RR ổn định 3 ngày liên tiếp → suggest UA tăng bid, whitelist chạy camp

## Cảnh báo thresholds
- ROAS giảm > 50% đột ngột → suggest block
- ROAS < avg 30% trong 3 ngày liên tiếp → cảnh báo
