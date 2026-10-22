# Case 4: Geo thay đổi traffic

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định geo/quốc gia nào thay đổi traffic (spend + install) nhiều nhất trong game.

## Bước 1: Lấy data + Tính toán

```sql
WITH geo_cost AS (
    SELECT 
        country,
        created_day,
        SUM(cost) as geo_cost
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY country, created_day
),
total_cost AS (
    SELECT 
        created_day,
        SUM(geo_cost) as total_cost
    FROM geo_cost
    GROUP BY created_day
),
geo_sov AS (
    SELECT 
        gc.country,
        gc.created_day,
        round(gc.geo_cost, 2) as geo_cost,
        round(tc.total_cost, 2) as total_cost,
        round(gc.geo_cost / tc.total_cost * 100, 2) as sov_pct
    FROM geo_cost gc
    JOIN total_cost tc ON gc.created_day = tc.created_day
),
geo_sov_ranked AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY created_day ORDER BY sov_pct DESC) as rank
    FROM geo_sov
)
SELECT 
    country,
    created_day,
    geo_cost,
    total_cost,
    sov_pct,
    rank
FROM geo_sov_ranked
ORDER BY created_day, rank
LIMIT 50
```

**Output columns:** `country`, `created_day`, `geo_cost`, `total_cost`, `sov_pct` (% SOV), `rank`

## Bước 2: Phân tích

- Xác định sự thay đổi tỉ trọng spend và install của các geo
- Có geo nào mất traffic bất thường không?
- Top 10 geo spend nhiều nhất → theo dõi SOV trend
- SOV tăng/giảm > 15% so với cùng kì → cảnh báo

## Bước 3: Gợi ý

- Top spend/top install → report cho UA, suggest giải pháp đẩy mạnh
- Tăng trưởng organic → report với UA chú ý
- Geo giảm SOV > 15% → kiểm tra campaign, creative tại geo đó
