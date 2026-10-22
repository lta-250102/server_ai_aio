# Case 10: Geo nào có ROAS lệch so với trung bình

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định geo nào trong campaign có ROAS cao/thấp hơn trung bình.

## Bước 1: Lấy data + Tính toán

```sql
-- ROAS theo geo
WITH geo_roas AS (
    SELECT 
        country,
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
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY country, created_day
),
avg_roi AS (
    SELECT AVG(roi_pct) as avg_roi
    FROM geo_roas
    WHERE installs >= 50
)
SELECT 
    gr.country,
    gr.created_day,
    gr.revenue,
    gr.cost,
    gr.installs,
    gr.roi_pct,
    round(ar.avg_roi, 2) as avg_roi,
    round(
        (gr.roi_pct - ar.avg_roi) / NULLIF(ar.avg_roi, 0) * 100,
        2
    ) as deviation_pct
FROM geo_roas gr
CROSS JOIN avg_roi ar
WHERE gr.installs >= 50
ORDER BY gr.created_day, deviation_pct
```

**Output columns:** `country_code`, `created_day`, `revenue`, `cost`, `installs`, `roi_pct`, `avg_roi`, `deviation_pct`

## Bước 2: Phân tích

- Lọc geo có > 50 installs và > $20 trong cohort days
- ROAS D0, D7 cao hơn trung bình 20% → geo tốt
- ROAS D0, D7 thấp hơn trung bình 20% → geo kém
- Geo có spend lớn nhưng ROI âm → rủi ro cao

## Bước 3: Gợi ý

**Facebook, TikTok, Google:**
- ROAS geo < 30% trong 3 ngày liên tiếp so với ROAS trung bình game → suggest exclude geo khỏi campaign

**Các mạng khác:**
- ROAS geo < 30% trong 3 ngày liên tiếp → suggest nâng goal
- ROAS geo > 30% trong 3 ngày liên tiếp → suggest hạ goal scale thêm

## Cảnh báo thresholds
- ROAS < 30% trong 3 ngày liên tiếp → cảnh báo
- Geo spend > 20% total nhưng ROI âm → cảnh báo nghiêm trọng
