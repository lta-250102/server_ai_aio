# Case 14: Network CPI cao/thấp bất thường (Network CPI Analysis)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định network nào đang có CPI cao/thấp bất thường.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ đầy đủ các metrics SPEND và INSTALLS theo network, cho phép tính toán CPI hàng ngày cho từng network.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và danh sách network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

networks = growX_ua_list_networks()
active_networks = [n for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]
network_codes = [n['code'] for n in active_networks]
```

### 1.2. Query SPEND và INSTALLS theo từng network
```python
from collections import defaultdict

def get_network_daily_metrics(game_id, network_code, days):
    """
    Lấy daily metrics cho 1 network
    Trả về: {day: {spend: float, installs: int}}
    """
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=network_code,
        days=days,
        metrics=["SPEND", "INSTALLS"],
        getAll=True
    )
    
    daily_metrics = defaultdict(lambda: {'spend': 0.0, 'installs': 0})
    
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        
        daily_metrics[day]['spend'] += spend
        daily_metrics[day]['installs'] += installs
    
    return dict(daily_metrics)

# Query 14 ngày cho mỗi network
network_daily_data = {}
for net_code in network_codes:
    network_daily_data[net_code] = get_network_daily_metrics(game_id, net_code, 14)
```

### 1.3. Tính toán CPI theo network
```python
def calculate_network_cpi(network_daily_data):
    """
    Tính CPI và delta cho từng network
    Trả về list sorted by network and day
    """
    results = []
    
    for net_code, daily in network_daily_data.items():
        # Sắp xếp theo ngày
        sorted_days = sorted(daily.keys())
        prev_cpi = None
        
        for day in sorted_days:
            data = daily[day]
            spend = data['spend']
            installs = data['installs']
            
            if installs > 0:
                cpi = round(spend / installs, 4)
            else:
                cpi = 0
            
            # Tính delta so với ngày trước
            delta_cpi = None
            delta_cpi_pct = None
            if prev_cpi is not None and prev_cpi > 0:
                delta_cpi = round(cpi - prev_cpi, 4)
                delta_cpi_pct = round(delta_cpi / prev_cpi * 100, 2)
            
            results.append({
                'media_source': net_code,
                'created_day': day,
                'cost': round(spend, 2),
                'installs': installs,
                'cpi': cpi,
                'delta_cpi': round(delta_cpi, 4) if delta_cpi is not None else None,
                'delta_cpi_pct': round(delta_cpi_pct, 2) if delta_cpi_pct is not None else None
            })
            
            if installs > 0:
                prev_cpi = cpi
    
    return results

network_cpi = calculate_network_cpi(network_daily_data)
```

**Output columns:** `media_source`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- **Tương tự case 13** nhưng áp dụng cho từng media_source
- **Chỉ đánh giá network đã có > 200 installs** hoặc đã start > 7 ngày
- **Network mới test** (< 200 installs) → CPI chưa ổn định, cần theo dõi thêm
- **Network có CPI cao nhưng ROAS cũng cao** → user chất lượng cao

### Phân tích chi tiết:
```python
# Tổng hợp theo network
from collections import defaultdict

network_totals = defaultdict(lambda: {'total_spend': 0, 'total_installs': 0, 'days_active': 0, 'cpi_values': []})

for entry in network_cpi:
    net = entry['media_source']
    network_totals[net]['total_spend'] += entry['cost']
    network_totals[net]['total_installs'] += entry['installs']
    network_totals[net]['days_active'] += 1
    if entry['cpi'] > 0:
        network_totals[net]['cpi_values'].append(entry['cpi'])

# Tính CPI trung bình cho từng network
network_summary = []
for net, data in network_totals.items():
    avg_cpi = sum(data['cpi_values']) / len(data['cpi_values']) if data['cpi_values'] else 0
    network_summary.append({
        'media_source': net,
        'total_spend': round(data['total_spend'], 2),
        'total_installs': data['total_installs'],
        'days_active': data['days_active'],
        'avg_cpi': round(avg_cpi, 4)
    })

# Sắp xếp theo CPI
network_summary.sort(key=lambda x: x['avg_cpi'])

print("=" * 70)
print(f"BÁO CÁO NETWORK CPI - {package_name}")
print("=" * 70)
print(f"{'Network':<15} {'Total Spend':>12} {'Installs':>10} {'Avg CPI':>10} {'Days':>6}")
print("-" * 70)

for net in network_summary:
    print(f"{net['media_source']:<15} ${net['total_spend']:>11.2f} {net['total_installs']:>10} ${net['avg_cpi']:>9.4f} {net['days_active']:>6}")

print("=" * 70)

# Xác định network có vấn đề
total_installs = sum(n['total_installs'] for n in network_summary)
avg_cpi_overall = sum(n['total_spend'] for n in network_summary) / total_installs if total_installs > 0 else 0

print(f"\n📊 CPI trung bình toàn game: ${avg_cpi_overall:.4f}")
print("-" * 70)

for net in network_summary:
    # Chỉ đánh giá network có đủ data
    if net['total_installs'] >= 200 or net['days_active'] >= 7:
        deviation = ((net['avg_cpi'] - avg_cpi_overall) / avg_cpi_overall * 100) if avg_cpi_overall > 0 else 0
        
        if abs(deviation) > 20:
            direction = "Cao" if deviation > 0 else "Thấp"
            print(f"⚠️ {net['media_source']}: CPI {direction} hơn {abs(deviation):.1f}% so với trung bình")
            print(f"   - Avg CPI: ${net['avg_cpi']:.4f}")
            print(f"   - Total Installs: {net['total_installs']}")
```

## Bước 3: Gợi ý

- **Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20%** → báo UA → check tiếp campaign (#15)
- **Network CPI cao + ROAS thấp** → xem xét giảm budget
- **Network CPI thấp + ROAS cao** → xem xét tăng budget

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi network có > 200 installs hoặc start > 7 ngày

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Network CPI cho game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Lấy danh sách network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]

# Step 3: Query metrics
network_daily_data = {}
for net_code in network_codes:
    network_daily_data[net_code] = get_network_daily_metrics(game_id, net_code, 14)

# Step 4: Tính CPI
network_cpi = calculate_network_cpi(network_daily_data)

# Step 5: Phân tích delta từng network
print("\n🔍 KIỂM TRA DELTA CPI:")
print("-" * 50)

network_by_day = defaultdict(list)
for entry in network_cpi:
    network_by_day[entry['media_source']].append(entry)

for net_code, entries in network_by_day.items():
    # Sắp xếp theo ngày
    entries.sort(key=lambda x: x['created_day'])
    
    # Kiểm tra trend 3 ngày
    deltas = [e['delta_cpi_pct'] for e in entries[1:] if e['delta_cpi_pct'] is not None]
    
    if len(deltas) >= 2:
        last_3 = deltas[-3:]
        
        # Trend tăng liên tiếp
        if all(d > 0 for d in last_3):
            print(f"🔴 {net_code}: CPI TĂNG liên tiếp {len(last_3)} ngày")
            for d in last_3:
                print(f"     Δ CPI: {d:.1f}%")
        
        # Trend giảm liên tiếp
        elif all(d < 0 for d in last_3):
            print(f"🟢 {net_code}: CPI GIẢM liên tiếp {len(last_3)} ngày")
            for d in last_3:
                print(f"     Δ CPI: {d:.1f}%")
        
        # Biến động đột ngột
        for d in deltas:
            if abs(d) > 20:
                print(f"⚠️ {net_code}: Δ CPI đột ngột {d:.1f}%")

# Step 6: Kết hợp với ROAS để đánh giá chất lượng user
networks_with_roas = []
for net_code in network_codes:
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=net_code,
        days=14,
        metrics=["SPEND", "INSTALLS", "ROAS_D7"],
        getAll=True
    )
    
    total_spend = 0
    total_installs = 0
    weighted_roas = 0
    
    for campaign in result.get('campaigns', []):
        metrics = campaign.get('metrics', {})
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        roas_d7 = metrics.get('ROAS_D7', 0) or 0
        
        total_spend += spend
        total_installs += installs
        weighted_roas += spend * roas_d7
    
    if total_spend > 0 and total_installs > 0:
        cpi = total_spend / total_installs
        roas_d7 = weighted_roas / total_spend
        networks_with_roas.append({
            'network': net_code,
            'cpi': round(cpi, 4),
            'roas_d7': round(roas_d7, 2),
            'spend': round(total_spend, 2),
            'installs': total_installs
        })

# Sắp xếp theo CPI
networks_with_roas.sort(key=lambda x: x['cpi'])

print("\n" + "=" * 70)
print(f"{'Network':<15} {'CPI':>10} {'ROAS_D7':>10} {'Spend':>10} {'Installs':>10}")
print("-" * 70)

for net in networks_with_roas:
    print(f"{net['network']:<15} ${net['cpi']:>9.4f} {net['roas_d7']:>9.1f}% ${net['spend']:>9.2f} {net['installs']:>10}")

print("=" * 70)

# Đánh giá chất lượng
print("\n📋 ĐÁNH GIÁ CHẤT LƯỢNG:")
print("-" * 50)
for net in networks_with_roas:
    if net['cpi'] > 1.0:  # CPI cao
        if net['roas_d7'] > 100:
            print(f"✅ {net['network']}: CPI cao nhưng ROAS tốt → User chất lượng cao")
        else:
            print(f"🔴 {net['network']}: CPI cao + ROAS thấp → Cần xem xét giảm budget")
    else:
        if net['roas_d7'] > 100:
            print(f"🟢 {net['network']}: CPI thấp + ROAS tốt → Xem xét tăng budget")
        else:
            print(f"⚠️ {net['network']}: CPI thấp nhưng ROAS kém → Cần kiểm tra user quality")
```

## Lưu ý quan trọng

1. **CPI Calculation**:
   - CPI = Total Spend / Total Installs (theo network và ngày)
   - Luôn dùng weighted average khi tổng hợp từ nhiều campaigns

2. **Data Thresholds**:
   - Chỉ đánh giá network có > 200 installs hoặc start > 7 ngày
   - Network mới test (< 200 installs) → CPI chưa ổn định

3. **Context with ROAS**:
   - CPI cao không phải lúc nào cũng xấu (có thể do user chất lượng cao)
   - Luôn kết hợp CPI với ROAS để đánh giá toàn diện

4. **Network Competition**:
   - CPI tăng có thể do competition tăng trên network
   - CPI giảm có thể do network đang scale tốt hoặc creative kém hiệu quả

5. **Attribution Window**:
   - Installs có thể bị ảnh hưởng bởi attribution window khác nhau giữa networks
   - 1-2 ngày cuối cùng có thể chưa đầy đủ
