# Case 8: Network ảnh hưởng dòng tiền (LTV/ROAS)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Đánh giá phân bổ budget giữa các network có ổn chưa, network nào thu hồi vốn tốt nhất.

## Bước 1: Lấy data + Tính toán

```sql
-- LTV ROI (activity data) theo network
WITH network_metrics AS (
    SELECT 
        media_source,
        created_day,
        SUM(revenue) as revenue,
        SUM(cost) as cost
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY media_source, created_day
),
network_summary AS (
    SELECT 
        media_source,
        round(sum(revenue), 2) as total_revenue,
        round(sum(cost), 2) as total_cost,
        round((sum(revenue) - sum(cost)) / NULLIF(sum(cost), 0) * 100, 2) as ltv_roi_pct,
        round(sum(revenue) / NULLIF(sum(cost), 0) * 100, 2) as ltv_roas_pct,
        count() as days_active
    FROM network_metrics
    GROUP BY media_source
)
SELECT 
    media_source,
    total_revenue,
    total_cost,
    ltv_roi_pct,
    ltv_roas_pct,
    days_active
FROM network_summary
ORDER BY ltv_roi_pct DESC
```

**Output columns:** `media_source`, `total_revenue`, `total_cost`, `ltv_roi_pct` (%), `ltv_roas_pct` (%), `days_active`

## Bước 2: Phân tích

- Network mới test: ROI chưa ổn định nếu spend < $50 và installs < 50 → chưa vội đánh giá
- Xếp hạng LTV ROI từ cao → thấp, kết hợp tỷ trọng spend để tìm network ROI thấp + spend lớn (rủi ro cao)
- So sánh ROAS D0, D3, D7 theo từng ngày để xem trend
- Network có spend lớn nhưng ROI thấp → rủi ro cao nhất

## Bước 3: Gợi ý

- LTV ROI cao hơn trung bình + Retention tốt → xem xét scale
- ROAS D7 thấp hơn trung bình 20% + spend top 5 → phân tích xuống campaign (#9) + check Retention
- ROAS cao hơn trung bình + ổn định 5 ngày → đề xuất tăng budget/giảm goal để scale
- ROAS D0/D3/D7 có trend giảm → cảnh báo UA + check campaign (#9)

## Cảnh báo thresholds
- Network spend top 5 nhưng ROI âm → cảnh báo nghiêm trọng
- ROAS D7 giảm > 20% so với tuần trước → cảnh báo
