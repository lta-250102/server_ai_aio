# Case 1: Spend game tăng/giảm

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định trend spend (cost) của game trong 14 ngày gần nhất, so sánh 7 ngày gần nhất với 7 ngày trước.

## Bước 1: Lấy data + Tính toán

```sql
WITH daily_cost AS (
    SELECT 
        created_day,
        SUM(cost) as cost
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY created_day
)
SELECT 
    created_day,
    round(cost, 2) as cost,
    round(cost - LAG(cost) OVER (ORDER BY created_day), 2) as delta_abs,
    round(
        (cost - LAG(cost) OVER (ORDER BY created_day)) / NULLIF(LAG(cost) OVER (ORDER BY created_day), 0) * 100,
        2
    ) as delta_pct,
    round(cost - LAG(cost) OVER (ORDER BY created_day ROWS BETWEEN 6 PRECEDING AND 6 PRECEDING), 2) as delta_woy_abs,
    round(
        (cost - LAG(cost) OVER (ORDER BY created_day ROWS BETWEEN 6 PRECEDING AND 6 PRECEDING)) 
        / NULLIF(LAG(cost) OVER (ORDER BY created_day ROWS BETWEEN 6 PRECEDING AND 6 PRECEDING), 0) * 100,
        2
    ) as delta_woy_pct
FROM daily_cost
ORDER BY created_day
```

**Output columns:** `created_day`, `cost`, `delta_abs` (DoD), `delta_pct` (DoD%), `delta_woy_abs`, `delta_woy_pct` (WoW%)

## Bước 2: Phân tích

- **Trend tăng**: Cost tăng liên tục 2-3 ngày trở lên → game có khả năng trend đang tăng
- **Trend giảm**: Cost giảm liên tục → xác định game chủ động cut hay mất khả năng spend
- **Stable**: Trung bình 7 ngày gần nhất ≈ Trung bình 7 ngày trước đó (chênh lệch < 10%)
- **Single day spike**: Chỉ tăng/giảm 1 ngày rồi quay lại → chưa coi là trend
- **WoW (Week-over-Week)**: So sánh ngày hiện tại với cùng ngày tuần trước (7 ngày trước)

## Bước 3: Gợi ý

- Cost có trend tăng/giảm → kết hợp với ROAS (#7) và phân tích xuống media source (#2)
- Δ Cost DoD > 20% so với ngày trước → cảnh báo UA
- Δ Cost WoW > 20% so với cùng tuần trước → cảnh báo UA
- Stable → không có bất thường

## Cảnh báo thresholds
- Δ Cost DoD > 20% → cảnh báo UA
- Δ Cost WoW > 20% → cảnh báo UA
