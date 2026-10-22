---
name: case-19-retention-game
description: Retention game D1/D3/D7
---

# Case 19: Retention game D1/D3/D7 (Cohort Retention)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại chơi.

## Mục tiêu
Xác định Retention (D1/D3/D7) của game dựa trên cohort data từ `f_puller_ua_cohort`.

**Lưu ý:** Bigdata retention dùng gold user-day table với cohort pattern — D1/D3/D7 retention theo dimension.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
WITH base AS (
    SELECT 
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
    GROUP BY install_day
)
SELECT 
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

- **Retention D1 > 40%**: User quay lại tốt → game có hook tốt
- **Retention D1 20-40%**: Retention trung bình → cần cải thiện onboarding
- **Retention D1 < 20%**: Retention thấp → cần xem lại game mechanics
- **Retention D7/D1 > 30%**: User long-term engagement tốt
- **Retention D7/D1 < 10%**: User churn cao sau D1

## Bước 3: Gợi ý

- Nếu D1 thấp → cải thiện onboarding, tutorial
- Nếu D3 thấp → thêm daily rewards, events
- Nếu D7 thấp → thêm long-term goals, progression system

## Cảnh báo thresholds
- Retention D1 < 20% → cảnh báo nghiêm trọng
- Retention D1 20-40% → cảnh báo cần cải thiện
- Retention D7/D1 < 10% → cảnh báo churn cao
