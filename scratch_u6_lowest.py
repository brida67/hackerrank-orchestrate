import sys, os, pandas as pd
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
sim_res = engine.simulate_cash_flow('user_06', '2026-01-03')
dates = sim_res['dates']
bals = sim_res['balances']

df = pd.DataFrame({'date': dates, 'balance': bals})
print("Top 10 lowest balance days for user 06:")
print(df.sort_values('balance').head(10))

# Print what happened on or before the lowest day
min_date = df.sort_values('balance').iloc[0]['date']
print(f"\nEvents log on lowest day ({min_date}):", sim_res['events_log'][datetime.strptime(min_date, '%Y-%m-%d').date()])
