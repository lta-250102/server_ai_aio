# Case 22: Geo Retention thấp/cao bất thường (Geo Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định geo nào trong campaign có Retention thấp/cao bất thường.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Geo

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc phân tích theo country_code.
- Không có tham số `geo`, `country`, hay `country_code` trong function signature.
- Dữ liệu geo-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- Purchase-based retention theo geo
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        country_code
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
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
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
geo_retention AS (
    SELECT 
        country_code,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained,
        countIf(days_after = 3) as d3_retained,
        countIf(days_after = 7) as d7_retained
    FROM retention_calc
    GROUP BY country_code, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM geo_retention
    WHERE total_installs > 0
)
SELECT 
    gr.country_code,
    gr.install_date,
    gr.total_installs,
    round(gr.d0_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d0_pct,
    round(gr.d1_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d1_pct,
    round(gr.d3_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d3_pct,
    round(gr.d7_retained * 100.0 / NULLIF(gr.total_installs, 0), 2) as rr_d7_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (gr.d1_retained * 100.0 / NULLIF(gr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM geo_retention gr
CROSS JOIN avg_rr ar
WHERE gr.total_installs > 0
ORDER BY gr.install_date, deviation_pct
```

### Option 2: Sử dụng Appsflyer API Direct
Query từ Appsflyer Conversion Data API với filter geo.

## Hướng dẫn sử dụng GrowX (chỉ dành cho phân tích ở mức cao hơn)

Mặc dù growX không hỗ trợ geo, nhưng bạn vẫn có thể:

### 1. Phân tích theo Network (thay thế cho geo-level analysis)
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
            metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D7"],
            getAll=True
        )
        # Analyze retention per network instead of per geo
```

### 2. Phân tích theo Campaign (nếu campaign name chứa thông tin geo)
```python
# Nếu campaign name chứa country code (ví dụ: "[US] Campaign Name" hoặc "US_Campaign")
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D7"],
    getAll=True
)

from collections import defaultdict
import re

geo_retention_data = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
    # Extract geo code từ campaign name
    geo_match = re.search(r'\[([A-Z]{2})\]', camp_name) or re.search(r'^([A-Z]{2})_', camp_name)
    if geo_match:
        geo = geo_match.group(1)
        geo_retention_data[geo]['installs'] += installs
        geo_retention_data[geo]['weighted_ret_d1'] += installs * ret_d1

# Tính retention proxy theo geo
for geo, data in geo_retention_data.items():
    if data['installs'] > 0:
        data['ret_d1'] = data['weighted_ret_d1'] / data['installs']
    else:
        data['ret_d1'] = 0

# Sort by retention
sorted_geo = sorted(geo_retention_data.items(), key=lambda x: x[1]['ret_d1'], reverse=True)
for geo, data in sorted_geo:
    print(f"{geo}: D1 Ret = {data['ret_d1']:.2f}%, Installs = {data['installs']}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa country code.

## Kết luận

**Không thể thực hiện Case 22 (Geo Retention Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Geo Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export geo-level retention report

---

## Template báo cáo khi không có data geo

```markdown
# Báo Cáo Geo Retention - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]

⚠️ **LƯU Ý:** Không thể phân tích theo Geo do growX không hỗ trợ filter theo country_code.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Geo Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT country_code, install_date,
          count() as total_installs,
          countIf(days_after = 1) as d1_retained
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND install_time >= 'YYYY-MM-DD'
   GROUP BY country_code, install_date
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
    metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D7"],
    getAll=True
)

# Step 2: Group retention theo network
from collections import defaultdict

network_retention = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0, 'weighted_ret_d7': 0})
for campaign in campaigns.get('campaigns', []):
    network = campaign.get('network', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    ret_d7 = metrics.get('RETENTION_D7', 0) or 0
    
    network_retention[network]['installs'] += installs
    network_retention[network]['weighted_ret_d1'] += installs * ret_d1
    network_retention[network]['weighted_ret_d7'] += installs * ret_d7

# Tính retention cho từng network
network_summary = []
for network, data in network_retention.items():
    if data['installs'] > 0:
        ret_d1 = data['weighted_ret_d1'] / data['installs']
        ret_d7 = data['weighted_ret_d7'] / data['installs']
    else:
        ret_d1 = 0
        ret_d7 = 0
    
    network_summary.append({
        'network': network,
        'installs': data['installs'],
        'ret_d1': round(ret_d1, 2),
        'ret_d7': round(ret_d7, 2)
    })

# Sort by D1 Retention
network_summary.sort(key=lambda x: x['ret_d1'], reverse=True)
for net in network_summary:
    print(f"{net['network']}: D1 Ret = {net['ret_d1']:.2f}%, D7 Ret = {net['ret_d7']:.2f}%, Installs = {net['installs']}")
```

### Phân tích Retention theo Campaign
```python
# Group retention theo campaign
campaign_retention = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0, 'weighted_ret_d7': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    ret_d7 = metrics.get('RETENTION_D7', 0) or 0
    
    campaign_retention[camp_name]['installs'] += installs
    campaign_retention[camp_name]['weighted_ret_d1'] += installs * ret_d1
    campaign_retention[camp_name]['weighted_ret_d7'] += installs * ret_d7

# Tính và sort
campaign_summary = []
for camp, data in campaign_retention.items():
    if data['installs'] > 0:
        ret_d1 = data['weighted_ret_d1'] / data['installs']
        ret_d7 = data['weighted_ret_d7'] / data['installs']
    else:
        ret_d1 = 0
        ret_d7 = 0
    
    campaign_summary.append({
        'campaign': camp,
        'installs': data['installs'],
        'ret_d1': round(ret_d1, 2),
        'ret_d7': round(ret_d7, 2)
    })

campaign_summary.sort(key=lambda x: x['ret_d1'], reverse=True)
for c in campaign_summary[:10]:
    print(f"{c['campaign']}: D1 Ret = {c['ret_d1']:.2f}%, D7 Ret = {c['ret_d7']:.2f}%")
```

## Các phân tích có thể thực hiện với GrowX (không cần geo)

1. **Retention theo Network** - So sánh chất lượng user giữa các mạng
2. **Retention theo Campaign** - Xếp hạng campaigns theo retention
3. **Trend Retention** - Theo dõi retention thay đổi theo thời gian (Case 19)
4. **Network Retention** - Phân tích retention theo từng network (Case 20)

## Các threshold cần lưu ý (khi có data geo)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **Chỉ đánh giá khi geo có > 50 installs**
- **RR biến động > 20%** → cảnh báo
- **RR thấp kéo dài > 7 ngày** → cảnh báo
- **Geo RR thấp kéo dài > 7 ngày hoặc biến động > 20%** → kết hợp check ROAS → suggest UA remove hoặc giảm spend
- **Geo RR cao trong top 5 + ROAS tăng trưởng** → tiếp tục ưu tiên ngân sách dài hạn (đủ cohort D14/D28/D60 để đánh giá)

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
        metrics=["SPEND", "INSTALLS", "RETENTION_D1", "RETENTION_D7"],
        getAll=True
    )
    
    daily = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0, 'weighted_ret_d7': 0})
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        installs = metrics.get('INSTALLS', 0) or 0
        ret_d1 = metrics.get('RETENTION_D1', 0) or 0
        ret_d7 = metrics.get('RETENTION_D7', 0) or 0
        
        daily[day]['installs'] += installs
        daily[day]['weighted_ret_d1'] += installs * ret_d1
        daily[day]['weighted_ret_d7'] += installs * ret_d7
    
    network_daily_retention[net_code] = dict(daily)

# Bước 2: Tính retention hàng ngày và phát hiện anomaly
anomalies = []
for net_code, daily in network_daily_retention.items():
    sorted_days = sorted(daily.keys())
    
    daily_ret = []
    for day in sorted_days:
        data = daily[day]
        if data['installs'] > 0:
            ret_d1 = data['weighted_ret_d1'] / data['installs']
            ret_d7 = data['weighted_ret_d7'] / data['installs']
        else:
            ret_d1 = 0
            ret_d7 = 0
        
        daily_ret.append({
            'day': day,
            'installs': data['installs'],
            'ret_d1': round(ret_d1, 2),
            'ret_d7': round(ret_d7, 2)
        })
    
    # Kiểm tra trend 3 ngày
    if len(daily_ret) >= 3:
        last_3 = daily_ret[-3:]
        first_3 = daily_ret[:3]
        
        avg_ret_last = sum(d['ret_d1'] for d in last_3) / len(last_3)
        avg_ret_first = sum(d['ret_d1'] for d in first_3) / len(first_3)
        
        if avg_ret_first > 0:
            delta = ((avg_ret_last - avg_ret_first) / avg_ret_first) * 100
            
            if delta < -20:
                anomalies.append({
                    'network': net_code,
                    'trend': 'GIẢM',
                    'delta': round(delta, 2),
                    'avg_ret_first': round(avg_ret_first, 2),
                    'avg_ret_last': round(avg_ret_last, 2)
                })

# Report anomalies
if anomalies:
    print("🔍 PHÁT HIỆN ANOMALY RETENTION:")
    print("=" * 70)
    print(f"{'Network':<15} {'Trend':<10} {'Δ%':>10} {'Avg First':>12} {'Avg Last':>12}")
    print("-" * 70)
    for a in anomalies:
        print(f"{a['network']:<15} {a['trend']:<10} {a['delta']:>9.1f}% {a['avg_ret_first']:>11.2f}% {a['avg_ret_last']:>11.2f}%")
else:
    print("✅ Không phát hiện anomaly retention đáng kể")
```
