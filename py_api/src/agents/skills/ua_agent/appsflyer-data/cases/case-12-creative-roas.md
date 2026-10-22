# Case 12: Creative ROAS tốt/xấu

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định creative (af_ad) nào đang thu hút traffic có ROAS tốt/xấu.

## Bước 1: Lấy data + Tính toán

```sql
-- ROAS theo ad (trừ networks không có ad)
WITH creative_roas AS (
    SELECT 
        ad,
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
      AND media_source NOT IN ('greedygam7_int', 'mintegral_int', 'tapjoy_int', 'mobvista_int', 'googleadwords_int')
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY ad, created_day
),
avg_roi AS (
    SELECT AVG(roi_pct) as avg_roi
    FROM creative_roas
    WHERE installs >= 50
)
SELECT 
    cr.ad,
    cr.created_day,
    cr.revenue,
    cr.cost,
    cr.installs,
    cr.roi_pct,
    round(ar.avg_roi, 2) as avg_roi,
    round(
        (cr.roi_pct - ar.avg_roi) / NULLIF(ar.avg_roi, 0) * 100,
        2
    ) as deviation_pct
FROM creative_roas cr
CROSS JOIN avg_roi ar
WHERE cr.installs >= 50
ORDER BY cr.created_day, deviation_pct
```

**Output columns:** `ad`, `created_day`, `revenue`, `cost`, `installs`, `roi_pct`, `avg_roi`, `deviation_pct`

**Lưu ý:** Với `googleadwords_int`: thay `ad` bằng `ad_set`

## Bước 2: Phân tích

- Lọc af_ad có > 50 installs trong cohort days
- ROAS D0, D7 cao hơn trung bình 20% → creative tốt
- ROAS D0, D7 thấp hơn trung bình 20% → creative kém
- Creative chạy > 21 ngày có install < 100 hoặc ROAS < 30% so với avg campaign → report UA

## Bước 3: Gợi ý

- ROAS kém + spending ở #6 cũng kém → suggest remove khỏi campaign
- ROAS cao ổn định + spending top 5 trên 1 tuần → suggest UA chú ý và nhân bản creative
- Creative chạy > 21 ngày có ROAS thấp → check spending (#6), nếu spending thấp ở top 30% → suggest remove

## Cảnh báo thresholds
- ROAS < avg 30% trong 3 ngày liên tiếp → cảnh báo
- Creative chạy > 21 ngày mà ROAS < 30% → suggest remove
