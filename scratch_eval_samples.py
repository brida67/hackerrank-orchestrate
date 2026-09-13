import sys
import os
import pandas as pd
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
samples = pd.read_csv('dataset/sample_requests.csv')

print(f"Testing engine on {len(samples)} sample requests:")

for idx in range(10):
    r = samples.iloc[idx]
    traj = engine.simulate_cash_flow(r['user_id'], r['request_date'])
    min_bal = traj['min_balance']
    lowest_b = min(traj['balances'])
    safe_today = min(float(r['requested_amount']), max(0.0, lowest_b - min_bal))
    
    print(f"[{r['request_id']}] User: {r['user_id']} | ReqAmt: {r['requested_amount']} | GT_Safe: {r['amount_safe_to_pay']} | Computed_Safe: {safe_today:.2f} | LowestB: {lowest_b:.2f} | MinB: {min_bal:.2f}")
