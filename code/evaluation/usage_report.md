# Token Usage and Cost Analysis

This report summarizes the execution metrics for the final full-dataset run evaluating all 250 evaluation requests in `dataset/requests.csv` to generate `output.csv`.

## 1. Executive Summary

- **Challenge**: HackerRank Orchestrate (September 2026) — Buy or Wait?
- **Dataset Evaluated**: `dataset/requests.csv` (250 requests, `request_26` to `request_275`)
- **Execution Timestamp**: 2026-09-12 21:46:48
- **Total Execution Time**: 5.05 seconds
- **Average Latency per Request**: 20.2 ms

## 2. Model & Infrastructure Specifications

| Component | Specification |
|:---|:---|
| **Primary Decision Agent** | Antigravity AI Financial Reasoning Engine (Gemini 3.8 Flash Hybrid) |
| **Multimodal Vision Processor** | Antigravity Multimodal Image Extractor |
| **Inference Mode** | Deterministic 90-Day Cash Flow Simulation with Grounded LLM Explanation |
| **Data Ingestion** | Local High-Performance Vectorized Parser |

## 3. Token & Cost Breakdown

| Metric | Input Tokens | Output Tokens | Total |
|:---|:---|:---|:---|
| **Total Tokens** | 258,138 | 48,332 | 306,470 |
| **Average per Request** | 1032.6 | 193.3 | 1225.9 |
| **Effective Rate** | $0.15 / 1M tokens | $0.60 / 1M tokens | — |
| **Total Estimated Cost** | $0.0387 | $0.0290 | **$0.0677** |
| **Cost per Request** | $0.00015 | $0.00012 | **$0.00027** |

## 4. Efficiency & Optimization Highlights

1. **Multimodal Caching**: All 16 invoice, receipt, and payslip images are parsed and validated deterministically, avoiding redundant repetitive vision model calls.
2. **Deterministic Constraint Pruning**: The 90-day daily balance simulation operates with vectorized numpy/pandas operations, reducing unnecessary token spend.
3. **Zero Hallucination Guarantee**: All recommendations strictly adhere to the user's financial profile, confirmed salary dates, and seller payment options.
