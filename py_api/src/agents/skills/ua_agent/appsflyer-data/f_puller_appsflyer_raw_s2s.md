# `dwh_system.f_puller_appsflyer_raw_s2s`

> **GENERATED** bởi `tools/SchemaReferenceGenerator` từ code schema (`*Tables.kt`).
> Đổi schema → sửa code (kèm `desc`) → chạy lại generator TRONG CÙNG COMMIT.
> Nghĩa cột = field `Column.desc`; cột "(chưa có mô tả)" = desc còn trống trong code.

## Meta

| Field | Value |
|---|---|
| Engine | `CnchMergeTree` |
| Partition | `toYYYYMM(created_day)` |
| Order by | `package_name, platform, created_day, media_source, event_name` |
| UNIQUE KEY | — (APPEND) |
| TTL | `created_day + toIntervalDay(730)` |
| Fill blank → `UNKNOWN`/`""` | `media_source, event_name` |
| Settings | `index_granularity = 8192` |

## Columns

| Column | Type | Meaning |
|---|---|---|
| `package_name` | `LowCardinality(String)` | Package game |
| `platform` | `LowCardinality(String)` | android/ios |
| `server_receive_time` | `DateTime64(3)` | Mốc bản tin tới cổng ingest |
| `client_sent_time` | `Nullable(DateTime64(3))` | Client/puller stamp từ envelope (nullable) |
| `created_day` | `Date` | Ngày event — partition |
| `account_id` | `Nullable(String)` | Account id nếu map được (D60 chung) |
| `device_id` | `Nullable(String)` | Device id nếu có (D60 chung) |
| `uuid` | `Nullable(String)` | UUID bản tin từ envelope (audit) |
| `appsflyer_id` | `Nullable(String)` | AppsFlyer device id (AF SDK) |
| `customer_user_id` | `Nullable(String)` | User id do game set qua AF SDK |
| `advertising_id` | `Nullable(String)` | GAID của device (Android) |
| `idfa` | `Nullable(String)` | IDFA của device (iOS) |
| `idfv` | `Nullable(String)` | IDFV của device (iOS) |
| `amazon_aid` | `Nullable(String)` | Amazon advertising id |
| `app_set_id` | `Nullable(String)` | Android App Set ID |
| `app_id` | `Nullable(String)` | App id phía AF (nullable — KHÔNG phải trục key như ua_*) |
| `app_name` | `Nullable(String)` | Tên app |
| `app_version` | `Nullable(String)` | Version app |
| `bundle_id` | `Nullable(String)` | Bundle id (iOS) |
| `api_version` | `Nullable(String)` | Version API AF |
| `sdk_version` | `Nullable(String)` | Version AF SDK |
| `os_version` | `Nullable(String)` | Version OS device |
| `event_name` | `LowCardinality(String)` | Tên event AF (install/in-app…) — blank fill UNKNOWN |
| `event_source` | `LowCardinality(Nullable(String))` | Nguồn event (SDK/S2S) |
| `event_type` | `LowCardinality(Nullable(String))` | Loại event AF |
| `created_date` | `Nullable(DateTime64(3))` | Business date từ vendor (nullable) |
| `event_time` | `Nullable(DateTime64(3))` | Thời điểm event (UTC) |
| `event_time_selected_timezone` | `Nullable(String)` | Event time theo timezone chọn trong AF (String) |
| `install_time` | `Nullable(DateTime64(3))` | Thời điểm install attributed |
| `install_time_selected_timezone` | `Nullable(String)` | Install time theo timezone chọn trong AF (String) |
| `attributed_touch_time` | `Nullable(DateTime64(3))` | Thời điểm touch (click/impression) được attribute |
| `attributed_touch_time_selected_timezone` | `Nullable(String)` | Touch time theo timezone chọn trong AF (String) |
| `device_download_time` | `Nullable(DateTime64(3))` | Thời điểm download trên device |
| `device_download_time_selected_timezone` | `Nullable(String)` | Download time theo timezone chọn trong AF (String) |
| `selected_timezone` | `Nullable(String)` | Timezone chọn trong app settings AF |
| `media_source` | `LowCardinality(String)` | Nguồn media attribution — blank fill UNKNOWN |
| `af_channel` | `LowCardinality(Nullable(String))` | Kênh trong media source |
| `af_prt` | `Nullable(String)` | Agency/partner (af_prt) |
| `campaign` | `Nullable(String)` | Tên campaign |
| `campaign_type` | `LowCardinality(Nullable(String))` | Loại campaign |
| `af_c_id` | `Nullable(String)` | ID campaign (af_c_id) |
| `af_ad` | `Nullable(String)` | Tên ad |
| `af_ad_id` | `Nullable(String)` | ID ad |
| `af_ad_type` | `LowCardinality(Nullable(String))` | Loại ad |
| `af_adset` | `Nullable(String)` | Tên ad set |
| `af_adset_id` | `Nullable(String)` | ID ad set |
| `af_siteid` | `Nullable(String)` | Site/publisher id phía network |
| `af_sub5` | `Nullable(String)` | Sub-param 5 (chỉ sub5 được promote — sub1..4 vào event_extra_props) |
| `af_attribution_lookback` | `Nullable(String)` | Cửa sổ lookback attribution (vd 7d) |
| `af_reengagement_window` | `Nullable(String)` | Cửa sổ re-engagement |
| `conversion_type` | `LowCardinality(Nullable(String))` | Loại conversion (install/re-install/re-engagement) |
| `engagement_type` | `LowCardinality(Nullable(String))` | Loại engagement (click/impression) |
| `match_type` | `LowCardinality(Nullable(String))` | Cách match attribution (id matching/probabilistic…) |
| `is_retargeting` | `Nullable(Bool)` | Cờ event thuộc campaign retargeting |
| `is_primary_attribution` | `Nullable(Bool)` | Cờ attribution chính (trong re-engagement window đôi) |
| `retention` | `Nullable(String)` | (chưa có mô tả — cần bổ sung) |
| `original_url` | `Nullable(String)` | URL attribution gốc (click URL) |
| `network_account_id` | `Nullable(Int64)` | (chưa có mô tả — cần bổ sung) |
| `total_candidates` | `Nullable(Int32)` | (chưa có mô tả — cần bổ sung) |
| `af_cost_model` | `LowCardinality(Nullable(String))` | Model cost (CPI/CPC/CPM…) |
| `af_cost_currency` | `LowCardinality(Nullable(String))` | Tiền tệ của af_cost_value |
| `af_cost_value` | `Nullable(Float64)` | Chi phí attributed theo cost model |
| `event_revenue` | `Nullable(Float64)` | Doanh thu event theo event_revenue_currency |
| `event_revenue_currency` | `LowCardinality(Nullable(String))` | Tiền tệ của event_revenue |
| `event_revenue_usd` | `Nullable(Float64)` | Doanh thu event quy đổi USD |
| `event_value` | `Nullable(String)` | Payload event free-form (giữ String) |
| `selected_currency` | `LowCardinality(Nullable(String))` | Tiền tệ chọn trong AF app settings |
| `revenue_in_selected_currency` | `Nullable(Float64)` | Doanh thu theo selected_currency |
| `country` | `LowCardinality(Nullable(String))` | Country user (chỉ 3 cột geo được promote — còn lại vào event_extra_props) |
| `country_code` | `LowCardinality(Nullable(String))` | Country code user |
| `language` | `LowCardinality(Nullable(String))` | Ngôn ngữ device |
| `gp_install_begin` | `Nullable(DateTime64(3))` | Google Play install referrer — mốc bắt đầu install |
| `gp_referrer` | `Nullable(String)` | Google Play install referrer string |
| `contributor_1_campaign` | `Nullable(String)` | Multi-touch contributor 1 — tên campaign |
| `contributor_1_media_source` | `LowCardinality(Nullable(String))` | Multi-touch contributor 1 — media source |
| `contributor_1_touch_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 1 — loại touch (click/impression) |
| `contributor_1_touch_time` | `Nullable(DateTime64(3))` | Multi-touch contributor 1 — thời điểm touch |
| `contributor_1_match_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 1 — match type |
| `contributor_1_engagement_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 1 — engagement type |
| `contributor_2_campaign` | `Nullable(String)` | Multi-touch contributor 2 — tên campaign |
| `contributor_2_media_source` | `LowCardinality(Nullable(String))` | Multi-touch contributor 2 — media source |
| `contributor_2_touch_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 2 — loại touch (click/impression) |
| `contributor_2_touch_time` | `Nullable(DateTime64(3))` | Multi-touch contributor 2 — thời điểm touch |
| `contributor_2_match_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 2 — match type |
| `contributor_2_engagement_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 2 — engagement type |
| `contributor_3_campaign` | `Nullable(String)` | Multi-touch contributor 3 — tên campaign |
| `contributor_3_media_source` | `LowCardinality(Nullable(String))` | Multi-touch contributor 3 — media source |
| `contributor_3_touch_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 3 — loại touch (click/impression) |
| `contributor_3_touch_time` | `Nullable(DateTime64(3))` | Multi-touch contributor 3 — thời điểm touch |
| `contributor_3_match_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 3 — match type |
| `contributor_3_engagement_type` | `LowCardinality(Nullable(String))` | Multi-touch contributor 3 — engagement type |
| `event_extra_props` | `JSONB` | Tail field hiếm của source (JSONB) |
| `pre_enrich_props` | `JSONB` | Giá trị trước enrich (JSONB, audit) |
| `sink_time` | `DateTime64(3)` | Loader stamp lúc ghi (KHÔNG phải BH default) — tie-break last-write-wins |

---

## Pitfalls

> **Loại:** bẫy per-table · **Cho ai:** analyst/viz/dev query bảng này · **Map:** từng bẫy → column(s) cụ thể

### 1. APPEND table — `package_name`, `platform`, `created_day`, `media_source`, `event_name`

Mỗi lần pull thêm 1 bản mới — không upsert, không dedup tự động.

**Hậu quả:** Re-run pipeline → duplicate rows trong bảng.

**Cách tránh:** Dùng `uuid` cho dedup downstream; hiểu rằng APPEND là append-only.

### 2. Sentinel fill — `media_source`, `event_name`

String key dims blank → `UNKNOWN`; filter "loại unknown" nhớ cover cả 3 dạng.

**Hậu quả:** Filter `WHERE media_source != 'UNKNOWN'` vẫn còn dòng blank `''` → kết quả sai.

**Cách tránh:** Filter `WHERE media_source NOT IN ('UNKNOWN', '') AND media_source IS NOT NULL`.

### 3. `mmp_install_time` là String — `mmp_install_time`

Không phải DateTime — không cast ngầm được.

**Hậu quả:** `CAST(mmp_install_time AS DateTime)` → error hoặc sai kết quả.

**Cách tránh:** Dùng `mmp_install_time` as String; parse thủ công nếu cần DateTime.

### 4. `event_revenue`/`event_revenue_usd` — `event_revenue`, `event_revenue_currency`, `event_revenue_usd`

`event_revenue` theo `event_revenue_currency`; `event_revenue_usd` = quy đổi USD.

**Hậu quả:** Dùng `event_revenue` cho so sánh cross-currency → sai.

**Cách tránh:** Dùng `event_revenue_usd` cho so sánh đa tiền tệ; `event_revenue` chỉ trong currency gốc.

### 5. Multi-touch contributors — `contributor_1_*`, `contributor_2_*`, `contributor_3_*`

3 cột contributor — mỗi contributor có campaign/media_source/touch_type/touch_time/match_type/engagement_type.

**Hậu quả:** Query contributor 1 riêng → miss attribution từ contributor 2/3.

**Cách tránh:** UNION ALL 3 contributors cho multi-touch analysis; hiểu rằng attribution có thể split.

### 6. `af_sub5` promoted, sub1..4 vào event_extra_props — `af_sub5`, `event_extra_props`

Chỉ sub5 được promote lên cột; sub1..4 nằm trong `event_extra_props`.

**Hậu quả:** Tìm `af_sub1` → không thấy; data nằm trong JSONB.

**Cách tránh:** Dùng `jsonb_extract_string(event_extra_props, '$.af_sub1')` cho sub1..4.
