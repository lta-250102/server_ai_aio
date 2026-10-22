# Case 3: Campaign trong network biến động (Campaign Analysis)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định campaign nào là nguyên nhân chính gây biến động cost trong network đang biến động.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và xác định network
```python
# Tìm appId từ package_name
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

# Xác định network code
networks = growX_ua_list_networks()
network_code = [n['code'] for n in networks if n['displayName'] == '<network_name>'][0]
```

### 1.2. Query campaigns trong network
Dùng `growX_ua_list_campaigns` với filter network để lấy tất cả campaigns:

```python
# Query 14 ngày gần nhất cho network cụ thể
campaigns_14d = growX_ua_list_campaigns(
    appId=game_id,
    network=network_code,  # Lọc theo network
    days=14,
    getAll=True
)
```

### 1.3. Tổng hợp Spend theo campaign và ngày
```python
from collections import defaultdict

def extract_campaign_daily_spend(result):
    """
    Extract spend grouped by campaign và day
    Trả về: {campaign_name: {day: spend, campaign_type: type}}
    """
    campaign_spend = {}
    
    for campaign in result.get('campaigns', []):
        camp_name = campaign.get('name', 'Unknown')
        camp_type = campaign.get('type', campaign.get('campaignType', 'Unknown'))
        metrics = campaign.get('metrics', {})
        spend = metrics.get('SPEND', 0) or 0
        day = campaign.get('reportingDay', '')
        
        if camp_name not in campaign_spend:
            campaign_spend[camp_name] = {'daily': {}, 'type': camp_type}
        
        campaign_spend[camp_name]['daily'][day] = spend
        campaign_spend[camp_name]['type'] = camp_type
    
    return campaign_spend

campaign_data = extract_campaign_daily_spend(campaigns_14d)
```

### 1.4. Tính toán Delta (DoD)
```python
def calculate_campaign_delta(campaign_spend):
    """Tính delta_abs và delta_pct cho từng campaign"""
    results = []
    
    for camp_name, data in campaign_spend.items():
        camp_type = data['type']
        daily = data['daily']
        
        # Sắp xếp theo ngày
        sorted_days = sorted(daily.keys())
        
        for i, day in enumerate(sorted_days):
            current_spend = daily[day]
            
            if i > 0:
                prev_spend = daily[sorted_days[i-1]]
                delta_abs = round(current_spend - prev_spend, 2)
                
                if prev_spend > 0:
                    delta_pct = round(delta_abs / prev_spend * 100, 2)
                else:
                    delta_pct = None
            else:
                delta_abs = 0
                delta_pct = None
            
            results.append({
                'campaign': camp_name,
                'campaign_type': camp_type,
                'created_day': day,
                'cost': round(current_spend, 2),
                'delta_abs': delta_abs,
                'delta_pct': delta_pct
            })
    
    return results

campaign_delta = calculate_campaign_delta(campaign_data)
```

### 1.5. Xác định top campaigns theo spend
```python
# Tổng spend theo campaign
camp_totals = {}
for entry in campaign_delta:
    camp = entry['campaign']
    camp_totals[camp] = camp_totals.get(camp, 0) + entry['cost']

# Total spend của network
total_spend = sum(camp_totals.values())

# Tính % contribution
for camp, total in camp_totals.items():
    camp_totals[camp] = {
        'total': round(total, 2),
        'pct': round(total / total_spend * 100, 2) if total_spend > 0 else 0
    }

# Sắp xếp theo total spend
top_campaigns = sorted(camp_totals.items(), key=lambda x: x[1]['total'], reverse=True)
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `cost`, `delta_abs` (DoD), `delta_pct` (DoD%)

## Bước 2: Phân tích

- So sánh Δ Cost để xem campaign nào tăng/giảm bất thường so với cùng kì
- Xác định trend tương tự case 1 với cost của từng campaign
- Campaign chiếm > 30% total spend của network → **campaign chủ đạo** (major driver)
- Campaign mới xuất hiện → kiểm tra creative, targeting

### Tiêu chí nhận diện vấn đề:
- **Campaign chiếm > 30% spend**: Đây là campaign chủ đạo, biến động của nó ảnh hưởng lớn nhất
- **Δ > 20% so với ngày trước**: Biến động đáng chú ý
- **Campaign mới < 3 ngày**: Chưa ổn định, cần monitoring

## Bước 3: Gợi ý

- **Campaign có trend tăng/giảm** → đánh giá thêm ROAS, phân tích xuống geo (#10)
- **Tất cả campaign trong cùng network có cost giảm > 20% so với cùng kì** → cảnh báo UA kiểm tra policy creative hoặc vấn đề với network
- **Campaign đã start 3 ngày kể từ ngày tạo nhưng không có install hoặc cost < $50 daily** → cảnh báo (campaign chưa hoạt động hiệu quả)

## Cảnh báo thresholds
- Cost giảm > 20% so với cùng kì → cảnh báo UA
- Cost < $50 daily sau 3 ngày start → cảnh báo
- Campaign chiếm > 30% total spend nhưng ROAS < 100% → cần tối ưu hoặc pause

## Ví dụ minh họa

```python
# Ví dụ: Phân tích campaigns trên Unity cho game "MyGame"
package_name = "com.example.mygame"
network_name = "Unity"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Tìm network code
networks = growX_ua_list_networks()
unity_code = [n['code'] for n in networks if n['displayName'] == 'Unity'][0]

# Step 3: Query campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    network=unity_code,
    days=14,
    getAll=True
)

# Step 4: Phân tích
campaign_data = extract_campaign_daily_spend(campaigns)
campaign_delta = calculate_campaign_delta(campaign_data)
top_campaigns = identify_major_drivers(campaign_data)

# Step 5: Report
for camp, stats in top_campaigns[:5]:
    print(f"{camp}: ${stats['total']} ({stats['pct']}%)")
    
    # Check if major driver with issues
    if stats['pct'] > 30:
        # Check ROAS
        camp_details = [c for c in campaigns['campaigns'] if c['name'] == camp][0]
        roas = camp_details.get('metrics', {}).get('ROAS_D7', 0) or 0
        if roas < 100:
            print(f"  ⚠️ MAJOR ISSUE: {camp} chiếm {stats['pct']}% nhưng ROAS_D7 = {roas}%")
```

## Lưu ý quan trọng

1. **Campaign status**: Check `status` trong response của `growX_ua_list_campaigns`:
   - `RUNNING`: Campaign đang hoạt động
   - `PAUSED`: Campaign đã pause
   - `PENDING`: Campaign đang chờ phê duyệt
   
2. **Network reporting**: Một số network có `supportsReporting = false`, khi đó metrics sẽ absent. Check `metricsSupported` trong response.

3. **Cohort metrics**: ROAS và Retention là cohort metrics, cần đảm bảo reporting window đủ 7+ ngày để có giá trị D7 chính xác.
