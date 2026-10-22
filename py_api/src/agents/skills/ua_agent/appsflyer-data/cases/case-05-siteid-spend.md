# Case 5: Site_id nào đẩy spend

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định site_id nào trong campaign đang đẩy spend nhiều nhất.

## Bước 1: Lấy data + Tính toán

```sql
WITH site_cost AS (
    SELECT 
        campaign,
        publisher_id,
        created_day,
        SUM(cost) as cost,
        SUM(installs) as installs
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY campaign, publisher_id, created_day
)
SELECT 
    campaign,
    publisher_id,
    created_day,
    round(cost, 2) as cost,
    installs,
    round(cost - LAG(cost) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day), 2) as delta_cost,
    round(
        (cost - LAG(cost) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day)) 
        / NULLIF(LAG(cost) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day), 0) * 100,
        2
    ) as delta_pct,
    installs - LAG(installs) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day) as delta_installs,
    round(
        (installs - LAG(installs) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day)) 
        / NULLIF(LAG(installs) OVER (PARTITION BY campaign, publisher_id ORDER BY created_day), 0) * 100,
        2
    ) as delta_installs_pct
FROM site_cost
ORDER BY campaign, created_day
```

**Output columns:** `campaign`, `publisher_id`, `created_day`, `cost`, `installs`, `delta_cost`, `delta_pct` (DoD%), `delta_installs`, `delta_installs_pct`

**Lưu ý:**
- Không áp dụng cho Google, Facebook, TikTok (không có site_id)
- Với Facebook/Google: thay `publisher_id` bằng `media_source`

## Bước 2: Phân tích

- Xác định sự thay đổi tỉ trọng spend và install của các site ID
- Có site ID mới đang tăng spending hoặc install không?
- Có site ID nào mất/giảm traffic trong top 25 spending hoặc top 25 install không?
- Δ Cost DoD và Δ Install DoD > 20% → cảnh báo

## Bước 3: Gợi ý

- Biến động top spending/top install → cảnh báo UA
- Δ Cost DoD và Δ Install DoD > 20% → cảnh báo, kết hợp xem CPI, ROAS, RR
- Site ID mới top spend → kiểm tra chất lượng (RR, ROAS) trước khi scale

## Cảnh báo thresholds
- Δ Cost DoD hoặc Δ Install DoD > 20% → cảnh báo UA
