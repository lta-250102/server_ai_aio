---
name: growx-mcp
description: GrowX MCP — UA analysis qua tools (ua_list_apps, ua_list_campaigns, etc). Dùng cho quick overview, spend/ROAS/CPI/retention ở network/campaign level.
version: 1.0
last_updated: 2026-09-28
---

# GrowX MCP Skills

## Trigger
Khi user hỏi về phân tích UA qua GrowX MCP: spend, ROAS, CPI, retention, budget, campaign performance.

## Khi nào dùng
- ✅ Spend, ROAS, CPI, Retention cơ bản
- ✅ Quick campaign overview — nhanh, không cần SQL
- ❌ Geo/creative/site_id analysis → dùng Appsflyer DWH
- ❌ Retention purchase-based (D0) → dùng Appsflyer DWH

## Resources
- [Metrics Reference](metrics-reference.md) — Full metric dictionary, scales, units

## Cases

### Spend & Budget (Cases 1-6)
| # | Case | File |
|---|------|------|
| 1 | Spend game tăng/giảm | [cases/case-01-spend-trend.md](cases/case-01-spend-trend.md) |
| 2 | Phân bổ budget media source | [cases/case-02-budget-allocation.md](cases/case-02-budget-allocation.md) |
| 3 | Campaign trong network biến động | [cases/case-03-campaign-analysis.md](cases/case-03-campaign-analysis.md) |
| 4 | Geo thay đổi traffic | [cases/case-04-geo-traffic.md](cases/case-04-geo-traffic.md) |
| 5 | Site_id đẩy spend | [cases/case-05-siteid-spend.md](cases/case-05-siteid-spend.md) |
| 6 | Creative spending nhiều nhất | [cases/case-06-creative-spending.md](cases/case-06-creative-spending.md) |

### ROAS/ROI (Cases 7-12)
| # | Case | File |
|---|------|------|
| 7 | ROAS/ROI game | [cases/case-07-roas-roi.md](cases/case-07-roas-roi.md) |
| 8 | Network ảnh hưởng dòng tiền (LTV/ROAS) | [cases/case-08-network-ltv.md](cases/case-08-network-ltv.md) |
| 9 | ROAS của campaign | [cases/case-09-campaign-roas.md](cases/case-09-campaign-roas.md) |
| 10 | Geo nào có ROAS lệch | [cases/case-10-geo-roas.md](cases/case-10-geo-roas.md) |
| 11 | Site_id ROAS thấp/cao | [cases/case-11-siteid-roas.md](cases/case-11-siteid-roas.md) |
| 12 | Creative ROAS tốt/xấu | [cases/case-12-creative-roas.md](cases/case-12-creative-roas.md) |

### CPI (Cases 13-18)
| # | Case | File |
|---|------|------|
| 13 | CPI game tăng/giảm | [cases/case-13-cpi-game.md](cases/case-13-cpi-game.md) |
| 14 | Network CPI cao/thấp | [cases/case-14-network-cpi.md](cases/case-14-network-cpi.md) |
| 15 | Campaign CPI lệch | [cases/case-15-campaign-cpi.md](cases/case-15-campaign-cpi.md) |
| 16 | Geo CPI lệch | [cases/case-16-geo-cpi.md](cases/case-16-geo-cpi.md) |
| 17 | Site_id CPI bất thường | [cases/case-17-siteid-cpi.md](cases/case-17-siteid-cpi.md) |
| 18 | Creative CPI thấp/cao | [cases/case-18-creative-cpi.md](cases/case-18-creative-cpi.md) |

### Retention (Cases 19-24)
| # | Case | File |
|---|------|------|
| 19 | Retention game D1/D3/D7 | [cases/case-19-retention-game.md](cases/case-19-retention-game.md) |
| 20 | Network Retention | [cases/case-20-network-retention.md](cases/case-20-network-retention.md) |
| 21 | Campaign Retention | [cases/case-21-campaign-retention.md](cases/case-21-campaign-retention.md) |
| 22 | Geo Retention | [cases/case-22-geo-retention.md](cases/case-22-geo-retention.md) |
| 23 | Site_id Retention | [cases/case-23-siteid-retention.md](cases/case-23-siteid-retention.md) |
| 24 | Creative Retention | [cases/case-24-creative-retention.md](cases/case-24-creative-retention.md) |

## Tools
- `growX_ua_list_apps` — List games, get appId
- `growX_ua_list_networks` — List ad networks
- `growX_ua_list_connectors` — List ad accounts
- `growX_ua_list_campaigns` — Query campaign metrics
- `growX_ua_describe_metrics` — Metric dictionary
