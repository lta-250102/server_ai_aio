---
name: case-23-siteid-retention
description: Site_id Retention
---

# Case 23: Site_id Retention (Site_id-level Retention)

**Lưu ý:** Bigdata retention dùng gold user-day table với cohort pattern — D1/D3/D7 retention theo dimension.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
WITH base AS (
    SELECT 
        mmp_adset_id,
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
      AND mmp_adset_id != ''
      AND mmp_adset_id != 'UNKNOWN'
    GROUP BY mmp_adset_id, install_day
)
SELECT 
    mmp_adset_id AS site_id,
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

- **Site_id rev_per_install cao**: Site có user value cao → tăng bid
- **Site_id rev_per_install thấp**: Site có user value thấp → cân nhắc giảm bid
- **Site_id ROAS < 100%**: Site đang lỗ → xem lại hoặc block

## Bước 3: Gợi ý

- Tăng bid cho site_ids có rev_per_install cao nhất
- Giảm bid cho site_ids có rev_per_install thấp nhất
- Review creative phù hợp với từng site_id

## Cảnh báo thresholds
- Site_id ROAS < 50% avg → cảnh báo kém hiệu quả
- Site_id rev_per_install < 0.5x avg → cảnh báo user quality thấp

## Ghi chú schema
- Để có true retention analysis (D1/D3/D7), cần thêm `site_id` vào `f_puller_ua_cohort` UNIQUE KEY
- Hiện tại cohort table chỉ có grain ở cấp `campaign_id` + `location`
