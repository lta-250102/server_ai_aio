# Case 23: Site_id Retention thấp/cao

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định site_id nào trong geo đang cho user có Retention thấp/cao.

**Lưu ý quan trọng:** Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng).

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention theo site_id
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        country_code,
        af_siteid
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
      AND country_code = '<country_code>'
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
        i.af_siteid,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
siteid_retention AS (
    SELECT 
        af_siteid,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained
    FROM retention_calc
    GROUP BY af_siteid, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM siteid_retention
    WHERE total_installs > 0
)
SELECT 
    sr.af_siteid,
    sr.install_date,
    sr.total_installs,
    round(sr.d0_retained * 100.0 / NULLIF(sr.total_installs, 0), 2) as rr_d0_pct,
    round(sr.d1_retained * 100.0 / NULLIF(sr.total_installs, 0), 2) as rr_d1_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (sr.d1_retained * 100.0 / NULLIF(sr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM siteid_retention sr
CROSS JOIN avg_rr ar
WHERE sr.total_installs > 0
ORDER BY sr.install_date, deviation_pct
```

**Output columns:** `af_siteid`, `install_date`, `total_installs`, `rr_d0_pct`, `rr_d1_pct`, `avg_rr_d1`, `deviation_pct`

## Bước 2: Phân tích

- RR D1 < 15% hoặc RR D1 < Avg campaign trên 50% → user cài xong rời đi ngay, không quay lại mua → dấu hiệu fraud/incentivized/click injection
- RR ổn định, tương đương mặt bằng chung → check thêm ROAS và spending
- Đánh giá khi site_id đã chạy > 7 ngày và có 20 installs trở lên

## Bước 3: Gợi ý

- Site ID có RR thấp hơn trung bình 30% kéo dài > 5 ngày → kết hợp check ROAS
  - Nếu ROAS cao → check fraud
  - Nếu ROAS thấp → suggest block
- Creative có RR rất thấp dù CPI tốt → check thêm ROAS
  - Nếu ROAS cao hơn avg → theo dõi thêm D14/D28
  - Nếu RR chênh > 20% mà ROAS không tốt hơn → suggest exclude khỏi campaign
  - Nếu RR chênh < 20% mà ROAS cao hơn 20% → chú ý theo dõi thêm

## Cảnh báo thresholds
- Chỉ đánh giá khi site_id có > 20 installs và chạy > 7 ngày
- RR D1 < 15% → dấu hiệu fraud mạnh
- RR thấp hơn avg 30% kéo dài > 5 ngày → cảnh báo
