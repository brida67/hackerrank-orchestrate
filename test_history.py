import pandas as pd
from datetime import datetime, timedelta

events = pd.read_csv('dataset/financial_events.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
samples = pd.read_csv('dataset/sample_requests.csv')

for u_id, r_date_str in [('user_01', '2024-03-03'), ('user_02', '2025-08-05'), ('user_03', '2019-09-03')]:
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    req_date = datetime.strptime(r_date_str, '%Y-%m-%d').date()
    current_bal = float(prof['current_available_balance'])
    min_bal = float(prof['minimum_balance_to_keep'])
    
    u_ev = events[events['user_id'] == u_id].copy()
    u_ev['s_dt'] = pd.to_datetime(u_ev['settlement_date']).dt.date
    past = u_ev[(u_ev['s_dt'] <= req_date) & (u_ev['status'] == 'settled')].sort_values('s_dt')
    
    # Category spending breakdown
    debits = past[past['direction'] == 'debit']
    cat_spending = debits.groupby('category')['amount'].sum().sort_values(ascending=False).to_dict()
    
    # Monthly spending and income
    past['month'] = past['s_dt'].apply(lambda d: d.strftime('%Y-%m'))
    monthly_in = past[past['direction'] == 'credit'].groupby('month')['amount'].sum().to_dict()
    monthly_out = past[past['direction'] == 'debit'].groupby('month')['amount'].sum().to_dict()
    
    print(f"\n=== {u_id} (Date: {req_date}, Bal: {current_bal}, Min: {min_bal}) ===")
    print("Past Settled Count:", len(past))
    print("Category Breakdown:", {k: round(v, 2) for k, v in list(cat_spending.items())[:6]})
    print("Monthly Inflows:", {k: round(v, 2) for k, v in monthly_in.items()})
    print("Monthly Outflows:", {k: round(v, 2) for k, v in monthly_out.items()})
