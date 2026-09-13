import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')

def inspect_user_recurring(user_id, req_date):
    u_events = events[events['user_id'] == user_id].copy()
    print(f"\n================ USER: {user_id} (Req Date: {req_date}) ================")
    # Look at settled debits in the last 2 months prior to req_date
    u_events['event_date'] = pd.to_datetime(u_events['event_date'])
    u_events['settlement_date'] = pd.to_datetime(u_events['settlement_date'])
    rd = pd.to_datetime(req_date)
    
    past_60d = u_events[(u_events['settlement_date'] <= rd) & (u_events['settlement_date'] >= rd - pd.Timedelta(days=60))]
    print("Recent settled debits in 60d:")
    for cat, grp in past_60d[past_60d['direction'] == 'debit'].groupby('category'):
        print(f"  Category: {cat:20s} | Rows: {len(grp):2d} | Total: {grp['amount'].sum():10.2f} | Unique Descs: {list(grp['description'].unique())[:2]}")

inspect_user_recurring('user_06', '2026-01-03')
inspect_user_recurring('user_11', '2025-05-03')
inspect_user_recurring('user_21', '2026-04-03')
inspect_user_recurring('user_01', '2024-03-03')
