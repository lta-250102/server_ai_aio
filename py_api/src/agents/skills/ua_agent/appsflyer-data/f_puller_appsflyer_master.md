# `dwh_system.f_puller_appsflyer_master`

> **GENERATED** bởi `tools/SchemaReferenceGenerator` từ code schema (`*Tables.kt`).
> Đổi schema → sửa code (kèm `desc`) → chạy lại generator TRONG CÙNG COMMIT.
> Nghĩa cột = field `Column.desc`; cột "(chưa có mô tả)" = desc còn trống trong code.

## Meta

| Field | Value |
|---|---|
| Engine | `CnchMergeTree` |
| Partition | `toYYYYMM(created_day)` |
| Order by | `package_name, platform, created_day, media_source, campaign_id` |
| **UNIQUE KEY** | `package_name, platform, created_day, media_source, campaign_id, ad_set_id, ad_id, country, data_type` |
| TTL | `created_day + toIntervalDay(730)` |
| Fill blank → `UNKNOWN`/`""` | `media_source, campaign_id, ad_set_id, ad_id, country, data_type` |
| Settings | `index_granularity = 8192, partition_level_unique_keys = 1` |

## Columns

| Column | Type | Meaning |
|---|---|---|
| `package_name` | `LowCardinality(String)` | Package game — trong UNIQUE KEY |
| `platform` | `LowCardinality(String)` | android/ios — trong UNIQUE KEY (bảng flat legacy, khác hợp đồng ua_*) |
| `server_receive_time` | `DateTime64(3)` | Mốc bản tin tới cổng ingest |
| `client_sent_time` | `Nullable(DateTime64(3))` | Puller stamp = data-date của report (envelope) |
| `created_day` | `Date` | DATA-DATE của report — AF revise tới T+30, re-pull upsert đúng ngày; partition + key |
| `account_id` | `Nullable(String)` | Không dùng cho report aggregate (thường null) |
| `device_id` | `Nullable(String)` | Không dùng cho report aggregate (thường null) |
| `uuid` | `Nullable(String)` | UUID bản tin từ envelope (audit) |
| `media_source` | `LowCardinality(String)` | Nguồn media attribution (AF) — key dim, blank fill UNKNOWN |
| `channel` | `LowCardinality(Nullable(String))` | Kênh trong media source (nullable) |
| `partner` | `LowCardinality(Nullable(String))` | Partner/agency attribution (nullable) |
| `campaign` | `Nullable(String)` | Tên campaign (cột thường — id mới là key) |
| `campaign_id` | `String` | ID campaign — key dim, blank fill UNKNOWN |
| `ad_set` | `Nullable(String)` | Tên ad set (cột thường) |
| `ad_set_id` | `String` | ID ad set — key dim; rollup row campaign-level có thể UNKNOWN |
| `ad` | `Nullable(String)` | Tên ad (cột thường) |
| `ad_id` | `String` | ID ad — key dim; rollup row có thể UNKNOWN |
| `keywords` | `Nullable(String)` | Keyword targeting (nullable) |
| `publisher_id` | `Nullable(String)` | ID publisher/site (nullable) |
| `country` | `LowCardinality(String)` | Country — key dim, blank fill UNKNOWN |
| `data_type` | `LowCardinality(String)` | Loại dòng report AF (organic/non-organic…) — key dim |
| `created_date` | `Nullable(DateTime64(3))` | Business date của report từ vendor (nullable) |
| `impressions` | `Nullable(Int32)` | Số impression |
| `clicks` | `Nullable(Int32)` | Số click |
| `installs` | `Nullable(Int32)` | Số install attributed |
| `sessions` | `Nullable(Int32)` | Số session |
| `loyal_users` | `Nullable(Int32)` | Số loyal user (định nghĩa AF) |
| `cost` | `Nullable(Float64)` | Chi phí UA (USD) |
| `avg_e_cpi` | `Nullable(Float64)` | eCPI trung bình — cột ratio (bảng duy nhất còn giữ) |
| `conversion_rate` | `Nullable(Float64)` | Tỷ lệ conversion — cột ratio (bảng duy nhất còn giữ) |
| `roi` | `Nullable(Float64)` | ROI — cột ratio (bảng duy nhất còn giữ) |
| `revenue` | `Nullable(Float64)` | Doanh thu attributed (USD) |
| `event_extra_props` | `JSONB` | Tail field hiếm của source (JSONB) |
| `pre_enrich_props` | `JSONB` | Giá trị trước enrich (JSONB, audit) |
| `sink_time` | `DateTime64(3)` | Loader stamp lúc ghi (KHÔNG phải BH default) — tie-break last-write-wins |

---

## Pitfalls

> **Loại:** bẫy per-table · **Cho ai:** analyst/viz/dev query bảng này · **Map:** từng bẫy → column(s) cụ thể

### 1. UNIQUE-KEY upsert — `package_name`, `platform`, `created_day`, `media_source`, `campaign_id`, `ad_set_id`, `ad_id`, `country`, `data_type`

Re-pull/vendor revise tới T+30, re-pull upsert đúng ngày — count theo ngày có thể NHÍCH LÊN theo thời gian, không phải bug.

**Hậu quả:** Đếm row `WHERE created_day = '2026-07-01'` ngày hôm sau > ngày hôm trước → hiểu nhầm là data duplicate.

**Cách tránh:** Hiểu rằng re-pull là upsert; không dùng row count làm metric ổn định.

### 2. Sentinel fill — `media_source`, `campaign_id`, `ad_set_id`, `ad_id`, `country`, `data_type`

String key dims blank → `UNKNOWN`; filter "loại unknown" nhớ cover cả 3 dạng: `UNKNOWN`, `''`, `NULL`.

**Hậu quả:** Filter `WHERE media_source != 'UNKNOWN'` vẫn còn dòng blank `''` → kết quả sai.

**Cách tránh:** Filter `WHERE media_source NOT IN ('UNKNOWN', '') AND media_source IS NOT NULL`.

### 3. Cột ratio chỉ còn trên bảng này — `avg_e_cpi`, `conversion_rate`, `roi`

Bảng duy nhất còn giữ 3 cột ratio; các grain khác tự derive downstream từ cost/installs/revenue.

**Hậu quả:** Tìm `conversion_rate` trên bảng ua_* khác → không thấy.

**Cách tránh:** Dùng `f_puller_appsflyer_master` cho ratio; các bảng khác tự tính từ cost/installs/revenue.

### 4. Dòng lịch sử trước fix alias 2026-07-15 — `media_source`, `campaign_id`

Trước fix: `media_source`/`campaign_id` = `UNKNOWN` (giá trị thật nằm trong `event_extra_props.appsflyer_*`).

**Hậu quả:** Data trước 2026-07-15 có thể có `media_source = 'UNKNOWN'` → hiểu nhầm là missing data.

**Cách tránh:** Tự lành trong ~30 ngày qua chu kỳ re-pull của AF; tra `event_extra_props.appsflyer_*` cho data cũ.

### 5. `platform` trong UNIQUE KEY — `platform`

Bảng flat legacy, khác hợp đồng ua_* — `platform` là trục key, không phải resolved field.

**Hậu quả:** So sánh với ua_* tables (platform không trong key) → grain khác nhau.

**Cách tránh:** Group-by `platform` khi query bảng này; hiểu rằng đây là flat table, không aggregated.
