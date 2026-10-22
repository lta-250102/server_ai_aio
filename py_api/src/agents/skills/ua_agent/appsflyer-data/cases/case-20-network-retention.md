# Case 20: Network Retention tốt/kém

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định network nào đang mang lại user có Retention tốt/kém.

**Lưu ý quan trọng:** Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng), không phải session data.

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention theo network
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        media_source
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
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
        i.media_source,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
network_retention AS (
    SELECT 
        media_source,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained,
        countIf(days_after = 3) as d3_retained,
        countIf(days_after = 7) as d7_retained
    FROM retention_calc
    GROUP BY media_source, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM network_retention
    WHERE total_installs > 0
)
SELECT 
    nr.media_source,
    nr.install_date,
    nr.total_installs,
    nr.d0_retained,
    round(nr.d0_retained * 100.0 / NULLIF(nr.total_installs, 0), 2) as rr_d0_pct,
    nr.d1_retained,
    round(nr.d1_retained * 100.0 / NULLIF(nr.total_installs, 0), 2) as rr_d1_pct,
    nr.d3_retained,
    round(nr.d3_retained * 100.0 / NULLIF(nr.total_installs, 0), 2) as rr_d3_pct,
    nr.d7_retained,
    round(nr.d7_retained * 100.0 / NULLIF(nr.total_installs, 0), 2) as rr_d7_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (nr.d1_retained * 100.0 / NULLIF(nr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM network_retention nr
CROSS JOIN avg_rr ar
WHERE nr.total_installs > 0
ORDER BY nr.install_date, deviation_pct
```

**Output columns:** `media_source`, `install_date`, `total_installs`, `rr_d0_pct`, `rr_d1_pct`, `rr_d3_pct`, `rr_d7_pct`, `avg_rr_d1`, `deviation_pct`

## Bước 2: Phân tích

- Network RR thấp hơn hẳn mặt bằng chung dù CPI/ROAS cao hơn → check fraud
- Network RR cao → nguồn user chất lượng, xem xét ưu tiên thêm
- Chỉ đánh giá khi có > 200 installs mới có ý nghĩa thống kê
- Network mới test → RR chưa ổn định

## Bước 3: Gợi ý

- Network RR thấp kéo dài > 7 ngày hoặc biến động đột ngột > 20% → kết hợp check ROAS → giảm ưu tiên + check campaign (#21)
- Network RR cao trong top 5 + ROAS tăng trưởng qua các cohort → tiếp tục ưu tiên ngân sách dài hạn
- Tất cả network đều có RR giảm → cảnh báo UA check level app (bug/MO issue)
- Network có RR cao nhưng spend thấp → xem xét scale budget

## Cảnh báo thresholds
- Chỉ đánh giá khi network có > 200 installs
- RR biến động > 20% → cảnh báo
- RR thấp kéo dài > 7 ngày → cảnh báo
