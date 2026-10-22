# Case 2: Phân bổ budget theo media source (Budget Allocation)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.

## Mục tiêu
Đánh giá phân bổ budget giữa các network có ổn không, tìm network tăng/giảm bất thường.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId từ package_name
Dùng `growX_ua_list_apps` để tìm `appId` tương ứng:

```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']
```

### 1.2. Lấy danh sách network
Dùng `growX_ua_list_networks` để lấy danh sách network đang có account:

```python
networks = growX_ua_list_networks()
# Filter lấy các network có connectorCount > 0 và supportsReporting
active_networks = [n for n in networks if n['connectorCount'] > 0]
network_codes = [n['code'] for n in active_networks]
```

### 1.3. Query Spend theo từng network (2 giai đoạn)

**Giai đoạn 1: 7 ngày gần nhất (Hôm nay - 6 ngày)**
```python
def get_spend_by_network(app_id, network_code, days):
    """Query spend cho 1 network trong cửa sổ time"""
    result = growX_ua_list_campaigns(
        appId=app_id,
        network=network_code,
        days=days,
        getAll=True
    )
    daily_spend = {}
    for campaign in result.get('campaigns', []):
        metrics = campaign.get('metrics', {})
        spend = metrics.get('SPEND', 0) or 0
        day = campaign.get('reportingDay', '')
        daily_spend[day] = daily_spend.get(day, 0) + spend
    return daily_spend

# Lấy spend 7 ngày gần nhất theo từng network
recent_spend = {}
for net_code in network_codes:
    recent_spend[net_code] = get_spend_by_network(game_id, net_code, 7)

# Lấy spend 7 ngày trước đó (từ 8-14 ngày trước)
past_spend = {}
for net_code in network_codes:
    past_spend[net_code] = get_spend_by_network(
        game_id, net_code, days=14
    )
    # Trừ 7 ngày đầu ra (vì đã lấy ở recent)
```

**Cách đơn giản hơn: Query 14 ngày và tự chia**

```python
# Query 14 ngày cho mỗi network
full_spend = {}
for net_code in network_codes:
    full_spend[net_code] = get_spend_by_network(game_id, net_code, 14)
```

### 1.4. Tính toán SOV (Share of Voice)

```python
from collections import defaultdict

def calculate_sov(daily_spend_dict):
    """
    daily_spend_dict: {network_code: {day: spend}}
    Trả về: list of dicts với thông tin sov cho từng network/day
    """
    # Collect all days
    all_days = set()
    for nd in daily_spend_dict.values():
        all_days.update(nd.keys())
    all_days = sorted(all_days)
    
    results = []
    for day in all_days:
        total = sum(nd.get(day, 0) for nd in daily_spend_dict.values())
        day_entries = []
        for net_code, spend_dict in daily_spend_dict.items():
            spend = spend_dict.get(day, 0)
            sov_pct = (spend / total * 100) if total > 0 else 0
            day_entries.append({
                'media_source': net_code,
                'created_day': day,
                'network_cost': round(spend, 2),
                'total_cost': round(total, 2),
                'sov_pct': round(sov_pct, 2)
            })
        # Sort by sov_pct desc
        day_entries.sort(key=lambda x: x['sov_pct'], reverse=True)
        # Add rank
        for i, entry in enumerate(day_entries):
            entry['rank'] = i + 1
        results.extend(day_entries)
    
    return results

sov_data = calculate_sov(full_spend)
```

### 1.5. So sánh 2 giai đoạn (7 ngày gần nhất vs 7 ngày trước)

```python
# Chia 14 ngày thành 2 giai đoạn
days_7d = set(full_spend.values())[0].keys()  # Lấy tất cả ngày từ network đầu tiên
sorted_days = sorted(days_7d)
last_7_days = sorted_days[-7:]    # 7 ngày gần nhất
prev_7_days = sorted_days[:7]     # 7 ngày trước

# Tính tổng spend 7 ngày theo network
recent_totals = {}
past_totals = {}

for net_code in network_codes:
    recent_totals[net_code] = sum(full_spend[net_code].get(d, 0) for d in last_7_days)
    past_totals[net_code] = sum(full_spend[net_code].get(d, 0) for d in prev_7_days)

# Tính SOV cho từng giai đoạn
def calc_period_sov(totals):
    total = sum(totals.values())
    sov = {}
    for net, spend in totals.items():
        sov[net] = (spend / total * 100) if total > 0 else 0
    return sov, total

sov_recent, total_recent = calc_period_sov(recent_totals)
sov_past, total_past = calc_period_sov(past_totals)

# Tính delta SOV
sov_delta = {}
for net in network_codes:
    sov_delta[net] = round(sov_recent.get(net, 0) - sov_past.get(net, 0), 2)
```

**Output columns:** `media_source`, `created_day`, `network_cost`, `total_cost`, `sov_pct` (% SOV), `rank`

## Bước 2: Phân tích

- **Top spend last 7 days** so sánh với top spend cùng kì tuần trước → có thay đổi không?
- **SOV tăng/giảm bất thường**: Network nào có SOV tăng/giảm > 15% so với cùng kì → cảnh báo
- **Trend**: Áp dụng tương tự case 1 cho từng media source
- **Network mới xuất hiện**: Network nào mới xuất hiện trong top 5 → đánh giá chất lượng

## Bước 3: Gợi ý

- Network tăng → đánh giá CPI + ROAS network (#8) → đề xuất đẩy budget thêm
- Network giảm > 15% so với cùng kì → cảnh báo UA, kiểm tra integration, trạng thái tài khoản, daily budget
- Tất cả media source giảm đồng loạt → cảnh báo UA check ở level app
- Network mới top spend → kiểm tra chất lượng user (RR, ROAS) trước khi đẩy budget

## Cảnh báo thresholds
- SOV network giảm > 15% so với cùng kì → cảnh báo UA
- Tất cả network giảm → cảnh báo UA check level app

## Ví dụ minh họa

```python
# Ví dụ: Phân tích budget allocation game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Lấy danh sách network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0]

# Step 3: Query spend 14 ngày cho từng network
full_spend = {}
for net_code in network_codes:
    full_spend[net_code] = get_spend_by_network(game_id, net_code, 14)

# Step 4: Tính toán SOV và so sánh
sov_data = calculate_sov(full_spend)
sov_delta = calculate_sov_delta(full_spend, network_codes)

# Step 5: Phân tích
for net, delta in sov_delta.items():
    if delta < -15:
        print(f"CẢNH BÁO: {net} giảm SOV {delta}% so với tuần trước")
    elif delta > 15:
        print(f"THẬN TRỌNG: {net} tăng SOV {delta}% so với tuần trước")
```
