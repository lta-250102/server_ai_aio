# Case 11: Site_id ROAS thấp/cao (Site ID ROAS Analysis)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định site_id nào trong geo đang cho traffic có ROAS thấp/cao.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Site ID

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc phân tích theo af_siteid.
- Không có tham số `site_id`, `af_siteid` trong function signature.
- Dữ liệu site_id-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- ROAS theo site_id
WITH siteid_roas AS (
    SELECT 
        af_siteid,
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
      AND country_code = '<country_code>'
      AND created_day >= today() - interval 14 day
      AND af_cost_value IS NOT NULL
    GROUP BY af_siteid, created_day
),
avg_roi AS (
    SELECT AVG(roi_pct) as avg_roi
    FROM siteid_roas
    WHERE installs >= 20
)
SELECT 
    sr.af_siteid,
    sr.created_day,
    sr.revenue,
    sr.cost,
    sr.installs,
    sr.roi_pct,
    round(ar.avg_roi, 2) as avg_roi,
    round(
        (sr.roi_pct - ar.avg_roi) / NULLIF(ar.avg_roi, 0) * 100,
        2
    ) as deviation_pct
FROM siteid_roas sr
CROSS JOIN avg_roi ar
WHERE sr.installs >= 20
ORDER BY sr.created_day, deviation_pct
```

### Option 2: Sử dụng Appsflyer API Direct
Query từ Appsflyer Conversion Data API với filter site_id.

## Hướng dẫn sử dụng GrowX (chỉ dành cho phân tích ở mức cao hơn)

Mặc dù growX không hỗ trợ site_id, nhưng bạn vẫn có thể:

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
        # Analyze ROAS per network instead of per site_id
```

### 2. Phân tích theo Campaign (nếu campaign name chứa site_id)
```python
# Nếu campaign name chứa site_id information
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

from collections import defaultdict
import re

siteid_roas = defaultdict(lambda: {'spend': 0, 'installs': 0, 'weighted_roas': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    # Try to extract site_id from campaign name
    # Pattern: "site_12345" hoặc "SID_12345"
    site_match = re.search(r'(?:site|SID)[-_](\d+)', camp_name, re.IGNORECASE)
    if site_match:
        site_id = site_match.group(1)
        siteid_roas[site_id]['spend'] += spend
        siteid_roas[site_id]['installs'] += installs
        siteid_roas[site_id]['weighted_roas'] += spend * roas_d7

# Tính weighted ROAS cho từng site_id
for site, data in siteid_roas.items():
    if data['spend'] > 0:
        data['roas_d7'] = data['weighted_roas'] / data['spend']
        data['revenue'] = data['spend'] * (data['roas_d7'] / 100)
        del data['weighted_roas']

# Sort by ROAS
sorted_sites = sorted(siteid_roas.items(), key=lambda x: x[1]['roas_d7'], reverse=True)
for site, data in sorted_sites:
    print(f"Site {site}: ROAS_D7={data['roas_d7']:.1f}%, Spend=${data['spend']:.2f}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa site_id.

## Kết luận

**Không thể thực hiện Case 11 (Site ID ROAS Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Site ID Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export site_id-level ROAS report

---

## Template báo cáo khi không có data site_id

```markdown
# Báo Cáo Site ID ROAS - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]
## Geo: [Country Code]

⚠️ **LƯU Ý:** Không thể phân tích theo Site ID do growX không hỗ trợ filter theo af_siteid.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Site ID Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT af_siteid, created_day,
          SUM(event_revenue_usd) as revenue,
          SUM(af_cost_value) as cost,
          count() as installs
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND created_day >= 'YYYY-MM-DD'
   GROUP BY af_siteid, created_day
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

## Các phân tích có thể thực hiện với GrowX (không cần site_id)

1. **ROAS theo Network** - So sánh hiệu quả giữa các mạng quảng cáo
2. **ROAS theo Campaign** - Xếp hạng campaigns trong cùng network
3. **Trend ROAS** - Theo dõi ROAS thay đổi theo thời gian (Case 7)
4. **Campaign Spending** - Xác định campaigns nào chi nhiều tiền nhất (Case 3)
5. **Network LTV** - Đánh giá hiệu quả thu hồi vốn theo network (Case 8)

## Các threshold cần lưu ý (khi có data site_id)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **ROAS giảm > 50% đột ngột** → suggest block site_id
- **ROAS < avg game 30% trong 3 ngày liên tiếp** → cảnh báo, check spending (#5)
- **ROAS < Avg game 30% trong 3 ngày liên tiếp + top 25 spending** → suggest block
- **ROAS tăng + RR ổn định 3 ngày** → suggest UA tăng bid, whitelist chạy campaign
