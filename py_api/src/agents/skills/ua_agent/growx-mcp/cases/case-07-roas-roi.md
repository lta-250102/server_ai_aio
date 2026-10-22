# Case 7: ROAS/ROI game tăng/giảm (ROAS/ROI Trend)

## Trigger
- Khi user hỏi về ROAS, ROI, hiệu quả campaign, LTV, return on ad spend.


## Mục tiêu
Xác định trend ROI của game trong 14 ngày gần nhất.

## ✅ GrowX Hỗ Trợ

**Khác với Case 4, 5, 6:** growX hỗ trợ đầy đủ các metrics ROAS, SPEND, và các chỉ số tài chính khác. Đây là case có thể phân tích trực tiếp mà không cần DWH.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']
```

### 1.2. Query ROAS và Spend 2 giai đoạn
Dùng `growX_ua_list_campaigns` với các metrics cần thiết:

**Giai đoạn 1: 7 ngày gần nhất**
```python
result_recent = growX_ua_list_campaigns(
    appId=game_id,
    days=7,
    metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
    getAll=True
)
```

**Giai đoạn 2: 7 ngày trước đó (từ 8-14 ngày trước)**
```python
# Tính ngày từ/to (ví dụ từ 2024-05-01 đến 2024-05-07)
result_past = growX_ua_list_campaigns(
    appId=game_id,
    from="YYYY-MM-DD",
    to="YYYY-MM-DD",
    metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
    getAll=True
)
```

### 1.3. Tổng hợp Revenue và Cost theo ngày

**Lưu ý quan trọng:** growX trả về ROAS trực tiếp, nhưng **không trả về Revenue (revenue_usd)**.
- ROAS là **PERCENT_0_100** (ví dụ: `85` nghĩa là 85%).
- Cost (SPEND) có sẵn.
- **Revenue cần tính toán ngược từ ROAS**: `Revenue = Cost × ROAS / 100`.

```python
from collections import defaultdict

def extract_daily_metrics(result):
    """
    Extract daily spend và aggregate ROAS
    Trả về: {day: {spend: float, roas_d7: float, ...}}
    """
    daily_metrics = defaultdict(lambda: {
        'spend': 0.0,
        'installs': 0,
        'roas_d7': 0.0,
        'roas_d0': 0.0,
        'camp_count': 0,
        'weighted_roas_d7': 0.0,
    })
    
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        roas_d7 = metrics.get('ROAS_D7', 0) or 0
        roas_d0 = metrics.get('ROAS_D0', 0) or 0
        
        daily_metrics[day]['spend'] += spend
        daily_metrics[day]['installs'] += installs
        # Weighted average ROAS theo spend
        daily_metrics[day]['weighted_roas_d7'] += spend * roas_d7
        daily_metrics[day]['camp_count'] += 1
    
    # Tính weighted average ROAS
    for day, data in daily_metrics.items():
        if data['spend'] > 0:
            data['roas_d7'] = data['weighted_roas_d7'] / data['spend']
            data['roas_d0'] = roas_d0 # Simple fallback if not aggregated properly
        else:
            data['roas_d7'] = 0
        
        # Revenue tính từ ROAS (vì growX không trả về revenue)
        # ROAS là %: 85 = 85%
        # Revenue = Spend × (ROAS / 100)
        data['revenue'] = data['spend'] * (data['roas_d7'] / 100)
    
    return dict(daily_metrics)

recent_metrics = extract_daily_metrics(result_recent)
past_metrics = extract_daily_metrics(result_past)
```

### 1.4. Tính toán ROI và các chỉ số

```python
import pandas as pd

# Combine và sort theo ngày
all_days = sorted(set(list(recent_metrics.keys()) + list(past_metrics.keys())))

daily_data = []
for day in all_days:
    m = recent_metrics.get(day, past_metrics.get(day, {'spend': 0, 'revenue': 0, 'roas_d7': 0}))
    spend = m['spend']
    revenue = m['revenue']
    roas_d7 = m['roas_d7']
    
    if spend > 0:
        # ROI = (revenue - cost) / cost × 100
        roi_pct = round((revenue - spend) / spend * 100, 2)
        # Profit = revenue - cost
        profit = round(revenue - spend, 2)
    else:
        roi_pct = 0
        profit = 0
    
    daily_data.append({
        'created_day': day,
        'revenue': round(revenue, 2),
        'cost': round(spend, 2),
        'roi_pct': roi_pct,
        'roas_pct': round(roas_d7, 2),
        'profit': profit
    })

df = pd.DataFrame(daily_data)
```

**Output columns:** `created_day`, `revenue`, `cost`, `roi_pct` (%), `roas_pct` (%), `profit`

- `ROI` = (revenue - cost) / cost × 100
- `ROAS` = revenue / cost × 100
- So sánh ROI với cùng kì tuần trước

## Bước 2: Phân tích

- **Trend tương tự case 1** (spend trend): Xem 7 ngày gần nhất có trend tăng/giảm không
- So sánh với 7 ngày trước
- **ROI tăng** → hiệu quả spend đang cải thiện
- **ROI giảm** → spend đang kém hiệu quả hơn
- **ROAS_D7 vs ROAS_D0**: 
  - ROAS_D0 < 100 nhưng ROAS_D7 > 100 → User có giá trị dài hạn
  - ROAS_D7 < 100 → Campaign không hiệu quả

### Lưu ý về Cohort Metrics
> ⚠️ **ROAS là COHORT METRIC**: D7 value cho window kết thúc ít hơn 7 ngày trước sẽ vẫn đang maturing (chưa ổn định) và sẽ tăng lên. Không nên đánh giá campaign là "tệ" dựa trên D7 ROAS cho window < 7 ngày.

## Bước 3: Gợi ý

- Mức độ cảnh báo Δ ROI tùy UA (phụ thuộc thể loại game và giai đoạn)
- Game có spend > $100 daily mà ROI > 30% → thông báo UA
- ROI có xu hướng tăng/giảm → kết hợp với trend spend (#1) để đánh giá scale
- ROI giảm liên tục 3 ngày → xem xét giảm budget hoặc tối ưu campaign

## Cảnh báo thresholds
- ROI giảm > 20% so với tuần trước → cảnh báo
- Spend > $100/ngày mà ROI < 0% → cảnh báo nghiêm trọng
- ROAS_D7 < 100% với spend > $50/ngày → cần tối ưu hoặc pause campaign

## Ví dụ minh họa

```python
# Ví dụ: Phân tích ROAS/ROI game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Query ROAS 14 ngày
result_14d = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7", "ROAS_D0", "IAA_ROAS_D7", "IAP_ROAS_D7"],
    getAll=True
)

# Step 3: Tính toán metrics
daily_metrics = extract_daily_metrics(result_14d)

# Step 4: Phân tích trend
daily_data = []
for day, m in sorted(daily_metrics.items()):
    spend = m['spend']
    revenue = m['revenue']
    roas_d7 = m['roas_d7']
    
    if spend > 0:
        roi = (revenue - spend) / spend * 100
    else:
        roi = 0
    
    daily_data.append({
        'day': day,
        'spend': round(spend, 2),
        'revenue': round(revenue, 2),
        'roas_d7': round(roas_d7, 2),
        'roi': round(roi, 2),
        'profit': round(revenue - spend, 2)
    })

# Step 5: Cảnh báo
df = pd.DataFrame(daily_data)
for _, row in df.iterrows():
    if row['spend'] > 100 and row['roi'] < 0:
        print(f"⚠️ NGHIÊM TRỌNG: {row['day']} - Spend ${row['spend']}, ROI {row['roi']:.1f}%")
    elif row['roi'] < -20:
        print(f"⚠️ ROI giảm mạnh: {row['day']} - ROI {row['roi']:.1f}%")

# Step 6: So sánh 2 giai đoạn
recent_7d = df.tail(7)
past_7d = df.head(7)

avg_roi_recent = recent_7d['roi'].mean()
avg_roi_past = past_7d['roi'].mean()

delta_roi = avg_roi_recent - avg_roi_past
if delta_roi < -20:
    print(f"🔴 CẢNH BÁO: ROI giảm {delta_roi:.1f}% so với tuần trước")
elif delta_roi > 20:
    print(f"🟢 ROA: ROI tăng {delta_roi:.1f}% so với tuần trước")
```

## Lưu ý quan trọng

1. **ROAS Scale**: Luôn nhớ ROAS là **PERCENT (0-100)**, không phải multiplier.
   - `ROAS_D7 = 85` nghĩa là 85%, không phải 85 lần.
   - Break-even tại `ROAS = 100%`.

2. **Cohort Metrics**: 
   - ROAS_D7 cho window < 7 ngày sẽ chưa ổn định.
   - Chỉ nên đánh giá ROAS_D7 khi reporting window đã đủ 7 ngày.

3. **Weighted Average**: Khi tổng hợp ROAS từ nhiều campaigns, luôn dùng **weighted average** theo spend, không phải average đơn giản.

4. **Revenue Calculation**: 
   - growX không trả về `event_revenue_usd`.
   - Tính ngược: `Revenue = Spend × (ROAS / 100)`
