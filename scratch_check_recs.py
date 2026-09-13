import os
import sys
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath('code'))
from financial_engine import FinancialDecisionEngine

engine = FinancialDecisionEngine(data_dir='dataset')
samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
options = pd.read_csv('dataset/request_payment_options.csv')

# Let's see all sample requests recommendations
for idx, r in samples.iterrows():
    req_id = r['request_id']
    u_id = r['user_id']
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    considered = str(prof['payment_methods_user_will_consider']).split('|')
    opt_for_req = options[options['request_id'] == req_id]
    
    print(f"[{req_id}] User: {u_id} | Status: {r['affordability_status']:20s} | Method: {r['recommended_payment_method']:15s} | Plan: {r['payment_plan'][:30]} | Earliest: {r['earliest_date_for_full_payment']} | Changes: {r['spending_changes_needed']}")
