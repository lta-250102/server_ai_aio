# Case 4: Geo thay đổi traffic (Geo Traffic Analysis)

## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Trigger
- Khi user hỏi về spend, budget, chi phí campaign, phân bổ ngân sách, network spend, creative spending.


## Mục tiêu
Xác định geo/quốc gia nào thay đổi traffic (spend + install) nhiều nhất trong game.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Geo

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có tham số** để filter theo geo/country_code. 
- Không có tham số `geo`, `country`, hay `country_code` trong function signature.
- Dữ liệu geo-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH, hoặc tool reporting chuyên dụng).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
Nếu có quyền truy cập DWH hệ thống, query trực tiếp từ bảng raw data:

```sql
-- Query geo spend 14 ngày
SELECT 
    country_code,
    created_day,
    SUM(af_cost_value) as geo_cost
FROM dwh_system.f_puller_appsflyer_raw_s2s
WHERE package_name = '<package_name>'
  AND created_day >= today() - interval 14 day
GROUP BY country_code, created_day
```

### Option 2: Sử dụng Appsflyer API Direct
Query trực tiếp từ Appsflyer API với endpoint `/get_raw_events` hoặc `/get_conversion_data` với filter geo.

### Option 3: Báo cáo hạn chế
Nếu không có access đến DWH/API, cần báo cáo:
> "⚠️ **Không thể phân tích theo Geo bằng growX**: Tool hiện tại chỉ hỗ trợ filter theo appId, network, và networkConnectorId. 
> Để phân tích geo, vui lòng:
> 1. Truy cập Appsflyer Dashboard → Reports → Geo Report
> 2. Hoặc query DWH raw data trực tiếp
> 3. Hoặc yêu cầu team data export geo-level report"

## Hướng dẫn sử dụng GrowX (chỉ dành cho phân tích ở mức cao hơn)

Mặc dù growX không hỗ trợ geo, nhưng bạn vẫn có thể:

### 1. Phân tích theo Network (thay thế cho geo-level analysis)
```python
# Thay vì phân tích country, phân tích theo network
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
        # Analyze spend per network instead of per geo
```

### 2. Phân tích theo Campaign (nếu campaign được tạo theo geo)
```python
# Nếu campaign name chứa thông tin geo (ví dụ: "US_Campaign_01")
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    getAll=True
)

# Parse geo từ campaign name
from collections import defaultdict
geo_spend = defaultdict(float)
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    # Giả sử campaign name có format: "[US] Campaign Name" hoặc "US_Campaign"
    # Extract geo code
    import re
    geo_match = re.search(r'\[([A-Z]{2})\]', camp_name) or re.search(r'^([A-Z]{2})_', camp_name)
    if geo_match:
        geo = geo_match.group(1)
        spend = campaign.get('metrics', {}).get('SPEND', 0) or 0
        geo_spend[geo] += spend
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa country code.

## Kết luận

**Không thể thực hiện Case 4 (Geo Traffic Analysis) với growX hiện tại.** 

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Geo Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export geo-level report theo khoảng thời gian cần phân tích

---

## Template báo cáo khi không có data geo

```markdown
# Báo Cáo Geo Traffic - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]

⚠️ **LƯU Ý:** Không thể phân tích theo Geo do growX không hỗ trợ filter theo country_code.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Geo Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT country_code, created_day, SUM(af_cost_value) as cost
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND created_day >= 'YYYY-MM-DD'
   GROUP BY country_code, created_day
   ```
```
