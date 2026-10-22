# Case 23: Site_id Retention thấp/cao (Site ID Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định site_id nào trong geo đang cho user có Retention thấp/cao.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Site ID

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc phân tích theo af_siteid.
- Không có tham số `site_id`, `af_siteid` trong function signature.
- Dữ liệu site_id-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- Purchase-based retention theo site_id
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        country_code,
        af_siteid
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
      AND country_code = '<country_code>'
      AND install_time >= now() - interval 14 day
),
purchases AS (
    SELECT 
        appsflyer_id,
        toDate(event_time) as purchase_date
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'af_purchase'
      AND event_time >= now() - interval 14 day
),
retention_calc AS (
    SELECT 
        i.appsflyer_id,
        i.install_date,
        i.campaign,
        i.country_code,
        i.af_siteid,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
siteid_retention AS (
    SELECT 
        af_siteid,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained
    FROM retention_calc
    GROUP BY af_siteid, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM siteid_retention
    WHERE total_installs > 0
)
SELECT 
    sr.af_siteid,
    sr.install_date,
    sr.total_installs,
    round(sr.d0_retained * 100.0 / NULLIF(sr.total_installs, 0), 2) as rr_d0_pct,
    round(sr.d1_retained * 100.0 / NULLIF(sr.total_installs, 0), 2) as rr_d1_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (sr.d1_retained * 100.0 / NULLIF(sr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM siteid_retention sr
CROSS JOIN avg_rr ar
WHERE sr.total_installs > 0
ORDER BY sr.install_date, deviation_pct
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
            metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
            getAll=True
        )
        # Analyze retention per network instead of per site_id
```

### 2. Phân tích theo Campaign (nếu campaign name chứa site_id)
```python
# Nếu campaign name chứa site_id information
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
    getAll=True
)

from collections import defaultdict
import re

siteid_retention_data = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
    # Try to extract site_id from campaign name
    # Pattern: "site_12345" hoặc "SID_12345"
    site_match = re.search(r'(?:site|SID)[-_](\d+)', camp_name, re.IGNORECASE)
    if site_match:
        site_id = site_match.group(1)
        siteid_retention_data[site_id]['installs'] += installs
        siteid_retention_data[site_id]['weighted_ret_d1'] += installs * ret_d1

# Tính retention proxy theo site_id
for site, data in siteid_retention_data.items():
    if data['installs'] > 0:
        data['ret_d1'] = data['weighted_ret_d1'] / data['installs']
    else:
        data['ret_d1'] = 0

# Sort by retention
sorted_sites = sorted(siteid_retention_data.items(), key=lambda x: x[1]['ret_d1'], reverse=True)
for site, data in sorted_sites:
    print(f"Site {site}: D1 Ret = {data['ret_d1']:.2f}%, Installs = {data['installs']}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa site_id.

## Kết luận

**Không thể thực hiện Case 23 (Site ID Retention Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Site ID Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export site_id-level retention report

---

## Template báo cáo khi không có data site_id

```markdown
# Báo Cáo Site ID Retention - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]
## Geo: [Country Code]

⚠️ **LƯU Ý:** Không thể phân tích theo Site ID do growX không hỗ trợ filter theo af_siteid.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Site ID Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT af_siteid, install_date,
          count() as total_installs,
          countIf(days_after = 1) as d1_retained
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND install_time >= 'YYYY-MM-DD'
   GROUP BY af_siteid, install_date
   ```
```

---

## Phân tích thay thế bằng GrowX

Dưới đây là cách phân tích **theo network** và **theo campaign** thay thế:

### Phân tích Retention theo Network
```python
# Step 1: Query tất cả campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
    getAll=True
)

# Step 2: Group retention theo network
from collections import defaultdict

network_retention = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    network = campaign.get('network', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
    network_retention[network]['installs'] += installs
    network_retention[network]['weighted_ret_d1'] += installs * ret_d1

# Tính retention cho từng network
network_summary = []
for network, data in network_retention.items():
    if data['installs'] > 0:
        ret_d1 = data['weighted_ret_d1'] / data['installs']
    else:
        ret_d1 = 0
    
    network_summary.append({
        'network': network,
        'installs': data['installs'],
        'ret_d1': round(ret_d1, 2)
    })

# Sort by D1 Retention
network_summary.sort(key=lambda x: x['ret_d1'], reverse=True)
for net in network_summary:
    print(f"{net['network']}: D1 Ret = {net['ret_d1']:.2f}%, Installs = {net['installs']}")
```

### Phân tích Retention theo Campaign
```python
# Group retention theo campaign
campaign_retention = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
    campaign_retention[camp_name]['installs'] += installs
    campaign_retention[camp_name]['weighted_ret_d1'] += installs * ret_d1

# Tính và sort
campaign_summary = []
for camp, data in campaign_retention.items():
    if data['installs'] > 0:
        ret_d1 = data['weighted_ret_d1'] / data['installs']
    else:
        ret_d1 = 0
    
    campaign_summary.append({
        'campaign': camp,
        'installs': data['installs'],
        'ret_d1': round(ret_d1, 2)
    })

campaign_summary.sort(key=lambda x: x['ret_d1'], reverse=True)
for c in campaign_summary[:10]:
    print(f"{c['campaign']}: D1 Ret = {c['ret_d1']:.2f}%, Installs = {c['installs']}")
```

## Các phân tích có thể thực hiện với GrowX (không cần site_id)

1. **Retention theo Network** - So sánh chất lượng user giữa các mạng
2. **Retention theo Campaign** - Xếp hạng campaigns theo retention
3. **Trend Retention** - Theo dõi retention thay đổi theo thời gian (Case 19)
4. **Network Retention** - Phân tích retention theo từng network (Case 20)

## Các threshold cần lưu ý (khi có data site_id)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **Chỉ đánh giá khi site_id có > 20 installs và chạy > 7 ngày**
- **RR D1 < 15%** → dấu hiệu fraud mạnh
- **RR thấp hơn avg 30% kéo dài > 5 ngày** → cảnh báo
- **Site ID có RR thấp hơn trung bình 30% kéo dài > 5 ngày** → kết hợp check ROAS
  - Nếu ROAS cao → check fraud
  - Nếu ROAS thấp → suggest block

## Dấu hiệu Fraud cần lưu ý

```markdown
## Dấu hiệu Fraud qua Retention:
- RR D1 < 15% → user cài xong rời đi ngay, không quay lại
- RR D1 < Avg campaign trên 50% → dấu hiệu click injection
- Retention thấp nhưng CPI cũng thấp → nghi ngờ incentivized traffic
- Retention thấp nhưng ROAS cao → có thể là fraud sophisticated
```

## Phân tích thay thế chi tiết

### Phân tích Retention theo Network chi tiết
```python
# Bước 1: Query 14 ngày cho mỗi network
networks = growX_ua_list_networks()
network_codes = [n['code'] for n in networks if n['connectorCount'] > 0]

network_daily_retention = {}
for net_code in network_codes:
    result = growX_ua_list_campaigns(
        appId=game_id,
        network=net_code,
        days=14,
        metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
        getAll=True
    )
    
    daily = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        installs = metrics.get('INSTALLS', 0) or 0
        ret_d1 = metrics.get('RETENTION_D1', 0) or 0
        
        daily[day]['installs'] += installs
        daily[day]['weighted_ret_d1'] += installs * ret_d1
    
    network_daily_retention[net_code] = dict(daily)

# Bước 2: Tính retention hàng ngày và phát hiện anomaly
anomalies = []
for net_code, daily in network_daily_retention.items():
    sorted_days = sorted(daily.keys())
    
    for i, day in enumerate(sorted_days):
        data = daily[day]
        if data['installs'] > 0:
            ret_d1 = data['weighted_ret_d1'] / data['installs']
        else:
            ret_d1 = 0
        
        # Kiểm tra nếu retention quá thấp
        if ret_d1 < 15 and data['installs'] > 20:
            anomalies.append({
                'network': net_code,
                'day': day,
                'ret_d1': round(ret_d1, 2),
                'installs': data['installs'],
                'risk': 'HIGH_FRAUD_RISK'
            })

# Report anomalies
if anomalies:
    print("🔍 PHÁT HIỆN ANOMALY RETENTION (Nghi Fraud):")
    print("=" * 70)
    print(f"{'Network':<15} {'Day':<12} {'D1 Ret%':>10} {'Installs':>10} {'Risk':>15}")
    print("-" * 70)
    for a in anomalies:
        print(f"{a['network']:<15} {a['day']:<12} {a['ret_d1']:>9.2f}% {a['installs']:>10} {a['risk']:>15}")
else:
    print("✅ Không phát hiện anomaly retention đáng kể")
```
