# Case 16: Geo CPI lệch (Geo CPI Analysis)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định geo nào trong campaign khiến CPI lệch.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Geo

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc phân tích theo country_code.
- Không có tham số `geo`, `country`, hay `country_code` trong function signature.
- Dữ liệu geo-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- CPI theo geo với DoD delta
WITH geo_cpi AS (
    SELECT 
        country_code,
        created_day,
        round(SUM(af_cost_value), 2) as cost,
        count() as installs,
        round(SUM(af_cost_value) / NULLIF(count(), 0), 4) as cpi
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND campaign = '<campaign>'
      AND event_name = 'install'
      AND created_day >= today() - interval 14 day
    GROUP BY country_code, created_day
)
SELECT 
    country_code,
    created_day,
    cost,
    installs,
    cpi,
    round(cpi - LAG(cpi) OVER (PARTITION BY country_code ORDER BY created_day), 4) as delta_cpi,
    round(
        (cpi - LAG(cpi) OVER (PARTITION BY country_code ORDER BY created_day)) 
        / NULLIF(LAG(cpi) OVER (PARTITION BY country_code ORDER BY created_day), 0) * 100,
        2
    ) as delta_cpi_pct
FROM geo_cpi
WHERE installs > 0
ORDER BY country_code, created_day
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
            metrics=["SPEND", "INSTALLS"],
            getAll=True
        )
        # Analyze CPI per network instead of per geo
```

### 2. Phân tích theo Campaign (nếu campaign name chứa thông tin geo)
```python
# Nếu campaign name chứa country code (ví dụ: "[US] Campaign Name" hoặc "US_Campaign")
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS"],
    getAll=True
)

from collections import defaultdict
import re

geo_cpi_data = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    
    # Extract geo code từ campaign name
    geo_match = re.search(r'\[([A-Z]{2})\]', camp_name) or re.search(r'^([A-Z]{2})_', camp_name)
    if geo_match:
        geo = geo_match.group(1)
        geo_cpi_data[geo]['spend'] += spend
        geo_cpi_data[geo]['installs'] += installs

# Tính CPI cho từng geo
for geo, data in geo_cpi_data.items():
    if data['installs'] > 0:
        data['cpi'] = data['spend'] / data['installs']
    else:
        data['cpi'] = 0

# Sort by CPI
sorted_geo = sorted(geo_cpi_data.items(), key=lambda x: x[1]['cpi'], reverse=True)
for geo, data in sorted_geo:
    print(f"{geo}: CPI=${data['cpi']:.4f}, Spend=${data['spend']:.2f}, Installs={data['installs']}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa country code.

## Kết luận

**Không thể thực hiện Case 16 (Geo CPI Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Geo Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export geo-level CPI report

---

## Template báo cáo khi không có data geo

```markdown
# Báo Cáo Geo CPI - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]

⚠️ **LƯU Ý:** Không thể phân tích theo Geo do growX không hỗ trợ filter theo country_code.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Geo Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT country_code, created_day,
          SUM(af_cost_value) as cost,
          count() as installs
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND created_day >= 'YYYY-MM-DD'
   GROUP BY country_code, created_day
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

## Các phân tích có thể thực hiện với GrowX (không cần geo)

1. **CPI theo Network** - So sánh chi phí cài đặt giữa các mạng
2. **CPI theo Campaign** - Xếp hạng campaigns theo chi phí
3. **Trend CPI** - Theo dõi CPI thay đổi theo thời gian (Case 13)
4. **Network CPI** - Phân tích CPI theo từng network (Case 14)

## Các threshold cần lưu ý (khi có data geo)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **Δ CPI DoD > 20% hoặc trend 3 ngày** → cảnh báo UA
- **Chỉ đánh giá khi geo có > 50 installs**
- **Geo CPI cao + ROAS thấp** → xem xét giảm budget tại geo
- **Δ CPI DoD có trend tăng/giảm** → báo UA + kết hợp check ROAS và RR

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

# Bước 2: Tính CPI hàng ngày
for net_code, daily in network_daily_data.items():
    for day, data in daily.items():
        if data['installs'] > 0:
            cpi = data['spend'] / data['installs']
        else:
            cpi = 0
        print(f"{net_code} | {day} | CPI=${cpi:.4f} | Spend=${data['spend']:.2f} | Installs={data['installs']}")
```
