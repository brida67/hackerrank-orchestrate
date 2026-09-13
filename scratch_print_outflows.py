import sys, os, pandas as pd
from datetime import datetime
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
sim_res = engine.simulate_cash_flow('user_06', '2026-01-03')

print("Daily outflows between 2026-01-03 and 2026-01-15:")
tot = 0
for d in pd.date_range('2026-01-03', '2026-01-15'):
    dt = d.date()
    log = sim_res['events_log'][dt]
    if len(log) > 0:
        for item in log:
            print(f"  {dt} | {item['type']:15s} | {item['desc']:30s} | {item['amount']}")
            tot += item['amount']

print("Total outflows in that period:", tot)
