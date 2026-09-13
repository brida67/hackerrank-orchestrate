import sys, os, pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
samples = pd.read_csv('dataset/sample_requests.csv')

# Let's inspect each sample request with our exact logic:
correct_status = 0
correct_method = 0
correct_earliest = 0
correct_changes = 0

for idx, r in samples.iterrows():
    # Ground truth values
    gt_stat = r['affordability_status']
    gt_meth = r['recommended_payment_method']
    gt_earl = str(r['earliest_date_for_full_payment']) if pd.notna(r['earliest_date_for_full_payment']) else ''
    gt_chg = r['spending_changes_needed']
    
    # Evaluate
    pred = engine.evaluate_request(r)
    
    s_m = pred['affordability_status'] == gt_stat
    m_m = pred['recommended_payment_method'] == gt_meth
    e_m = pred['earliest_date_for_full_payment'] == gt_earl
    c_m = pred['spending_changes_needed'] == gt_chg
    
    if s_m: correct_status += 1
    if m_m: correct_method += 1
    if e_m: correct_earliest += 1
    if c_m: correct_changes += 1
    
    if not (s_m and m_m):
        print(f"Mismatch [{r['request_id']}]: Pred ({pred['affordability_status']}, {pred['recommended_payment_method']}, earl={pred['earliest_date_for_full_payment']}, chg={pred['spending_changes_needed']}) vs GT ({gt_stat}, {gt_meth}, earl={gt_earl}, chg={gt_chg})")

print(f"\nResults on Sample Requests (N={len(samples)}):")
print(f"Status:   {correct_status}/{len(samples)} ({correct_status/len(samples)*100:.1f}%)")
print(f"Method:   {correct_method}/{len(samples)} ({method_matches if 'method_matches' in locals() else correct_method}/{len(samples)}) ({correct_method/len(samples)*100:.1f}%)")
print(f"Earliest: {correct_earliest}/{len(samples)} ({correct_earliest/len(samples)*100:.1f}%)")
print(f"Changes:  {correct_changes}/{len(samples)} ({correct_changes/len(samples)*100:.1f}%)")
