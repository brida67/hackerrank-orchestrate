import pandas as pd

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')

merged = pd.merge(samples, profiles, on='user_id')
for idx, r in merged.iterrows():
    curr_bal = r['current_available_balance']
    min_bal = r['minimum_balance_to_keep']
    req_amt = r['requested_amount']
    safe_amt = r['amount_safe_to_pay']
    headroom = curr_bal - min_bal
    diff = headroom - safe_amt
    print(f"{r['request_id']} | Curr: {curr_bal:12.2f} | Min: {min_bal:10.2f} | Headroom: {headroom:12.2f} | ReqAmt: {req_amt:12.2f} | SafeAmt: {safe_amt:12.2f} | Diff: {diff:10.2f}")
