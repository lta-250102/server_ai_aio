# Case 15: Campaign CPI lệch nhiều nhất (Campaign CPI Analysis)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định campaign nào trong network có CPI lệch nhiều nhất.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ đầy đủ các metrics SPEND và INSTALLS theo campaign, cho phép tính toán CPI hàng ngày cho từng campaign.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

# Xác định network để phân tích
networks = growX_ua_list_networks()
network_code = [n['code'] for n in networks if n['displayName'] == '<network_name>'][0]
```

### 1.2. Query SPEND và INSTALLS cho network
```python
# Query 14 ngày gần nhất cho network cụ thể
campaigns_14d = growX_ua_list_campaigns(
    appId=game_id,
    network=network_code,
    days=14,
    metrics=["SPEND", "INSTALLS"],
    getAll=True
)
```

### 1.3. Tổng hợp metrics theo campaign
```python
from collections import defaultdict

def extract_campaign_daily_metrics(result):
    """
    Extract daily metrics cho từng campaign
    Trả về: {campaign_name: {day: {spend: float, installs: int}}}
    """
    campaign_data = defaultdict(lambda: defaultdict(lambda: {'spend': 0.0, 'installs': 0}))
    
    for campaign in result.get('campaigns', []):
        camp_name = campaign.get('name', 'Unknown')
        camp_type = campaign.get('type', campaign.get('campaignType', 'Unknown'))
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        
        campaign_data[camp_name]['daily'][day]['spend'] += spend
        campaign_data[camp_name]['daily'][day]['installs'] += installs
        campaign_data[camp_name]['type'] = camp_type
    
    return dict(campaign_data)

campaign_data = extract_campaign_daily_metrics(campaigns_14d)
```

### 1.4. Tính toán CPI và Delta theo campaign
```python
def calculate_campaign_cpi(campaign_data):
    """
    Tính CPI và delta cho từng campaign
    Trả về list sorted by campaign and day
    """
    results = []
    
    for camp_name, data in campaign_data.items():
        camp_type = data.get('type', 'Unknown')
        daily = data.get('daily', {})
        
        # Sắp xếp theo ngày
        sorted_days = sorted(daily.keys())
        prev_cpi = None
        
        for day in sorted_days:
            d = daily[day]
            spend = d['spend']
            installs = d['installs']
            
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
                'campaign': camp_name,
                'campaign_type': camp_type,
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

campaign_cpi = calculate_campaign_cpi(campaign_data)
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

## Bước 2: Phân tích

- **Tương tự case 13** cho campaign
- **Chỉ đánh giá campaign đã có > 200 installs** hoặc đã start > 7 ngày
- **Campaign có CPI cao nhưng ROAS cũng cao** → user chất lượng cao
- **Campaign mới test** → CPI chưa ổn định

### Phân tích chi tiết:
```python
# Tổng hợp theo campaign
from collections import defaultdict

campaign_totals = defaultdict(lambda: {
    'total_spend': 0, 'total_installs': 0, 'days_active': 0, 
    'cpi_values': [], 'camp_type': 'Unknown'
})

for entry in campaign_cpi:
    camp = entry['campaign']
    campaign_totals[camp]['total_spend'] += entry['cost']
    campaign_totals[camp]['total_installs'] += entry['installs']
    campaign_totals[camp]['days_active'] += 1
    campaign_totals[camp]['camp_type'] = entry['campaign_type']
    if entry['cpi'] > 0:
        campaign_totals[camp]['cpi_values'].append(entry['cpi'])

# Tính CPI trung bình cho từng campaign
campaign_summary = []
for camp, data in campaign_totals.items():
    avg_cpi = sum(data['cpi_values']) / len(data['cpi_values']) if data['cpi_values'] else 0
    campaign_summary.append({
        'campaign': camp,
        'campaign_type': data['camp_type'],
        'total_spend': round(data['total_spend'], 2),
        'total_installs': data['total_installs'],
        'days_active': data['days_active'],
        'avg_cpi': round(avg_cpi, 4)
    })

# Sắp xếp theo CPI
campaign_summary.sort(key=lambda x: x['avg_cpi'])

print("=" * 70)
print(f"BÁO CÁO CAMPAIGN CPI - {network_code}")
print("=" * 70)
print(f"{'Campaign':<30} {'Type':<15} {'Spend':>10} {'Installs':>10} {'Avg CPI':>10}")
print("-" * 70)

for camp in campaign_summary[:20]:  # Top 20 campaigns by CPI
    print(f"{camp['campaign']:<30} {camp['campaign_type']:<15} ${camp['total_spend']:>9.2f} {camp['total_installs']:>10} ${camp['avg_cpi']:>9.4f}")

print("-" * 70)

# Xác định campaign có vấn đề
total_installs = sum(c['total_installs'] for c in campaign_summary)
total_spend = sum(c['total_spend'] for c in campaign_summary)
avg_cpi_overall = total_spend / total_installs if total_installs > 0 else 0

print(f"\n📊 CPI trung bình network: ${avg_cpi_overall:.4f}")
print("-" * 70)

for camp in campaign_summary:
    # Chỉ đánh giá campaign có đủ data
    if camp['total_installs'] >= 200 or camp['days_active'] >= 7:
        if avg_cpi_overall > 0 and camp['avg_cpi'] > 0:
            deviation = ((camp['avg_cpi'] - avg_cpi_overall) / avg_cpi_overall * 100)
            
            if abs(deviation) > 30:
                direction = "Cao" if deviation > 0 else "Thấp"
                print(f"⚠️ {camp['campaign']}: CPI {direction} hơn {abs(deviation):.1f}% so với trung bình")
                print(f"   - Avg CPI: ${camp['avg_cpi']:.4f}, Installs: {camp['total_installs']}")
```

## Bước 3: Gợi ý

- **Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20%** → báo UA → check tiếp geo (#16) và site_id
- **Campaign CPI cao + ROAS thấp** → xem xét giảm budget
- **Campaign CPI thấp + ROAS cao** → xem xét tăng budget

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA
- Chỉ đánh giá khi campaign có > 200 installs hoặc start > 7 ngày

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Campaign CPI trên Unity cho game "MyGame"
package_name = "com.example.mygame"
network_name = "Unity"

# Step 1: Tìm appId và network
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

networks = growX_ua_list_networks()
unity_code = [n['code'] for n in networks if n['displayName'] == 'Unity'][0]

# Step 2: Query campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    network=unity_code,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

# Step 3: Phân tích
campaign_data = extract_campaign_daily_metrics(campaigns)
campaign_cpi = calculate_campaign_cpi(campaign_data)

# Step 4: Kiểm tra delta CPI
print("\n🔍 KIỂM TRA DELTA CPI THEO CAMPAIGN:")
print("=" * 60)

# Group theo campaign
campaign_by_name = defaultdict(list)
for entry in campaign_cpi:
    campaign_by_name[entry['campaign']].append(entry)

for camp_name, entries in campaign_by_name.items():
    # Sắp xếp theo ngày
    entries.sort(key=lambda x: x['created_day'])
    
    # Kiểm tra trend 3 ngày
    deltas = [e['delta_cpi_pct'] for e in entries[1:] if e['delta_cpi_pct'] is not None]
    
    if len(deltas) >= 2:
        last_3 = deltas[-3:]
        
        # Trend tăng liên tiếp
        if all(d > 0 for d in last_3):
            print(f"🔴 {camp_name}: CPI TĂNG liên tiếp {len(last_3)} ngày")
            for d in last_3:
                print(f"     Δ CPI: {d:.1f}%")
        
        # Trend giảm liên tiếp
        elif all(d < 0 for d in last_3):
            print(f"🟢 {camp_name}: CPI GIẢM liên tiếp {len(last_3)} ngày")
            for d in last_3:
                print(f"     Δ CPI: {d:.1f}%")
        
        # Biến động đột ngột
        for d in deltas:
            if abs(d) > 20:
                print(f"⚠️ {camp_name}: Δ CPI đột ngột {d:.1f}%")

# Step 5: Kết hợp với ROAS để đánh giá chất lượng user
print("\n" + "=" * 70)
print("ĐÁNH GIÁ CHẤT LƯỢNG USER THEO CAMPAIGN:")
print("=" * 70)

campaign_with_roas = []
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    if spend > 0 and installs > 0:
        cpi = spend / installs
        campaign_with_roas.append({
            'campaign': camp_name,
            'cpi': round(cpi, 4),
            'roas_d7': round(roas_d7, 2),
            'spend': round(spend, 2),
            'installs': installs
        })

# Sắp xếp theo CPI
campaign_with_roas.sort(key=lambda x: x['cpi'])

print(f"{'Campaign':<30} {'CPI':>10} {'ROAS_D7':>10} {'Spend':>10} {'Installs':>10}")
print("-" * 70)

for camp in campaign_with_roas[:15]:
    print(f"{camp['campaign']:<30} ${camp['cpi']:>9.4f} {camp['roas_d7']:>9.1f}% ${camp['spend']:>9.2f} {camp['installs']:>10}")

# Đánh giá
print("\n📋 ĐÁNH GIÁ CHI TIẾT:")
print("-" * 50)
for camp in campaign_with_roas:
    if camp['cpi'] > 1.0:  # CPI cao
        if camp['roas_d7'] > 100:
            print(f"✅ {camp['campaign']}: CPI cao nhưng ROAS tốt → User chất lượng")
        else:
            print(f"🔴 {camp['campaign']}: CPI cao + ROAS thấp → Giảm budget")
    else:
        if camp['roas_d7'] > 100:
            print(f"🟢 {camp['campaign']}: CPI thấp + ROAS tốt → Tăng budget")
        else:
            print(f"⚠️ {camp['campaign']}: CPI thấp nhưng ROAS kém → Kiểm tra quality")
```

## Lưu ý quan trọng

1. **CPI Calculation**:
   - CPI = Total Spend / Total Installs (theo campaign và ngày)
   - Luôn dùng weighted average khi tổng hợp từ nhiều ngày

2. **Data Thresholds**:
   - Chỉ đánh giá campaign có > 200 installs hoặc start > 7 ngày
   - Campaign mới test (< 200 installs) → CPI chưa ổn định

3. **Context with ROAS**:
   - CPI cao không phải lúc nào cũng xấu (có thể do user chất lượng cao)
   - Luôn kết hợp CPI với ROAS để đánh giá toàn diện

4. **Campaign Status**:
   - Check `status` trong response: `RUNNING`, `PAUSED`, `PENDING`
   - Chỉ nên phân tích các campaign đang `RUNNING`

5. **Campaign Type**:
   - Phân biệt giữa `APP_INSTALL`, `REEngagement`, `WEB`...
   - Chỉ nên phân tích các campaign `APP_INSTALL` cho CPI analysis

6. **Attribution Window**:
   - Installs có thể bị ảnh hưởng bởi attribution window
   - 1-2 ngày cuối cùng có thể chưa đầy đủ
