# Case 7: ROAS/ROI game tăng/giảm

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định trend ROI của game trong 14 ngày gần nhất.

## Bước 1: Lấy data + Tính toán

```sql
WITH daily_metrics AS (
    SELECT 
        created_day,
        SUM(revenue) as revenue,
        SUM(cost) as cost
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
    GROUP BY created_day
)
SELECT 
    created_day,
    round(revenue, 2) as revenue,
    round(cost, 2) as cost,
    round((revenue - cost) / NULLIF(cost, 0) * 100, 2) as roi_pct,
    round(revenue / NULLIF(cost, 0) * 100, 2) as roas_pct,
    round(revenue - cost, 2) as profit
FROM daily_metrics
WHERE cost > 0
ORDER BY created_day
```

**Output columns:** `created_day`, `revenue`, `cost`, `roi_pct` (%), `roas_pct` (%), `profit`

- `ROI` = (revenue - cost) / cost × 100
- `ROAS` = revenue / cost × 100
- So sánh ROI với cùng kì tuần trước

## Bước 2: Phân tích

- Trend tương tự case 1 (spend trend)
- Xem 7 ngày gần nhất có trend tăng/giảm không
- So sánh với 7 ngày trước
- ROI tăng → hiệu quả spend đang cải thiện
- ROI giảm → spend đang kém hiệu quả hơn

## Bước 3: Gợi ý

- Mức độ cảnh báo Δ ROI tùy UA (phụ thuộc thể loại game và giai đoạn)
- Game có spend > $100 daily mà ROI > 30% → thông báo UA
- ROI có xu hướng tăng/giảm → kết hợp với trend spend (#1) để đánh giá scale
- ROI giảm liên tục 3 ngày → xem xét giảm budget hoặc tối ưu campaign

## Cảnh báo thresholds
- ROI giảm > 20% so với tuần trước → cảnh báo
- Spend > $100/ngày mà ROI < 0% → cảnh báo nghiêm trọng
