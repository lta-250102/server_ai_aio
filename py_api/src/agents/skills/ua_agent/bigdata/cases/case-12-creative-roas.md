---
name: case-12-creative-roas
description: Creative ROAS tốt/xấu
---

# Case 12: Creative ROAS tốt/xấu (Creative ROAS)

## Trigger
- Khi user hỏi về creative ROAS, creative nào hiệu quả nhất.

## Mục tiêu
Xác định creatives có ROAS cao nhất/thấp nhất, tối ưu creative portfolio.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        creative_id,
        created_day,
        sum(cost) AS spend,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND creative_id != ''
      AND creative_id != 'UNKNOWN'
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY creative_id, created_day
)
SELECT
    creative_id,
    created_day,
    round(spend, 2) AS spend,
    round(revenue, 2) AS revenue,
    installs,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY creative_id, created_day
LIMIT 20
```

**Output columns:** `creative_id`, `spend`, `revenue`, `installs`, `cpi`, `roas`

## Bước 2: Phân tích

- **Creative ROAS > 200%**: Creative rất hiệu quả → scale up
- **Creative ROAS 100-200%**: Creative hiệu quả → giữ nguyên
- **Creative ROAS 50-100%**: Creative hòa vốn/lỗ nhẹ → theo dõi
- **Creative ROAS < 50%**: Creative kém hiệu quả → pause

## Bước 3: Gợi ý

- Tăng budget cho top 10 creatives có ROAS cao nhất
- Pause creatives có ROAS < 50% của trung bình
- Tạo thêm creatives mới dựa trên top performers

## Cảnh báo thresholds
- Creative ROAS > 200% → gợi ý scale up
- Creative ROAS 100-200% → giữ nguyên
- Creative ROAS < 50% avg → cảnh báo pause
