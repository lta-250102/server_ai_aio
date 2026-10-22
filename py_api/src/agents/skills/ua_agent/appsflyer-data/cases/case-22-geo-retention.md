# Case 22: Geo Retention thấp/cao bất thường

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định geo nào trong campaign có Retention thấp/cao bất thường.

**Lưu ý quan trọng:** Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng).

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention theo geo
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        country_code
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
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
        i.country_code,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
geo_retention AS (
    SELECT 
        country_code,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained,
        countIf(days_after = 3) as d3_retained,
        countIf(days_after = 7) as d7_retained
    FROM retention_calc
    GROUP BY country_code, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM geo_retention
    WHERE total_installs > 0
)
SELECT 
    gr.country_code,
    gr.install_date,
    gr.total_installs,
    round(gr.d0_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d0_pct,
    round(gr.d1_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d1_pct,
    round(gr.d3_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d3_pct,
    round(gr.d7_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d7_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (gr.d1_retained * 100.0 / NULLIF(gr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM geo_retention gr
CROSS JOIN avg_rr ar
WHERE gr.total_installs > 0
ORDER BY gr.install_date, deviation_pct
```

**Output columns:** `country_code`, `install_date`, `total_installs`, `rr_d0_pct`, `rr_d1_pct`, `rr_d3_pct`, `rr_d7_pct`, `avg_rr_d1`, `deviation_pct`

## Bước 2: Phân tích

- Đánh giá khi geo đã có > 50 installs
- List các geo có Δ RR trend tăng → suggest UA ưu tiên
- Geo có RR cao nhưng spend thấp → xem xét scale budget
- Geo có RR thấp nhưng spend cao → rủi ro cao

## Bước 3: Gợi ý

- Geo RR thấp kéo dài > 7 ngày hoặc biến động > 20% → kết hợp check ROAS → suggest UA remove hoặc giảm spend
- Geo RR cao trong top 5 + ROAS tăng trưởng → tiếp tục ưu tiên ngân sách dài hạn (đủ cohort D14/D28/D60 để đánh giá)
- Nếu đã có đủ số + ROAS D14/D28/D60 tốt → suggest scale thêm
- Tất cả campaign đều có RR giảm → cảnh báo UA check level network

## Cảnh báo thresholds
- Chỉ đánh giá khi geo có > 50 installs
- RR biến động > 20% → cảnh báo
- RR thấp kéo dài > 7 ngày → cảnh báo
