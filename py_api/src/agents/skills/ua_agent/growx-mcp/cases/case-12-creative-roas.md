# Case 12: Creative ROAS tốt/xấu (Creative ROAS Analysis)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định creative (af_ad) nào đang thu hút traffic có ROAS tốt/xấu.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Creative

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có trường** để phân biệt creative (af_ad).
- Không có tham số `af_ad`, `creative_id` trong function signature.
- Không có trường `af_ad` trong response của campaign.
- Dữ liệu creative-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- ROAS theo af_ad (trừ networks không có af_ad)
WITH creative_roas AS (
    SELECT 
        af_ad,
        created_day,
        round(SUM(event_revenue_usd), 2) as revenue,
        round(SUM(af_cost_value), 2) as cost,
        count() as installs,
        round(
            (SUM(event_revenue_usd) - SUM(af_cost_value)) / NULLIF(SUM(af_cost_value), 0) * 100,
            2
        ) as roi_pct
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND media_source NOT IN ('greedygam7_int', 'mintegral_int', 'tapjoy_int', 'mobvista_int', 'googleadwords_int')
      AND created_day >= today() - interval 14 day
      AND af_cost_value IS NOT NULL
    GROUP BY af_ad, created_day
),
avg_roi AS (
    SELECT AVG(roi_pct) as avg_roi
    FROM creative_roas
    WHERE installs >= 50
)
SELECT 
    cr.af_ad,
    cr.created_day,
    cr.revenue,
    cr.cost,
    cr.installs,
    cr.roi_pct,
    round(ar.avg_roi, 2) as avg_roi,
    round(
        (cr.roi_pct - ar.avg_roi) / NULLIF(ar.avg_roi, 0) * 100,
        2
    ) as deviation_pct
FROM creative_roas cr
CROSS JOIN avg_roi ar
WHERE cr.installs >= 50
ORDER BY cr.created_day, deviation_pct
```

**Lưu ý:** Với `googleadwords_int`: thay `af_ad` bằng `af_adset`

### Option 2: Sử dụng Appsflyer API Direct
Query từ Appsflyer Conversion Data API với filter creative ID.

## Hướng dẫn sử dụng GrowX (chỉ dành cho phân tích ở mức cao hơn)

Mặc dù growX không hỗ trợ af_ad, nhưng bạn vẫn có thể:

### 1. Phân tích theo Network (thay thế)
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']

networks = growX_ua_list_networks()
for network in networks:
    if network['connectorCount'] > 0:
        result = growX_ua_list_campaigns(
            appId=game_id,
            network=network['code'],
            days=14,
            metrics=["SPEND", "INSTALLS", "ROAS_D7"],
            getAll=True
        )
        # Analyze ROAS per network instead of per creative
```

### 2. Phân tích theo Campaign (nếu campaign name chứa creative ID)
```python
# Nếu campaign name chứa creative ID
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

from collections import defaultdict
import re

creative_roas = defaultdict(lambda: {'spend': 0, 'installs': 0, 'weighted_roas': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    # Try to extract creative ID from campaign name
    # Pattern 1: "Creative_12345"
    match1 = re.search(r'(?:Creative|creative)[-_](\d+)', camp_name, re.IGNORECASE)
    # Pattern 2: "CR_12345"
    match2 = re.search(r'(?:CR|cr)[-_](\d+)', camp_name, re.IGNORECASE)
    # Pattern 3: "ad_12345"
    match3 = re.search(r'(?:ad|AD)[-_](\d+)', camp_name, re.IGNORECASE)
    
    if match1:
        creative_id = match1.group(1)
    elif match2:
        creative_id = match2.group(1)
    elif match3:
        creative_id = match3.group(1)
    else:
        creative_id = 'Unknown'
    
    creative_roas[creative_id]['spend'] += spend
    creative_roas[creative_id]['installs'] += installs
    creative_roas[creative_id]['weighted_roas'] += spend * roas_d7

# Tính weighted ROAS cho từng creative
for cid, data in creative_roas.items():
    if data['spend'] > 0:
        data['roas_d7'] = data['weighted_roas'] / data['spend']
        data['revenue'] = data['spend'] * (data['roas_d7'] / 100)
        del data['weighted_roas']

# Sort by ROAS
sorted_creatives = sorted(creative_roas.items(), key=lambda x: x[1]['roas_d7'], reverse=True)
for cid, data in sorted_creatives:
    print(f"Creative {cid}: ROAS_D7={data['roas_d7']:.1f}%, Spend=${data['spend']:.2f}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa creative ID.

## Kết luận

**Không thể thực hiện Case 12 (Creative ROAS Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Creative Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export creative-level ROAS report

---

## Template báo cáo khi không có data creative

```markdown
# Báo Cáo Creative ROAS - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]
## Network: [Network Name]

⚠️ **LƯU Ý:** Không thể phân tích theo Creative (af_ad) do growX không hỗ trợ filter theo creative ID.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Creative Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT af_ad, created_day,
          SUM(event_revenue_usd) as revenue,
          SUM(af_cost_value) as cost,
          count() as installs
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND created_day >= 'YYYY-MM-DD'
   GROUP BY af_ad, created_day
   ```
```

---

## Phân tích thay thế bằng GrowX

Dưới đây là cách phân tích **theo network** và **theo campaign** thay thế:

### Phân tích ROAS theo Network
```python
# Step 1: Query tất cả campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

# Step 2: Group ROAS theo network
from collections import defaultdict

network_roas = defaultdict(lambda: {'spend': 0, 'installs': 0, 'weighted_roas': 0})
for campaign in campaigns.get('campaigns', []):
    network = campaign.get('network', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    network_roas[network]['spend'] += spend
    network_roas[network]['installs'] += installs
    network_roas[network]['weighted_roas'] += spend * roas_d7

# Tính weighted ROAS cho từng network
network_summary = []
for network, data in network_roas.items():
    if data['spend'] > 0:
        roas = data['weighted_roas'] / data['spend']
        revenue = data['spend'] * (roas / 100)
        roi = ((revenue - data['spend']) / data['spend']) * 100
    else:
        roas = 0
        revenue = 0
        roi = 0
    
    network_summary.append({
        'network': network,
        'spend': round(data['spend'], 2),
        'installs': data['installs'],
        'roas_d7': round(roas, 2),
        'roi': round(roi, 2),
        'revenue': round(revenue, 2)
    })

# Sort by ROI
network_summary.sort(key=lambda x: x['roi'], reverse=True)
for net in network_summary:
    print(f"{net['network']}: ROAS={net['roas_d7']:.1f}%, ROI={net['roi']:.1f}%, Spend=${net['spend']:.2f}")
```

### Phân tích ROAS theo Campaign
```python
# Group ROAS theo campaign
campaign_roas = defaultdict(lambda: {'spend': 0, 'installs': 0, 'weighted_roas': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    campaign_roas[camp_name]['spend'] += spend
    campaign_roas[camp_name]['installs'] += installs
    campaign_roas[camp_name]['weighted_roas'] += spend * roas_d7

# Tính và sort
campaign_summary = []
for camp, data in campaign_roas.items():
    if data['spend'] > 0:
        roas = data['weighted_roas'] / data['spend']
        revenue = data['spend'] * (roas / 100)
        roi = ((revenue - data['spend']) / data['spend']) * 100
    else:
        roas = 0
        revenue = 0
        roi = 0
    
    campaign_summary.append({
        'campaign': camp,
        'spend': round(data['spend'], 2),
        'installs': data['installs'],
        'roas_d7': round(roas, 2),
        'roi': round(roi, 2)
    })

campaign_summary.sort(key=lambda x: x['roi'], reverse=True)
for c in campaign_summary[:10]:
    print(f"{c['campaign']}: ROAS={c['roas_d7']:.1f}%, ROI={c['roi']:.1f}%")
```

## Các phân tích có thể thực hiện với GrowX (không cần creative)

1. **ROAS theo Network** - So sánh hiệu quả giữa các mạng quảng cáo
2. **ROAS theo Campaign** - Xếp hạng campaigns trong cùng network
3. **Trend ROAS** - Theo dõi ROAS thay đổi theo thời gian (Case 7)
4. **Creative Spending** - Phân tích spend theo campaign (proxy cho creative nếu naming convention phù hợp)

## Các threshold cần lưu ý (khi có data creative)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **ROAS < avg 30% trong 3 ngày liên tiếp** → cảnh báo
- **Creative chạy > 21 ngày mà ROAS < 30%** → suggest remove
- **ROAS kém + spending kém** → suggest remove khỏi campaign
- **ROAS cao ổn định + spending top 5 trên 1 tuần** → suggest UA chú ý và nhân bản creative

## Networks không có af_ad

Các networks sau **không có trường af_ad** trong raw data:
- `greedygam7_int`
- `mintegral_int`
- `tapjoy_int`
- `mobvista_int`
- `googleadwords_int` (dùng `af_adset` thay vì `af_ad`)

Khi query DWH, cần filter ra các networks này hoặc sử dụng trường thay thế.
