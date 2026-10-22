# Case 9: ROAS của campaign (Campaign ROAS Analysis)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Đánh giá ROAS của từng campaign, xem có allocate budget giữa các campaign ổn chưa.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ đầy đủ các metrics SPEND và ROAS theo campaign. Ta có thể filter theo network để phân tích chi tiết.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId và network
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

# Xác định network để phân tích
networks = growX_ua_list_networks()
network_code = [n['code'] for n in networks if n['displayName'] == '<network_name>'][0]
```

### 1.2. Query campaigns trong network
```python
# Query 14 ngày gần nhất cho network cụ thể
campaigns_14d = growX_ua_list_campaigns(
    appId=game_id,
    network=network_code,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
    getAll=True
)
```

### 1.3. Tổng hợp metrics theo campaign
```python
from collections import defaultdict

def extract_campaign_metrics(result):
    """
    Extract và aggregate metrics theo campaign
    Trả về: {campaign_name: {spend: float, revenue: float, roas_d7: float, ...}}
    """
    campaign_data = defaultdict(lambda: {
        'spend': 0.0,
        'installs': 0,
        'revenue': 0.0,
        'roas_d7': 0.0,
        'roas_d0': 0.0,
        'camp_type': 'Unknown',
        'weighted_roas': 0.0,
    })
    
    for campaign in result.get('campaigns', []):
        camp_name = campaign.get('name', 'Unknown')
        camp_type = campaign.get('type', campaign.get('campaignType', 'Unknown'))
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        roas_d7 = metrics.get('ROAS_D7', 0) or 0
        roas_d0 = metrics.get('ROAS_D0', 0) or 0
        
        campaign_data[camp_name]['spend'] += spend
        campaign_data[camp_name]['installs'] += installs
        campaign_data[camp_name]['camp_type'] = camp_type
        campaign_data[camp_name]['weighted_roas'] += spend * roas_d7
    
    # Tính weighted average ROAS và revenue
    for camp, data in campaign_data.items():
        if data['spend'] > 0:
            data['roas_d7'] = data['weighted_roas'] / data['spend']
            # Revenue = Spend × (ROAS / 100)
            data['revenue'] = data['spend'] * (data['roas_d7'] / 100)
        else:
            data['roas_d7'] = 0
            data['revenue'] = 0
        
        del data['weighted_roas']  # Clean up
    
    return dict(campaign_data)

campaign_metrics = extract_campaign_metrics(campaigns_14d)
```

### 1.4. Tính toán ROI cho từng campaign
```python
def calculate_campaign_roi(campaign_data):
    """
    Tính ROI và xếp hạng campaigns
    Trả về list sorted by ROI desc
    """
    results = []
    
    for camp_name, data in campaign_data.items():
        spend = data['spend']
        revenue = data['revenue']
        roas_d7 = data['roas_d7']
        
        if spend > 0:
            roi_pct = round((revenue - spend) / spend * 100, 2)
        else:
            roi_pct = 0
        
        results.append({
            'campaign': camp_name,
            'campaign_type': data['camp_type'],
            'cost': round(spend, 2),
            'revenue': round(revenue, 2),
            'roi_pct': roi_pct,
            'roas_d7': round(roas_d7, 2),
            'installs': data['installs']
        })
    
    # Sort by ROI desc
    results.sort(key=lambda x: x['roi_pct'], reverse=True)
    return results

campaign_roi = calculate_campaign_roi(campaign_metrics)
```

**Output columns:** `campaign`, `campaign_type`, `created_day`, `revenue`, `cost`, `roi_pct`

## Bước 2: Phân tích

- **Xếp hạng campaign** trong network theo ROAS cao → thấp, kết hợp tỷ trọng spend
- **Campaign có spend > 30% total network spend** → campaign chủ đạo (major driver)
- **Campaign ROI < 0%** → đang lỗ
- **Campaign ROI tăng liên tục 3 ngày** → đang cải thiện

### Phân tích chi tiết:
```python
# Tính total spend của network
total_spend = sum(c['cost'] for c in campaign_roi)

# Xác định campaigns chủ đạo
print("=" * 70)
print(f"BÁO CÁO CAMPAIGN ROAS - {network_code}")
print("=" * 70)
print(f"{'Campaign':<30} {'Type':<15} {'Spend':>10} {'Revenue':>10} {'ROI%':>8} {'ROAS_D7':>8}")
print("-" * 70)

for camp in campaign_roi[:20]:  # Top 20 campaigns
    camp_pct = (camp['cost'] / total_spend * 100) if total_spend > 0 else 0
    marker = "🔴" if camp['roi_pct'] < 0 and camp_pct > 5 else "🟢"
    print(f"{marker} {camp['campaign']:<28} {camp['campaign_type']:<15} ${camp['cost']:>9.2f} ${camp['revenue']:>9.2f} {camp['roi_pct']:>7.1f}% {camp['roas_d7']:>7.1f}%")

print("=" * 70)

# Cảnh báo: Campaign spend > 30% nhưng ROI âm
for camp in campaign_roi:
    camp_pct = (camp['cost'] / total_spend * 100) if total_spend > 0 else 0
    if camp_pct > 30 and camp['roi_pct'] < 0:
        print(f"\n🔴 NGHIÊM TRỌNG: {camp['campaign']}")
        print(f"   - Chiếm {camp_pct:.1f}% tổng spend")
        print(f"   - ROI: {camp['roi_pct']:.1f}% (đang lỗ)")
        print(f"   - Khuyến nghị: Xem xét pause hoặc tối ưu gấp")
```

## Bước 3: Gợi ý

### Facebook, TikTok, Google:
- **ROAS campaign < 30%** trong 3 ngày liên tiếp so với ROAS trung bình game → thống kê cost_cohort report UA
- **Spending < 30%** → suggest tắt campaign
- **Spending > 30%** → check geo (#10)

### Các mạng khác:
- **ROAS có trend giảm/tăng** trong 3 ngày liên tiếp hoặc thay đổi > 20% → phân tích xuống geo (#10) và site_id (#11)
- **Campaign ROI cao + spend tăng** → scale thêm
- **Campaign ROI âm + spend lớn** → xem xét pause

## Cảnh báo thresholds
- ROAS < 30% trong 3 ngày liên tiếp → cảnh báo
- Campaign spend > 30% total network nhưng ROI âm → cảnh báo nghiêm trọng

## Ví dụ minh họa

```python
# Ví dụ: Phân tích Campaign ROAS trên Unity cho game "MyGame"
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
    metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
    getAll=True
)

# Step 3: Phân tích
campaign_metrics = extract_campaign_metrics(campaigns)
campaign_roi = calculate_campaign_roi(campaign_metrics)

# Step 4: Report
total_spend = sum(c['cost'] for c in campaign_roi)

for camp in campaign_roi:
    camp_pct = (camp['cost'] / total_spend * 100) if total_spend > 0 else 0
    
    # Cảnh báo theo thresholds
    if camp_pct > 30 and camp['roi_pct'] < 0:
        print(f"🔴 NGHIÊM TRỌNG: {camp['campaign']} - Chiếm {camp_pct:.1f}% spend nhưng ROI {camp['roi_pct']:.1f}%")
    elif camp['roi_pct'] < 30 and camp_pct > 5:
        print(f"⚠️ CẢNH BÁO: {camp['campaign']} - ROI {camp['roi_pct']:.1f}% (< 30%)")
    elif camp['roi_pct'] > 100:
        print(f"🟢 TỐT: {camp['campaign']} - ROI {camp['roi_pct']:.1f}% (suggest scale)")
```

## Lưu ý quan trọng

1. **Revenue Calculation**:
   - growX không trả về `event_revenue_usd`.
   - Tính ngược: `Revenue = Spend × (ROAS / 100)`.
   - Đảm bảo ROAS là PERCENT (0-100), không phải multiplier.

2. **Weighted Average ROAS**:
   - Khi tổng hợp ROAS từ nhiều campaigns trong cùng network, dùng weighted average theo spend.
   - Không dùng average đơn giản.

3. **Campaign Status**:
   - Check `status` trong response: `RUNNING`, `PAUSED`, `PENDING`.
   - Chỉ nên phân tích các campaign đang `RUNNING`.

4. **Cohort Metrics**:
   - ROAS_D7 chỉ chính xác khi reporting window đủ 7 ngày.
   - Với window < 7 ngày, giá trị có thể chưa ổn định.

5. **Campaign Naming**:
   - Một số campaign có thể có cùng tên trên các network khác nhau.
   - Nên kết hợp `campaign name + network` để xác định duy nhất.

6. **Campaign Type**:
   - Phân biệt giữa `APP_INSTALL`, `REEngagement`, `WEB`...
   - Chỉ nên phân tích các campaign `APP_INSTALL` cho ROAS analysis.
