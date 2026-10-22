---
name: case-01-spend-trend
description: Spend trend 14 ngày, DoD/WoW delta
---

# Case 1: Spend game tăng/giảm (Spend Trend Analysis)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.

## Mục tiêu
Xác định trend spend (cost) của game trong 14 ngày gần nhất, so sánh 7 ngày gần nhất với 7 ngày trước đó.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH daily_spend AS (
    SELECT
        created_day,
        sum(cost) AS spend
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 13 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY created_day
    ORDER BY created_day
)
SELECT
    created_day,
    round(spend, 2) AS spend,
    round(spend - LAG(spend, 1) OVER (ORDER BY created_day), 2) AS delta_abs,
    round(
        (spend - LAG(spend, 1) OVER (ORDER BY created_day)) 
        / NULLIF(LAG(spend, 1) OVER (ORDER BY created_day), 0) * 100,
        2
    ) AS delta_pct,
    round(spend - LAG(spend, 7) OVER (ORDER BY created_day), 2) AS delta_woy_abs,
    round(
        (spend - LAG(spend, 7) OVER (ORDER BY created_day)) 
        / NULLIF(LAG(spend, 7) OVER (ORDER BY created_day), 0) * 100,
        2
    ) AS delta_woy_pct
FROM daily_spend
```

**Output columns:** `created_day`, `spend`, `delta_abs` (DoD), `delta_pct` (DoD%), `delta_woy_abs`, `delta_woy_pct` (WoW%)

## Bước 2: Phân tích

- **Trend tăng**: Spend tăng liên tục 2-3 ngày trở lên → game có khả năng trend đang tăng
- **Trend giảm**: Spend giảm liên tục → xác định game chủ động cut hay mất khả năng spend
- **Stable**: Trung bình 7 ngày gần nhất ≈ Trung bình 7 ngày trước đó (chênh lệch < 10%)
- **Single day spike**: Chỉ tăng/giảm 1 ngày rồi quay lại → chưa coi là trend
- **WoW (Week-over-Week)**: So sánh ngày hiện tại với cùng ngày tuần trước (7 ngày trước)

## Bước 3: Gợi ý

- Spend có trend tăng/giảm → kết hợp với ROAS (#7) và phân tích xuống network (#2)
- Δ Spend DoD > 20% so với ngày trước → cảnh báo UA
- Δ Spend WoW > 20% so với cùng tuần trước → cảnh báo UA

## Cảnh báo thresholds
- Δ Spend DoD > 20% → cảnh báo UA
- Δ Spend WoW > 20% → cảnh báo UA
