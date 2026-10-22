# Case 6: Creative spending nhiều nhất

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định creative (af_ad) nào đang có spending và traffic nhiều nhất.

## Bước 1: Lấy data + Tính toán

```sql
-- Với networks có ad (trừ greedygam7_int, mintegral_int, tapjoy_int, mobvista_int, googleadwords_int)
WITH creative_cost AS (
    SELECT 
        campaign,
        ad,
        created_day,
        SUM(cost) as cost,
        SUM(installs) as installs
    FROM dwh_system.f_puller_appsflyer_master
    WHERE package_name = '<package_name>'
      AND media_source NOT IN ('greedygam7_int', 'mintegral_int', 'tapjoy_int', 'mobvista_int', 'googleadwords_int')
      AND created_day >= today() - interval 14 day
      AND cost IS NOT NULL
    GROUP BY campaign, ad, created_day
),
creative_ranked AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY created_day ORDER BY cost DESC) as rank
    FROM creative_cost
)
SELECT 
    campaign,
    ad,
    created_day,
    round(cost, 2) as cost,
    installs,
    rank,
    round(cost - LAG(cost) OVER (PARTITION BY campaign, ad ORDER BY created_day), 2) as delta_cost,
    round(
        (cost - LAG(cost) OVER (PARTITION BY campaign, ad ORDER BY created_day)) 
        / NULLIF(LAG(cost) OVER (PARTITION BY campaign, ad ORDER BY created_day), 0) * 100,
        2
    ) as delta_pct
FROM creative_ranked
ORDER BY created_day, rank
```

**Output columns:** `campaign`, `ad`, `created_day`, `cost`, `installs`, `rank`, `delta_cost`, `delta_pct` (DoD%)

**Lưu ý:**
- Với `googleadwords_int`: thay `ad` bằng `ad_set`
- Networks không có ad: `greedygam7_int`, `mintegral_int`, `tapjoy_int`, `mobvista_int`, `googleadwords_int`

## Bước 2: Phân tích

- Xác định sự thay đổi tỉ trọng spend và install của các af_ad
- Có af_ad mới đang tăng spending hoặc install không?
- Có af_ad nào mất/giảm traffic trong top 10 spending hoặc top 10 install không?
- Δ Cost DoD và Δ Install DoD > 20% → cảnh báo

## Bước 3: Gợi ý

- Biến động top spending/top install → thông báo UA
- Δ Cost DoD và Δ Install DoD > 20% → cảnh báo UA, tổng hợp CPI, ROAS, RR
- af_ad chạy > 3 tuần nhưng spending vẫn thuộc top 10 creative spending thấp nhất → suggest UA tối ưu
- Creative top spend + ROAS tốt → nhân bản creative

## Cảnh báo thresholds
- Δ Cost DoD > 20% → cảnh báo UA
