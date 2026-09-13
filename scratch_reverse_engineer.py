import pandas as pd
from datetime import datetime

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
events = pd.read_csv('dataset/financial_events.csv')
messages = pd.read_csv('dataset/messages.csv')

# Let's inspect each sample request:
# req_date, current_available_balance, minimum_balance_to_keep, requested_amount, amount_safe_to_pay
for idx, r in samples.iterrows():
    u_id = r['user_id']
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    curr_bal = prof['current_available_balance']
    min_bal = prof['minimum_balance_to_keep']
    req_amt = r['requested_amount']
    safe_amt = r['amount_safe_to_pay']
    headroom = curr_bal - min_bal
    diff = headroom - safe_amt
    
    # Check pending debits
    u_events = events[events['user_id'] == u_id]
    pending = u_events[(u_events['status'] == 'pending') & (u_events['direction'] == 'debit')]
    pending_sum = pending['amount'].sum() if len(pending) > 0 else 0
    
    print(f"[{r['request_id']}] User: {u_id} | Date: {r['request_date']} | Curr: {curr_bal:.2f} | Min: {min_bal:.2f} | Headroom: {headroom:.2f} | Safe: {safe_amt:.2f} | Diff: {diff:.2f} | Pending: {pending_sum:.2f}")
