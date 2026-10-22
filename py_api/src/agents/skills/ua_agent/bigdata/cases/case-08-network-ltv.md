---
name: case-08-network-roas
description: Network ROAS (Network-level ROAS)
---

# Case 8: Network ROAS (Network-level ROAS)

## Trigger
- Khi user hỏi về ROAS theo network, network nào hiệu quả nhất, so sánh ROAS giữa các network.

## Mục tiêu
Phân tích ROAS của các network, xác định network nào có hiệu quả cao nhất.

## Bước 1: Lấy data + Tính toán

**Dùng [Generic Template 1](../SKILL.md#template-1-dimension-roascpi-attribution-table)** — thay `{{dimension_column}}` = `network_code`.

**Dùng tool `query_sql` để thực thi query SQL dưới đây:**

```sql
-- Dùng tool `query_sql` để thực thi query này
WITH base_agg AS (
    SELECT
        network_code,
        created_day,
        sum(cost) AS cost,
        sum(revenue) AS revenue,
        sum(conversion) AS installs
    FROM dwh_system.f_puller_ua_attribution
    WHERE package_name = '<package_name>'
      AND platform = 'android'
      AND created_day BETWEEN today() - INTERVAL 6 DAY AND today() - 1
      AND network_code NOT IN ('UNKNOWN', '', 'organic')
    GROUP BY network_code, created_day
)
SELECT
    network_code AS dimension,
    created_day,
    cost,
    revenue,
    installs,
    round(revenue / NULLIF(cost, 0) * 100, 2) AS roas,
    round(cost / NULLIF(installs, 0), 4) AS cpi
FROM base_agg
ORDER BY dimension, created_day
```

**Output columns:** `dimension`, `cost`, `revenue`, `installs`, `roas`, `cpi`

## Bước 2: Phân tích

- **Network ROAS > 200%**: Network chất lượng cao → ưu tiên scale
- **Network ROAS 100-200%**: Network hiệu quả → giữ nguyên
- **Network ROAS < 100%**: Network kém hiệu quả → cân nhắc giảm budget
- **Network có spend cao nhưng ROAS thấp**: Network ngốn ngân sách nhưng hiệu quả thấp → giảm budget

## Bước 3: Gợi ý

- Tăng budget cho network có ROAS cao nhất
- Giảm budget cho network có ROAS thấp nhất
- Diversify budget sang network có ROAS cao nhưng spend thấp

## Cảnh báo thresholds
- Network ROAS < 100% → cảnh báo kém hiệu quả
- Network ROAS > 200% → gợi ý scale up
- Network spend > 40% tổng spend nhưng ROAS < avg → cảnh báo inefficiency
