# Case 24: Creative Retention thấp/cao

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định creative (af_ad) nào đang thu hút user có Retention thấp/cao.

**Lưu ý quan trọng:** Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng).

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention theo af_ad (trừ networks không có af_ad)
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        af_ad
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
      AND media_source NOT IN ('greedygam7_int', 'mintegral_int', 'tapjoy_int', 'mobvista_int', 'googleadwords_int')
      AND install_time >= now() - interval 14 day
),
purchases AS (
    SELECT 
        appsflyer_id,
        toDate(event_time) as purchase_date
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'af_purchase'
      AND event_time >= now() - interval 14 day
),
retention_calc AS (
    SELECT 
        i.appsflyer_id,
        i.install_date,
        i.campaign,
        i.af_ad,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
creative_retention AS (
    SELECT 
        af_ad,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained
    FROM retention_calc
    GROUP BY af_ad, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM creative_retention
    WHERE total_installs > 0
)
SELECT 
    cr.af_ad,
    cr.install_date,
    cr.total_installs,
    round(cr.d0_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d0_pct,
    round(cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d1_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM creative_retention cr
CROSS JOIN avg_rr ar
WHERE cr.total_installs > 0
ORDER BY cr.install_date, deviation_pct
```

**Output columns:** `af_ad`, `install_date`, `total_installs`, `rr_d0_pct`, `rr_d1_pct`, `avg_rr_d1`, `deviation_pct`

**Lưu ý:** Với `googleadwords_int`: thay `af_ad` bằng `af_adset`

## Bước 2: Phân tích

- Creative fake thường RR rất thấp dù CPI tốt
- Creative thể hiện đúng gameplay, đúng đối tượng → RR tốt và bền theo thời gian
- Creative có trend spending tăng, CPI và ROAS chênh < 10% so với tổng thể game → creative tốt
- Đánh giá khi creative đã chạy > 7 ngày và có 20 installs trở lên

## Bước 3: Gợi ý

- Creative có RR rất thấp dù CPI tốt → check thêm ROAS
  - Nếu ROAS cao hơn avg → theo dõi thêm D14/D28
  - Nếu RR chênh > 20% mà ROAS không tốt hơn → suggest exclude khỏi campaign
  - Nếu RR chênh < 20% mà ROAS cao hơn 20% → chú ý theo dõi thêm
- Creative có RR và ROAS tốt, spending trong top 5 → suggest UA nhân bản
- Creative chạy > 21 ngày có RR thấp → check thêm spending (#6), nếu spending thấp ở top 30% → suggest remove

## Cảnh báo thresholds
- Chỉ đánh giá khi creative có > 20 installs và chạy > 7 ngày
- RR rất thấp dù CPI tốt → dấu hiệu creative fake
- RR thấp kéo dài > 21 ngày → suggest remove
