# Case 1: Spend game tăng/giảm (Spend Trend Analysis)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.

## Mục tiêu
Xác định trend spend (cost) của game trong 14 ngày gần nhất, so sánh 7 ngày gần nhất với 7 ngày trước đó.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId từ package_name
Dùng `growX_ua_list_apps` để tìm `appId` tương ứng với `package_name` của game cần phân tích:

```python
# Trong output của growX_ua_list_apps, tìm game có bundleId == <package_name>
# Ví dụ: bundleId == "com.company.game"
```

**Lưu ý:** Chỉ dùng `bundleId` để match, không bao giờ sửa `appId` dưới mọi hình thức.

### 1.2. Query Spend 2 giai đoạn
Dùng `growX_ua_list_campaigns` với `getAll=True` để lấy toàn bộ campaign spend của game:

**Giai đoạn 1: 7 ngày gần nhất (tức ngày)**
```python
result_recent = growX_ua_list_campaigns(
    appId="<appId>",
    days=7,
    getAll=True
)
```

**Giai đoạn 2: 7 ngày trước đó (từ 8-14 ngày trước)**
```python
# Tính ngày từ/to
from_date = "YYYY-MM-DD"  # 14 ngày trước
to_date = "YYYY-MM-DD"    # 8 ngày trước (inclusive)

result_past = growX_ua_list_campaigns(
    appId="<appId>",
    from=from_date,
    to=to_date,
    getAll=True
)
```

### 1.3. Tổng hợp Spend theo ngày
Từ `result_recent` và `result_past`, tổng hợp `SPEND` theo từng ngày:

```python
from collections import defaultdict

def extract_daily_spend(result):
    """Extract spend grouped by reporting_day"""
    daily_spend = defaultdict(float)
    for campaign in result.get('campaigns', []):
        metrics = campaign.get('metrics', {})
        spend = metrics.get('SPEND', 0) or 0
        reporting_day = campaign.get('reportingDay', '')
        daily_spend[reporting_day] += spend
    return dict(daily_spend)

recent_spend = extract_daily_spend(result_recent)
past_spend = extract_daily_spend(result_past)
```

### 1.4. Tính toán DoD và WoW
Dùng Python để tính các chỉ số delta:

```python
import pandas as pd

# Combine and sort all days
all_days = sorted(set(list(recent_spend.keys()) + list(past_spend.keys())))
spend_series = pd.Series({d: recent_spend.get(d, 0) + past_spend.get(d, 0) for d in all_days})

# Calculate DoD (Day-over-Day)
spend_series['delta_abs'] = spend_series.diff()
spend_series['delta_pct'] = (spend_series.diff() / spend_series.shift(1).replace(0, None)) * 100

# Calculate WoW (Week-over-Week)
spend_series['delta_woy_abs'] = spend_series.diff(7)
spend_series['delta_woy_pct'] = (spend_series.diff(7) / spend_series.shift(7).replace(0, None)) * 100
```

**Output columns:** `created_day`, `cost`, `delta_abs` (DoD), `delta_pct` (DoD%), `delta_woy_abs`, `delta_woy_pct` (WoW%)

## Bước 2: Phân tích

- **Trend tăng**: Cost tăng liên tục 2-3 ngày trở lên → game có khả năng trend đang tăng
- **Trend giảm**: Cost giảm liên tục → xác định game chủ động cut hay mất khả năng spend
- **Stable**: Trung bình 7 ngày gần nhất ≈ Trung bình 7 ngày trước đó (chênh lệch < 10%)
- **Single day spike**: Chỉ tăng/giảm 1 ngày rồi quay lại → chưa coi là trend
- **WoW (Week-over-Week)**: So sánh ngày hiện tại với cùng ngày tuần trước (7 ngày trước)

## Bước 3: Gợi ý

- Cost có trend tăng/giảm → kết hợp với ROAS (#7) và phân tích xuống media source (#2)
- Δ Cost DoD > 20% so với ngày trước → cảnh báo UA
- Δ Cost WoW > 20% so với cùng tuần trước → cảnh báo UA
- Stable → không có bất thường

## Cảnh báo thresholds
- Δ Cost DoD > 20% → cảnh báo UA
- Δ Cost WoW > 20% → cảnh báo UA

## Ví dụ minh họa

```python
# Ví dụ: Phân tích spend game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Query spend 14 ngày
result_7d = growX_ua_list_campaigns(appId=game_id, days=7, getAll=True)
result_14d = growX_ua_list_campaigns(appId=game_id, days=14, getAll=True)

# Step 3: Tính toán trend
daily_spend = extract_daily_spend(result_14d)
spend_series = pd.Series(daily_spend)
# ... tính toán như bước 1.4
```
