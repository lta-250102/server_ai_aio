---
name: case-24-creative-retention
description: Creative Retention
---

# Case 24: Creative Retention (Creative-level Retention)

**Lưu ý:** Bigdata retention dùng gold user-day table với cohort pattern — D1/D3/D7 retention theo dimension.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
WITH base AS (
    SELECT 
        mmp_ad_id,
        install_day,
        uniqExact(account_id) AS total_installs,
        uniqExactIf(account_id, created_day = install_day + 1) AS d1_retained,
        uniqExactIf(account_id, created_day = install_day + 3) AS d3_retained,
        uniqExactIf(account_id, created_day = install_day + 7) AS d7_retained
    FROM dwh_system.f_summarised_user_daily_v2_utc
    WHERE package_name = '<package_name>'
      AND install_day BETWEEN today() - INTERVAL 14 DAY AND today() - INTERVAL 7 DAY
      AND created_day BETWEEN today() - INTERVAL 14 DAY AND today()
      AND install_day IS NOT NULL
      AND mmp_ad_id != ''
      AND mmp_ad_id != 'UNKNOWN'
    GROUP BY mmp_ad_id, install_day
)
SELECT 
    mmp_ad_id AS creative,
    install_day AS cohort_day,
    total_installs,
    d1_retained,
    round(d1_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d1_pct,
    d3_retained,
    round(d3_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d3_pct,
    d7_retained,
    round(d7_retained * 100.0 / NULLIF(total_installs, 0), 2) AS rr_d7_pct
FROM base
WHERE total_installs > 0
ORDER BY install_day
```

**Output columns:** `cohort_day`, `total_installs`, `d1_retained`, `rr_d1_pct`, `d3_retained`, `rr_d3_pct`, `d7_retained`, `rr_d7_pct`

## Bước 2: Phân tích

- **Creative rev_per_install cao**: Creative có user value cao → scale up
- **Creative rev_per_install thấp**: Creative có user value thấp → cân nhắc pause
- **Creative ROAS < 100%**: Creative đang lỗ → xem lại hoặc pause

## Bước 3: Gợi ý

- Tăng budget cho creatives có rev_per_install cao nhất
- Giảm budget cho creatives có rev_per_install thấp nhất
- Tạo thêm creatives mới dựa trên top performers

## Cảnh báo thresholds
- Creative ROAS < 50% avg → cảnh báo kém hiệu quả
- Creative rev_per_install < 0.5x avg → cảnh báo user quality thấp

## Ghi chú schema
- Để có true retention analysis (D1/D3/D7), cần thêm `creative_id` vào `f_puller_ua_cohort` UNIQUE KEY
- Hiện tại cohort table chỉ có grain ở cấp `campaign_id` + `country`
