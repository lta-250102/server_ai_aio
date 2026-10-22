# Case 2: Phân bổ budget theo media source

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Đánh giá phân bổ budget giữa các network có ổn không, tìm network tăng/giảm bất thường.

## Bước 1: Lấy data + Tính toán

```sql
WITH network_cost AS (
    SELECT 
        media_source,
        created_day,
        SUM(cost) as network_cost
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY media_source, created_day
),
total_cost AS (
    SELECT 
        created_day,
        SUM(network_cost) as total_cost
    FROM network_cost
    GROUP BY created_day
),
network_sov AS (
    SELECT 
        nc.media_source,
        nc.created_day,
        round(nc.network_cost, 2) as network_cost,
        round(tc.total_cost, 2) as total_cost,
        round(nc.network_cost / tc.total_cost * 100, 2) as sov_pct
    FROM network_cost nc
    JOIN total_cost tc ON nc.created_day = tc.created_day
),
network_sov_ranked AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY created_day ORDER BY sov_pct DESC) as rank
    FROM network_sov
)
SELECT 
    media_source,
    created_day,
    network_cost,
    total_cost,
    sov_pct,
    rank
FROM network_sov_ranked
ORDER BY created_day, rank
```

**Output columns:** `media_source`, `created_day`, `network_cost`, `total_cost`, `sov_pct` (% SOV), `rank`

## Bước 2: Phân tích

- **Top spend last 7 days** so sánh với top spend cùng kì tuần trước → có thay đổi không?
- **SOV tăng/giảm bất thường**: Network nào có SOV tăng/giảm > 15% so với cùng kì → cảnh báo
- **Trend**: Áp dụng tương tự case 1 cho từng media source
- **Network mới xuất hiện**: Network nào mới xuất hiện trong top 5 → đánh giá chất lượng

## Bước 3: Gợi ý

- Network tăng → đánh giá CPI + ROAS network (#8) → đề xuất đẩy budget thêm
- Network giảm > 15% so với cùng kì → cảnh báo UA, kiểm tra integration, trạng thái tài khoản, daily budget
- Tất cả media source giảm đồng loạt → cảnh báo UA check ở level app
- Network mới top spend → kiểm tra chất lượng user (RR, ROAS) trước khi đẩy budget

## Cảnh báo thresholds
- SOV network giảm > 15% so với cùng kì → cảnh báo UA
- Tất cả network giảm → cảnh báo UA check level app
