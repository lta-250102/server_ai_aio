# Case 5: Site_id nào đẩy spend (Site ID Spend Analysis)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định site_id nào trong campaign đang đẩy spend nhiều nhất.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Site ID

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter hoặc group by af_siteid.
- Không có tham số `site_id`, `af_siteid` trong function signature.
- Dữ liệu site_id-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
WITH site_cost AS (
    SELECT 
        campaign,
        af_siteid,
        created_day,
        SUM(af_cost_value) as cost,
        count() as installs
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND created_day >= today() - interval 14 day
      AND af_cost_value IS NOT NULL
    GROUP BY campaign, af_siteid, created_day
)
SELECT 
    campaign,
    af_siteid,
    created_day,
    round(cost, 2) as cost,
    installs,
    round(cost - LAG(cost) OVER (PARTITION BY campaign, af_siteid ORDER BY created_day), 2) as delta_cost,
    round(
        (cost - LAG(cost) OVER (PARTITION BY campaign, af_siteid ORDER BY created_day)) 
        / NULLIF(LAG(cost) OVER (PARTITION BY campaign, af_siteid ORDER BY created_day), 0) * 100,
        2
    ) as delta_pct
FROM site_cost
ORDER BY campaign, created_day
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
            getAll=True
        )
        # Analyze spend per network instead of per site_id
```

### 2. Phân tích theo Campaign
```python
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    getAll=True
)

# Group spend by campaign name
camp_spend = defaultdict(float)
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    spend = campaign.get('metrics', {}).get('SPEND', 0) or 0
    camp_spend[camp_name] += spend

# Sort by spend
top_campaigns = sorted(camp_spend.items(), key=lambda x: x[1], reverse=True)
for camp, spend in top_campaigns[:10]:
    print(f"{camp}: ${spend}")
```

## Kết luận

**Không thể thực hiện Case 5 (Site ID Spend Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Site ID Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export site_id-level report

---

## Template báo cáo khi không có data site_id

```markdown
# Báo Cáo Site ID Spend - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]

⚠️ **LƯU Ý:** Không thể phân tích theo Site ID do growX không hỗ trợ filter theo af_siteid.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Site ID Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT campaign, af_siteid, created_day, SUM(af_cost_value) as cost
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND created_day >= 'YYYY-MM-DD'
   GROUP BY campaign, af_siteid, created_day
   ```
```

---

## Phân tích thay thế bằng GrowX

Dưới đây là cách phân tích **theo network** và **theo campaign** thay thế:

### Phân tích Spend theo Network
```python
# Step 1: Query tất cả campaigns
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    getAll=True
)

# Step 2: Group by network (từ campaign info)
network_spend = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    # Network info có thể nằm trong campaign metadata
    network = campaign.get('network', 'Unknown')
    metrics = campaign.get('metrics', {})
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    network_spend[network]['spend'] += spend
    network_spend[network]['installs'] += installs

# Step 3: Sort và analyze
for network, stats in sorted(network_spend.items(), key=lambda x: x[1]['spend'], reverse=True):
    print(f"{network}: ${stats['spend']} spend, {stats['installs']} installs")
```

### Phân tích Spend theo Campaign
```python
# Group by campaign
campaign_spend = defaultdict(lambda: {'spend': 0, 'installs': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', 'Unknown')
    metrics = campaign.get('metrics', {})
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    campaign_spend[camp_name]['spend'] += spend
    campaign_spend[camp_name]['installs'] += installs

# Top 10 campaigns
top_camps = sorted(campaign_spend.items(), key=lambda x: x[1]['spend'], reverse=True)[:10]
for name, stats in top_camps:
    print(f"{name}: ${stats['spend']} spend, {stats['installs']} installs")
```
