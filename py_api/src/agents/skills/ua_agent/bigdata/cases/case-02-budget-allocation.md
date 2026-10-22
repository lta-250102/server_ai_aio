---
name: case-02-budget-allocation
description: Phân bổ budget theo media source
---

# Case 2: Phân bổ budget media source (Budget Allocation)

## Trigger
- Khi user hỏi về phân bổ budget, chi tiêu theo network, so sánh spend giữa các media source.

## Mục tiêu
Phân tích phân bổ budget giữa các network, xác định network nào chiếm tỷ trọng cao và hiệu quả của chúng.

## Bước 1: Lấy data + Tính toán

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        network_code,
        created_day,
        sum(cost) AS spend,
        sum(conversion) AS installs,
        sum(revenue) AS revenue
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY network_code, created_day
)
SELECT
    network_code,
    created_day,
    spend,
    installs,
    revenue,
    round(spend / NULLIF(installs, 0), 4) AS cpi,
    round(revenue / NULLIF(spend, 0) * 100, 2) AS roas
FROM base_agg
ORDER BY network_code, created_day
```

**Output columns:** `network_code`, `spend`, `installs`, `revenue`, `cpi`, `roas`

## Bước 2: Phân tích

- **Network spend > 30% nhưng ROAS < 100%**: Network này đang ngốn ngân sách nhưng hiệu quả thấp → cân nhắc giảm budget
- **Network spend < 10% nhưng ROAS > 200%**: Network nhỏ nhưng hiệu quả cao → cân nhắc tăng budget để scale
- **Top 3 networks chiếm > 70% spend**: Phụ thuộc quá nhiều vào vài network → diversify risk

## Bước 3: Gợi ý

- Chuyển budget từ network ROAS thấp sang network ROAS cao
- Đặt budget cap cho network chiếm > 40% tổng spend
- Test thêm networks mới để diversify

## Cảnh báo thresholds
- Single network spend % > 40% → cảnh báo phụ thuộc
- Network ROAS < 100% → cảnh báo lỗ
- Network ROAS > 300% → gợi ý tăng budget
