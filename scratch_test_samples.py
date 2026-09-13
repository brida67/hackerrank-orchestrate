import sys
import os
import pandas as pd
sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
samples = pd.read_csv('dataset/sample_requests.csv')

print(f"{'ReqID':10s} | {'Status_Match':12s} | {'Method_Match':12s} | {'Computed_Method':15s} | {'GT_Method':15s} | {'Computed_Status':18s} | {'GT_Status':18s}")
print("-" * 110)

status_matches = 0
method_matches = 0

for idx, r in samples.iterrows():
    pred = engine.evaluate_request(r)
    s_match = pred['affordability_status'] == r['affordability_status']
    m_match = pred['recommended_payment_method'] == r['recommended_payment_method']
    if s_match: status_matches += 1
    if m_match: method_matches += 1
    
    print(f"{r['request_id']:10s} | {str(s_match):12s} | {str(m_match):12s} | {pred['recommended_payment_method']:15s} | {r['recommended_payment_method']:15s} | {pred['affordability_status']:18s} | {r['affordability_status']:18s}")

print(f"\nStatus Match: {status_matches}/{len(samples)} ({status_matches/len(samples)*100:.1f}%)")
print(f"Method Match: {method_matches}/{len(samples)} ({method_matches/len(samples)*100:.1f}%)")
