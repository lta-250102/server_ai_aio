# Case 17: Site_id CPI thấp/cao bất thường (Site ID CPI Analysis)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định site_id nào đang cho CPI thấp/cao bất thường.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Site ID

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc phân tích theo af_siteid.
- Không có tham số `site_id`, `af_siteid` trong function signature.
- Dữ liệu site_id-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- CPI theo site_id với DoD delta
WITH siteid_cpi AS (
    SELECT 
        af_siteid,
        created_day,
        round(SUM(af_cost_value), 2) as cost,
        count() as installs,
        round(SUM(af_cost_value) / NULLIF(count(), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND event_name = 'install'
      AND created_day >= today() - interval 14 day
    GROUP BY af_siteid, created_day
)
SELECT 
    af_siteid,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY af_siteid ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY af_siteid ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY af_siteid ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM siteid_cpi
WHERE installs > 0
ORDER BY af_siteid, created_day
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
            metrics=["SPEND", "INSTALLS"],
            getAll=True
        )
        # Analyze CPI per network instead of per site_id
```

### 2. Phân tích theo Campaign (nếu campaign name chứa site_id)
```python
# Nếu campaign name chứa site_id information
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS"],
    getAll=True
)

from collections import defaultdict
import re

siteid_cpi_data = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    
    # Try to extract site_id from campaign name
    # Pattern: "site_12345" hoặc "SID_12345"
    site_match = re.search(r'(?:site|SID)[-_](\d+)', camp_name, re.IGNORECASE)
    if site_match:
        site_id = site_match.group(1)
        siteid_cpi_data[site_id]['spend'] += spend
        siteid_cpi_data[site_id]['installs'] += installs

# Tính CPI cho từng site_id
for site, data in siteid_cpi_data.items():
    if data['installs'] > 0:
        data['cpi'] = data['spend'] / data['installs']
    else:
        data['cpi'] = 0

# Sort by CPI
sorted_sites = sorted(siteid_cpi_data.items(), key=lambda x: x[1]['cpi'], reverse=True)
for site, data in sorted_sites:
    print(f"Site {site}: CPI=${data['cpi']:.4f}, Spend=${data['spend']:.2f}, Installs={data['installs']}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa site_id.

## Kết luận

**Không thể thực hiện Case 17 (Site ID CPI Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Site ID Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export site_id-level CPI report

---

## Template báo cáo khi không có data site_id

```markdown
# Báo Cáo Site ID CPI - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]

⚠️ **LƯU Ý:** Không thể phân tích theo Site ID do growX không hỗ trợ filter theo af_siteid.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Site ID Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT af_siteid, created_day,
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

### Phân tích CPI theo Network
```python
# Step 1: Query tất cả campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS"],
    getAll=True
)

# Step 2: Group CPI theo network
from collections import defaultdict

network_cpi = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    network = campaign.get('network', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    
    network_cpi[network]['spend'] += spend
    network_cpi[network]['installs'] += installs

# Tính CPI cho từng network
network_summary = []
for network, data in network_cpi.items():
    if data['installs'] > 0:
        cpi = data['spend'] / data['installs']
    else:
        cpi = 0
    
    network_summary.append({
        'network': network,
        'cpi': round(cpi, 4),
        'spend': round(data['spend'], 2),
        'installs': data['installs']
    })

# Sort by CPI
network_summary.sort(key=lambda x: x['cpi'])
for net in network_summary:
    print(f"{net['network']}: CPI=${net['cpi']:.4f}, Spend=${net['spend']:.2f}, Installs={net['installs']}")
```

### Phân tích CPI theo Campaign
```python
# Group CPI theo campaign
campaign_cpi = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    
    campaign_cpi[camp_name]['spend'] += spend
    campaign_cpi[camp_name]['installs'] += installs

# Tính và sort
campaign_summary = []
for camp, data in campaign_cpi.items():
    if data['installs'] > 0:
        cpi = data['spend'] / data['installs']
    else:
        cpi = 0
    
    campaign_summary.append({
        'campaign': camp,
        'cpi': round(cpi, 4),
        'spend': round(data['spend'], 2),
        'installs': data['installs']
    })

campaign_summary.sort(key=lambda x: x['cpi'])
for c in campaign_summary[:10]:
    print(f"{c['campaign']}: CPI=${c['cpi']:.4f}, Spend=${c['spend']:.2f}")
```

## Các phân tích có thể thực hiện với GrowX (không cần site_id)

1. **CPI theo Network** - So sánh chi phí cài đặt giữa các mạng
2. **CPI theo Campaign** - Xếp hạng campaigns theo chi phí
3. **Trend CPI** - Theo dõi CPI thay đổi theo thời gian (Case 13)
4. **Network CPI** - Phân tích CPI theo từng network (Case 14)

## Các threshold cần lưu ý (khi có data site_id)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **Δ CPI DoD > 20% hoặc trend 3 ngày** → cảnh báo UA
- **Δ CPI DoD > 50%** → suggest block site_id
- **Chỉ đánh giá khi site_id có > 20 installs hoặc traffic > 5 ngày**
- **Site_id CPI cao + ROAS thấp** → xem xét block

## Cảnh báo đặc biệt cho Site ID

```markdown
## Cảnh báo fraud khi:
- CPI giảm đột ngột > 50% → nghi ngờ click fraud
- ROAS giảm > 20% → nghi ngờ low-quality traffic
- Retention giảm đột ngột → nghi ngờ fake installs
```

## Các network analysis thay thế

### Phân tích CPI theo Network chi tiết
```python
# Bước 1: Query 14 ngày cho mỗi network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0]

network_daily_data = {}
for net_code in network_codes:
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=net_code,
        days=14,
        metrics=["SPEND", "INSTALLS"],
        getAll=True
    )
    
    daily = defaultdict(lambda: {'spend': 0, 'installs': 0})
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        daily[day]['spend'] += metrics.get('SPEND', 0) or 0
        daily[day]['installs'] += metrics.get('INSTALLS', 0) or 0
    
    network_daily_data[net_code] = dict(daily)

# Bước 2: Tính CPI hàng ngày và phát hiện anomaly
anomalies = []
for net_code, daily in network_daily_data.items():
    sorted_days = sorted(daily.keys())
    
    for i, day in enumerate(sorted_days):
        data = daily[day]
        if data['installs'] > 0:
            cpi = data['spend'] / data['installs']
        else:
            cpi = 0
        
        # So sánh với ngày trước
        if i > 0:
            prev_data = daily[sorted_days[i-1]]
            if prev_data['installs'] > 0:
                prev_cpi = prev_data['spend'] / prev_data['installs']
                
                if prev_cpi > 0:
                    delta_pct = (cpi - prev_cpi) / prev_cpi * 100
                    
                    if abs(delta_pct) > 50:
                        anomalies.append({
                            'network': net_code,
                            'day': day,
                            'cpi': round(cpi, 4),
                            'prev_cpi': round(prev_cpi, 4),
                            'delta_pct': round(delta_pct, 2)
                        })

# Report anomalies
if anomalies:
    print("🔍 PHÁT HIỆN ANOMALY:")
    print("=" * 70)
    print(f"{'Network':<15} {'Day':<12} {'CPI':>10} {'Prev CPI':>10} {'Δ%':>10}")
    print("-" * 70)
    for a in anomalies:
        print(f"{a['network']:<15} {a['day']:<12} ${a['cpi']:>9.4f} ${a['prev_cpi']:>9.4f} {a['delta_pct']:>9.1f}%")
else:
    print("✅ Không phát hiện anomaly CPI đáng kể")
```
