import os
import sys
import time
import pandas as pd
from datetime import datetime

from code.financial_engine import FinancialDecisionEngine


def main():
    start_time = time.time()
    print("=" * 65)
    print("  CLARIFIED AGENTIC RUN: GENERATING RIDA.csv")
    print("=" * 65)
    
    data_dir = 'dataset'
    requests_path = os.path.join(data_dir, 'requests.csv')
    requests_df = pd.read_csv(requests_path)
    total_reqs = len(requests_df)
    print(f"Loaded {total_reqs} requests from {requests_path}")
    
    engine = FinancialDecisionEngine(data_dir=data_dir)
    print("Initialized Financial Decision Engine with full multimodal evidence.")
    
    results = []
    
    for idx, row in requests_df.iterrows():
        pred = engine.evaluate_request(row)
        results.append(pred)
        
        if (idx + 1) % 50 == 0 or (idx + 1) == total_reqs:
            print(f"  [Agentic Evaluation] Evaluated {idx + 1:3d}/{total_reqs} requests...")

    output_df = pd.DataFrame(results)
    
    # Required columns in exact required order
    req_cols = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]
    output_df = output_df[req_cols]
    
    # Write RIDA.csv in root and dataset/
    rida_csv_path = 'RIDA.csv'
    dataset_rida_csv_path = os.path.join('dataset', 'RIDA.csv')
    output_csv_path = 'output.csv'
    
    output_df.to_csv(rida_csv_path, index=False)
    output_df.to_csv(dataset_rida_csv_path, index=False)
    output_df.to_csv(output_csv_path, index=False)
    
    elapsed = time.time() - start_time
    print(f"\n[OK] Successfully generated {rida_csv_path} and {dataset_rida_csv_path} in {elapsed:.2f}s!")
    
    # Validation Sanity Checks
    print("\n" + "=" * 65)
    print("  VERIFICATION & VALIDATION AUDIT")
    print("=" * 65)
    
    assert len(output_df) == total_reqs, f"Row count mismatch: expected {total_reqs}, got {len(output_df)}"
    assert list(output_df.columns) == req_cols, f"Column mismatch: {list(output_df.columns)}"
    print(f"  [OK] Row Count: {len(output_df)} / {total_reqs} (100% complete)")
    print(f"  [OK] Schema: 8/8 columns present in exact specification order")
    
    # Check bounds
    merged = pd.merge(output_df, requests_df, on='request_id')
    valid_bounds = ((merged['amount_safe_to_pay'] >= 0) & (merged['amount_safe_to_pay'] <= merged['requested_amount'] + 1e-4)).all()
    print(f"  [OK] Safe Amount Bounds (0 <= amount_safe_to_pay <= requested_amount): {valid_bounds}")
    
    # Check nulls in critical columns
    no_null_id = output_df['request_id'].notna().all()
    no_null_status = output_df['affordability_status'].notna().all()
    no_null_method = output_df['recommended_payment_method'].notna().all()
    no_null_plan = output_df['payment_plan'].notna().all()
    no_null_changes = output_df['spending_changes_needed'].notna().all()
    no_null_exp = output_df['decision_explanation'].notna().all()
    print(f"  [OK] No Null Fields: id={no_null_id}, status={no_null_status}, method={no_null_method}, plan={no_null_plan}, changes={no_null_changes}, exp={no_null_exp}")
    
    print("\nAffordability Status Distribution:")
    for stat, cnt in output_df['affordability_status'].value_counts().items():
        print(f"  - {stat:25s}: {cnt:3d} ({cnt/total_reqs*100:5.1f}%)")
        
    print("\nRecommended Payment Method Distribution:")
    for meth, cnt in output_df['recommended_payment_method'].value_counts().items():
        print(f"  - {meth:25s}: {cnt:3d} ({cnt/total_reqs*100:5.1f}%)")
        
    print("\nSample Clarified Agentic Decisions:")
    for i in [0, 1, 4, 10, 25, 50, 100, 200]:
        row = output_df.iloc[i]
        print(f"\n  [{row['request_id']}] Status: {row['affordability_status']} | Method: {row['recommended_payment_method']}")
        print(f"   Safe: {row['amount_safe_to_pay']} | Plan: {row['payment_plan']} | Earliest: {row['earliest_date_for_full_payment']}")
        print(f"   Spending Changes: {row['spending_changes_needed']}")
        print(f"   Clarified Explanation: \"{row['decision_explanation']}\"")

if __name__ == '__main__':
    main()
