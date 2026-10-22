# Case 19: Retention game D0/D1/D3/D7 (Purchase-based)

## Trigger
- Khi user hỏi về retention, D0/D1/D3/D7, user retention, user quay lại mua hàng.

## Mục tiêu
Xác định Retention (D0/D1/D3/D7) của game có tăng/giảm so với target không.

**Lưu ý quan trọng:** Bảng `dwh_system.f_puller_appsflyer_raw_s2s` KHÔNG có cột `days_post_attribution`, `unique_users`, `af_session`, hay `af_conversion`. Retention được tính dựa trên **purchase events** (user cài app rồi quay lại mua hàng).

## Bước 1: Lấy data + Tính toán

```sql
-- Purchase-based retention D0-D7
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND install_time >= now() - interval 14 day
),
purchases AS (
    SELECT 
        appsflyer_id,
        toDate(event_time) as purchase_date,
        event_revenue_usd
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'af_purchase'
      AND event_time >= now() - interval 14 day
),
retention_calc AS (
    SELECT 
        i.appsflyer_id,
        i.install_date,
        p.purchase_date,
        p.event_revenue_usd,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
daily_retention AS (
    SELECT 
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained,
        countIf(days_after = 3) as d3_retained,
        countIf(days_after = 7) as d7_retained,
        round(sum(event_revenue_usd), 2) as total_revenue
    FROM retention_calc
    GROUP BY install_date
)
SELECT 
    install_date,
    total_installs,
    d0_retained,
    round(d0_retained * 100.0 / NULLIF(total_installs, 0), 2) as rr_d0_pct,
    d1_retained,
    round(d1_retained * 100.0 / NULLIF(total_installs, 0), 2) as rr_d1_pct,
    d3_retained,
    round(d3_retained * 100.0 / NULLIF(total_installs, 0), 2) as rr_d3_pct,
    d7_retained,
    round(d7_retained * 100.0 / NULLIF(total_installs, 0), 2) as rr_d7_pct,
    total_revenue
FROM daily_retention
ORDER BY install_date
```

**Output columns:** `install_date`, `total_installs`, `d0_retained`, `rr_d0_pct`, `d1_retained`, `rr_d1_pct`, `d3_retained`, `rr_d3_pct`, `d7_retained`, `rr_d7_pct`, `total_revenue`

- `Retention DN` = số user purchase ở ngày N sau install / tổng số install × 100
- D0 = ngày install, D1 = ngày sau install 1 ngày, D3 = 3 ngày, D7 = 7 ngày
- So với target RR (đối thủ, thể loại game, hoặc benchmark)
- Tính Δ RR giữa các cohort tuần gần đây so tuần trước

## Bước 2: Phân tích

- Chỉ so sánh cohort đã đủ "chín" (đủ N ngày trôi qua từ install)
- RR giảm dần qua các cohort gần đây → chất lượng user mới kém hơn hoặc có thay đổi sản phẩm
- RR ổn định/tăng → traffic và sản phẩm đang tốt
- D0 retention cao → user có xu hướng mua ngay sau khi install
- D7 retention cao → user trung thành, game có khả năng giữ chân tốt

## Bước 3: Gợi ý

- RR dưới target và giảm dần → phân tích xuống Network (#20) tìm nguồn user chất lượng kém; kiểm tra app update/creative update trùng thời điểm giảm
- RR tốt, ổn định → yên tâm scale spend
- RR D7 giảm nhưng D0 tăng → user mới mua nhưng không quay lại → cần cải thiện game loop
- RR tất cả giảm → cảnh báo UA check level app (bug/MO issue)

## Cảnh báo thresholds
- RR D1 giảm > 20% so với tuần trước → cảnh báo
- RR D7 giảm > 15% so với tuần trước → cảnh báo
- RR dưới target 2 ngày liên tiếp → cảnh báo
