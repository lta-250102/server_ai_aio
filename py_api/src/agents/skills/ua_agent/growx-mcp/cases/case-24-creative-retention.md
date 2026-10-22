# Case 24: Creative Retention thấp/cao (Creative Retention Analysis)

## Trigger
- Khi user hỏi về retention, D1/D3/D7, user retention, user quay lại mở game.


## Mục tiêu
Xác định creative (af_ad) nào đang thu hút user có Retention thấp/cao.

## ⚠️ Limitation: GrowX không hỗ trợ query theo Creative

**Quan trọng:** Tool `growX_ua_list_campaigns` **không có trường** để phân biệt creative (af_ad).
- Không có tham số `af_ad`, `creative_id` trong function signature.
- Không có trường `af_ad` trong response của campaign.
- Dữ liệu creative-level cần lấy từ hệ thống khác (AppsFlyer Direct, DWH).

## Các tùy chọn xử lý

### Option 1: Sử dụng Data từ DWH (khuyên dùng)
```sql
-- Purchase-based retention theo af_ad (trừ networks không có af_ad)
WITH installs AS (
    SELECT 
        appsflyer_id,
        toDate(install_time) as install_date,
        campaign,
        af_ad
    FROM dwh_system.f_puller_appsflyer_raw_s2s
    WHERE package_name = '<package_name>'
      AND event_name = 'install'
      AND campaign = '<campaign>'
      AND media_source NOT IN ('greedygam7_int', 'mintegral_int', 'tapjoy_int', 'mobvista_int', 'googleadwords_int')
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
        i.af_ad,
        p.purchase_date,
        dateDiff('day', i.install_date, p.purchase_date) as days_after
    FROM installs i
    LEFT JOIN purchases p ON i.appsflyer_id = p.appsflyer_id
),
creative_retention AS (
    SELECT 
        af_ad,
        install_date,
        count() as total_installs,
        countIf(days_after = 0) as d0_retained,
        countIf(days_after = 1) as d1_retained
    FROM retention_calc
    GROUP BY af_ad, install_date
),
avg_rr AS (
    SELECT AVG(d1_retained * 100.0 / NULLIF(total_installs, 0)) as avg_rr_d1
    FROM creative_retention
    WHERE total_installs > 0
)
SELECT 
    cr.af_ad,
    cr.install_date,
    cr.total_installs,
    round(cr.d0_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d0_pct,
    round(cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0), 2) as rr_d1_pct,
    round(ar.avg_rr_d1, 2) as avg_rr_d1,
    round(
        (cr.d1_retained * 100.0 / NULLIF(cr.total_installs, 0) - ar.avg_rr_d1) 
        / NULLIF(ar.avg_rr_d1, 0) * 100,
        2
    ) as deviation_pct
FROM creative_retention cr
CROSS JOIN avg_rr ar
WHERE cr.total_installs > 0
ORDER BY cr.install_date, deviation_pct
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
            metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
            getAll=True
        )
        # Analyze retention per network instead of per creative
```

### 2. Phân tích theo Campaign (nếu campaign name chứa creative ID)
```python
# Nếu campaign name chứa creative ID
campaigns = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "RETENTION_D1"],
    getAll=True
)

from collections import defaultdict
import re

creative_retention_data = defaultdict(lambda: {'installs': 0, 'weighted_ret_d1': 0})
for campaign in campaigns.get('campaigns', []):
    camp_name = campaign.get('name', '')
    metrics = campaign.get('metrics', {})
    
    installs = metrics.get('INSTALLS', 0) or 0
    ret_d1 = metrics.get('RETENTION_D1', 0) or 0
    
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
    
    creative_retention_data[creative_id]['installs'] += installs
    creative_retention_data[creative_id]['weighted_ret_d1'] += installs * ret_d1

# Tính retention proxy theo creative
for cid, data in creative_retention_data.items():
    if data['installs'] > 0:
        data['ret_d1'] = data['weighted_ret_d1'] / data['installs']
    else:
        data['ret_d1'] = 0

# Sort by retention
sorted_creatives = sorted(creative_retention_data.items(), key=lambda x: x[1]['ret_d1'], reverse=True)
for cid, data in sorted_creatives:
    print(f"Creative {cid}: D1 Ret = {data['ret_d1']:.2f}%, Installs = {data['installs']}")
```

**Lưu ý:** Cách này chỉ hoạt động nếu campaign naming convention có chứa creative ID.

## Kết luận

**Không thể thực hiện Case 24 (Creative Retention Analysis) với growX hiện tại.**

Yêu cầu:
1. 🔍 **Kiểm tra DWH**: Truy vấn raw data từ bảng `f_puller_appsflyer_raw_s2s`
2. 📊 **Dùng Appsflyer Dashboard**: Reports → Creative Performance
3. 📤 **Yêu cầu Export**: Nhờ team data export creative-level retention report

---

## Template báo cáo khi không có data creative

```markdown
# Báo Cáo Creative Retention - [Package Name]
## Khoảng thời gian: [Start Date] - [End Date]
## Campaign: [Campaign Name]
## Network: [Network Name]

⚠️ **LƯU Ý:** Không thể phân tích theo Creative (af_ad) do growX không hỗ trợ filter theo creative ID.

### Đề xuất:
1. Truy cập Appsflyer → Reports → Creative Performance
2. Hoặc cung cấp data từ DWH:
   ```sql
   SELECT af_ad, install_date,
          count() as total_installs,
          countIf(days_after = 1) as d1_retained
   FROM dwh_system.f_puller_appsflyer_raw_s2s
   WHERE package_name = '<package_name>' AND install_time >= 'YYYY-MM-DD'
   GROUP BY af_ad, install_date
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

## Các phân tích có thể thực hiện với GrowX (không cần creative)

1. **Retention theo Network** - So sánh chất lượng user giữa các mạng
2. **Retention theo Campaign** - Xếp hạng campaigns theo retention
3. **Trend Retention** - Theo dõi retention thay đổi theo thời gian (Case 19)
4. **Network Retention** - Phân tích retention theo từng network (Case 20)

## Các threshold cần lưu ý (khi có data creative)

Khi lấy data từ DWH/Appsflyer, áp dụng các cảnh báo sau:

- **Chỉ đánh giá khi creative có > 20 installs và chạy > 7 ngày**
- **RR rất thấp dù CPI tốt** → dấu hiệu creative fake
- **RR thấp kéo dài > 21 ngày** → suggest remove
- **Creative chạy > 21 ngày có RR thấp** → check thêm spending (#6), nếu spending thấp ở top 30% → suggest remove

## Dấu hiệu Creative Fake cần lưu ý

```markdown
## Dấu hiệu Creative Fake qua Retention:
- RR rất thấp (D1 < 15%) dù CPI tốt → nghi ngờ fake clicks
- RR thấp nhưng spend cao → creative thu hút clicks nhưng user không chất lượng
- RR tăng đột ngột rồi giảm mạnh → có thể là fraud attack
- RR thấp nhưng ROAS cao → creative sophisticated fraud (user thật nhưng không engagement)
```

## Networks không có af_ad

Các networks sau **không có trường af_ad** trong raw data:
- `greedygam7_int`
- `mintegral_int`
- `tapjoy_int`
- `mobvista_int`
- `googleadwords_int` (dùng `af_adset` thay vì `af_ad`)

Khi query DWH, cần filter ra các networks này hoặc sử dụng trường thay thế.

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

## Kết hợp với Creative Spending (Case 6) và Creative ROAS (Case 12)

Để phân tích toàn diện khi có data từ DWH/Appsflyer:

```markdown
## Quy trình phân tích Creative toàn diện:

1. **B1**: Kiểm tra Creative Spending (#6) → xác định top/bottom spenders
2. **B2**: Kiểm tra Creative ROAS (#12) → đánh giá hiệu quả doanh thu
3. **B3**: Kiểm tra Creative Retention (#24) → đánh giá chất lượng user
4. **B4**: Tổng hợp:
   - Creative TOP (spend cao + ROAS cao + RR cao) → Scale ngay
   - Creative MEDIUM (spend trung bình + ROAS ổn + RR ổn) → Duy trì
   - Creative LOW (spend thấp + ROAS thấp + RR thấp) → Remove hoặc tối ưu
   - Creative FAKE RISK (spend cao + ROAS cao nhưng RR thấp) → Kiểm tra fraud
```

## Ma trận đánh giá Creative

| RR cao + ROAS cao | RR cao + ROAS thấp |
|-------------------|-------------------|
| 🟢 **Tốt nhất** - Scale ngay | ⚠️ User giữ chân tốt nhưng không chi tiêu |

| RR thấp + ROAS cao | RR thấp + ROAS thấp |
|-------------------|-------------------|
| ⚠️ **Cần kiểm tra fraud** - Chi tiêu tốt nhưng không quay lại | 🔴 **Tệ nhất** - Remove khỏi campaign |

## Benchmark tham khảo (Creative Retention)

| Loại Creative | D1 Retention Target | D7 Retention Target |
|--------------|---------------------|---------------------|
| Gameplay真实 | 30-40% | 12-20% |
| CGI/3D | 25-35% | 10-18% |
| UGC/User-generated | 25-35% | 10-18% |
| Fake/Misleading | < 15% | < 5% |

*Lưu ý: Benchmark chỉ mang tính tham khảo, phụ thuộc vào thể loại game và region.*

## Tóm tắt các case cần Data từ DWH/Appsflyer

| Case | Đối tượng | growX hỗ trợ? |
|------|-----------|---------------|
| #01 | Spend Trend | ✅ |
| #02 | Budget Allocation | ✅ |
| #03 | Campaign Analysis | ✅ |
| #04 | Geo Traffic | ❌ Cần DWH |
| #05 | Site ID Spend | ❌ Cần DWH |
| #06 | Creative Spending | ❌ Cần DWH |
| #07 | ROAS/ROI | ✅ |
| #08 | Network LTV | ✅ |
| #09 | Campaign ROAS | ✅ |
| #10 | Geo ROAS | ❌ Cần DWH |
| #11 | Site ID ROAS | ❌ Cần DWH |
| #12 | Creative ROAS | ❌ Cần DWH |
| #13 | Game CPI | ✅ |
| #14 | Network CPI | ✅ |
| #15 | Campaign CPI | ✅ |
| #16 | Geo CPI | ❌ Cần DWH |
| #17 | Site ID CPI | ❌ Cần DWH |
| #18 | Creative CPI | ❌ Cần DWH |
| #19 | Game Retention | ✅ |
| #20 | Network Retention | ✅ |
| #21 | Campaign Retention | ✅ |
| #22 | Geo Retention | ❌ Cần DWH |
| #23 | Site ID Retention | ❌ Cần DWH |
| #24 | Creative Retention | ❌ Cần DWH |

**Tổng kết:** 15/24 case có thể thực hiện với growX. 9 case còn lại cần data từ DWH hoặc Appsflyer API.
