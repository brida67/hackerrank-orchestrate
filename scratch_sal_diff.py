import pandas as pd
from datetime import datetime, timedelta

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
events = pd.read_csv('dataset/financial_events.csv')

for idx in range(10):
    r = samples.iloc[idx]
    u_id = r['user_id']
    req_date = r['request_date']
    req_dt = datetime.strptime(req_date, '%Y-%m-%d').date()
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    
    # Let's find the next salary date after req_date
    u_ev = events[events['user_id'] == u_id].copy()
    u_ev['s_dt'] = pd.to_datetime(u_ev['settlement_date']).dt.date
    future_sal = u_ev[(u_ev['category'] == 'salary') & (u_ev['s_dt'] >= req_dt)]
    
    next_sal_date = future_sal['s_dt'].min() if len(future_sal) > 0 else req_dt + timedelta(days=90)
    
    # Pending debits
    pending = u_ev[(u_ev['status'] == 'pending') & (u_ev['direction'] == 'debit')]
    pending_sum = pending['amount'].sum() if len(pending) > 0 else 0
    
    # Debits between req_date and next_sal_date in history:
    # Let's see how much was spent in the same period last month
    days_to_sal = (next_sal_date - req_dt).days if next_sal_date else 30
    
    headroom = prof['current_available_balance'] - prof['minimum_balance_to_keep']
    safe = r['amount_safe_to_pay']
    diff = headroom - safe
    
    print(f"[{r['request_id']}] {u_id} | ReqDate: {req_date} | NextSal: {next_sal_date} ({days_to_sal}d) | Headroom: {headroom:.2f} | Safe: {safe:.2f} | Diff: {diff:.2f} | Pending: {pending_sum:.2f}")
