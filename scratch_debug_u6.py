import sys, os, pandas as pd
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
u6_traj = engine.simulate_cash_flow('user_06', '2026-01-03')
print("User 06 streams:")
for s in u6_traj['streams']:
    print(s)
