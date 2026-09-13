import sys, os, pandas as pd
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
samples = pd.read_csv('dataset/sample_requests.csv')
r6 = samples[samples['request_id'] == 'request_06'].iloc[0]
res = engine.evaluate_request(r6)
print("Request 06 evaluated:", res)
print("Ground truth:", r6['affordability_status'], r6['recommended_payment_method'], r6['payment_plan'], r6['spending_changes_needed'])
