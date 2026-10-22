# Case 20: Network Retention tốt/kém (Network Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định network nào đang mang lại user có Retention tốt/kém.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ các metrics RETENTION_D1, RETENTION_D3, RETENTION_D7, RETENTION_D14, RETENTION_D28 và có thể query theo network.
**Lưu ý:** Retention của growX là dựa trên **app open events** (người dùng quay lại mở game), không phải purchase-based như original case.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và danh sách network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

networks = growX_ua_list_networks()
active_networks = [n for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]
network_codes = [n['code'] for n in active_networks]
```

### 1.2. Query Retention theo từng network
```python
from collections import defaultdict

def get_network_retention(game_id, network_code, days):
    """
    Lấy retention metrics cho 1 network
    Trả về: {day: {installs: int, ret_d1: float, ret_d3: float, ret_d7: float}}
    """
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=network_code,
        days=days,
        metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D3", "RETENTION_D7"],
        getAll=True
    )
    
    daily_metrics = defaultdict(lambda: {
        'installs': 0, 'ret_d1': 0.0, 'ret_d3': 0.0, 'ret_d7': 0.0,
        'weighted_ret_d1': 0.0, 'weighted_ret_d3': 0.0, 'weighted_ret_d7': 0.0
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
        
        del data['weighted_ret_d1']
        del data['weighted_ret_d3']
        del data['weighted_ret_d7']
    
    return dict(daily_metrics)

# Query 14 ngày cho mỗi network
network_retention_data = {}
for net_code in network_codes:
    network_retention_data[net_code] = get_network_retention(game_id, net_code, 14)
```

### 1.3. Tổng hợp metrics theo network
```python
def aggregate_network_retention(network_retention_data):
    """
    Aggregate retention metrics cho toàn bộ 14 ngày theo network
    Trả về list of network summary
    """
    results = []
    
    for net_code, daily in network_retention_data.items():
        total_installs = 0
        total_ret_d1 = 0
        total_ret_d3 = 0
        total_ret_d7 = 0
        days_active = 0
        
        for day, data in daily.items():
            total_installs += data['installs']
            total_ret_d1 += data['installs'] * data['ret_d1']
            total_ret_d3 += data['installs'] * data['ret_d3']
            total_ret_d7 += data['installs'] * data['ret_d7']
            days_active += 1
        
        # Tính weighted average retention
        if total_installs > 0:
            avg_ret_d1 = total_ret_d1 / total_installs
            avg_ret_d3 = total_ret_d3 / total_installs
            avg_ret_d7 = total_ret_d7 / total_installs
        else:
            avg_ret_d1 = 0
            avg_ret_d3 = 0
            avg_ret_d7 = 0
        
        results.append({
            'media_source': net_code,
            'total_installs': total_installs,
            'days_active': days_active,
            'ret_d1': round(avg_ret_d1, 2),
            'ret_d3': round(avg_ret_d3, 2),
            'ret_d7': round(avg_ret_d7, 2)
        })
    
    return results

network_retention = aggregate_network_retention(network_retention_data)
```

**Output columns:** `media_source`, `install_date`, `total_installs`, `rr_d1_pct`, `rr_d3_pct`, `rr_d7_pct`, `deviation_pct`

- **Retention DN** = tỷ lệ user quay lại ở ngày N sau install × 100
- growX trả về **PERCENT_0_100** (ví dụ: `35` nghĩa là 35%)
- Tính deviation so với average retention toàn game

## Bước 2: Phân tích

- **Network RR thấp hơn hẳn mặt bằng chung** dù CPI/ROAS cao hơn → check fraud
- **Network RR cao** → nguồn user chất lượng, xem xét ưu tiên thêm
- **Chỉ đánh giá khi có > 200 installs** mới có ý nghĩa thống kê
- **Network mới test** → RR chưa ổn định

### Phân tích chi tiết:
```python
# Tính average retention toàn game
total_installs_all = sum(n['total_installs'] for n in network_retention)
if total_installs_all > 0:
    # Tính weighted average retention toàn game
    total_weighted_d1 = 0
    total_weighted_d3 = 0
    total_weighted_d7 = 0
    
    for net_code, daily in network_retention_data.items():
        for day, data in daily.items():
            total_weighted_d1 += data['installs'] * data['ret_d1']
            total_weighted_d3 += data['installs'] * data['ret_d3']
            total_weighted_d7 += data['installs'] * data['ret_d7']
    
    avg_ret_d1_all = total_weighted_d1 / total_installs_all
    avg_ret_d3_all = total_weighted_d3 / total_installs_all
    avg_ret_d7_all = total_weighted_d7 / total_installs_all
    
    print("=" * 70)
    print(f"BÁO CÁO NETWORK RETENTION - {package_name}")
    print("=" * 70)
    print(f"{'Network':<15} {'Installs':>10} {'D1 Ret%':>10} {'D3 Ret%':>10} {'D7 Ret%':>10} {'Δ D1%':>10}")
    print("-" * 70)
    
    for net in network_retention:
        deviation_d1 = ((net['ret_d1'] - avg_ret_d1_all) / avg_ret_d1_all * 100) if avg_ret_d1_all > 0 else 0
        
        # Chỉ hiển thị network có đủ data
        if net['total_installs'] >= 200:
            status = "🟢" if deviation_d1 > 0 else "🔴"
            print(f"{status} {net['media_source']:<13} {net['total_installs']:>10} "
                  f"{net['ret_d1']:>9.2f}% {net['ret_d3']:>9.2f}% {net['ret_d7']:>9.2f} "
                  f"{deviation_d1:>+9.1f}%")
    
    print("-" * 70)
    print(f"📊 Average toàn game: D1={avg_ret_d1_all:.2f}%, D3={avg_ret_d3_all:.2f}%, D7={avg_ret_d7_all:.2f}%")
    print("=" * 70)
```

## Bước 3: Gợi ý

- **Network RR thấp kéo dài > 7 ngày hoặc biến động đột ngột > 20%** → kết hợp check ROAS → giảm ưu tiên + check campaign (#21)
- **Network RR cao trong top 5 + ROAS tăng trưởng qua các cohort** → tiếp tục ưu tiên ngân sách dài hạn
- **Tất cả network đều có RR giảm** → cảnh báo UA check level app (bug/MO issue)
- **Network có RR cao nhưng spend thấp** → xem xét scale budget

## Cảnh báo thresholds
- Chỉ đánh giá khi network có > 200 installs
- RR biến động > 20% → cảnh báo
- RR thấp kéo dài > 7 ngày → cảnh báo

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Network Retention cho game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Lấy danh sách network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]

# Step 3: Query và aggregate
network_retention_data = {}
for net_code in network_codes:
    network_retention_data[net_code] = get_network_retention(game_id, net_code, 14)

network_retention = aggregate_network_retention(network_retention_data)

# Step 4: Kết hợp với ROAS và CPI để đánh giá toàn diện
print("\n" + "=" * 80)
print("ĐÁNH GIÁ TOÀN DIỆN: RETENTION + ROAS + CPI")
print("=" * 80)
print(f"{'Network':<15} {'Installs':>10} {'D1 Ret%':>10} {'D7 Ret%':>10} {'ROAS_D7':>10} {'CPI':>10}")
print("-" * 80)

for net_code in network_codes:
    # Lấy retention
    net_ret = [n for n in network_retention if n['media_source'] == net_code]
    if not net_ret:
        continue
    net_data = net_ret[0]
    
    # Lấy ROAS và Spend
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=net_code,
        days=14,
        metrics=["SPEND", "INSTALLS", "ROAS_D7", "RETENTION_D7"],
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
        
        print(f"{net_code:<15} {net_data['total_installs']:>10} "
              f"{net_data['ret_d1']:>9.2f}% {net_data['ret_d7']:>9.2f}% "
              f"{roas_d7:>9.1f}% ${cpi:>9.4f}")

print("=" * 80)

# Step 5: Đánh giá và cảnh báo
print("\n📋 ĐÁNH GIÁ CHẤT LƯỢNG NETWORK:")
print("-" * 50)

total_installs_all = sum(n['total_installs'] for n in network_retention)
if total_installs_all > 0:
    total_weighted_d1 = 0
    for net_code, daily in network_retention_data.items():
        for day, data in daily.items():
            total_weighted_d1 += data['installs'] * data['ret_d1']
    
    avg_ret_d1_all = total_weighted_d1 / total_installs_all
    
    for net in network_retention:
        if net['total_installs'] < 200:
            print(f"⏳ {net['media_source']}: Chưa đủ data ({net['total_installs']} installs)")
            continue
        
        deviation = ((net['ret_d1'] - avg_ret_d1_all) / avg_ret_d1_all * 100) if avg_ret_d1_all > 0 else 0
        
        if deviation < -20:
            print(f"🔴 {net['media_source']}: RR THẤP hơn {abs(deviation):.1f}% - Cần kiểm tra fraud")
        elif deviation > 20:
            print(f"🟢 {net['media_source']}: RR CAO hơn {deviation:.1f}% - Ưu tiên thêm budget")
        else:
            print(f"✅ {net['media_source']}: RR ổn định (deviation: {deviation:+.1f}%)")

# Step 6: Phát hiện tất cả network đều giảm retention
print("\n🔍 PHÁT HIỆN ANOMALY:")
print("-" * 50)

# So sánh 7 ngày gần nhất với 7 ngày trước
anomaly_detected = False
for net_code in network_codes:
    daily = network_retention_data.get(net_code, {})
    sorted_days = sorted(daily.keys())
    
    if len(sorted_days) >= 7:
        first_7 = sorted_days[:7]
        last_7 = sorted_days[-7:]
        
        first_avg = sum(daily[d]['ret_d1'] for d in first_7 if daily[d]['installs'] > 0) / max(len(first_7), 1)
        last_avg = sum(daily[d]['ret_d1'] for d in last_7 if daily[d]['installs'] > 0) / max(len(last_7), 1)
        
        if first_avg > 0:
            delta = ((last_avg - first_avg) / first_avg) * 100
            
            if delta < -20:
                print(f"⚠️ {net_code}: Retention giảm {abs(delta):.1f}% - Cảnh báo")
                anomaly_detected = True

if not anomaly_detected:
    print("✅ Không phát hiện anomaly retention đáng kể")
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
   - Chỉ đánh giá network có > 200 installs mới có ý nghĩa thống kê.
   - Network mới test (< 200 installs) → RR chưa ổn định.

5. **GrowX vs Purchase-based**:
   - growX retention dựa trên **app open events** (user mở lại game).
   - Original case dựa trên **purchase events** (user mua hàng).
   - Hai metrics này khác nhau.

6. **Context with ROAS và CPI**:
   - RR cao không phải lúc nào cũng tốt (có thể do user low-value).
   - Luôn kết hợp RR với ROAS và CPI để đánh giá toàn diện.

## Ma trận đánh giá Network

| RR cao + ROAS cao | RR cao + ROAS thấp |
|-------------------|-------------------|
| 🟢 **Tốt nhất** - Ưu tiên scale | ⚠️ Cần kiểm tra - User giữ chân tốt nhưng không chi tiêu |

| RR thấp + ROAS cao | RR thấp + ROAS thấp |
|-------------------|-------------------|
| ⚠️ Cần kiểm tra - User chi tiêu tốt nhưng không quay lại | 🔴 **Tệ nhất** - Xem xét giảm budget hoặc pause |

## Benchmark tham khảo (App Open Retention theo Network)

| Network | D1 Retention Target | D7 Retention Target |
|---------|---------------------|---------------------|
| Unity | 25-35% | 10-18% |
| AppLovin | 25-35% | 10-18% |
| Mintegral | 20-30% | 8-15% |
| Moloco | 20-30% | 8-15% |
| Facebook | 25-35% | 10-18% |

*Lưu ý: Benchmark chỉ mang tính tham khảo, phụ thuộc vào thể loại game và region.*
