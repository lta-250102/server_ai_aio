# Case 13: CPI game tăng/giảm (Game CPI Trend)

## Trigger
- Khi user hỏi về CPI, cost per install, giá thành cài đặt, network CPI.


## Mục tiêu
Xác định CPI trung bình của game có tăng/giảm và có hợp lý so với target không.

## ✅ GrowX Hỗ Trợ

growX hỗ trợ đầy đủ các metrics SPEND và INSTALLS, cho phép tính toán CPI hàng ngày.

## Bước 1: Lấy data từ GrowX

### 1.1. Tìm appId
```python
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == '<package_name>'][0]['appId']
```

### 1.2. Query SPEND và INSTALLS 14 ngày
```python
# Query 14 ngày gần nhất
result_14d = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS"],
    getAll=True
)
```

### 1.3. Tổng hợp metrics theo ngày
```python
from collections import defaultdict

def extract_daily_metrics(result):
    """
    Extract spend và installs theo ngày
    Trả về: {day: {spend: float, installs: int}}
    """
    daily_metrics = defaultdict(lambda: {'spend': 0.0, 'installs': 0})
    
    for campaign in result.get('campaigns', []):
        day = campaign.get('reportingDay', '')
        metrics = campaign.get('metrics', {})
        
        spend = metrics.get('SPEND', 0) or 0
        installs = metrics.get('INSTALLS', 0) or 0
        
        daily_metrics[day]['spend'] += spend
        daily_metrics[day]['installs'] += installs
    
    return dict(daily_metrics)

daily_metrics = extract_daily_metrics(result_14d)
```

### 1.4. Tính toán CPI và Delta
```python
import pandas as pd

def calculate_cpi_trend(daily_metrics):
    """
    Tính CPI và delta theo ngày
    Trả về list sorted by day
    """
    results = []
    
    # Sắp xếp theo ngày
    sorted_days = sorted(daily_metrics.keys())
    
    for i, day in enumerate(sorted_days):
        data = daily_metrics[day]
        spend = data['spend']
        installs = data['installs']
        
        if installs > 0:
            cpi = round(spend / installs, 4)
        else:
            cpi = 0
        
        results.append({
            'created_day': day,
            'cost': round(spend, 2),
            'installs': installs,
            'cpi': cpi
        })
    
    df = pd.DataFrame(results)
    
    # Tính delta
    if len(df) > 0:
        df['delta_cpi'] = df['cpi'].diff().round(4)
        df['delta_cpi_pct'] = ((df['cpi'].diff() / df['cpi'].shift(1).replace(0, None)) * 100).round(2)
    
    return df

cpi_df = calculate_cpi_trend(daily_metrics)
```

**Output columns:** `created_day`, `cost`, `installs`, `cpi`, `delta_cpi`, `delta_cpi_pct` (DoD%)

- `CPI` = Σ Cost / Σ Installs (theo ngày)
- `Δ CPI DoD` = (CPI Dx - CPI Dx-1) / CPI Dx-1
- `Δ CPI tuần` = (CPI tuần này - CPI tuần trước) / CPI tuần trước

## Bước 2: Phân tích

- **Xem 7 ngày gần nhất** trend của CPI là gì
- **Trend tương tự case 1** (spend trend)
- **CPI tăng** → network đang đắt hơn, có thể do competition tăng hoặc quality user giảm
- **CPI giảm** → network đang rẻ hơn, có thể do scale tốt hoặc quality user giảm

### Phân tích chi tiết:
```python
# Phân tích trend 7 ngày gần nhất
recent_7d = cpi_df.tail(7)
prev_7d = cpi_df.head(7)

avg_cpi_recent = recent_7d['cpi'].mean()
avg_cpi_prev = prev_7d['cpi'].mean()

if avg_cpi_prev > 0:
    cpi_week_delta = ((avg_cpi_recent - avg_cpi_prev) / avg_cpi_prev) * 100
else:
    cpi_week_delta = 0

print("=" * 60)
print(f"BÁO CÁO CPI GAME - {package_name}")
print("=" * 60)
print(f"{'Ngày':<12} {'Spend':>10} {'Installs':>10} {'CPI':>8} {'Δ CPI%':>10}")
print("-" * 60)

for _, row in cpi_df.iterrows():
    delta_str = f"{row['delta_cpi_pct']:.1f}%" if pd.notna(row['delta_cpi_pct']) else "N/A"
    print(f"{row['created_day']:<12} ${row['cost']:>9.2f} {row['installs']:>10} ${row['cpi']:>7.2f} {delta_str:>10}")

print("-" * 60)
print(f"Trung bình 7 ngày gần: ${avg_cpi_recent:.2f}")
print(f"Trung bình 7 ngày trước: ${avg_cpi_prev:.2f}")
print(f"Delta tuần: {cpi_week_delta:+.1f}%")
print("=" * 60)
```

## Bước 3: Gợi ý

- **Δ CPI DoD có trend tăng/giảm trên 3 ngày hoặc thay đổi đột ngột > 20%** → báo UA → check tiếp network (#14)
- **CPI tăng nhưng ROAS cũng tăng** → có thể chấp nhận (user chất lượng cao hơn)
- **CPI tăng mà ROAS giảm** → cảnh báo nghiêm trọng

## Cảnh báo thresholds
- Δ CPI DoD > 20% hoặc trend 3 ngày → cảnh báo UA

## Ví dụ minh họa

```python
# Ví dụ: Phân tích CPI game "MyGame"
package_name = "com.example.mygame"

# Step 1: Tìm appId
apps = growX_ua_list_apps()
game_id = [a for a in apps if a['bundleId'] == package_name][0]['appId']

# Step 2: Query SPEND và INSTALLS
result_14d = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

# Step 3: Tính CPI
daily_metrics = extract_daily_metrics(result_14d)
cpi_df = calculate_cpi_trend(daily_metrics)

# Step 4: Cảnh báo
print("🔍 KIỂM TRA CẢNH BÁO:")
print("-" * 40)

for _, row in cpi_df.iterrows():
    if pd.notna(row['delta_cpi_pct']):
        if row['delta_cpi_pct'] > 20:
            print(f"⚠️ CPI tăng mạnh {row['delta_cpi_pct']:.1f}% vào ngày {row['created_day']}")
        elif row['delta_cpi_pct'] < -20:
            print(f"✅ CPI giảm mạnh {abs(row['delta_cpi_pct']):.1f}% vào ngày {row['created_day']}")

# Kiểm tra trend 3 ngày liên tiếp
if len(cpi_df) >= 3:
    last_3 = cpi_df.tail(3)
    deltas = last_3['delta_cpi_pct'].dropna().tolist()
    
    if len(deltas) >= 2:
        if all(d > 0 for d in deltas):
            print(f"🔴 CẢNH BÁO: CPI tăng liên tiếp {len(deltas)} ngày")
        elif all(d < 0 for d in deltas):
            print(f"🟢 CPI giảm liên tiếp {len(deltas)} ngày")

# Kết hợp với ROAS
recent_7d = cpi_df.tail(7)
if recent_7d['cpi'].iloc[-1] > recent_7d['cpi'].iloc[-2]:
    print("⚠️ CPI đang tăng: Cần kiểm tra ROAS để xem user có chất lượng hơn không")
else:
    print("✅ CPI đang giảm hoặc ổn định")
```

## Kết hợp với ROAS Analysis

Để có phân tích đầy đủ, nên kết hợp CPI với ROAS:

```python
# Lấy thêm ROAS để phân tích kết hợp
result_with_roas = growX_ua_list_campaigns(
    appId=game_id,
    days=14,
    metrics=["SPEND", "INSTALLS", "ROAS_D7"],
    getAll=True
)

daily_with_roas = defaultdict(lambda: {'spend': 0, 'installs': 0, 'weighted_roas': 0})
for campaign in result_with_roas.get('campaigns', []):
    day = campaign.get('reportingDay', '')
    metrics = campaign.get('metrics', {})
    
    spend = metrics.get('SPEND', 0) or 0
    installs = metrics.get('INSTALLS', 0) or 0
    roas_d7 = metrics.get('ROAS_D7', 0) or 0
    
    daily_with_roas[day]['spend'] += spend
    daily_with_roas[day]['installs'] += installs
    daily_with_roas[day]['weighted_roas'] += spend * roas_d7

# Tính cả CPI và ROAS
combined_df = []
for day, data in daily_with_roas.items():
    spend = data['spend']
    installs = data['installs']
    
    cpi = spend / installs if installs > 0 else 0
    roas_d7 = data['weighted_roas'] / spend if spend > 0 else 0
    
    combined_df.append({
        'day': day,
        'cpi': round(cpi, 2),
        'roas_d7': round(roas_d7, 2),
        'spend': round(spend, 2),
        'installs': installs
    })

combined_df.sort(key=lambda x: x['day'])
combined = pd.DataFrame(combined_df)

# Phân tích kết hợp
for _, row in combined.iterrows():
    if row['cpi'] > 1.0:  # CPI cao
        if row['roas_d7'] > 100:
            print(f"{row['day']}: CPI cao (${row['cpi']:.2f}) nhưng ROAS tốt ({row['roas_d7']:.1f}%) → Chấp nhận")
        else:
            print(f"{row['day']}: CPI cao (${row['cpi']:.2f}) + ROAS kém ({row['roas_d7']:.1f}%) → NGHIÊM TRỌNG")
```

## Lưu ý quan trọng

1. **CPI Calculation**:
   - CPI = Total Spend / Total Installs (theo ngày)
   - Luôn dùng weighted average khi tổng hợp từ nhiều campaigns

2. **Cohort Metrics**:
   - Installs có thể bị ảnh hưởng bởi attribution window
   - 1-2 ngày cuối cùng có thể chưa đầy đủ

3. **Seasonality**:
   - CPI thường tăng vào các ngày lễ, sự kiện lớn
   - So sánh với cùng tuần trước (WoW) để loại bỏ yếu tố ngày trong tuần

4. **Network Competition**:
   - CPI tăng có thể do competition tăng trên network
   - CPI giảm có thể do network đang scale tốt hoặc creative kém hiệu quả
