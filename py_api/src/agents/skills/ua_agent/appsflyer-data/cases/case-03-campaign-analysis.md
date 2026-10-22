# Case 3: Campaign trong network biến động

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định campaign nào là nguyên nhân chính gây biến động cost trong network đang biến động.

## Bước 1: Lấy data + Tính toán

```sql
WITH campaign_cost AS (
    SELECT 
        campaign,
        created_day,
        SUM(cost) as network_cost
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
    round(cost, 2) as cost,
    round(cost - LAG(cost) OVER (PARTITION BY campaign ORDER BY created_day), 2) as delta_abs,
    round(
        (cost - LAG(cost) OVER (PARTITION BY campaign ORDER BY created_day)) 
        / NULLIF(LAG(cost) OVER (PARTITION BY campaign ORDER BY created_day), 0) * 100,
        2
    ) as delta_pct
FROM campaign_cost
ORDER BY campaign, created_day
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `cost`, `delta_abs` (DoD), `delta_pct` (DoD%)

**Lưu ý:** Cần thay `<media_source>` bằng network đang phân tích (ví dụ: `unityads_int`, `applovin_int`).

## Bước 2: Phân tích

- So sánh Δ Cost để xem campaign nào tăng/giảm bất thường so với cùng kì
- Xác định trend tương tự case 1 với cost của từng campaign
- Campaign chiếm > 30% total spend của network → campaign chủ đạo
- Campaign mới xuất hiện → kiểm tra creative, targeting

## Bước 3: Gợi ý

- Campaign có trend tăng/giảm → đánh giá thêm ROAS, phân tích xuống geo (#10)
- Tất cả campaign trong cùng network có cost giảm > 20% so với cùng kì → cảnh báo UA kiểm tra policy creative hoặc vấn đề với network
- Campaign đã start 3 ngày kể từ ngày tạo nhưng không có install hoặc cost < $50 daily → cảnh báo

## Cảnh báo thresholds
- Cost giảm > 20% so với cùng kì → cảnh báo UA
- Cost < $50 daily sau 3 ngày start → cảnh báo
