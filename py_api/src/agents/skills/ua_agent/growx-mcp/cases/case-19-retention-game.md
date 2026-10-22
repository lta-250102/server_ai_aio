# Case 19: Retention game D1/D3/D7 (Game Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định Retention (D1/D3/D7) của game có tăng/giảm so với target không.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ các metrics RETENTION_D1, RETENTION_D3, RETENTION_D7, RETENTION_D14, RETENTION_D28.
**Lưu ý:** Retention của growX là dựa trên **app open events** (người dùng quay lại mở game), không phải purchase-based.

**⚠️ Khác biệt so với original case:**
- growX **không có** RETENTION_D0 (chỉ có D1, D3, D7, D14, D28)
- Original case dùng purchase events (af_purchase), growX dùng app open events

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']
```

### 1.2. Query Retention 2 giai đoạn
```python
# Giai đoạn 1: 7 ngày gần nhất
result_recent = growX_ua_list_campaigns(
    appId=game_id,
    days=7,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7"],
    getAll=True
)

# Giai đoạn 2: 7 ngày trước đó (từ 8-14 ngày trước)
result_past = growX_ua_list_campaigns(
    appId=game_id,
    from="YYYY-MM-DD",  # Tính ngày từ hiện tại - 14 ngày
    to="YYYY-MM-DD",    # Tính ngày từ hiện tại - 8 ngày
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7"],
    getAll=True
)
```

### 1.3. Tổng hợp metrics theo ngày
```python
from collections import defaultdict

def extract_daily_retention(result):
    """
    Extract retention và aggregates theo ngày
    Trả về: {day: {installs: int, ret_d1: float, ret_d3: float, ret_d7: float}}
    """
    daily_metrics = defaultdict(lambda: {
        'installs': 0,
        'ret_d1': 0.0,
        'ret_d3': 0.0,
        'ret_d7': 0.0,
        'weighted_ret_d1': 0.0,
        'weighted_ret_d3': 0.0,
        'weighted_ret_d7': 0.0,
    })
    
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        installs = metrics.get('INSTALLS', 0) or 0
        ret_d1 = metrics.get('RETENTION_D1', 0) or 0
        ret_d3 = metrics.get('RETENTION_D3', 0) or 0
        ret_d7 = metrics.get('RETENTION_D7', 0) or 0
        
        daily_metrics[day]['installs'] += installs
        daily_metrics[day]['weighted_ret_d1'] += installs * ret_d1
        daily_metrics[day]['weighted_ret_d3'] += installs * ret_d3
        daily_metrics[day]['weighted_ret_d7'] += installs * ret_d7
    
    # Tính weighted average retention
    for day, data in daily_metrics.items():
        if data['installs'] > 0:
            data['ret_d1'] = data['weighted_ret_d1'] / data['installs']
            data['ret_d3'] = data['weighted_ret_d3'] / data['installs']
            data['ret_d7'] = data['weighted_ret_d7'] / data['installs']
        else:
            data['ret_d1'] = 0
            data['ret_d3'] = 0
            data['ret_d7'] = 0
        
        # Clean up temp fields
        del data['weighted_ret_d1']
        del data['weighted_ret_d3']
        del data['weighted_ret_d7']
    
    return dict(daily_metrics)

recent_retention = extract_daily_retention(result_recent)
past_retention = extract_daily_retention(result_past)
```

### 1.4. Tính toán và so sánh retention
```python
import pandas as pd

# Combine và sort theo ngày
all_days = sorted(set(list(recent_retention.keys()) + list(past_retention.keys())))

daily_data = []
for day in all_days:
    m = recent_retention.get(day, past_retention.get(day, {
        'installs': 0, 'ret_d1': 0, 'ret_d3': 0, 'ret_d7': 0
    }))
    
    daily_data.append({
        'install_date': day,
        'total_installs': m['installs'],
        'ret_d1': round(m['ret_d1'], 2),
        'ret_d3': round(m['ret_d3'], 2),
        'ret_d7': round(m['ret_d7'], 2)
    })

df = pd.DataFrame(daily_data)
```

**Output columns:** `install_date`, `total_installs`, `ret_d1` (%), `ret_d3` (%), `ret_d7` (%)

- **Retention DN** = tỷ lệ user quay lại ở ngày N sau install × 100
- D1 = 1 ngày sau install, D3 = 3 ngày, D7 = 7 ngày
- growX trả về **PERCENT_0_100** (ví dụ: `35` nghĩa là 35%)
- So với target RR (đối thủ, thể loại game, hoặc benchmark)
- Tính Δ RR giữa các cohort tuần gần đây so tuần trước

## Bước 2: Phân tích

- **Chỉ so sánh cohort đã đủ "chín"** (đủ N ngày trôi qua từ install)
  - D1: cần ≥ 2 ngày data
  - D3: cần ≥ 4 ngày data
  - D7: cần ≥ 8 ngày data
- **RR giảm dần qua các cohort gần đây** → chất lượng user mới kém hơn hoặc có thay đổi sản phẩm
- **RR ổn định/tăng** → traffic và sản phẩm đang tốt
- **D1 retention cao** → user có xu hướng quay lại ngay sau khi install
- **D7 retention cao** → user trung thành, game có khả năng giữ chân tốt

### Phân tích chi tiết:
```python
# Phân tích trend retention
if len(df) >= 2:
    recent_7d = df.tail(7)
    prev_7d = df.head(7)
    
    # Tính retention trung bình
    avg_ret_d1_recent = recent_7d['ret_d1'].mean()
    avg_ret_d1_prev = prev_7d['ret_d1'].mean()
    
    avg_ret_d3_recent = recent_7d['ret_d3'].mean()
    avg_ret_d3_prev = prev_7d['ret_d3'].mean()
    
    avg_ret_d7_recent = recent_7d['ret_d7'].mean()
    avg_ret_d7_prev = prev_7d['ret_d7'].mean()
    
    # Tính delta
    d1_delta = avg_ret_d1_recent - avg_ret_d1_prev
    d3_delta = avg_ret_d3_recent - avg_ret_d3_prev
    d7_delta = avg_ret_d7_recent - avg_ret_d7_prev
    
    print("=" * 60)
    print(f"BÁO CÁO RETENTION GAME - {package_name}")
    print("=" * 60)
    print(f"{'':<20} {'7 ngày gần':>12} {'7 ngày trước':>12} {'Delta':>10}")
    print("-" * 60)
    print(f"D1 Retention       {avg_ret_d1_recent:>11.2f}% {avg_ret_d1_prev:>11.2f}% {d1_delta:>+9.2f}%")
    print(f"D3 Retention       {avg_ret_d3_recent:>11.2f}% {avg_ret_d3_prev:>11.2f}% {d3_delta:>+9.2f}%")
    print(f"D7 Retention       {avg_ret_d7_recent:>11.2f}% {avg_ret_d7_prev:>11.2f}% {d7_delta:>+9.2f}%")
    print("=" * 60)
```

## Bước 3: Gợi ý

- **RR dưới target và giảm dần** → phân tích xuống Network (#20) tìm nguồn user chất lượng kém; kiểm tra app update/creative update trùng thời điểm giảm
- **RR tốt, ổn định** → yên tâm scale spend
- **RR D7 giảm nhưng D1 tăng** → user mới quay lại nhưng không duy trì → cần cải thiện game loop
- **RR tất cả giảm** → cảnh báo UA check level app (bug/MO issue)

## Cảnh báo thresholds
- RR D1 giảm > 20% so với tuần trước → cảnh báo
- RR D7 giảm > 15% so với tuần trước → cảnh báo
- RR dưới target 2 ngày liên tiếp → cảnh báo

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Retention game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Query Retention 14 ngày
result_14d = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7"],
    getAll=True
)

# Step 3: Tính toán
daily_retention = extract_daily_retention(result_14d)

# Step 4: Report chi tiết theo ngày
print("\n" + "=" * 70)
print(f"CHI TIẾT RETENTION THEO NGÀY - {package_name}")
print("=" * 70)
print(f"{'Ngày':<12} {'Installs':>10} {'D1 Ret%':>10} {'D3 Ret%':>10} {'D7 Ret%':>10}")
print("-" * 70)

for day, data in sorted(daily_retention.items()):
    print(f"{day:<12} {data['installs']:>10} {data['ret_d1']:>9.2f}% {data['ret_d3']:>9.2f}% {data['ret_d7']:>9.2f}%")

# Step 5: Cảnh báo
print("\n🔍 KIỂM TRA CẢNH BÁO:")
print("-" * 50)

# So sánh 2 giai đoạn
all_days = sorted(daily_retention.keys())
if len(all_days) >= 7:
    first_7 = all_days[:7]
    last_7 = all_days[-7:]
    
    first_7_data = {d: daily_retention[d] for d in first_7}
    last_7_data = {d: daily_retention[d] for d in last_7}
    
    avg_d1_first = sum(d['ret_d1'] for d in first_7_data.values()) / len(first_7_data) if first_7_data else 0
    avg_d1_last = sum(d['ret_d1'] for d in last_7_data.values()) / len(last_7_data) if last_7_data else 0
    
    avg_d7_first = sum(d['ret_d7'] for d in first_7_data.values()) / len(first_7_data) if first_7_data else 0
    avg_d7_last = sum(d['ret_d7'] for d in last_7_data.values()) / len(last_7_data) if last_7_data else 0
    
    d1_delta = avg_d1_last - avg_d1_first
    d7_delta = avg_d7_last - avg_d7_first
    
    if d1_delta < -20:
        print(f"🔴 CẢNH BÁO: D1 Retention giảm {abs(d1_delta):.1f}% so với tuần trước")
    elif d1_delta > 0:
        print(f"🟢 D1 Retention tăng {d1_delta:.1f}% so với tuần trước")
    
    if d7_delta < -15:
        print(f"🔴 CẢNH BÁO: D7 Retention giảm {abs(d7_delta):.1f}% so với tuần trước")
    elif d7_delta > 0:
        print(f"🟢 D7 Retention tăng {d7_delta:.1f}% so với tuần trước")

# Step 6: Kết hợp với ROAS
result_with_roas = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7", "ROAS_D7"],
    getAll=True
)

daily_combined = defaultdict(lambda: {
    'installs': 0, 'ret_d1': 0, 'ret_d3': 0, 'ret_d7': 0,
    'roas_d7': 0, 'weighted_roas': 0
})

for campaign in result_with_roas.get('campaigns', []):
    day = campaign.get('reportingDay', '')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    ret_d3 = metrics.get('RETENTION_D3', 0) or 0
    ret_d7 = metrics.get('RETENTION_D7', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    daily_combined[day]['installs'] += installs
    daily_combined[day]['weighted_roas'] += installs * roas_d7
    daily_combined[day]['weighted_ret_d1'] = installs * ret_d1
    daily_combined[day]['weighted_ret_d3'] = installs * ret_d3
    daily_combined[day]['weighted_ret_d7'] = installs * ret_d7

print("\n" + "=" * 70)
print("KẾT HỢP RETENTION VÀ ROAS:")
print("=" * 70)
print(f"{'Ngày':<12} {'Installs':>10} {'D1 Ret%':>10} {'D7 Ret%':>10} {'ROAS_D7':>10}")
print("-" * 70)

for day in sorted(daily_combined.keys()):
    data = daily_combined[day]
    if data['installs'] > 0:
        avg_roas = data['weighted_roas'] / data['installs']
        # Không có weighted retention trong cách này, dùng từ previous calculation
    else:
        avg_roas = 0
    print(f"{day:<12} {data['installs']:>10} N/A N/A {avg_roas:>9.1f}%")

print("=" * 70)
```

## Kết hợp với Network Retention (Case 20)

Để phân tích sâu hơn, nên kết hợp với network-level retention:

```python
# Phân tích retention theo network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0]

network_retention = {}
for net_code in network_codes:
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=net_code,
        days=14,
        metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D7"],
        getAll=True
    )
    
    total_installs = 0
    weighted_ret_d1 = 0
    weighted_ret_d7 = 0
    
    for campaign in result.get('campaigns', []):
        metrics = campaign.get('metrics', {})
        installs = metrics.get('INSTALLS', 0) or 0
        ret_d1 = metrics.get('RETENTION_D1', 0) or 0
        ret_d7 = metrics.get('RETENTION_D7', 0) or 0
        
        total_installs += installs
        weighted_ret_d1 += installs * ret_d1
        weighted_ret_d7 += installs * ret_d7
    
    if total_installs > 0:
        network_retention[net_code] = {
            'installs': total_installs,
            'ret_d1': round(weighted_ret_d1 / total_installs, 2),
            'ret_d7': round(weighted_ret_d7 / total_installs, 2)
        }

print("\n" + "=" * 60)
print("RETENTION THEO NETWORK:")
print("=" * 60)
print(f"{'Network':<15} {'Installs':>10} {'D1 Ret%':>10} {'D7 Ret%':>10}")
print("-" * 60)

for net, data in sorted(network_retention.items(), key=lambda x: x[1]['ret_d7'], reverse=True):
    print(f"{net:<15} {data['installs']:>10} {data['ret_d1']:>9.2f}% {data['ret_d7']:>9.2f}%")
```

## Lưu ý quan trọng

1. **Retention Scale**: Luôn nhớ retention là **PERCENT (0-100)**, không phải ratio.
   - `RETENTION_D7 = 35` nghĩa là 35%, không phải 0.35.
   - Không average retention mà không dùng weighted average theo installs.

2. **Cohort Metrics**: 
   - Retention là cohort metrics, dữ liệu sẽ tăng dần theo thời gian.
   - D1 value cho window kết thúc < 1 ngày trước sẽ chưa ổn định.
   - D7 value cho window kết thúc < 7 ngày trước sẽ chưa ổn định.

3. **Weighted Average**: 
   - Khi tổng hợp retention từ nhiều campaigns, luôn dùng **weighted average** theo installs.
   - Không dùng average đơn giản.

4. **GrowX vs Purchase-based**:
   - growX retention dựa trên **app open events** (user mở lại game).
   - Original case dựa trên **purchase events** (user mua hàng).
   - Hai metrics này khác nhau: một người có thể mở game (retention D7 cao) nhưng không mua hàng (purchase-based retention thấp).

5. **Benchmark**:
   - RR phụ thuộc vào thể loại game, platform, region.
   - So sánh với benchmark industry hoặc target nội bộ.

## Các benchmark tham khảo (App Open Retention)

| Thể loại game | D1 Retention target | D7 Retention target |
|--------------|---------------------|---------------------|
| Hypercasual | 25-35% | 8-15% |
| Casual | 30-40% | 12-20% |
| Mid-core | 35-45% | 15-25% |
| Core | 40-50% | 20-30% |

*Lưu ý: Benchmark chỉ mang tính tham khảo, phụ thuộc vào nhiều yếu tố.*
