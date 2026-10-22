# Tài Liệu Tham Chiếu Chỉ Số UA (User Acquisition)
**Nguồn dữ liệu:** Appsflyer qua hệ thống growX

## ⚠️ LƯU Ý QUAN TRỌNG VỀ ĐƠN VỊ (SCALES)
Hệ thống có **2 thang đo** quan trọng cần phân biệt tuyệt đối trước khi phân tích:

1. **RATIO (Tỷ lệ - 0..1):**
   - Các metric: `CTR`, `IR`.
   - Ví dụ: `0.03` nghĩa là **3%** (không phải 3%).
2. **PERCENT (Phần trăm - 0..100):**
   - Các metric: `ROAS`, `RETENTION`.
   - Ví dụ: `85` nghĩa là **85%** (không phải 85 lần).
3. **CURRENCY (Tiền tệ - USD):**
   - Các metric: `SPEND`, `CPI`, `CPC`, `CPM`.

---

## 1. Nhóm Delivery (Hiển thị & Tương tác)
Đánh giá chất lượng quảng cáo và độ phủ.

| Key | Label | Đơn vị | Công thức | Ý nghĩa & Lưu ý |
| :--- | :--- | :--- | :--- | :--- |
| `IMPRESSIONS` | Impressions | COUNT | - | Số lần quảng cáo được hiển thị. Top of funnel: không có impression thì không có gì xảy ra. |
| `CLICKS` | Clicks | COUNT | - | Số lần người dùng nhấn vào ad. |
| `CTR` | CTR | **RATIO_0_1** | `clicks / impressions` | Tỷ lệ nhấp. Là chỉ số chất lượng Creative. CTR thấp nghĩa là ad không thu hút. |
| `CPC` | CPC | USD | `spend / clicks` | Chi phí trung bình cho 1 click. |
| `CPM` | CPM | USD | `spend / impressions * 1000` | Chi phí cho 1000 lần hiển thị. Dùng để so sánh giá cả audience giữa các network. |

---

## 2. Nhóm Cost (Chi phí)
Đánh giá hiệu quả chi tiêu.

| Key | Label | Đơn vị | Công thức | Ý nghĩa & Lưu ý |
| :--- | :--- | :--- | :--- | :--- |
| `SPEND` | Spend | USD | - | Tổng tiền đã chi. Là mẫu số của mọi chỉ số hiệu quả. |
| `CPI` | CPI | USD | `spend / installs` | **Chi phí trên mỗi lượt cài đặt (Core metric).** CPI thấp mà ROAS thấp thì user vô giá trị. |

---

## 3. Nhóm Conversions (Chuyển đổi)
Đánh giá quy trình từ Click -> Install.

| Key | Label | Đơn vị | Công thức | Ý nghĩa & Lưu ý |
| :--- | :--- | :--- | :--- | :--- |
| `INSTALLS` | Installs | COUNT | - | Số người cài app sau khi click. |
| `IR` | IR | **RATIO_0_1** | `installs / clicks` | Tỷ lệ cài đặt trên mỗi click (Click-to-Install Rate). IR thấp (khi CTR cao) thường do Store Listing (Icon/Screenshots) kém. |
| `IPM` | IPM | RATE_PER_1000 | `installs / impressions * 1000` | Số cài đặt trên 1000 impression. Dự báo khả năng scale của network. |

---

## 4. Nhóm ROAS (Doanh thu)
**Định nghĩa chung:** Trả về bao nhiêu tiền trên mỗi đô la chi ra.
**Lưu ý chung:** Là **COHORT metric** (thuộc nhóm người dùng cài đặt trong cửa sổ thời gian).
- Giá trị **100** = Break-even (Hòa vốn).
- Giá trị < 100 = Lỗ.
- Giá trị > 100 = Lãi.

### 4.1. Total ROAS (Tổng doanh thu: IAA + IAP)
*Dùng để ra quyết định scaling (D7 là điểm chuẩn).*

| Key | Label | Đơn vị | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `ROAS_D0` | D0 Total ROAS | **PERCENT_0_100** | Doanh thu 0 ngày sau cài đặt. |
| `ROAS_D1` | D1 Total ROAS | **PERCENT_0_100** | Doanh thu 1 ngày sau cài đặt. |
| `ROAS_D3` | D3 Total ROAS | **PERCENT_0_100** | Doanh thu 3 ngày sau cài đặt. |
| `ROAS_D7` | D7 Total ROAS | **PERCENT_0_100** | **Doanh thu 7 ngày (Deciding point).** |
| `ROAS_D28` | D28 Total ROAS | **PERCENT_0_100** | Doanh thu 28 ngày. |
| `ROAS_D60` | D60 Total ROAS | **PERCENT_0_100** | Doanh thu 60 ngày. |
| `ROAS_D90` | D90 Total ROAS | **PERCENT_0_100** | Doanh thu 90 ngày. |
| `ROAS_D180` | D180 Total ROAS | **PERCENT_0_100** | Doanh thu 180 ngày. |

### 4.2. IAA ROAS (Chỉ doanh thu từ Ads)
| Key | Label | Đơn vị |
| :--- | :--- | :--- |
| `IAA_ROAS_D0` ... `D180` | D0..D180 IAA ROAS | **PERCENT_0_100** |

### 4.3. IAP ROAS (Chỉ doanh thu từ Mua hàng)
| Key | Label | Đơn vị |
| :--- | :--- | :--- |
| `IAP_ROAS_D0` ... `D180` | D0..D180 IAP ROAS | **PERCENT_0_100** |

---

## 5. Nhóm Retention (Giữ chân)
Đánh giá chất lượng Traffic (Traffic phù hợp game hay không).
*Lưu ý: Retention là cohort metric, dữ liệu sẽ tăng dần theo thời gian.*

| Key | Label | Đơn vị | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `RETENTION_D1` | D1 Retention | **PERCENT_0_100** | Tỷ lệ người dùng quay lại sau 1 ngày. |
| `RETENTION_D3` | D3 Retention | **PERCENT_0_100** | Tỷ lệ người dùng quay lại sau 3 ngày. |
| `RETENTION_D7` | D7 Retention | **PERCENT_0_100** | Tỷ lệ người dùng quay lại sau 7 ngày. |
| `RETENTION_D14` | D14 Retention | **PERCENT_0_100** | Tỷ lệ người dùng quay lại sau 14 ngày. |
| `RETENTION_D28` | D28 Retention | **PERCENT_0_100** | Tỷ lệ người dùng quay lại sau 28 ngày. |