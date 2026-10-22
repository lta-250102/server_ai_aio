# Case 8: Network ảnh hưởng dòng tiền (Network LTV/ROAS)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Đánh giá phân bổ budget giữa các network có ổn chưa, network nào thu hồi vốn tốt nhất.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ đầy đủ các metrics SPEND và ROAS theo network, cho phép tính toán LTV ROI và ROAS.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và danh sách network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

networks = growX_ua_list_networks()
active_networks = [n for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]
network_codes = [n['code'] for n in active_networks]
```

### 1.2. Query ROAS và Spend theo từng network
```python
from collections import defaultdict

def get_network_metrics(game_id, network_code, days):
    """
    Lấy metrics cho 1 network trong cửa sổ time
    Trả về: {day: {spend: float, roas_d7: float, roas_d0: float, installs: int}}
    """
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=network_code,
        days=days,
        metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
        getAll=True
    )
    
    daily_metrics = {}
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        roas_d7 = metrics.get('ROAS_D7', 0) or 0
        roas_d0 = metrics.get('ROAS_D0', 0) or 0
        
        if day not in daily_metrics:
            daily_metrics[day] = {'spend': 0, 'installs': 0, 'roas_d7': 0, 'roas_d0': 0, 'weighted_roas': 0}
        
        daily_metrics[day]['spend'] += spend
        daily_metrics[day]['installs'] += installs
        daily_metrics[day]['weighted_roas'] += spend * roas_d7
    
    # Tính weighted average ROAS
    for day, data in daily_metrics.items():
        if data['spend'] > 0:
            data['roas_d7'] = data['weighted_roas'] / data['spend']
        else:
            data['roas_d7'] = 0
        del data['weighted_roas']  # Clean up temp field
    
    return daily_metrics

# Query 14 ngày cho mỗi network
network_data = {}
for net_code in network_codes:
    network_data[net_code] = get_network_metrics(game_id, net_code, 14)
```

### 1.3. Tổng hợp metrics cho toàn bộ 14 ngày
```python
def aggregate_network_ltv(network_data):
    """
    Aggregate metrics cho toàn bộ 14 ngày theo network
    Trả về list of network summary
    """
    results = []
    
    for net_code, daily in network_data.items():
        total_revenue = 0
        total_cost = 0
        total_installs = 0
        days_active = 0
        roas_values = []
        
        for day, data in daily.items():
            spend = data['spend']
            installs = data['installs']
            roas_d7 = data['roas_d7']
            
            total_cost += spend
            total_installs += installs
            days_active += 1
            
            # Tính revenue từ ROAS (vì growX không trả về revenue trực tiếp)
            # ROAS là %: 85 = 85%
            # Revenue = Spend × (ROAS / 100)
            revenue = spend * (roas_d7 / 100)
            total_revenue += revenue
            
            if roas_d7 > 0:
                roas_values.append(roas_d7)
        
        # Tính các chỉ số tổng hợp
        if total_cost > 0:
            ltv_roas_pct = round((total_revenue / total_cost) * 100, 2)
            ltv_roi_pct = round(((total_revenue - total_cost) / total_cost) * 100, 2)
        else:
            ltv_roas_pct = 0
            ltv_roi_pct = 0
        
        avg_roas_d7 = sum(roas_values) / len(roas_values) if roas_values else 0
        
        results.append({
            'media_source': net_code,
            'total_revenue': round(total_revenue, 2),
            'total_cost': round(total_cost, 2),
            'ltv_roi_pct': ltv_roi_pct,
            'ltv_roas_pct': ltv_roas_pct,
            'days_active': days_active,
            'total_installs': total_installs,
            'avg_roas_d7': round(avg_roas_d7, 2)
        })
    
    # Sắp xếp theo LTV ROI
    results.sort(key=lambda x: x['ltv_roi_pct'], reverse=True)
    return results

network_ltv = aggregate_network_ltv(network_data)
```

**Output columns:** `media_source`, `total_revenue`, `total_cost`, `ltv_roi_pct` (%), `ltv_roas_pct` (%), `days_active`

## Bước 2: Phân tích

- **Network mới test**: ROI chưa ổn định nếu spend < $50 và installs < 50 → chưa vội đánh giá
- **Xếp hạng LTV ROI** từ cao → thấp, kết hợp tỷ trọng spend để tìm network ROI thấp + spend lớn (rủi ro cao)
- **So sánh ROAS D0, D3, D7** theo từng ngày để xem trend
- Network có spend lớn nhưng ROI thấp → rủi ro cao nhất

### Phân tích chi tiết:
```python
# Xác định network có rủi ro cao
for net in network_ltv:
    # Network spend top 5 nhưng ROI âm
    if net['total_cost'] > 0:
        cost_pct = (net['total_cost'] / sum(n['total_cost'] for n in network_ltv)) * 100
        if cost_pct > 15 and net['ltv_roi_pct'] < 0:
            print(f"🔴 NGHIÊM TRỌNG: {net['media_source']} chiếm {cost_pct:.1f}% spend nhưng ROI {net['ltv_roi_pct']:.1f}%")

# Network có LTV ROI cao nhất
if network_ltv:
    best_net = network_ltv[0]
    print(f"🏆 Network tốt nhất: {best_net['media_source']} với ROI {best_net['ltv_roi_pct']:.1f}%")
```

## Bước 3: Gợi ý

- **LTV ROI cao hơn trung bình + Retention tốt** → xem xét scale
- **ROAS D7 thấp hơn trung bình 20% + spend top 5** → phân tích xuống campaign (#9) + check Retention
- **ROAS cao hơn trung bình + ổn định 5 ngày** → đề xuất tăng budget/giảm goal để scale
- **ROAS D0/D3/D7 có trend giảm** → cảnh báo UA + check campaign (#9)

## Cảnh báo thresholds
- Network spend top 5 nhưng ROI âm → cảnh báo nghiêm trọng
- ROAS D7 giảm > 20% so với tuần trước → cảnh báo

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Network LTV cho game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Lấy danh sách network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0 and n['supportsReporting']]

# Step 3: Query và aggregate
network_data = {}
for net_code in network_codes:
    network_data[net_code] = get_network_metrics(game_id, net_code, 14)

network_ltv = aggregate_network_ltv(network_data)

# Step 4: Report
print("=" * 60)
print(f"BÁO CÁO NETWORK LTV - {package_name}")
print("=" * 60)
print(f"{'Network':<15} {'Cost':>10} {'Revenue':>10} {'ROAS%':>8} {'ROI%':>8} {'Installs':>10}")
print("-" * 60)

for net in network_ltv:
    print(f"{net['media_source']:<15} ${net['total_cost']:>9.2f} ${net['total_revenue']:>9.2f} {net['ltv_roas_pct']:>7.1f}% {net['ltv_roi_pct']:>7.1f}% {net['total_installs']:>10}")

print("=" * 60)

# Step 5: Cảnh báo
total_spend = sum(n['total_cost'] for n in network_ltv)
for net in network_ltv:
    cost_pct = (net['total_cost'] / total_spend * 100) if total_spend > 0 else 0
    
    if cost_pct > 15 and net['ltv_roi_pct'] < 0:
        print(f"\n⚠️ CẢNH BÁO NGHIÊM TRỌNG: {net['media_source']}")
        print(f"   - Chiếm {cost_pct:.1f}% tổng spend")
        print(f"   - ROI: {net['ltv_roi_pct']:.1f}%")
        print(f"   - Khuyến nghị: Pause hoặc tối ưu gấp")
```

## Lưu ý quan trọng

1. **Revenue Calculation**: 
   - growX không trả về `event_revenue_usd`.
   - Tính ngược: `Revenue = Spend × (ROAS / 100)`.
   - Đảm bảo ROAS là PERCENT (0-100), không phải multiplier.

2. **Weighted Average ROAS**: 
   - Khi tổng hợp ROAS từ nhiều campaigns, dùng weighted average theo spend.
   - Không dùng average đơn giản vì sẽ không chính xác.

3. **Cohort Metrics**:
   - ROAS_D7 chỉ chính xác khi reporting window đủ 7 ngày.
   - Với window < 7 ngày, giá trị có thể chưa ổn định.

4. **Network Reporting**:
   - Chỉ query các network có `supportsReporting = true`.
   - Network không supports reporting sẽ có metrics absent.

5. **LTV (Life Time Value)**:
   - LTV ROI trong case này dựa trên dữ liệu 14 ngày.
   - Để có LTV chính xác hơn, nên query dài hạn hơn (28-90 ngày) nếu available.
