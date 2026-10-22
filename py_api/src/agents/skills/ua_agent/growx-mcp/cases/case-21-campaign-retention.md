# Case 21: Campaign Retention lệch nhiều (Campaign Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định campaign nào trong network có Retention lệch nhiều.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ các metrics RETENTION_D1, RETENTION_D3, RETENTION_D7, RETENTION_D14, RETENTION_D28 và có thể query campaigns trong cùng network.
**Lưu ý:** Retention của growX là dựa trên **app open events** (người dùng quay lại mở game), không phải purchase-based như original case.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

# Xác định network để phân tích
networks = growX_ua_list_networks()
network_code = [n['code'] for n in networks if n['displayName'] == '<network_name>'][0]
```

### 1.2. Query Retention theo campaigns trong network
```python
# Query 14 ngày gần nhất cho network cụ thể
campaigns_14d = growX_ua_list_campaigns(
    appId=game_id,
    network=network_code,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7"],
    getAll=True
)
```

### 1.3. Tổng hợp metrics theo campaign
```python
from collections import defaultdict

def extract_campaign_retention(result):
    """
    Extract retention metrics cho từng campaign
    Trả về: {campaign_name: {day: {installs: int, ret_d1: float, ret_d3: float, ret_d7: float}}}
    """
    campaign_data = defaultdict(lambda: defaultdict(lambda: {
        'installs': 0, 'ret_d1': 0.0, 'ret_d3': 0.0, 'ret_d7': 0.0
    }))
    
    for campaign in result.get('campaigns', []):
        camp_name = campaign.get('name', 'Unknown')
        camp_type = campaign.get('type', campaign.get('campaignType', 'Unknown'))
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        installs = metrics.get('INSTALLS', 0) or 0
        ret_d1 = metrics.get('RETENTION_D1', 0) or 0
        ret_d3 = metrics.get('RETENTION_D3', 0) or 0
        ret_d7 = metrics.get('RETENTION_D7', 0) or 0
        
        campaign_data[camp_name]['daily'][day]['installs'] += installs
        campaign_data[camp_name]['daily'][day]['ret_d1'] = ret_d1
        campaign_data[camp_name]['daily'][day]['ret_d3'] = ret_d3
        campaign_data[camp_name]['daily'][day]['ret_d7'] = ret_d7
        campaign_data[camp_name]['type'] = camp_type
    
    return dict(campaign_data)

campaign_data = extract_campaign_retention(campaigns_14d)
```

### 1.4. Tính toán retention trung bình cho từng campaign
```python
def calculate_campaign_retention(campaign_data):
    """
    Tính weighted average retention cho từng campaign
    Trả về list sorted by deviation from avg
    """
    results = []
    total_weighted_d1 = 0
    total_installs_all = 0
    
    # Tính tổng weighted retention để tính average
    campaign_totals = {}
    for camp_name, data in campaign_data.items():
        daily = data.get('daily', {})
        camp_type = data.get('type', 'Unknown')
        
        total_installs = 0
        weighted_ret_d1 = 0
        weighted_ret_d3 = 0
        weighted_ret_d7 = 0
        days_active = 0
        
        for day, d in daily.items():
            total_installs += d['installs']
            weighted_ret_d1 += d['installs'] * d['ret_d1']
            weighted_ret_d3 += d['installs'] * d['ret_d3']
            weighted_ret_d7 += d['installs'] * d['ret_d7']
            days_active += 1
        
        campaign_totals[camp_name] = {
            'campaign': camp_name,
            'campaign_type': camp_type,
            'total_installs': total_installs,
            'days_active': days_active,
            'weighted_ret_d1': weighted_ret_d1,
            'weighted_ret_d3': weighted_ret_d3,
            'weighted_ret_d7': weighted_ret_d7
        }
        
        total_weighted_d1 += weighted_ret_d1
        total_installs_all += total_installs
    
    # Tính weighted average retention cho từng campaign
    for camp, data in campaign_totals.items():
        if data['total_installs'] > 0:
            avg_ret_d1 = data['weighted_ret_d1'] / data['total_installs']
            avg_ret_d3 = data['weighted_ret_d3'] / data['total_installs']
            avg_ret_d7 = data['weighted_ret_d7'] / data['total_installs']
        else:
            avg_ret_d1 = 0
            avg_ret_d3 = 0
            avg_ret_d7 = 0
        
        data['avg_ret_d1'] = round(avg_ret_d1, 2)
        data['avg_ret_d3'] = round(avg_ret_d3, 2)
        data['avg_ret_d7'] = round(avg_ret_d7, 2)
    
    # Tính average retention toàn network
    if total_installs_all > 0:
        avg_ret_d1_all = total_weighted_d1 / total_installs_all
    else:
        avg_ret_d1_all = 0
    
    # Tính deviation so với average
    for camp, data in campaign_totals.items():
        if avg_ret_d1_all > 0 and data['total_installs'] > 0:
            deviation = ((data['avg_ret_d1'] - avg_ret_d1_all) / avg_ret_d1_all) * 100
        else:
            deviation = 0
        
        data['avg_ret_d1_all'] = round(avg_ret_d1_all, 2)
        data['deviation_pct'] = round(deviation, 2)
        
        results.append(data)
    
    # Sort by deviation desc
    results.sort(key=lambda x: x['deviation_pct'], reverse=True)
    return results

campaign_retention = calculate_campaign_retention(campaign_data)
```

**Output columns:** `campaign`, `campaign_type`, `install_date`, `total_installs`, `rr_d1_pct`, `rr_d3_pct`, `rr_d7_pct`, `deviation_pct`

- **Retention DN** = tỷ lệ user quay lại ở ngày N sau install × 100
- growX trả về **PERCENT_0_100** (ví dụ: `35` nghĩa là 35%)
- Tính deviation so với average retention toàn network

## Bước 2: Phân tích

- **Đánh giá khi campaign đã chạy > 3 ngày và có > 200 installs**
- **Campaign RR giảm đột ngột** dù campaign network ổn định → targeting/audience bị thay đổi hoặc network tự mở rộng audience
- **Check tiếp geo (#22)/site_id (#23)**. Nếu tất cả geo, site_id, creative đều giảm chung → do chất lượng campaign giảm

### Phân tích chi tiết:
```python
# Hiển thị campaign retention
print("=" * 80)
print(f"BÁO CÁO CAMPAIGN RETENTION - {network_code}")
print("=" * 80)
print(f"{'Campaign':<30} {'Type':<15} {'Installs':>10} {'D1 Ret%':>10} {'Dev%':>10}")
print("-" * 80)

for camp in campaign_retention:
    if camp['total_installs'] >= 200:
        status = "🟢" if camp['deviation_pct'] > 0 else "🔴"
        print(f"{status} {camp['campaign']:<28} {camp['campaign_type']:<15} "
              f"{camp['total_installs']:>10} {camp['avg_ret_d1']:>9.2f}% {camp['deviation_pct']:>9.1f}%")
    else:
        print(f"⏳ {camp['campaign']:<28} {camp['campaign_type']:<15} "
              f"{camp['total_installs']:>10} {camp['avg_ret_d1']:>9.2f}% N/A (chưa đủ data)")

print("-" * 80)
print(f"📊 Average D1 Retention toàn network: {campaign_retention[0]['avg_ret_d1_all'] if campaign_retention else 0:.2f}%")
print("=" * 80)
```

## Bước 3: Gợi ý

- **Campaign RR thấp kéo dài > 3 ngày hoặc biến động > 20%** → kết hợp check ROAS → giảm ưu tiên + check geo (#22)
- **Campaign RR cao trong top 5 + ROAS tăng trưởng** → tiếp tục ưu tiên ngân sách dài hạn
- **Tất cả campaign đều có RR giảm** → cảnh báo UA check level network
- **Facebook/Tiktok/Google: RR thấp hơn 30% so với avg network** → check ROAS và spending, nếu < 20% toàn bộ network → suggest off camp

## Cảnh báo thresholds
- Chỉ đánh giá khi campaign có > 200 installs và chạy > 3 ngày
- RR biến động > 20% → cảnh báo
- RR thấp kéo dài > 3 ngày → cảnh báo
- RR thấp hơn 30% so với avg network → suggest off camp (FB/Tiktok/Google)

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Campaign Retention trên Unity cho game "MyGame"
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
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7", "ROAS_D7"],
    getAll=True
)

# Step 3: Phân tích
campaign_data = extract_campaign_retention(campaigns)
campaign_retention = calculate_campaign_retention(campaign_data)

# Step 4: Kết hợp với ROAS
print("\n" + "=" * 80)
print("KẾT HỢP RETENTION VÀ ROAS THEO CAMPAIGN:")
print("=" * 80)
print(f"{'Campaign':<30} {'D1 Ret%':>10} {'D7 Ret%':>10} {'ROAS_D7':>10} {'Installs':>10}")
print("-" * 80)

for camp in campaign_retention[:15]:
    print(f"{camp['campaign']:<30} {camp['avg_ret_d1']:>9.2f}% {camp['avg_ret_d3']:>9.2f}% "
          f"N/A {camp['total_installs']:>10}")

# Step 5: Đánh giá và cảnh báo
print("\n📋 ĐÁNH GIÁ CHẤT LƯỢNG CAMPAIGN:")
print("-" * 50)

avg_ret_d1_all = campaign_retention[0]['avg_ret_d1_all'] if campaign_retention else 0

for camp in campaign_retention:
    if camp['total_installs'] < 200:
        print(f"⏳ {camp['campaign']}: Chưa đủ data ({camp['total_installs']} installs)")
        continue
    
    deviation = camp['deviation_pct']
    
    if deviation < -20:
        print(f"🔴 {camp['campaign']}: RR THẤP hơn {abs(deviation):.1f}% - Cần kiểm tra targeting")
    elif deviation > 20:
        print(f"🟢 {camp['campaign']}: RR CAO hơn {deviation:.1f}% - Ưu tiên thêm budget")
    else:
        print(f"✅ {camp['campaign']}: RR ổn định (deviation: {deviation:+.1f}%)")

# Step 6: Phát hiện trend giảm retention
print("\n🔍 KIỂM TRA TREND RETENTION:")
print("-" * 50)

for camp_name, data in campaign_data.items():
    daily = data.get('daily', {})
    sorted_days = sorted(daily.keys())
    
    if len(sorted_days) >= 3:
        first_3 = sorted_days[:3]
        last_3 = sorted_days[-3:]
        
        first_avg = sum(daily[d]['ret_d1'] for d in first_3 if daily[d]['installs'] > 0) / max(len(first_3), 1)
        last_avg = sum(daily[d]['ret_d1'] for d in last_3 if daily[d]['installs'] > 0) / max(len(last_3), 1)
        
        if first_avg > 0:
            delta = ((last_avg - first_avg) / first_avg) * 100
            
            if delta < -20:
                print(f"🔴 {camp_name}: Retention giảm {abs(delta):.1f}% trong 3 ngày gần nhất")
```

## Kết hợp với Geo Retention (Case 22) và Site ID Retention (Case 23)

Để phân tích sâu hơn, nên kết hợp với geo và site_id retention khi có data:

```python
# Nếu campaign name chứa geo code, có thể phân tích proxy
import re

geo_retention_proxy = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
    # Extract geo code từ campaign name
    geo_match = re.search(r'\[([A-Z]{2})\]', camp_name) or re.search(r'^([A-Z]{2})_', camp_name)
    if geo_match:
        geo = geo_match.group(1)
        geo_retention_proxy[geo]['installs'] += installs
        geo_retention_proxy[geo]['weighted_ret_d1'] += installs * ret_d1

# Tính retention proxy theo geo
for geo, data in geo_retention_proxy.items():
    if data['installs'] > 0:
        data['ret_d1'] = data['weighted_ret_d1'] / data['installs']

sorted_geo = sorted(geo_retention_proxy.items(), key=lambda x: x[1]['ret_d1'], reverse=True)
print("\n🌍 RETENTION PROXY THEO GEO (dựa trên campaign naming):")
for geo, data in sorted_geo:
    print(f"{geo}: D1 Ret = {data['ret_d1']:.2f}%, Installs = {data['installs']}")
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

4. **Data Thresholds**:
   - Chỉ đánh giá campaign có > 200 installs và chạy > 3 ngày.
   - Campaign mới test (< 200 installs) → RR chưa ổn định.

5. **Context with ROAS và CPI**:
   - RR cao không phải lúc nào cũng tốt (có thể do user low-value).
   - Luôn kết hợp RR với ROAS và CPI để đánh giá toàn diện.

6. **GrowX vs Purchase-based**:
   - growX retention dựa trên **app open events** (user mở lại game).
   - Original case dựa trên **purchase events** (user mua hàng).
   - Hai metrics này khác nhau.

7. **Campaign Status**:
   - Check `status` trong response: `RUNNING`, `PAUSED`, `PENDING`.
   - Chỉ nên phân tích các campaign đang `RUNNING`.

## Ma trận đánh giá Campaign

| RR cao + ROAS cao | RR cao + ROAS thấp |
|-------------------|-------------------|
| 🟢 **Tốt nhất** - Scale ngay | ⚠️ User giữ chân tốt nhưng không chi tiêu |

| RR thấp + ROAS cao | RR thấp + ROAS thấp |
|-------------------|-------------------|
| ⚠️ User chi tiêu tốt nhưng không quay lại | 🔴 **Tệ nhất** - Giảm budget hoặc pause |

## Benchmark tham khảo (Campaign Retention)

| Campaign Type | D1 Retention Target | D7 Retention Target |
|--------------|---------------------|---------------------|
| App Install (Hypercasual) | 25-35% | 10-18% |
| App Install (Casual) | 30-40% | 12-20% |
| App Install (Mid-core) | 35-45% | 15-25% |
| Retargeting/Re-engagement | 40-50% | 20-30% |

*Lưu ý: Benchmark chỉ mang tính tham khảo, phụ thuộc vào thể loại game và region.*
