# RIDA Results: Comprehensive Agentic Dataset Processing

This folder contains the complete, processed, and verified outputs for all datasets from the **HackerRank Orchestrate — Buy or Wait? Financial Decision Agent** challenge.

**Generation Timestamp**: 2026-09-13 11:15:46
**Total Evaluation Requests**: 250 requests (`request_26` to `request_275`)
**Total Master Requests**: 275 requests (`request_01` to `request_275`)
**Financial Decision Engine**: Multimodal 90-Day Cash Flow Simulation with Grounded Natural Reasoning

---

## 📁 Files in this Folder

| File Name | Description | Rows | Primary Key |
|:---|:---|:---|:---|
| [`01_requests_predictions.csv`](01_requests_predictions.csv) | **Official Submission File**: 250 evaluation requests in exact 8-column schema | 250 | `request_id` |
| [`02_requests_predictions_detailed.csv`](02_requests_predictions_detailed.csv) | Full context merge: Request inputs + Evaluated decisions side-by-side | 250 | `request_id` |
| [`03_sample_requests_evaluation.csv`](03_sample_requests_evaluation.csv) | Verified evaluation on the 25 benchmark sample requests | 25 | `request_id` |
| [`04_master_all_requests_results.csv`](04_master_all_requests_results.csv) | Complete master dataset of all 275 requests (`request_01` through `request_275`) | 275 | `request_id` |
| [`05_financial_profiles_analyzed.csv`](05_financial_profiles_analyzed.csv) | Reconstructed financial states, income, burn rates, and headroom for all 275 users | 275 | `user_id` |
| [`06_financial_events_resolved.csv`](06_financial_events_resolved.csv) | 25,342 financial transactions with image-extracted amounts and INR conversions | 25,342 | `event_id` |
| [`07_payment_options_evaluated.csv`](07_payment_options_evaluated.csv) | All 790 installment & financing options evaluated for affordability & suitability | 790 | `payment_option_id` |
| [`08_multimodal_images_extractions.csv`](08_multimodal_images_extractions.csv) | All 16 invoice, receipt, and payslip images with verified extracted amounts | 16 | `image_id` |
| [`09_messages_intelligence.csv`](09_messages_intelligence.csv) | Extracted message rules (rent increases, contract terminations, salary dates) | 215 | `message_id` |
| [`10_exchange_rates_matrix.csv`](10_exchange_rates_matrix.csv) | Currency conversion matrix and exchange rates across INR, USD, EUR, IDR, ZAR | 134 | `from_currency` |
| [`11_affordability_analytics.csv`](11_affordability_analytics.csv) | Summary distribution metrics and percentage breakdown | 9 | `category` |
| [`12_cashflow_90day_trajectories.csv`](12_cashflow_90day_trajectories.csv) | Day-by-day projected balances, inflows, outflows, and surplus over 90 days | 5,000+ | `request_id` + `day_offset` |
| [`RIDA.csv`](RIDA.csv) | Direct copy of the clarified evaluation predictions for single-file access | 250 | `request_id` |

---

## 📊 Summary of Decisions (250 Evaluation Requests)

- **`not_affordable`**: 73 (29.2%)
- **`affordable_now`**: 69 (27.6%)
- **`affordable_with_plan`**: 67 (26.8%)
- **`affordable_later`**: 41 (16.4%)

### Recommended Payment Methods:
- **`full_payment`**: 75 (30.0%)
- **`not_recommended`**: 73 (29.2%)
- **`installments`**: 53 (21.2%)
- **`wait`**: 41 (16.4%)
- **`partial_payment`**: 8 (3.2%)
