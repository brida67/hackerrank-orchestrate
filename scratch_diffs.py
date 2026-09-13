import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')

for u_id, diff in [('user_15', 487), ('user_18', 624), ('user_21', 568), ('user_22', 157), ('user_08', 452)]:
    u_ev = events[events['user_id'] == u_id]
    print(f"\n=================== {u_id} (Diff = {diff}) ===================")
    # Check fixed items (rent, utilities, loans, subscriptions, insurance)
    fixed = u_ev[u_ev['flexibility'] == 'fixed']
    for desc, grp in fixed.groupby('description'):
        print(f"  {desc:30s} | {grp['category'].iloc[0]:15s} | Amount: {grp['amount'].iloc[-1]} | Day of month: {grp['settlement_date'].iloc[-1]}")
