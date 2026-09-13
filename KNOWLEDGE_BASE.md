# Knowledge Base: Buy or Wait? — AI Financial Decision & Orchestration Engine

---

## 1. Executive Summary

The **"Buy or Wait?" AI Financial Decision Engine** is an intelligent, multi-agent financial advisory platform built for the **HackerRank Orchestrate** competition. It solves the real-world problem of personalized expense affordability: determining whether an individual can safely commit to an expense (e.g., purchasing a laptop, taking a professional course, paying a rental deposit, or funding travel) without risking insolvency, overdrafting, or violating their minimum required safety buffer over a strict 90-day forecast horizon.

The system synthesizes structured financial records, multi-currency exchange rates, unstructured employer/bank messages, OCR-extracted transaction images, and user preference profiles to generate mathematically verified, policy-compliant recommendations.

---

## 2. Core Problem Definition & Specification

### 2.1 The Core Question
When a user asks: **"Can I safely afford this expense?"**, the engine must evaluate:
1. **`amount_safe_to_pay`**: The maximum amount the user can safely pay today without optional spending changes while keeping their balance above `minimum_balance_to_keep` throughout the entire 90-day forecast.
2. **`affordability_status`**: One of four canonical statuses:
   - `affordable_now`: The full amount is safe to pay today and the user accepts `full_payment`.
   - `affordable_with_plan`: The full amount is safe via an installment plan, a partial payment schedule, or permitted spending adjustments.
   - `affordable_later`: The full amount will become safe on a later date (e.g., following salary credits) on or before `desired_completion_date`.
   - `not_affordable`: The request cannot be safely completed within the forecast period without violating safety buffers.
3. **`recommended_payment_method`**: The optimal chosen method (`full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`).
4. **`payment_plan`**: The exact chronological schedule formatted as `<YYYY-MM-DD>:<amount>|<YYYY-MM-DD>:<amount>` or `none`.
5. **`earliest_date_for_full_payment`**: The first calendar date on which paying the entire requested amount in full passes the 90-day safety check without spending modifications.
6. **`spending_changes_needed`**: Pipe-delimited list of required modifications to flexible subscriptions/expenses (`stop:<event_id>` or `reduce_to:<event_id>:<new_amount>`), or `none`.
7. **`decision_explanation`**: Clear, human-readable justification detailing safe headroom, minimum balance protection, and scheduled payments.

---

## 3. System Architecture & Dataset Schema

```
                           ┌───────────────────────────────┐
                           │       dataset/requests.csv    │
                           │  (250 evaluation requests)    │
                           └───────────────┬───────────────┘
                                           │
 ┌──────────────────────────┬──────────────┴─────────────┬──────────────────────────┐
 │                          │                            │                          │
 ▼                          ▼                            ▼                          ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│financial_profiles│ │ financial_events │ │   messages.csv   │ │    images.csv    │
│ • Home Currency  │ │ • Past Debits    │ │ • Salary Changes │ │ • OCR Receipts   │
│ • Min Balance    │ │ • Pending Debits │ │ • Rent Increases │ │ • Missing Amount │
│ • Current Cash   │ │ • Future Salary  │ │ • Arrears/Bonus  │ │   Extraction     │
│ • Allowed Methods│ │ • Outlier Filter │ │ • Disputed Debits│ └────────┬─────────┘
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘          │
         │                    │                    │                    ▼
         │                    │                    │           ┌──────────────────┐
         │                    │                    │           │  media/images/   │
         │                    │                    │           │ (16 image PNGs)  │
         │                    │                    │           └──────────────────┘
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       Cash-Flow Simulator & Intelligence Engine                 │
│  • Dated Multi-Currency Conversion Matrix (USD, EUR, IDR, INR, ZAR)             │
│  • Recurring Expense Streams Detection (Monthly & Interval Cycles)              │
│  • 90-Day Daily Balance Trajectory Simulation                                   │
│  • Multi-Tier Ranking & Tie-Breaking Optimization                               │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │           output.csv            │
                        │    (Consolidated 250 rows)      │
                        └─────────────────────────────────┘
```

### 3.1 Datasets Description

| File Name | Purpose & Primary Keys | Key Columns |
|---|---|---|
| `financial_profiles.csv` | User constraints & financial settings (`user_id`) | `home_currency`, `current_available_balance`, `minimum_balance_to_keep`, `payment_methods_user_will_consider`, `max_installment_months`, `expense_categories_user_is_willing_to_reduce`, `expense_categories_user_is_willing_to_stop` |
| `financial_events.csv` | Historical & future transaction ledger (`event_id`, `user_id`) | `amount`, `currency`, `event_date`, `settlement_date`, `status` (`settled`, `pending`, `scheduled`, `failed`, `cancelled`), `direction` (`credit`, `debit`), `category`, `flexibility`, `minimum_allowed_amount` |
| `requests.csv` | User purchase/expense inquiries (`request_id`, `user_id`) | `request_date`, `request_type`, `requested_amount`, `desired_completion_date`, `allows_partial_payment`, `request_text` |
| `sample_requests.csv` | 25 Verified reference sample requests with ground truth | Ground truth columns for calibration and verification |
| `request_payment_options.csv` | Financing and installment quotes (`payment_option_id`, `request_id`) | `number_of_payments`, `payment_amount`, `payment_frequency_days`, `first_payment_date`, `total_payable_amount` |
| `messages.csv` | Semi-structured email/SMS notifications (`message_id`, `user_id`) | `message_text`, `source_type` (`employer`, `bank`, `merchant`), `related_event_id` |
| `images.csv` | Document/receipt links (`image_id`, `related_event_id`) | `image_id`, `file_name` |
| `exchange_rates.csv` | Dated currency exchange table | `rate_date`, `from_currency`, `to_currency`, `rate` |

---

## 4. Multi-Modal Vision Extractions

When a financial event contains a missing (`NaN`) amount, its amount is resolved from the corresponding image in `dataset/media/images/<image_id>.png`:

| Image ID | Event ID | User ID | Extracted Amount | Native Currency |
|---|---|---|---|---|
| `image_01.png` | `event_253` | `user_03` | **4,365,000.00** | IDR |
| `image_02.png` | `event_1442` | `user_16` | **100,000.00** | INR |
| `image_03.png` | `event_1545` | `user_17` | **41,272.00** | INR |
| `image_04.png` | `event_1700` | `user_19` | **2,854.00** | INR |
| `image_05.png` | `event_1786` | `user_20` | **704.05** | INR |
| `image_06.png` | `event_3051` | `user_33` | **1,995.00** | INR |
| `image_07.png` | `event_3231` | `user_35` | **8,528.00** | INR |
| `image_08.png` | `event_4535` | `user_48` | **15,339.00** | INR |
| `image_09.png` | `event_5170` | `user_55` | **723.00** | INR |
| `image_10.png` | `event_6033` | `user_64` | **79,679.26** | INR |
| `image_11.png` | `event_6859` | `user_73` | **3,650.00** | INR |
| `image_12.png` | `event_7307` | `user_78` | **33.50** | USD |
| `image_13.png` | `event_7941` | `user_84` | **2,298.00** | INR |
| `image_14.png` | `event_9421` | `user_101` | **4,543.00** | INR |
| `image_15.png` | `event_9806` | `user_105` | **9,968.00** | INR |
| `image_16.png` | `event_10521` | `user_113` | **393.22** | INR |

---

## 5. Algorithmic Principles & Decision Logic

### 5.1 Currency Conversion
Any transaction in foreign currency is converted to the user's `home_currency` using the closest preceding rate in `exchange_rates.csv`:
$$\text{Amount}_{\text{home}} = \text{Amount}_{\text{foreign}} \times \text{Rate}(\text{foreign} \to \text{home}, \text{date})$$

### 5.2 Recurring Expense Streams
1. **Monthly Streams**: Categories with cadence $\ge 25$ days (e.g., rent, utilities, insurance, subscriptions) repeat on the same calendar day each month.
2. **Interval Streams**: High-frequency categories (e.g., groceries, transport, dining) repeat every $N$ days where $N = \text{mean}(\Delta\text{days})$.
3. **Outlier Dampening**: If the most recent transaction is an extreme bulk purchase ($> 2.5 \times \text{median}$), the recurring stream amount adopts the median.

### 5.3 90-Day Safety Simulation
For day $t \in [0, 90]$:
$$\text{Balance}(t) = \text{Balance}(t-1) + \text{Inflows}(t) - \text{Outflows}(t)$$
$$\text{Safety Constraint}: \quad \min_{t \in [0, 90]} \text{Balance}(t) \ge \text{minimum\_balance\_to\_keep}$$

### 5.4 Metric Definitions
- **Amount Safe to Pay**:
  $$\text{amount\_safe\_to\_pay} = \min\left(\text{requested\_amount}, \max\left(0, \min_{t \in [0, 90]} \text{Balance}(t) - \text{min\_balance}\right)\right)$$
- **Earliest Date for Full Payment**:
  The earliest date $D$ where paying `requested_amount` on $D$ maintains $\text{Balance}(t) \ge \text{min\_balance}$ for the remainder of the forecast cycle.

### 5.5 Plan Ranking Hierarchy (Tie-Breaking Rules)
When multiple plans are safe, candidate options are ordered by:
1. **Completion Deadline**: Must complete by `desired_completion_date`.
2. **Spending Changes**: Plans requiring **no spending changes** rank higher.
3. **Total Cost**: Lower `total_payable_amount` ranks higher.
4. **Start Date**: Earlier first payment date ranks higher.
5. **Payment Count**: Fewer total payments rank higher (e.g., 1 payment before 2 partial payments before 3 installments).
6. **Option ID**: Lowest numerical `payment_option_id` as deterministic tie-breaker.

---

## 6. Project Architecture & Directory Layout

```
hackerrank-orchestrate/
├── dataset/                                # Official source datasets
│   ├── financial_profiles.csv              # User profiles & risk thresholds
│   ├── financial_events.csv                # Ledger events (25,000+ rows)
│   ├── requests.csv                        # 250 evaluation requests
│   ├── sample_requests.csv                 # 25 reference ground-truth samples
│   ├── request_payment_options.csv         # Installment options
│   ├── messages.csv                        # User communications
│   ├── images.csv                          # Image mappings
│   ├── exchange_rates.csv                  # FX matrix
│   ├── output.csv                          # Submission output template
│   └── media/images/                       # 16 PNG multimodal vouchers
├── OUTPUT.csv/                             # Output deliverable artifacts
│   ├── 01_requests_predictions.csv         # Consolidated predictions (250 rows)
│   ├── 02_requests_predictions_detailed.csv# Expanded analysis
│   └── RIDA.csv                            # Submission formatted copy
├── code/                                   # Application code
│   ├── web_app.py                          # Flask interactive web application
│   ├── financial_engine.py                 # Core evaluation engine
│   ├── bank_connector.py                   # RBI Account Aggregator simulation
│   ├── account_database.py                 # User ledger management
│   ├── static/ & templates/                # Web UI dashboard assets
│   └── local_users.json                    # Saved user profiles
├── solve.py                                # Master end-to-end evaluation script
├── test_engine.py                          # Ground-truth verification suite
├── debug_samples.py                        # Diagnostic discrepancy analyzer
├── export_transcript.py                    # Session transcript exporter & sanitizer
├── upload_to_github_api.py                 # Automated GitHub Git Data API sync
├── chat_transcript.txt                     # Full session transcript (.txt)
├── chat_transcript                         # Clean submission transcript
└── KNOWLEDGE_BASE.md                       # This comprehensive documentation file
```

---

## 7. Web Application & Interactive Hub

A Flask-based financial dashboard is provided in [`code/web_app.py`](file:///c:/Users/Rida/Desktop/hackerrank-orchestrate-september26-main/hackerrank-orchestrate-september26-main/code/web_app.py), hosted locally at `http://localhost:5000`.

### Endpoints:
- `GET /`: Interactive web dashboard with 90-day trajectory charts, profile summary, and decision cards.
- `GET /api/requests`: Retrieves all 250 evaluated requests with payment plans and rationales.
- `GET /api/stats`: Distribution metrics across statuses and recommended methods.
- `POST /api/chat`: AI chat interface for querying individual user affordability in real-time.
- `POST /api/ocr_receipt`: Multi-modal receipt/invoice image parsing.
- `GET /connect/bank`: Interactive simulation of RBI Account Aggregator bank consent flow.

---

## 8. Summary of Results (250 Requests)

```
Distribution of Affordability Status:
  • affordable_with_plan : 78 (31.2%)
  • affordable_now       : 65 (26.0%)
  • not_affordable       : 57 (22.8%)
  • affordable_later     : 50 (20.0%)

Distribution of Recommended Payment Methods:
  • full_payment         : 71 (28.4%)
  • installments         : 60 (24.0%)
  • not_recommended      : 57 (22.8%)
  • wait                 : 50 (20.0%)
  • partial_payment      : 12 (4.8%)
```

---
*Generated for HackerRank Orchestrate — AI Financial Decision Engine*
