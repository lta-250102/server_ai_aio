---
name: case-20-network-retention
description: Network Retention
---

# Case 20: Network Retention (Network-level Retention)

## Trigger
- Khi user hỏi về retention theo network, network nào có user retention tốt nhất.

## Mục tiêu
So sánh retention giữa các network, xác định network nào có user quality cao nhất.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
WITH base AS (
    SELECT 
        mmp_media_source,
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
      AND mmp_media_source != ''
      AND mmp_media_source != 'UNKNOWN'
    GROUP BY mmp_media_source, install_day
)
SELECT 
    mmp_media_source AS network,
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

- **Network retention D7/D1 > 40%**: Network có user long-term engagement tốt → ưu tiên
- **Network retention D7/D1 20-40%**: Retention trung bình → theo dõi
- **Network retention D7/D1 < 20%**: Network có user churn cao → cân nhắc giảm budget

## Bước 3: Gợi ý

- Tăng budget cho network có retention D7/D1 cao nhất
- Giảm budget cho network có retention D7/D1 thấp nhất
- Kết hợp retention với ROAS để đánh giá network quality toàn diện

## Cảnh báo thresholds
- Network retention D7/D1 < 20% → cảnh báo churn cao
- Network retention D7/D1 > 40% → gợi ý scale up
