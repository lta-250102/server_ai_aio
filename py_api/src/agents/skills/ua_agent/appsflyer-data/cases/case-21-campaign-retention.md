# Case 21: Campaign Retention lệch nhiều

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định campaign nào trong network có Retention lệch nhiều.

**Lưu ý quan trọng:** Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng).

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention theo campaign
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        campaign_type,
        media_source
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND media_source = '<media_source>'
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
        i.campaign_type,
        i.media_source,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
campaign_retention AS (
    SELECT 
        campaign,
        campaign_type,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained,
        countIf(days_after = 3) as d3_retained,
        countIf(days_after = 7) as d7_retained
    FROM retention_calc
    GROUP BY campaign, campaign_type, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM campaign_retention
    WHERE total_installs > 0
)
SELECT 
    cr.campaign,
    cr.campaign_type,
    cr.install_date,
    cr.total_installs,
    round(cr.d0_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d0_pct,
    round(cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d1_pct,
    round(cr.d3_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d3_pct,
    round(cr.d7_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d7_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM campaign_retention cr
CROSS JOIN avg_rr ar
WHERE cr.total_installs > 0
ORDER BY cr.install_date, deviation_pct
```

**Output columns:** `campaign`, `campaign_type`, `install_date`, `total_installs`, `rr_d0_pct`, `rr_d1_pct`, `rr_d3_pct`, `rr_d7_pct`, `avg_rr_d1`, `deviation_pct`

## Bước 2: Phân tích

- Đánh giá khi campaign đã chạy > 3 ngày và có > 200 installs
- Campaign RR giảm đột ngột dù campaign network ổn định → targeting/audience bị thay đổi hoặc network tự mở rộng audience
- Check tiếp geo (#22)/site_id (#23). Nếu tất cả geo, site_id, creative đều giảm chung → do chất lượng campaign giảm

## Bước 3: Gợi ý

- Campaign RR thấp kéo dài > 3 ngày hoặc biến động > 20% → kết hợp check ROAS → giảm ưu tiên + check geo (#22)
- Campaign RR cao trong top 5 + ROAS tăng trưởng → tiếp tục ưu tiên ngân sách dài hạn
- Tất cả campaign đều có RR giảm → cảnh báo UA check level network
- Facebook/Tiktok/Google: RR thấp hơn 30% so với avg network → check ROAS và spending, nếu < 20% toàn bộ network → suggest off camp

## Cảnh báo thresholds
- Chỉ đánh giá khi campaign có > 200 installs và chạy > 3 ngày
- RR biến động > 20% → cảnh báo
- RR thấp kéo dài > 3 ngày → cảnh báo
- RR thấp hơn 30% so với avg network → suggest off camp (FB/Tiktok/Google)
