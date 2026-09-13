import pandas as pd, sys
sys.path.insert(0, 'code')
from financial_engine import FinancialDecisionEngine

eng = FinancialDecisionEngine('dataset')
samples = pd.read_csv('dataset/sample_requests.csv')
correct = 0
for _, r in samples.iterrows():
    pred = eng.evaluate_request(r)
    is_safe = pred['affordability_status'] == r['affordability_status']
    is_amt = abs(pred['amount_safe_to_pay'] - r['amount_safe_to_pay']) < 1.0
    if is_safe and is_amt:
        correct += 1
    else:
        req_id = r['request_id']
        p_st = pred['affordability_status']
        g_st = r['affordability_status']
        p_am = pred['amount_safe_to_pay']
        g_am = r['amount_safe_to_pay']
        print(f"{req_id}: Pred Status={p_st}, GT Status={g_st} | Pred Amt={p_am}, GT Amt={g_am}")
print(f"Total accurate: {correct} / {len(samples)} ({correct/len(samples)*100:.1f}%)")
