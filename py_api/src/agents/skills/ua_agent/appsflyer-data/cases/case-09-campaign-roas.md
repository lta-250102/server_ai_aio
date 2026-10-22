# Case 9: ROAS của campaign

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Đánh giá ROAS của từng campaign, xem có allocate budget giữa các campaign ổn chưa.

## Bước 1: Lấy data + Tính toán

```sql
-- ROAS theo campaign
WITH campaign_roas AS (
    SELECT 
        campaign,
        created_day,
        round(SUM(revenue), 2) as revenue,
        round(SUM(cost), 2) as cost,
        round(
            (SUM(revenue) - SUM(cost)) / NULLIF(SUM(cost), 0) * 100,
            2
        ) as roi_pct
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
    revenue,
    cost,
    roi_pct
FROM campaign_roas
ORDER BY campaign, created_day
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `revenue`, `cost`, `roi_pct`

## Bước 2: Phân tích

- Xếp hạng campaign trong từng network theo ROAS cao → thấp, kết hợp tỷ trọng spend
- Campaign có spend > 30% total network spend → campaign chủ đạo
- Campaign ROI < 0% → đang lỗ
- Campaign ROI tăng liên tục 3 ngày → đang cải thiện

## Bước 3: Gợi ý

**Facebook, TikTok, Google:**
- ROAS campaign < 30% trong 3 ngày liên tiếp so với ROAS trung bình game → thống kê cost_cohort report UA
- Spending < 30% → suggest tắt campaign
- Spending > 30% → check geo (#10)

**Các mạng khác:**
- ROAS có trend giảm/tăng trong 3 ngày liên tiếp hoặc thay đổi > 20% → phân tích xuống geo (#10) và site_id (#11)
- Campaign ROI cao + spend tăng → scale thêm
- Campaign ROI âm + spend lớn → xem xét pause

## Cảnh báo thresholds
- ROAS < 30% trong 3 ngày liên tiếp → cảnh báo
- Campaign spend > 30% total network nhưng ROI âm → cảnh báo nghiêm trọng
